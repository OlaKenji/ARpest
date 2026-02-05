"""Reusable ROI overlay for PyQtGraph figures."""

from __future__ import annotations

from typing import Callable, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QEvent


class _EdgeOnlyRectROI(pg.RectROI):
    """RectROI that only responds to drags that start on the border/handles."""

    def __init__(self, *args, edge_fraction: float = 0.15, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._edge_fraction = edge_fraction
        self._dragging = False
        self._drag_mode: str | None = None
        self._drag_parent = None

    def _hit_handle(self, scene_pos) -> bool:
        for handle in getattr(self, "getHandles", lambda: [])():
            try:
                local = handle.mapFromScene(scene_pos)
                if handle.contains(local):
                    return True
            except Exception:
                continue
        return False

    def _hit_edge(self, scene_pos) -> bool:
        if self._hit_handle(scene_pos):
            return True
        try:
            local = self.mapFromScene(scene_pos)
        except Exception:
            return False
        size = self.size()
        width = float(size.x())
        height = float(size.y())
        if width <= 0 or height <= 0:
            return False
        x = float(local.x())
        y = float(local.y())
        tol_x = max(width * self._edge_fraction, 1e-6)
        tol_y = max(height * self._edge_fraction, 1e-6)
        inside_x = (-tol_x) <= x <= (width + tol_x)
        inside_y = (-tol_y) <= y <= (height + tol_y)
        if not (inside_x and inside_y):
            return False
        on_left = abs(x) <= tol_x
        on_right = abs(x - width) <= tol_x
        on_bottom = abs(y) <= tol_y
        on_top = abs(y - height) <= tol_y
        return on_left or on_right or on_bottom or on_top

    def _hit_border_only(self, scene_pos) -> bool:
        if self._hit_handle(scene_pos):
            return False
        return self._hit_edge(scene_pos)

    def mouseDragEvent(self, ev):  # type: ignore[override]
        if ev.isStart():
            if self._hit_handle(ev.scenePos()):
                self._drag_mode = "handle"
                self._dragging = True
                super().mouseDragEvent(ev)
                return
            if self._hit_border_only(ev.scenePos()):
                self._drag_mode = "move"
                self._dragging = True
                self._drag_parent = self.parentItem()
                ev.accept()
                return
            self._drag_mode = None
            ev.ignore()
            return
        if self._drag_mode == "move":
            parent = self._drag_parent or self.parentItem()
            if parent is not None:
                try:
                    p1 = parent.mapFromScene(ev.lastScenePos())
                    p2 = parent.mapFromScene(ev.scenePos())
                    delta = p2 - p1
                    self.setPos(self.pos() + delta)
                    ev.accept()
                except Exception:
                    ev.ignore()
            if ev.isFinish():
                self._dragging = False
                self._drag_mode = None
                self._drag_parent = None
            return
        if self._drag_mode == "handle":
            super().mouseDragEvent(ev)
            if ev.isFinish():
                self._dragging = False
                self._drag_mode = None
                self._drag_parent = None
            return
        if ev.isFinish():
            self._dragging = False
            self._drag_mode = None
            self._drag_parent = None
        super().mouseDragEvent(ev)

    def mouseClickEvent(self, ev):  # type: ignore[override]
        if not self._hit_edge(ev.scenePos()):
            ev.ignore()
            return
        super().mouseClickEvent(ev)

    def is_dragging(self) -> bool:
        return self._dragging


class RoiOverlay:
    """Rectangle ROI that can be attached to a PlotItem."""

    def __init__(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        *,
        color: str = "#ff8800",
        line_width: int = 2,
        line_style: Qt.PenStyle = Qt.DashLine,
    ) -> None:
        self._x_values = np.asarray(x_values, dtype=float)
        self._y_values = np.asarray(y_values, dtype=float)
        self._roi_item: Optional[pg.RectROI] = None
        self._enabled = False
        self._callbacks: list[Callable[[], None]] = []
        self._default_pos: Tuple[float, float] | None = None
        self._default_size: Tuple[float, float] | None = None
        self._pen = pg.mkPen(color, width=line_width, style=line_style)
        self._pending_drag = False

    def attach(self, plot_item: pg.PlotItem) -> None:
        x_min = float(np.nanmin(self._x_values))
        x_max = float(np.nanmax(self._x_values))
        y_min = float(np.nanmin(self._y_values))
        y_max = float(np.nanmax(self._y_values))
        x_low, x_high = min(x_min, x_max), max(x_min, x_max)
        y_low, y_high = min(y_min, y_max), max(y_min, y_max)
        width = max(abs(x_high - x_low) * 0.6, 1e-6)
        height = max(abs(y_high - y_low) * 0.6, 1e-6)
        pos = (x_low + (abs(x_high - x_low) - width) * 0.5, y_low + (abs(y_high - y_low) - height) * 0.5)
        size = (width, height)
        roi = _EdgeOnlyRectROI(pos, size, pen=self._pen)
        if hasattr(roi, "setHandleSize"):
            roi.setHandleSize(12)
        roi.setZValue(10)
        roi.setVisible(False)
        roi.sigRegionChanged.connect(self._on_roi_changed)
        plot_item.addItem(roi)
        self._roi_item = roi
        self._default_pos = (float(pos[0]), float(pos[1]))
        self._default_size = (float(size[0]), float(size[1]))

    def add_listener(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def _on_roi_changed(self) -> None:
        if not self._enabled:
            return
        self._notify()

    def _notify(self) -> None:
        for callback in list(self._callbacks):
            try:
                callback()
            except Exception:
                continue

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if self._roi_item is not None:
            self._roi_item.setVisible(self._enabled)
        self._notify()
        if not self._enabled:
            self._pending_drag = False

    def is_enabled(self) -> bool:
        return self._enabled

    def reset(self) -> None:
        if self._roi_item is None or self._default_pos is None or self._default_size is None:
            return
        self._roi_item.setPos(*self._default_pos)
        self._roi_item.setSize(self._default_size)
        self.set_enabled(True)

    def clear(self) -> None:
        self.set_enabled(False)

    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        if not self._enabled or self._roi_item is None:
            return None
        pos = self._roi_item.pos()
        size = self._roi_item.size()
        x_min = float(pos.x())
        y_min = float(pos.y())
        x_max = x_min + float(size.x())
        y_max = y_min + float(size.y())
        if x_min > x_max:
            x_min, x_max = x_max, x_min
        if y_min > y_max:
            y_min, y_max = y_max, y_min
        return (x_min, x_max, y_min, y_max)

    def set_bounds(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        *,
        enabled: bool = True,
    ) -> None:
        if self._roi_item is None:
            return
        self._roi_item.setPos(min(x_min, x_max), min(y_min, y_max))
        self._roi_item.setSize((abs(x_max - x_min), abs(y_max - y_min)))
        self.set_enabled(enabled)

    def axis_masks(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        bounds = self.get_bounds()
        if bounds is None:
            return None
        x_min, x_max, y_min, y_max = bounds
        x_low, x_high = min(x_min, x_max), max(x_min, x_max)
        y_low, y_high = min(y_min, y_max), max(y_min, y_max)
        x_mask = (self._x_values >= x_low) & (self._x_values <= x_high)
        y_mask = (self._y_values >= y_low) & (self._y_values <= y_high)
        return x_mask, y_mask

    def hit_test(self, scene_pos) -> bool:
        if not self._enabled or self._roi_item is None:
            return False
        hit_edge = getattr(self._roi_item, "_hit_edge", None)
        if callable(hit_edge):
            return bool(hit_edge(scene_pos))
        return False

    def should_capture_event(self, scene_pos, event) -> bool:
        if not self._enabled or self._roi_item is None:
            return False
        etype = event.type()
        if etype == QEvent.MouseButtonPress:
            if event.button() != Qt.LeftButton:
                return False
            hit = self.hit_test(scene_pos)
            self._pending_drag = bool(hit)
            return bool(hit)
        dragging = getattr(self._roi_item, "is_dragging", None)
        if callable(dragging) and dragging():
            if etype in (QEvent.MouseMove, QEvent.MouseButtonRelease):
                return True
        if self._pending_drag and etype in (QEvent.MouseMove, QEvent.MouseButtonRelease):
            if etype == QEvent.MouseButtonRelease:
                self._pending_drag = False
            return True
        return False
