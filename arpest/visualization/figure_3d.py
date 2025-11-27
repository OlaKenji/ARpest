"""
High-performance Figure3D built on PyQtGraph.

Switching from Matplotlib to PyQtGraph keeps the existing slicing/cursor
functionality but relies on GPU-accelerated image items and graphics
primitives so the large 3D datasets remain interactive while dragging.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from matplotlib import cm
from PyQt5.QtCore import QObject, QEvent, Qt, QPointF, QRectF
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from ..models import FileStack
from ..utils.cursor.cursor_manager import CursorManager, CursorState
from ..utils.cursor.cursor_helpers import DragMode, DragState
from ..utils.cursor.pg_line_cursor import PGLineCursor

# Configure sane defaults for all plots hosted by this widget
pg.setConfigOptions(
    imageAxisOrder="row-major",
    antialias=True,
    background="w",
    foreground="k",
)

class _GraphicsViewEventFilter(QObject):
    """Intercept mouse events from the GraphicsLayoutWidget viewport."""

    def __init__(self, figure: "Figure3D") -> None:
        super().__init__(figure)
        self._figure = figure

    def eventFilter(self, obj, event):  # type: ignore[override]
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

class Figure3D(QWidget):
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

        self.z_index = len(self.dataset.z_axis) // 2

        self.cursor_mgr = CursorManager(self.dataset.x_axis.values, self.dataset.y_axis.values)
        initial_cursor = self.cursor_mgr.cursor
        self.fermi_cursor_x = initial_cursor.x_value
        self.fermi_cursor_y = initial_cursor.y_value

        self.curves_z_locked = self.dataset.z_axis.values[self.z_index]
        self.curves_z_cursor = self.curves_z_locked

        self.drag_state = DragState()

        self._lut = self._create_lut(self.colormap)
        self._color_levels: Optional[Tuple[float, float]] = None
        self._image_data: Dict[str, np.ndarray] = {}
        self._image_extents: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = {}

        self.view = pg.GraphicsLayoutWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self._setup_plots()
        self._plot_figures()
        self._plot_cursors()

        self.cursor_mgr.on_cut_change(self._on_cut_changed)

        self._event_filter = _GraphicsViewEventFilter(self)
        self.view.viewport().installEventFilter(self._event_filter)
        self.view.viewport().setMouseTracking(True)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _setup_plots(self) -> None:
        """Create PyQtGraph PlotItems for all panels."""
        ds = self.dataset
        self.ax_fermi = self._add_image_plot(
            0,
            0,
            title=f"Fermi Surface",
            x_label=f"{ds.x_axis.name} ({ds.x_axis.unit})",
            y_label=f"{ds.y_axis.name} ({ds.y_axis.unit})",
        )
        self.ax_cut_x = self._add_image_plot(
            0,
            1,
            title=f"Band @ {ds.x_axis.name}",
            x_label=f"{ds.z_axis.name} ({ds.z_axis.unit})",
            y_label=f"{ds.y_axis.name} ({ds.y_axis.unit})",
        )
        self.ax_cut_y = self._add_image_plot(
            1,
            0,
            title=f"Band @ {ds.y_axis.name}",
            x_label=f"{ds.x_axis.name} ({ds.x_axis.unit})",
            y_label=f"{ds.z_axis.name} ({ds.z_axis.unit})",
        )

        curves_layout = self.view.addLayout(row=1, col=1)
        curves_layout.layout.setRowStretchFactor(0, 1)
        curves_layout.layout.setRowStretchFactor(1, 1)

        self.ax_curves = curves_layout.addPlot(row=0, col=0)
        self.ax_curves.showGrid(x=True, y=True, alpha=0.3)
        self.ax_curves.setLabel("bottom", f"{ds.z_axis.name} ({ds.z_axis.unit})")
        self.ax_curves.setLabel("left", "Intensity")
        self.ax_curves.addLegend(offset=(10, 10))
        self.ax_curves.setMouseEnabled(x=False, y=False)
        self.ax_curves.hideButtons()
        self._set_viewbox_padding(self.ax_curves.getViewBox(), 0.0)

        self.ax_mdc = curves_layout.addPlot(row=1, col=0)
        self.ax_mdc.showGrid(x=True, y=True, alpha=0.3)
        self.ax_mdc.setLabel("bottom", f"{ds.y_axis.name} ({ds.y_axis.unit})")
        self.ax_mdc.setLabel("left", "Intensity")
        self.ax_mdc.addLegend(offset=(10, 10))
        self.ax_mdc.setMouseEnabled(x=False, y=False)
        self.ax_mdc.hideButtons()
        self._set_viewbox_padding(self.ax_mdc.getViewBox(), 0.0)

        self._axes = {
            "fermi": self.ax_fermi,
            "cut_x": self.ax_cut_x,
            "cut_y": self.ax_cut_y,
            "curves": self.ax_curves,
        }
        
        # Fix layout column/row sizes to prevent wiggling
        ci = self.view.ci
        ci.layout.setColumnStretchFactor(0, 1)
        ci.layout.setColumnStretchFactor(1, 1)
        ci.layout.setRowStretchFactor(0, 1)
        ci.layout.setRowStretchFactor(1, 1)

        # Optionally, enforce minimum sizes so cursor text doesn’t overlap:
        ci.layout.setColumnMinimumWidth(0, 380)
        ci.layout.setColumnMinimumWidth(1, 380)
        ci.layout.setRowMinimumHeight(0, 260)
        ci.layout.setRowMinimumHeight(1, 260)

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

    def _plot_figures(self) -> None:
        """Create image items and curve plots."""
        intensity = self._get_intensity_slice()
        cut = self.cursor_mgr.cut
        cut_y = self._compute_cut_y(cut)
        cut_x = self._compute_cut_x(cut)
        self._cut_y_data = cut_y
        self._cut_x_data = cut_x
        edc_from_cut_y, edc_from_cut_x = self._compute_edc_curves(cut)
        mdc_from_cut_y, mdc_from_cut_x = self._compute_mdc_curves(cut, cut_y, cut_x)

        self.im_fermi = pg.ImageItem()
        self.im_cut_y = pg.ImageItem()
        self.im_cut_x = pg.ImageItem()

        self.ax_fermi.addItem(self.im_fermi)
        self.ax_cut_y.addItem(self.im_cut_y)
        self.ax_cut_x.addItem(self.im_cut_x)

        x_extent = (float(self.dataset.x_axis.values.min()), float(self.dataset.x_axis.values.max()))
        y_extent = (float(self.dataset.y_axis.values.min()), float(self.dataset.y_axis.values.max()))
        z_extent = (float(self.dataset.z_axis.values.min()), float(self.dataset.z_axis.values.max()))

        self._image_items = {
            "fermi": self.im_fermi,
            "cut_y": self.im_cut_y,
            "cut_x": self.im_cut_x,
        }
        self._image_extents = {
            "fermi": (x_extent, y_extent),
            "cut_y": (x_extent, z_extent),
            "cut_x": (z_extent, y_extent),
        }

        self._set_image_data("fermi", intensity, x_extent, y_extent)
        self._set_image_data("cut_y", cut_y.T, x_extent, z_extent)
        self._set_image_data("cut_x", cut_x, z_extent, y_extent)

        self.ax_cut_y.setTitle(f"Band @ {self.dataset.y_axis.name}={cut.y_value:.2f}°")
        self.ax_cut_x.setTitle(f"Band @ {self.dataset.x_axis.name}={cut.x_value:.2f}°")
        self.ax_fermi.setTitle(
            f"Fermi Surface @ {self.dataset.z_axis.values[self.z_index]:.2f} {self.dataset.z_axis.unit}"
        )

        self._set_plot_range(self.ax_fermi, x_extent, y_extent)
        self._set_plot_range(self.ax_cut_y, x_extent, z_extent)
        self._set_plot_range(self.ax_cut_x, z_extent, y_extent)

        z_values = self.dataset.z_axis.values
        self.line_edc_cut_y = self.ax_curves.plot(
            z_values,
            edc_from_cut_y,
            pen=pg.mkPen("#1f77b4", width=1.5),
            name="EDC bottom-left",
        )
        self.line_edc_cut_x = self.ax_curves.plot(
            z_values,
            edc_from_cut_x,
            pen=pg.mkPen("#ff7f0e", width=1.5),
            name="EDC top-right",
        )
        self.ax_curves.setXRange(z_extent[0], z_extent[1], padding=0)
        self._update_edc_axis_limits(edc_from_cut_y, edc_from_cut_x)

        self.line_mdc_cut_y = self.ax_mdc.plot(
            self.dataset.x_axis.values,
            mdc_from_cut_y,
            pen=pg.mkPen("#1f77b4", width=1.5),
            name="MDC bottom-left",
        )
        self.line_mdc_cut_x = self.ax_mdc.plot(
            self.dataset.y_axis.values,
            mdc_from_cut_x,
            pen=pg.mkPen("#ff7f0e", width=1.5),
            name="MDC top-right",
        )
        self._update_mdc_axis_limits(mdc_from_cut_y, mdc_from_cut_x)

    def _plot_cursors(self) -> None:
        """Create cursor overlays using PyQtGraph primitives."""
        cut = self.cursor_mgr.cut
        ds = self.dataset
        z_extent = (ds.z_axis.values.min(), ds.z_axis.values.max())

        self.energy_cursor = PGLineCursor(
            self.ax_curves,
            orientation="vertical",
            locked_value=self.curves_z_locked,
            cursor_value=self.curves_z_cursor,
            show_band=True,
            solid_kwargs={"color": "red"},
            dashed_kwargs={"color": "gray"},
        )

        self.fermi_x_cursor = PGLineCursor(
            self.ax_fermi,
            orientation="vertical",
            locked_value=cut.x_value,
            cursor_value=self.fermi_cursor_x,
            show_band=True,
        )
        self.fermi_y_cursor = PGLineCursor(
            self.ax_fermi,
            orientation="horizontal",
            locked_value=cut.y_value,
            cursor_value=self.fermi_cursor_y,
            show_band=True,
        )

        self.cut_y_x_line = PGLineCursor(
            self.ax_cut_y,
            orientation="vertical",
            locked_value=cut.x_value,
            cursor_value=cut.x_value,
            show_band=True,
        )
        self.cut_y_z_line = PGLineCursor(
            self.ax_cut_y,
            orientation="horizontal",
            locked_value=self.curves_z_locked,
            cursor_value=self.curves_z_locked,
            show_band=True,
        )

        self.cut_x_y_line = PGLineCursor(
            self.ax_cut_x,
            orientation="horizontal",
            locked_value=cut.y_value,
            cursor_value=cut.y_value,
            show_band=True,
        )
        self.cut_x_z_line = PGLineCursor(
            self.ax_cut_x,
            orientation="vertical",
            locked_value=self.curves_z_locked,
            cursor_value=self.curves_z_locked,
            show_band=True,
        )

        self._update_integration_overlays()

    # ------------------------------------------------------------------
    # Mouse handling via event filter
    # ------------------------------------------------------------------
    def _handle_mouse_move_event(self, event) -> None:
        scene_pos = self.view.mapToScene(event.pos())
        axis_key, point = self._scene_pos_to_axis(scene_pos)
        if axis_key is None or point is None:
            return
        is_dragging = bool(event.buttons() & Qt.LeftButton)
        self._on_mouse_move(axis_key, point.x(), point.y(), is_dragging)

    def _handle_mouse_press_event(self, event) -> None:
        scene_pos = self.view.mapToScene(event.pos())
        axis_key, point = self._scene_pos_to_axis(scene_pos)
        if axis_key is None or point is None:
            return
        self._on_mouse_press(axis_key, point.x(), point.y())

    def _handle_mouse_release_event(self, event) -> None:
        self._on_mouse_release()

    def _scene_pos_to_axis(self, scene_pos) -> Tuple[Optional[str], Optional[QPointF]]:
        for key, plot in self._axes.items():
            if plot.sceneBoundingRect().contains(scene_pos):
                view_point = plot.getViewBox().mapSceneToView(scene_pos)
                return key, view_point
        return None, None

    def _on_mouse_move(self, axis_key: str, x: float, y: float, is_dragging: bool) -> None:
        if axis_key == "fermi":
            self.fermi_cursor_x = x
            self.fermi_cursor_y = y
            self.fermi_x_cursor.set_cursor(x)
            self.fermi_y_cursor.set_cursor(y)
            if is_dragging and self.drag_state.is_mode(DragMode.FERMI):
                self.cursor_mgr.update_cursor(x, y)
        elif axis_key == "cut_y":
            self.cut_y_x_line.set_cursor(x)
            self.cut_y_z_line.set_cursor(y)
            if is_dragging and self.drag_state.is_mode(DragMode.CUT_Y) and self.drag_state.anchor_y is not None:
                self.cursor_mgr.update_cursor(x, self.drag_state.anchor_y)
                self._set_locked_energy(y)
        elif axis_key == "cut_x":
            self.cut_x_y_line.set_cursor(y)
            self.cut_x_z_line.set_cursor(x)
            if is_dragging and self.drag_state.is_mode(DragMode.CUT_X) and self.drag_state.anchor_x is not None:
                self.cursor_mgr.update_cursor(self.drag_state.anchor_x, y)
                self._set_locked_energy(x)
        elif axis_key == "curves":
            self.curves_z_cursor = x
            self.energy_cursor.set_cursor(x)
            if is_dragging and self.drag_state.is_mode(DragMode.ENERGY):
                self._set_locked_energy(x)

    def _on_mouse_press(self, axis_key: str, x: float, y: float) -> None:
        if axis_key == "fermi":
            self.drag_state.start(DragMode.FERMI)
            self.cursor_mgr.start_drag()
            self.cursor_mgr.update_cursor(x, y)
        elif axis_key == "cut_y":
            anchor_y = self.cursor_mgr.cut.y_value
            self.drag_state.start(DragMode.CUT_Y, anchor_y=anchor_y)
            self.cursor_mgr.start_drag()
            self.cursor_mgr.update_cursor(x, anchor_y)
            self._set_locked_energy(y)
        elif axis_key == "cut_x":
            anchor_x = self.cursor_mgr.cut.x_value
            self.drag_state.start(DragMode.CUT_X, anchor_x=anchor_x)
            self.cursor_mgr.start_drag()
            self.cursor_mgr.update_cursor(anchor_x, y)
            self._set_locked_energy(x)
        elif axis_key == "curves":
            self.drag_state.start(DragMode.ENERGY)
            self.curves_z_cursor = x
            self.energy_cursor.set_cursor(x)
            self._set_locked_energy(x)

    def _on_mouse_release(self) -> None:
        self.cursor_mgr.end_drag()
        self.drag_state.stop()
        self._update_imshows_for_cut()
        self._update_imshow_for_energy()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _set_plot_range(self, plot, x_range, y_range) -> None:
        plot.setRange(xRange=x_range, yRange=y_range, padding=0)
        disable = getattr(plot, "disableAutoRange", None)
        if callable(disable):
            disable()

    def _set_image_data(self, key: str, data: np.ndarray, x_extent=None, y_extent=None) -> None:
        self._image_data[key] = data
        if x_extent is None or y_extent is None:
            x_extent, y_extent = self._image_extents[key]
        self._image_extents[key] = (x_extent, y_extent)
        self._apply_image(self._image_items[key], data, x_extent, y_extent)

    def _apply_image(self, image_item: pg.ImageItem, data: np.ndarray, x_extent, y_extent) -> None:
        auto_levels = self._color_levels is None
        levels = None if auto_levels else self._color_levels
        image = np.asarray(data)
        image_item.setImage(image, autoLevels=auto_levels, levels=levels, autoDownsample=True)
        dx = x_extent[1] - x_extent[0]
        dy = y_extent[1] - y_extent[0]
        rect = QRectF(x_extent[0], y_extent[0], dx, dy)
        image_item.setRect(rect)
        if self._lut is not None:
            image_item.setLookupTable(self._lut)

    def _refresh_images(self) -> None:
        for key, data in list(self._image_data.items()):
            x_extent, y_extent = self._image_extents[key]
            self._set_image_data(key, data, x_extent, y_extent)

    def _get_intensity_slice(self) -> np.ndarray:
        start, end = self._index_range(self.z_index, len(self.dataset.z_axis))
        block = self.dataset.intensity[:, :, start : end + 1]
        if block.ndim == 3:
            return np.nanmean(block, axis=2)
        return block

    def _update_imshows_for_cut(self) -> None:
        cut = self.cursor_mgr.cut
        cut_y = self._compute_cut_y(cut)
        cut_x = self._compute_cut_x(cut)
        self._cut_y_data = cut_y
        self._cut_x_data = cut_x
        cut_y_x_extent, cut_y_z_extent = self._image_extents["cut_y"]
        self._set_image_data("cut_y", cut_y.T, cut_y_x_extent, cut_y_z_extent)
        cut_x_z_extent, cut_x_y_extent = self._image_extents["cut_x"]
        self._set_image_data("cut_x", cut_x, cut_x_z_extent, cut_x_y_extent)

        self.ax_cut_y.setTitle(f"Band @ {self.dataset.y_axis.name}={cut.y_value:.2f}°")
        self.ax_cut_x.setTitle(f"Band @ {self.dataset.x_axis.name}={cut.x_value:.2f}°")

        edc_from_cut_y, edc_from_cut_x = self._compute_edc_curves(cut)
        self.line_edc_cut_y.setData(self.dataset.z_axis.values, edc_from_cut_y)
        self.line_edc_cut_x.setData(self.dataset.z_axis.values, edc_from_cut_x)
        self._update_edc_axis_limits(edc_from_cut_y, edc_from_cut_x)
        mdc_from_cut_y, mdc_from_cut_x = self._compute_mdc_curves(cut, cut_y, cut_x)
        self.line_mdc_cut_y.setData(self.dataset.x_axis.values, mdc_from_cut_y)
        self.line_mdc_cut_x.setData(self.dataset.y_axis.values, mdc_from_cut_x)
        self._update_mdc_axis_limits(mdc_from_cut_y, mdc_from_cut_x)

    def _update_imshow_for_energy(self) -> None:
        intensity = self._get_intensity_slice()
        x_extent, y_extent = self._image_extents["fermi"]
        self._set_image_data("fermi", intensity, x_extent, y_extent)
        edc_from_cut_y, edc_from_cut_x = self._compute_edc_curves(self.cursor_mgr.cut)
        self.line_edc_cut_y.setData(self.dataset.z_axis.values, edc_from_cut_y)
        self.line_edc_cut_x.setData(self.dataset.z_axis.values, edc_from_cut_x)
        self._update_edc_axis_limits(edc_from_cut_y, edc_from_cut_x)
        mdc_from_cut_y, mdc_from_cut_x = self._compute_mdc_curves(self.cursor_mgr.cut)
        self.line_mdc_cut_y.setData(self.dataset.x_axis.values, mdc_from_cut_y)
        self.line_mdc_cut_x.setData(self.dataset.y_axis.values, mdc_from_cut_x)
        self._update_mdc_axis_limits(mdc_from_cut_y, mdc_from_cut_x)

    def _update_edc_axis_limits(self, curve_a: np.ndarray, curve_b: np.ndarray) -> None:
        edc_y_min = min(np.nanmin(curve_a), np.nanmin(curve_b))
        edc_y_max = max(np.nanmax(curve_a), np.nanmax(curve_b))
        if np.isnan(edc_y_min) or np.isnan(edc_y_max) or not edc_y_max > edc_y_min:
            return
        margin = (edc_y_max - edc_y_min) * 0.1
        self.ax_curves.setYRange(edc_y_min - margin, edc_y_max + margin, padding=0)

    def _update_mdc_axis_limits(self, curve_a: np.ndarray, curve_b: np.ndarray) -> None:
        mdc_y_min = min(np.nanmin(curve_a), np.nanmin(curve_b))
        mdc_y_max = max(np.nanmax(curve_a), np.nanmax(curve_b))
        if np.isnan(mdc_y_min) or np.isnan(mdc_y_max) or not mdc_y_max > mdc_y_min:
            return
        margin = (mdc_y_max - mdc_y_min) * 0.1
        self.ax_mdc.setYRange(mdc_y_min - margin, mdc_y_max + margin, padding=0)

    def _set_locked_energy(self, z_value: Optional[float]) -> None:
        if z_value is None or self.dataset is None:
            return

        z_vals = self.dataset.z_axis.values
        clipped = float(np.clip(z_value, z_vals.min(), z_vals.max()))
        new_index = self._find_nearest_z_index(clipped)

        if np.isclose(clipped, self.curves_z_locked) and new_index == self.z_index:
            return

        self.curves_z_locked = clipped
        self.curves_z_cursor = clipped
        self.energy_cursor.set_locked(clipped)
        self.energy_cursor.set_cursor(clipped)
        self.cut_y_z_line.set_locked(clipped)
        self.cut_x_z_line.set_locked(clipped)

        if new_index != self.z_index:
            self.z_index = new_index
            self._update_imshow_for_energy()
            self._update_integration_overlays()

    def _on_cut_changed(self, cut: CursorState) -> None:
        self.fermi_x_cursor.set_locked(cut.x_value)
        self.fermi_y_cursor.set_locked(cut.y_value)
        self.cut_y_x_line.set_locked(cut.x_value)
        self.cut_x_y_line.set_locked(cut.y_value)
        self._update_integration_overlays()
        self._update_imshows_for_cut()

    def _find_nearest_z_index(self, z_value: float) -> int:
        return int(np.argmin(np.abs(self.dataset.z_axis.values - z_value)))

    def set_integration_radius(self, radius: int) -> None:
        radius = max(0, int(radius))
        if radius == self.integration_radius:
            return
        self.integration_radius = radius
        self._update_integration_overlays()
        self._update_imshows_for_cut()
        self._update_imshow_for_energy()

    def _index_range(self, center: int, length: int) -> Tuple[int, int]:
        radius = self.integration_radius
        start = max(0, center - radius)
        end = min(length - 1, center + radius)
        return start, end

    def _axis_value_range(self, values: np.ndarray, index: int) -> Tuple[float, float]:
        start, end = self._index_range(index, len(values))
        return float(values[start]), float(values[end])

    def _compute_cut_y(self, cut: CursorState) -> np.ndarray:
        start, end = self._index_range(cut.y_idx, len(self.dataset.y_axis))
        slice_data = self.dataset.intensity[start : end + 1, :, :]
        return np.nanmean(slice_data, axis=0)

    def _compute_cut_x(self, cut: CursorState) -> np.ndarray:
        start, end = self._index_range(cut.x_idx, len(self.dataset.x_axis))
        slice_data = self.dataset.intensity[:, start : end + 1, :]
        return np.nanmean(slice_data, axis=1)

    def _compute_edc_curves(self, cut: CursorState) -> Tuple[np.ndarray, np.ndarray]:
        """Return EDCs derived independently from horizontal and vertical cuts."""
        x_start, x_end = self._index_range(cut.x_idx, len(self.dataset.x_axis))
        y_start, y_end = self._index_range(cut.y_idx, len(self.dataset.y_axis))

        # Cut_y (x vs energy) -> average a narrow band along y only
        y_slice = self.dataset.intensity[y_start : y_end + 1, cut.x_idx, :]
        edc_from_cut_y = np.nanmean(y_slice, axis=0)

        # Cut_x (y vs energy) -> average a narrow band along x only
        x_slice = self.dataset.intensity[cut.y_idx, x_start : x_end + 1, :]
        edc_from_cut_x = np.nanmean(x_slice, axis=0)
        return edc_from_cut_y, edc_from_cut_x

    def _compute_mdc_curves(
        self,
        cut: CursorState,
        cut_y_data: Optional[np.ndarray] = None,
        cut_x_data: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return MDCs (intensity vs angle) from the two cut panels."""
        if cut_y_data is None:
            cut_y_data = getattr(self, "_cut_y_data", None)
        if cut_x_data is None:
            cut_x_data = getattr(self, "_cut_x_data", None)
        if cut_y_data is None or cut_x_data is None:
            return np.zeros_like(self.dataset.x_axis.values), np.zeros_like(self.dataset.y_axis.values)

        z_start, z_end = self._index_range(self.z_index, len(self.dataset.z_axis))
        mdc_from_cut_y = np.nanmean(cut_y_data[:, z_start : z_end + 1], axis=1)
        mdc_from_cut_x = np.nanmean(cut_x_data[:, z_start : z_end + 1], axis=1)
        return mdc_from_cut_y, mdc_from_cut_x

    def _update_integration_overlays(self) -> None:
        cut = self.cursor_mgr.cut
        x_low, x_high = self._axis_value_range(self.dataset.x_axis.values, cut.x_idx)
        y_low, y_high = self._axis_value_range(self.dataset.y_axis.values, cut.y_idx)
        z_low, z_high = self._axis_value_range(self.dataset.z_axis.values, self.z_index)
        self.fermi_x_cursor.set_band_region(x_low, x_high)
        self.fermi_y_cursor.set_band_region(y_low, y_high)
        self.cut_y_x_line.set_band_region(x_low, x_high)
        self.cut_x_y_line.set_band_region(y_low, y_high)
        self.energy_cursor.set_band_region(z_low, z_high)
        self.cut_y_z_line.set_band_region(z_low, z_high)
        self.cut_x_z_line.set_band_region(z_low, z_high)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------
    def get_cursor_state(self) -> CursorState:
        """Return the current cursor location on the fermi panel."""
        return self.cursor_mgr.cursor

    def get_cut_state(self) -> CursorState:
        """Return the current cut anchor."""
        return self.cursor_mgr.cut

    def set_cursor_state(self, state: Optional[CursorState]) -> None:
        """Restore the cursor from a saved state."""
        if state is None:
            return
        self.cursor_mgr.update_cursor(state.x_value, state.y_value)

    def set_cut_state(self, state: Optional[CursorState]) -> None:
        """Restore the cut anchor from a saved state."""
        if state is None:
            return
        self.cursor_mgr.set_cut(state.x_value, state.y_value)

    # ------------------------------------------------------------------
    # Appearance controls
    # ------------------------------------------------------------------
    def set_colormap(self, colormap: str) -> None:
        if not colormap:
            return
        self.colormap = colormap
        self._lut = self._create_lut(colormap)
        self._apply_lut()

    def _apply_lut(self) -> None:
        if self._lut is None:
            return
        for image in (self.im_fermi, self.im_cut_y, self.im_cut_x):
            if image is not None:
                image.setLookupTable(self._lut)

    def set_color_limits(self, vmin: Optional[float], vmax: Optional[float]) -> None:
        if vmin is None or vmax is None:
            self._color_levels = None
        else:
            self._color_levels = (float(vmin), float(vmax))
        self._refresh_images()

    def _create_lut(self, cmap_name: str) -> Optional[np.ndarray]:
        try:
            cmap = cm.get_cmap(cmap_name, 512)
        except ValueError:
            cmap = cm.get_cmap("viridis", 512)
        lut = (cmap(np.linspace(0, 1, 512)) * 255).astype(np.uint8)
        return lut
