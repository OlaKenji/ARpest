"""
Interactive 4D visualization for spatial maps.

Displays a spatial (x–y) slice taken at the current kinetic energy and
analyser angle, along with the corresponding local EDC, angular trace,
and full energy/angle spectrum extracted from the selected point.
Energy/angle selections are adjusted by dragging directly on the plots.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from matplotlib import cm
from PyQt5.QtCore import QObject, QEvent, Qt, QPointF, QRectF
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from ..models import Dataset, FileStack
from ..utils.cursor.cursor_helpers import DragMode, DragState
from ..utils.cursor.cursor_manager import CursorManager, CursorState
from ..utils.cursor.pg_line_cursor import PGLineCursor

pg.setConfigOptions(
    imageAxisOrder="row-major",
    antialias=True,
    background="w",
    foreground="k",
)


class _GraphicsViewEventFilter(QObject):
    """Intercept mouse events on the GraphicsLayoutWidget."""

    def __init__(self, figure: "Figure4D") -> None:
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


class Figure4D(QWidget):
    """Spatial 4D visualisation widget."""

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
        if not self.dataset.is_4d or self.dataset.z_axis is None or self.dataset.w_axis is None:
            raise ValueError("Figure4D requires a 4D dataset with energy and angle axes.")

        self.colormap = colormap
        self.integration_radius = max(0, int(integration_radius))

        self.x_axis = self.dataset.x_axis
        self.y_axis = self.dataset.y_axis
        self.z_axis = self.dataset.z_axis
        self.w_axis = self.dataset.w_axis
        self.z_index = len(self.z_axis.values) // 2
        self.w_index = len(self.w_axis.values) // 2
        self._energy_x_range: Tuple[float, float] | None = None
        self._angle_x_range: Tuple[float, float] | None = None
        self._energy_y_range: Tuple[float, float] | None = None
        self._angle_y_range: Tuple[float, float] | None = None

        self.cursor_mgr = CursorManager(self.x_axis.values, self.y_axis.values)
        self.drag_state = DragState()

        self._lut = self._create_lut(self.colormap)
        self._color_levels: Optional[Tuple[float, float]] = None
        self._image_extent: Tuple[Tuple[float, float], Tuple[float, float]] = (
            (float(self.x_axis.values.min()), float(self.x_axis.values.max())),
            (float(self.y_axis.values.min()), float(self.y_axis.values.max())),
        )
        self._point_extent: Tuple[Tuple[float, float], Tuple[float, float]] = (
            (float(self.z_axis.values.min()), float(self.z_axis.values.max())),
            (float(self.w_axis.values.min()), float(self.w_axis.values.max())),
        )

        self.view = pg.GraphicsLayoutWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self._setup_plots()
        self._plot_map_and_profiles()

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

        self.ax_map = self._add_image_plot(
            0,
            0,
            title="",
            x_label=f"{self.x_axis.name} ({self.x_axis.unit})",
            y_label=f"{self.y_axis.name} ({self.y_axis.unit})",
        )
        self.ax_map.invertY(True)

        self.ax_point = self._add_image_plot(
            0,
            1,
            title="Local spectrum",
            x_label=f"{self.z_axis.name} ({self.z_axis.unit})",
            y_label=f"{self.w_axis.name} ({self.w_axis.unit})",
        )
        self.ax_point.setMouseEnabled(x=False, y=False)
        self.ax_point.hideButtons()

        self.ax_energy = self.view.addPlot(row=1, col=1)
        self.ax_energy.showGrid(x=True, y=True, alpha=0.3)
        self.ax_energy.setLabel("bottom", f"{self.z_axis.name} ({self.z_axis.unit})")
        self.ax_energy.setLabel("left", "Intensity")
        self.ax_energy.setMouseEnabled(x=False, y=False)
        self.ax_energy.hideButtons()

        self.ax_angle = self.view.addPlot(row=1, col=0)
        self.ax_angle.showGrid(x=True, y=True, alpha=0.3)
        self.ax_angle.setLabel("bottom", f"{self.w_axis.name} ({self.w_axis.unit})")
        self.ax_angle.setLabel("left", "Intensity")
        self.ax_angle.setMouseEnabled(x=False, y=False)
        self.ax_angle.hideButtons()

        ci = self.view.ci
        ci.layout.setColumnStretchFactor(0, 3)
        ci.layout.setColumnStretchFactor(1, 2)
        ci.layout.setRowStretchFactor(0, 3)
        ci.layout.setRowStretchFactor(1, 1)

        self._axes: Dict[str, pg.PlotItem] = {
            "map": self.ax_map,
            "energy": self.ax_energy,
            "angle": self.ax_angle,
            "point": self.ax_point,
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

    def _plot_map_and_profiles(self) -> None:
        self.im_map = pg.ImageItem()
        self.ax_map.addItem(self.im_map)
        self._update_map_image()

        cut = self.cursor_mgr.cut
        edc = self._compute_edc(cut)
        angle_curve = self._compute_angle_curve(cut)

        self._current_edc_curve = np.asarray(edc, dtype=float)
        self._current_angle_curve = np.asarray(angle_curve, dtype=float)

        self.line_energy = self.ax_energy.plot(
            self.z_axis.values, edc, pen=pg.mkPen("#1f77b4", width=1.5), name="EDC"
        )
        self.line_angle = self.ax_angle.plot(
            self.w_axis.values, angle_curve, pen=pg.mkPen("#ff7f0e", width=1.5), name="Angle"
        )

        self.energy_cursor = PGLineCursor(
            self.ax_energy,
            orientation="vertical",
            locked_value=self.z_axis.values[self.z_index],
            show_band=False,
            show_cursor=False,
        )
        self.angle_cursor = PGLineCursor(
            self.ax_angle,
            orientation="vertical",
            locked_value=self.w_axis.values[self.w_index],
            show_band=False,
            show_cursor=False,
        )

        cursor = self.cursor_mgr.cursor
        cut_state = self.cursor_mgr.cut
        self.cut_vertical_line = PGLineCursor(
            self.ax_map,
            orientation="vertical",
            locked_value=cut_state.x_value,
            show_cursor=False,
            show_band=True,
        )
        self.cut_horizontal_line = PGLineCursor(
            self.ax_map,
            orientation="horizontal",
            locked_value=cut_state.y_value,
            show_cursor=False,
            show_band=True,
        )
        self.cursor_vertical_line = PGLineCursor(
            self.ax_map,
            orientation="vertical",
            locked_value=cursor.x_value,
            cursor_value=cursor.x_value,
            show_locked=False,
        )
        self.cursor_horizontal_line = PGLineCursor(
            self.ax_map,
            orientation="horizontal",
            locked_value=cursor.y_value,
            cursor_value=cursor.y_value,
            show_locked=False,
        )

        self.im_point = pg.ImageItem()
        self.ax_point.addItem(self.im_point)
        self._update_point_spectrum()
        self.point_energy_cursor = PGLineCursor(
            self.ax_point,
            orientation="vertical",
            locked_value=self.z_axis.values[self.z_index],
            show_band=False,
            show_cursor=False,
        )
        self.point_angle_cursor = PGLineCursor(
            self.ax_point,
            orientation="horizontal",
            locked_value=self.w_axis.values[self.w_index],
            show_band=False,
            show_cursor=False,
        )

        self._update_integration_overlays()
        self._update_map_title()

    # ------------------------------------------------------------------
    # Curve helpers
    # ------------------------------------------------------------------
    def _current_map_slice(self) -> np.ndarray:
        return self.dataset.intensity[:, :, self.z_index, self.w_index]

    def _update_map_image(self) -> None:
        image = np.asarray(self._current_map_slice(), dtype=float)
        self._set_image_data(image)
        self._update_map_title()

    def _set_image_data(self, data: np.ndarray) -> None:
        x_extent, y_extent = self._image_extent
        auto_levels = self._color_levels is None
        levels = None if auto_levels else self._color_levels
        image = np.asarray(data)
        self.im_map.setImage(image, autoLevels=auto_levels, levels=levels, autoDownsample=True)
        dx = x_extent[1] - x_extent[0]
        dy = y_extent[1] - y_extent[0]
        rect = QRectF(x_extent[0], y_extent[0], dx, dy)
        self.im_map.setRect(rect)
        if self._lut is not None:
            self.im_map.setLookupTable(self._lut)
        self._lock_plot_range(self.ax_map, x_extent, y_extent)

    def _set_point_image(self, data: np.ndarray) -> None:
        x_extent, y_extent = self._point_extent
        auto_levels = True
        image = np.asarray(data)
        self.im_point.setImage(image, autoLevels=auto_levels, autoDownsample=True)
        dx = x_extent[1] - x_extent[0]
        dy = y_extent[1] - y_extent[0]
        rect = QRectF(x_extent[0], y_extent[0], dx, dy)
        self.im_point.setRect(rect)
        if self._lut is not None:
            self.im_point.setLookupTable(self._lut)
        self._lock_plot_range(self.ax_point, x_extent, y_extent)

    def _compute_region_average(self, cut: CursorState) -> np.ndarray:
        """Return spatially averaged spectrum (z × w) for the selected region."""
        y_start, y_end = self._index_range(cut.y_idx, len(self.y_axis.values))
        x_start, x_end = self._index_range(cut.x_idx, len(self.x_axis.values))
        block = self.dataset.intensity[y_start : y_end + 1, x_start : x_end + 1]
        averaged = np.nanmean(block, axis=(0, 1))
        if averaged.ndim != 2:
            averaged = np.reshape(averaged, (len(self.z_axis.values), len(self.w_axis.values)))
        return averaged

    def _compute_edc(self, cut: CursorState) -> np.ndarray:
        averaged = self._compute_region_average(cut)
        return averaged[:, self.w_index]

    def _compute_angle_curve(self, cut: CursorState) -> np.ndarray:
        averaged = self._compute_region_average(cut)
        return averaged[self.z_index, :]

    def _update_edc_curve(self) -> None:
        edc = self._compute_edc(self.cursor_mgr.cut)
        self._current_edc_curve = np.asarray(edc, dtype=float)
        self.line_energy.setData(self.z_axis.values, edc)

    def _update_angle_curve(self) -> None:
        angle_curve = self._compute_angle_curve(self.cursor_mgr.cut)
        self._current_angle_curve = np.asarray(angle_curve, dtype=float)
        self.line_angle.setData(self.w_axis.values, angle_curve)

    def _update_point_spectrum(self) -> None:
        averaged = self._compute_region_average(self.cursor_mgr.cut)
        self._set_point_image(averaged.T)

    def _update_map_title(self) -> None:
        energy_value = self.z_axis.values[self.z_index]
        angle_value = self.w_axis.values[self.w_index]
        self.ax_map.setTitle("")

    def get_current_edc_curves(self) -> dict[str, np.ndarray]:
        """Expose local EDC for analysis tools."""
        if getattr(self, "_current_edc_curve", None) is None:
            return {}
        return {"z": np.asarray(self._current_edc_curve, dtype=float).copy()}

    def get_current_mdc_curves(self) -> dict[str, np.ndarray]:
        """Expose local angle curve (treated as MDC analogue)."""
        if getattr(self, "_current_angle_curve", None) is None:
            return {}
        return {"w": np.asarray(self._current_angle_curve, dtype=float).copy()}

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _set_energy_value(self, value: float) -> None:
        idx = int(np.argmin(np.abs(self.z_axis.values - value)))
        idx = max(0, min(idx, len(self.z_axis.values) - 1))
        if idx == self.z_index:
            self.energy_cursor.set_cursor(float(value))
            self.point_energy_cursor.set_cursor(float(value))
            return
        self.z_index = idx
        actual = float(self.z_axis.values[idx])
        self.energy_cursor.set_locked(actual)
        self.energy_cursor.set_cursor(actual)
        self.point_energy_cursor.set_locked(actual)
        self.point_energy_cursor.set_cursor(actual)
        self._update_map_image()
        self._update_angle_curve()
        self._update_point_spectrum()

    def _set_angle_value(self, value: float) -> None:
        idx = int(np.argmin(np.abs(self.w_axis.values - value)))
        idx = max(0, min(idx, len(self.w_axis.values) - 1))
        if idx == self.w_index:
            self.angle_cursor.set_cursor(float(value))
            self.point_angle_cursor.set_cursor(float(value))
            return
        self.w_index = idx
        actual = float(self.w_axis.values[idx])
        self.angle_cursor.set_locked(actual)
        self.angle_cursor.set_cursor(actual)
        self.point_angle_cursor.set_locked(actual)
        self.point_angle_cursor.set_cursor(actual)
        self._update_map_image()
        self._update_edc_curve()
        self._update_point_spectrum()

    def _update_integration_overlays(self) -> None:
        cut = self.cursor_mgr.cut
        x_low, x_high = self._axis_value_range(self.x_axis.values, cut.x_idx)
        y_low, y_high = self._axis_value_range(self.y_axis.values, cut.y_idx)
        self.cut_vertical_line.set_band_region(x_low, x_high)
        self.cut_horizontal_line.set_band_region(y_low, y_high)

    def _index_range(self, center: int, length: int) -> Tuple[int, int]:
        radius = max(0, self.integration_radius)
        start = max(0, center - radius)
        end = min(length - 1, center + radius)
        return start, end

    def _axis_value_range(self, values: np.ndarray, index: int) -> Tuple[float, float]:
        start, end = self._index_range(index, len(values))
        return float(values[start]), float(values[end])

    # ------------------------------------------------------------------
    # Mouse handling
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
        if axis_key == "map":
            self.cursor_vertical_line.set_cursor(x)
            self.cursor_horizontal_line.set_cursor(y)
            if is_dragging and self.drag_state.is_mode(DragMode.FERMI):
                self.cursor_mgr.update_cursor(x, y)
        elif axis_key == "energy":
            self.energy_cursor.set_cursor(x)
            if is_dragging and self.drag_state.is_mode(DragMode.ENERGY):
                self._set_energy_value(x)
        elif axis_key == "angle":
            self.angle_cursor.set_cursor(x)
            if is_dragging and self.drag_state.is_mode(DragMode.ANGLE):
                self._set_angle_value(x)
        elif axis_key == "point":
            self.point_energy_cursor.set_cursor(x)
            self.point_angle_cursor.set_cursor(y)
            if is_dragging and self.drag_state.is_mode(DragMode.POINT):
                self._set_energy_value(x)
                self._set_angle_value(y)

    def _on_mouse_press(self, axis_key: str, x: float, y: float) -> None:
        if axis_key == "map":
            self.drag_state.start(DragMode.FERMI)
            self.cursor_mgr.start_drag()
            self.cursor_mgr.update_cursor(x, y)
        elif axis_key == "energy":
            self.drag_state.start(DragMode.ENERGY)
            self._set_energy_value(x)
        elif axis_key == "angle":
            self.drag_state.start(DragMode.ANGLE)
            self._set_angle_value(x)
        elif axis_key == "point":
            self.drag_state.start(DragMode.POINT)
            self._set_energy_value(x)
            self._set_angle_value(y)

    def _on_mouse_release(self) -> None:
        if self.drag_state.is_mode(DragMode.FERMI):
            self.cursor_mgr.end_drag()
        self.drag_state.stop()

    def _on_cursor_changed(self, cursor: CursorState) -> None:
        self.cursor_vertical_line.set_cursor(cursor.x_value)
        self.cursor_horizontal_line.set_cursor(cursor.y_value)

    def _on_cut_changed(self, cut: CursorState) -> None:
        self._update_cut_visuals(cut)

    def _update_cut_visuals(self, cut: CursorState) -> None:
        self.cut_vertical_line.set_locked(cut.x_value)
        self.cut_horizontal_line.set_locked(cut.y_value)
        self._update_edc_curve()
        self._update_angle_curve()
        self._update_point_spectrum()
        self._update_integration_overlays()

    # ------------------------------------------------------------------
    # Appearance controls
    # ------------------------------------------------------------------
    def _create_lut(self, cmap_name: str) -> Optional[np.ndarray]:
        try:
            cmap = cm.get_cmap(cmap_name, 512)
        except ValueError:
            cmap = cm.get_cmap("viridis", 512)
        lut = (cmap(np.linspace(0, 1, 512)) * 255).astype(np.uint8)
        return lut

    def _apply_lut(self) -> None:
        if self._lut is None:
            return
        self.im_map.setLookupTable(self._lut)
        if hasattr(self, "im_point"):
            self.im_point.setLookupTable(self._lut)

    def set_colormap(self, colormap: str) -> None:
        if not colormap:
            return
        self.colormap = colormap
        self._lut = self._create_lut(colormap)
        self._apply_lut()

    def set_color_limits(self, vmin: Optional[float], vmax: Optional[float]) -> None:
        if vmin is None or vmax is None:
            self._color_levels = None
        else:
            self._color_levels = (float(vmin), float(vmax))
        self._update_map_image()

    def set_integration_radius(self, radius: int) -> None:
        radius = max(0, int(radius))
        if radius == self.integration_radius:
            return
        self.integration_radius = radius
        self._update_cut_visuals(self.cursor_mgr.cut)

    # ------------------------------------------------------------------
    # State persistence helpers
    # ------------------------------------------------------------------
    def get_cursor_state(self) -> CursorState:
        return self.cursor_mgr.cursor

    def get_cut_state(self) -> CursorState:
        return self.cursor_mgr.cut

    def set_cursor_state(self, state: Optional[CursorState]) -> None:
        if state is None:
            return
        self.cursor_mgr.update_cursor(state.x_value, state.y_value)

    def set_cut_state(self, state: Optional[CursorState]) -> None:
        if state is None:
            return
        self.cursor_mgr.set_cut(state.x_value, state.y_value)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _lock_plot_range(self, plot, x_range, y_range) -> None:
        plot.setRange(xRange=x_range, yRange=y_range, padding=0)
        viewbox = plot.getViewBox()
        if viewbox is not None:
            viewbox.enableAutoRange(x=False, y=False)
            viewbox.setLimits(
                xMin=x_range[0],
                xMax=x_range[1],
                yMin=y_range[0],
                yMax=y_range[1],
            )
