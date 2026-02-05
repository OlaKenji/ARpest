"""
High-performance 2D visualization based on PyQtGraph.

This ports the previous Matplotlib widget to the same GPU-accelerated
infrastructure used by Figure3D so panning the cursor and dragging cuts
remains responsive even for large datasets.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from matplotlib import cm
from PyQt5.QtCore import QObject, QEvent, Qt, QPointF, QRectF
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from ..models import Dataset, FileStack
from ..utils.cursor.cursor_manager import CursorManager, CursorState
from ..utils.cursor.cursor_helpers import DragMode, DragState
from ..utils.cursor.pg_line_cursor import PGLineCursor
from .roi import RoiOverlay

# Configure PyQtGraph defaults for the whole module
pg.setConfigOptions(
    imageAxisOrder="row-major",
    antialias=True,
    background="w",
    foreground="k",
)


class _GraphicsViewEventFilter(QObject):
    """Intercept mouse events on the GraphicsLayoutWidget."""

    def __init__(self, figure: "Figure2D") -> None:
        super().__init__(figure)
        self._figure = figure

    def eventFilter(self, obj, event):  # type: ignore[override]
        if self._figure._roi_event_passthrough(event):
            return False
        etype = event.type()
        if etype == QEvent.MouseMove:
            self._figure._handle_mouse_move_event(event)
        elif etype == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._figure._handle_mouse_press_event(event)
            return True
        elif etype == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            self._figure._handle_mouse_release_event(event)
            return True
        return False

class Figure2D(QWidget):
    """2D visualization widget using PyQtGraph."""

    def __init__(
        self,
        file_stack: FileStack,
        parent: Optional[QWidget] = None,
        colormap: str = "RdYlBu_r",
        integration_radius: int = 0,
    ) -> None:
        super().__init__(parent)
        self.file_stack = file_stack
        self.dataset = file_stack.current_state
        self.colormap = colormap
        self.integration_radius = max(0, int(integration_radius))

        self.intensity, self.x_axis, self.y_axis = self.dataset.get_slice_2d()

        self.cursor_mgr = CursorManager(self.x_axis.values, self.y_axis.values)
        self.drag_state = DragState()

        self._lut = self._create_lut(self.colormap)
        self._color_levels: Optional[Tuple[float, float]] = None
        self._image_extent: Tuple[Tuple[float, float], Tuple[float, float]] = (
            (float(self.x_axis.values.min()), float(self.x_axis.values.max())),
            (float(self.y_axis.values.min()), float(self.y_axis.values.max())),
        )
        self._roi: Optional[RoiOverlay] = None

        self.view = pg.GraphicsLayoutWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self._setup_plots()
        self._plot_band_and_curves()
        self._init_roi()

        self.cursor_mgr.on_cursor_change(self._on_cursor_changed)
        self.cursor_mgr.on_cut_change(self._on_cut_changed)

        self._event_filter = _GraphicsViewEventFilter(self)
        self.view.viewport().installEventFilter(self._event_filter)
        self.view.viewport().setMouseTracking(True)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _setup_plots(self) -> None:
        ds = self.dataset

        self.ax_band = self._add_image_plot(
            0,
            0,
            title=f"{ds.filename}",
            x_label=f"{self.x_axis.name} ({self.x_axis.unit})",
            y_label=f"{self.y_axis.name} ({self.y_axis.unit})",
        )

        self.ax_edc = self.view.addPlot(row=0, col=1)
        self.ax_edc.showGrid(x=True, y=True, alpha=0.3)
        self.ax_edc.setLabel("bottom", "Intensity")
        self.ax_edc.setLabel("left", f"{self.y_axis.name} ({self.y_axis.unit})")
        self.ax_edc.setMouseEnabled(x=False, y=False)
        self.ax_edc.hideButtons()

        self.ax_mdc = self.view.addPlot(row=1, col=0)
        self.ax_mdc.showGrid(x=True, y=True, alpha=0.3)
        self.ax_mdc.setLabel("bottom", f"{self.x_axis.name} ({self.x_axis.unit})")
        self.ax_mdc.setLabel("left", "Intensity")
        self.ax_mdc.setMouseEnabled(x=False, y=False)
        self.ax_mdc.hideButtons()

        # Empty spacer bottom-right to replicate original layout ratios
        self.view.addPlot(row=1, col=1).hide()

        ci = self.view.ci
        ci.layout.setColumnStretchFactor(0, 3)
        ci.layout.setColumnStretchFactor(1, 1)
        ci.layout.setRowStretchFactor(0, 3)
        ci.layout.setRowStretchFactor(1, 1)

        self._axes: Dict[str, pg.PlotItem] = {
            "band": self.ax_band,
            "edc": self.ax_edc,
            "mdc": self.ax_mdc,
        }

    def _add_image_plot(self, row: int, col: int, *, title: str, x_label: str, y_label: str):
        plot = self.view.addPlot(row=row, col=col)
        plot.setTitle(title)
        plot.setLabel("bottom", x_label)
        plot.setLabel("left", y_label)
        plot.setMouseEnabled(x=False, y=False)
        plot.hideButtons()
        self._set_viewbox_padding(plot.getViewBox(), 0.0)
        return plot

    def _set_viewbox_padding(self, viewbox, padding: float) -> None:
        if viewbox is None:
            return
        if hasattr(viewbox, "setDefaultPadding"):
            viewbox.setDefaultPadding(padding)
        elif hasattr(viewbox, "setPadding"):
            viewbox.setPadding(padding)

    def _plot_band_and_curves(self) -> None:
        x_extent, y_extent = self._image_extent

        self.im_band = pg.ImageItem()
        self.ax_band.addItem(self.im_band)
        self._set_image_data(self.intensity)
        self.ax_band.setRange(xRange=x_extent, yRange=y_extent, padding=0)

        cut = self.cursor_mgr.cut
        edc = self._compute_edc(cut)
        mdc = self._compute_mdc(cut)

        self._current_edc_curve = np.asarray(edc, dtype=float)
        self._current_mdc_curve = np.asarray(mdc, dtype=float)

        self.line_edc = self.ax_edc.plot(edc, self.y_axis.values, pen=pg.mkPen("k", width=1.5), name="EDC")
        self.line_mdc = self.ax_mdc.plot(self.x_axis.values, mdc, pen=pg.mkPen("k", width=1.5), name="MDC")

        self._update_edc_axis_limits(edc)
        self._update_mdc_axis_limits(mdc)

        cursor = self.cursor_mgr.cursor
        self.cut_vertical_line = PGLineCursor(
            self.ax_band,
            orientation="vertical",
            locked_value=cut.x_value,
            show_cursor=False,
            show_band=True,
        )
        self.cut_horizontal_line = PGLineCursor(
            self.ax_band,
            orientation="horizontal",
            locked_value=cut.y_value,
            show_cursor=False,
            show_band=True,
        )
        self.cursor_vertical_line = PGLineCursor(
            self.ax_band,
            orientation="vertical",
            locked_value=cursor.x_value,
            cursor_value=cursor.x_value,
            show_locked=False,
        )
        self.cursor_horizontal_line = PGLineCursor(
            self.ax_band,
            orientation="horizontal",
            locked_value=cursor.y_value,
            cursor_value=cursor.y_value,
            show_locked=False,
        )

        self._update_integration_overlays()
        self._overlay_scatter = None
        self._overlay_scatter_items: list[pg.ScatterPlotItem] = []

    # ------------------------------------------------------------------
    # Overlay helpers
    # ------------------------------------------------------------------
    def set_overlay_points(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        *,
        color: str = "#ff8800",
        size: int = 6,
        symbol: str = "o",
    ) -> None:
        if self._overlay_scatter is None:
            self._overlay_scatter = pg.ScatterPlotItem(
                pen=pg.mkPen(color),
                brush=pg.mkBrush(color),
                size=size,
                symbol=symbol,
            )
            self.ax_band.addItem(self._overlay_scatter)
        else:
            self._overlay_scatter.setPen(pg.mkPen(color))
            self._overlay_scatter.setBrush(pg.mkBrush(color))
            self._overlay_scatter.setSize(size)
            self._overlay_scatter.setSymbol(symbol)
        self._overlay_scatter.setData(np.asarray(x_values, dtype=float), np.asarray(y_values, dtype=float))

    def clear_overlay_points(self) -> None:
        if self._overlay_scatter is not None:
            self.ax_band.removeItem(self._overlay_scatter)
            self._overlay_scatter = None
        if self._overlay_scatter_items:
            for item in self._overlay_scatter_items:
                self.ax_band.removeItem(item)
            self._overlay_scatter_items = []

    def set_overlay_series(self, series: list[dict]) -> None:
        self.clear_overlay_points()
        for entry in series:
            x_vals = np.asarray(entry.get("x_values", []), dtype=float)
            y_vals = np.asarray(entry.get("y_values", []), dtype=float)
            if x_vals.size == 0 or y_vals.size == 0:
                continue
            color = entry.get("color", "#ff8800")
            size = int(entry.get("size", 6))
            symbol = entry.get("symbol", "o")
            scatter = pg.ScatterPlotItem(
                pen=pg.mkPen(color),
                brush=pg.mkBrush(color),
                size=size,
                symbol=symbol,
            )
            scatter.setData(x_vals, y_vals)
            self.ax_band.addItem(scatter)
            self._overlay_scatter_items.append(scatter)

    # ------------------------------------------------------------------
    # ROI helpers
    # ------------------------------------------------------------------
    def _init_roi(self) -> None:
        self._roi = RoiOverlay(self.x_axis.values, self.y_axis.values)
        self._roi.attach(self.ax_band)
        self._roi.add_listener(self._on_roi_changed)

    def _on_roi_changed(self) -> None:
        self._update_cut_visuals(self.cursor_mgr.cut)

    def add_roi_listener(self, callback: Callable[[], None]) -> None:
        if self._roi is not None:
            self._roi.add_listener(callback)

    def _roi_event_passthrough(self, event) -> bool:
        if self._roi is None:
            return False
        etype = event.type()
        if etype not in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            return False
        scene_pos = self.view.mapToScene(event.pos())
        return self._roi.should_capture_event(scene_pos, event)

    def set_roi_enabled(self, enabled: bool) -> None:
        if self._roi is None:
            return
        self._roi.set_enabled(enabled)
        self._update_cut_visuals(self.cursor_mgr.cut)

    def is_roi_enabled(self) -> bool:
        return self._roi.is_enabled() if self._roi is not None else False

    def reset_roi(self) -> None:
        if self._roi is not None:
            self._roi.reset()

    def clear_roi(self) -> None:
        if self._roi is not None:
            self._roi.clear()

    def get_roi_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        return self._roi.get_bounds() if self._roi is not None else None

    def set_roi_bounds(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        *,
        enabled: bool = True,
    ) -> None:
        if self._roi is None:
            return
        self._roi.set_bounds(x_min, x_max, y_min, y_max, enabled=enabled)

    def get_roi_axis_labels(self) -> Tuple[str, str]:
        def label(axis) -> str:
            return f"{axis.name} ({axis.unit})" if axis.unit else axis.name

        return (
            label(self.x_axis),
            label(self.y_axis),
        )

    def _roi_masks(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        return self._roi.axis_masks() if self._roi is not None else None

    def get_current_edc_curves(self) -> dict[str, np.ndarray]:
        """Return the currently displayed MDC curve keyed by its axis."""
        curve = getattr(self, "_current_mdc_curve", None)
        if curve is None or curve.size == 0:
            return {}
        return {"x": np.asarray(curve, dtype=float).copy()}        

    def get_current_mdc_curves(self) -> dict[str, np.ndarray]:
        """Return the currently displayed EDC curve keyed by its axis."""
        curve = getattr(self, "_current_edc_curve", None)
        if curve is None or curve.size == 0:
            return {}
        return {"y": np.asarray(curve, dtype=float).copy()}

    # ------------------------------------------------------------------
    # Mouse handling & callbacks
    # ------------------------------------------------------------------
    def _handle_mouse_move_event(self, event) -> None:
        scene_pos = self.view.mapToScene(event.pos())
        axis_key, point = self._scene_pos_to_axis(scene_pos)
        if axis_key != "band" or point is None:
            return
        is_dragging = bool(event.buttons() & Qt.LeftButton)
        self._on_mouse_move(point.x(), point.y(), is_dragging)

    def _handle_mouse_press_event(self, event) -> None:
        scene_pos = self.view.mapToScene(event.pos())
        axis_key, point = self._scene_pos_to_axis(scene_pos)
        if axis_key != "band" or point is None:
            return
        self._on_mouse_press(point.x(), point.y())

    def _handle_mouse_release_event(self, event) -> None:
        self._on_mouse_release()

    def _scene_pos_to_axis(self, scene_pos) -> Tuple[Optional[str], Optional[QPointF]]:
        for key, plot in self._axes.items():
            if plot.sceneBoundingRect().contains(scene_pos):
                view_point = plot.getViewBox().mapSceneToView(scene_pos)
                return key, view_point
        return None, None

    def _on_mouse_move(self, x: float, y: float, is_dragging: bool) -> None:
        self.cursor_vertical_line.set_cursor(x)
        self.cursor_horizontal_line.set_cursor(y)
        if is_dragging and self.drag_state.is_mode(DragMode.FERMI):
            self.cursor_mgr.update_cursor(x, y)
        else:
            self.cursor_mgr.update_cursor(x, y)

    def _on_mouse_press(self, x: float, y: float) -> None:
        self.drag_state.start(DragMode.FERMI)
        self.cursor_mgr.start_drag()
        self.cursor_mgr.set_cut(x, y)

    def _on_mouse_release(self) -> None:
        self.cursor_mgr.end_drag()
        self.drag_state.stop()

    def _on_cursor_changed(self, cursor: CursorState) -> None:
        self.cursor_vertical_line.set_cursor(cursor.x_value)
        self.cursor_horizontal_line.set_cursor(cursor.y_value)

    def _on_cut_changed(self, cut: CursorState) -> None:
        self._update_cut_visuals(cut)

    # ------------------------------------------------------------------
    # Data updates
    # ------------------------------------------------------------------
    def _update_cut_visuals(self, cut: CursorState) -> None:
        edc = self._compute_edc(cut)
        mdc = self._compute_mdc(cut)
        self._current_edc_curve = np.asarray(edc, dtype=float)
        self._current_mdc_curve = np.asarray(mdc, dtype=float)
        self.line_edc.setData(edc, self.y_axis.values)
        self.line_mdc.setData(self.x_axis.values, mdc)
        self._update_edc_axis_limits(edc)
        self._update_mdc_axis_limits(mdc)

        self.cut_vertical_line.set_locked(cut.x_value)
        self.cut_horizontal_line.set_locked(cut.y_value)
        self._update_integration_overlays()

    def _compute_edc(self, cut: CursorState) -> np.ndarray:
        start, end = self._index_range(cut.x_idx, self.intensity.shape[1])
        edc_slice = self.intensity[:, start : end + 1]
        masks = self._roi_masks()
        if masks is not None:
            x_mask, y_mask = masks
            x_local = x_mask[start : end + 1]
            if not np.any(x_local) or not np.any(y_mask):
                return np.full(edc_slice.shape[0], np.nan)
            edc_slice = edc_slice.copy()
            if not np.all(y_mask):
                edc_slice[~y_mask, :] = np.nan
            if not np.all(x_local):
                edc_slice[:, ~x_local] = np.nan
        return np.nanmean(edc_slice, axis=1)

    def _compute_mdc(self, cut: CursorState) -> np.ndarray:
        start, end = self._index_range(cut.y_idx, self.intensity.shape[0])
        mdc_slice = self.intensity[start : end + 1, :]
        masks = self._roi_masks()
        if masks is not None:
            x_mask, y_mask = masks
            y_local = y_mask[start : end + 1]
            if not np.any(x_mask) or not np.any(y_local):
                return np.full(mdc_slice.shape[1], np.nan)
            mdc_slice = mdc_slice.copy()
            if not np.all(y_local):
                mdc_slice[~y_local, :] = np.nan
            if not np.all(x_mask):
                mdc_slice[:, ~x_mask] = np.nan
        return np.nanmean(mdc_slice, axis=0)

    def _update_integration_overlays(self) -> None:
        cut = self.cursor_mgr.cut
        x_low, x_high = self._axis_value_range(self.x_axis.values, cut.x_idx)
        y_low, y_high = self._axis_value_range(self.y_axis.values, cut.y_idx)
        self.cut_vertical_line.set_band_region(x_low, x_high)
        self.cut_horizontal_line.set_band_region(y_low, y_high)

    # ------------------------------------------------------------------
    # Image helpers
    # ------------------------------------------------------------------
    def _set_image_data(self, data: np.ndarray) -> None:
        x_extent, y_extent = self._image_extent
        auto_levels = self._color_levels is None
        levels = None if auto_levels else self._color_levels
        image = np.asarray(data)
        self.im_band.setImage(image, autoLevels=auto_levels, levels=levels, autoDownsample=True)
        dx = x_extent[1] - x_extent[0]
        dy = y_extent[1] - y_extent[0]
        rect = QRectF(x_extent[0], y_extent[0], dx, dy)
        self.im_band.setRect(rect)
        if self._lut is not None:
            self.im_band.setLookupTable(self._lut)

    # ------------------------------------------------------------------
    # Appearance controls
    # ------------------------------------------------------------------
    def set_colormap(self, colormap: str) -> None:
        if not colormap:
            return
        self.colormap = colormap
        self._lut = self._create_lut(colormap)
        if self._lut is not None:
            self.im_band.setLookupTable(self._lut)

    def set_color_limits(self, vmin: Optional[float], vmax: Optional[float]) -> None:
        if vmin is None or vmax is None:
            self._color_levels = None
        else:
            self._color_levels = (float(vmin), float(vmax))
        self._set_image_data(self.intensity)

    def set_integration_radius(self, radius: int) -> None:
        radius = max(0, int(radius))
        if radius == self.integration_radius:
            return
        self.integration_radius = radius
        self._update_cut_visuals(self.cursor_mgr.cut)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------
    def get_cursor_state(self) -> CursorState:
        """Return the current cursor position."""
        return self.cursor_mgr.cursor

    def get_cut_state(self) -> CursorState:
        """Return the current cut position."""
        return self.cursor_mgr.cut

    def set_cursor_state(self, state: Optional[CursorState]) -> None:
        """Restore the cursor to a previously saved state."""
        if state is None:
            return
        self.cursor_mgr.update_cursor(state.x_value, state.y_value)

    def set_cut_state(self, state: Optional[CursorState]) -> None:
        """Restore the cut position from a saved state."""
        if state is None:
            return
        self.cursor_mgr.set_cut(state.x_value, state.y_value)

    def export_display_dataset(self) -> Dataset:
        """Return a copy of the dataset currently shown in this figure."""
        return self.file_stack.current_state.copy()

    def export_panel_dataset(self, view: Optional[str] = None) -> Dataset:
        """Return the requested panel; 2D figures only expose the main image."""
        return self.export_display_dataset()

    # ------------------------------------------------------------------
    # Axis helpers
    # ------------------------------------------------------------------
    def _update_edc_axis_limits(self, edc: np.ndarray) -> None:
        y_min, y_max = float(self.y_axis.values.min()), float(self.y_axis.values.max())
        self.ax_edc.setYRange(y_min, y_max, padding=0)
        if not np.all(np.isnan(edc)):
            x_min = np.nanmin(edc)
            x_max = np.nanmax(edc)
            if np.isfinite(x_min) and np.isfinite(x_max):
                if x_max <= x_min:
                    margin = max(abs(x_max), 1e-6)
                    x_min -= margin * 0.5
                    x_max += margin * 0.5
                margin = (x_max - x_min) * 0.1
                self.ax_edc.setXRange(x_min - margin, x_max + margin, padding=0)

    def _update_mdc_axis_limits(self, mdc: np.ndarray) -> None:
        x_min, x_max = float(self.x_axis.values.min()), float(self.x_axis.values.max())
        self.ax_mdc.setXRange(x_min, x_max, padding=0)
        if not np.all(np.isnan(mdc)):
            y_min = np.nanmin(mdc)
            y_max = np.nanmax(mdc)
            if np.isfinite(y_min) and np.isfinite(y_max):
                if y_max <= y_min:
                    margin = max(abs(y_max), 1e-6)
                    y_min -= margin * 0.5
                    y_max += margin * 0.5
                margin = (y_max - y_min) * 0.1
                self.ax_mdc.setYRange(y_min - margin, y_max + margin, padding=0)

    def _index_range(self, center: int, length: int) -> Tuple[int, int]:
        radius = self.integration_radius
        start = max(0, center - radius)
        end = min(length - 1, center + radius)
        return start, end

    def _axis_value_range(self, values: np.ndarray, index: int) -> Tuple[float, float]:
        start, end = self._index_range(index, len(values))
        return float(values[start]), float(values[end])

    def _create_lut(self, cmap_name: str) -> Optional[np.ndarray]:
        try:
            cmap = cm.get_cmap(cmap_name, 512)
        except ValueError:
            cmap = cm.get_cmap("viridis", 512)
        return (cmap(np.linspace(0, 1, 512)) * 255).astype(np.uint8)
