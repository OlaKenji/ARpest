from typing import Optional, Tuple
import pyqtgraph as pg
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


def _normalize_pen_color(color_value):
    """Convert any string shortcuts into QColor objects for pyqtgraph pens."""
    if color_value is None:
        return None
    if isinstance(color_value, str):
        shortcuts = {
            "r": "#ff0000",
            "g": "#00ff00",
            "b": "#0000ff",
            "k": "#000000",
            "w": "#ffffff",
            "y": "#ffff00",
            "m": "#ff00ff",
            "c": "#00ffff",
        }
        mapped = shortcuts.get(color_value.lower(), color_value)
        q_color = QColor(mapped)
        if q_color.isValid():
            return q_color
    return color_value


class PGLineCursor:
    """Simple infinite-line cursor with optional filled band for PyQtGraph."""

    def __init__(
        self,
        plot,
        *,
        orientation: str,
        locked_value: float,
        cursor_value: Optional[float] = None,
        solid_kwargs: Optional[dict] = None,
        dashed_kwargs: Optional[dict] = None,
        show_locked: bool = True,
        show_cursor: bool = True,
        show_band: bool = False,
        band_kwargs: Optional[dict] = None,
    ) -> None:
        if orientation not in {"vertical", "horizontal"}:
            raise ValueError("orientation must be 'vertical' or 'horizontal'")

        self.plot = plot
        self.orientation = orientation
        self.locked_value = float(locked_value)
        self.cursor_value = float(cursor_value if cursor_value is not None else locked_value)
        self.show_band = show_band
        self._band_region = (self.locked_value, self.locked_value)
        self.extent: Optional[Tuple[float, float]] = None

        solid_pen_opts = {"width": 1.5, "color": "#ff0000"}
        solid_pen_opts.update(solid_kwargs or {})
        solid_pen_opts["color"] = _normalize_pen_color(solid_pen_opts.get("color"))
        solid_pen = pg.mkPen(**solid_pen_opts)

        dashed_pen_opts = {"width": 1, "color": "#000000", "style": Qt.DashLine}
        dashed_pen_opts.update(dashed_kwargs or {})
        dashed_pen_opts["color"] = _normalize_pen_color(dashed_pen_opts.get("color"))
        dashed_pen = pg.mkPen(**dashed_pen_opts)
        angle = 90 if orientation == "vertical" else 0

        self.locked_line = None
        self.cursor_line = None
        self.band = None

        if show_locked:
            self.locked_line = pg.InfiniteLine(pos=self.locked_value, angle=angle, movable=False, pen=solid_pen)
            self.locked_line.setZValue(100)
            self.plot.addItem(self.locked_line)
        if show_cursor:
            self.cursor_line = pg.InfiniteLine(pos=self.cursor_value, angle=angle, movable=False, pen=dashed_pen)
            self.cursor_line.setZValue(100)
            self.plot.addItem(self.cursor_line)
        if self.show_band:
            orientation_flag = pg.LinearRegionItem.Vertical if orientation == "vertical" else pg.LinearRegionItem.Horizontal
            band_defaults = {"brush": pg.mkBrush(255, 0, 0, 40)}
            opts = {**band_defaults, **(band_kwargs or {})}
            self.band = pg.LinearRegionItem(values=self._band_region, orientation=orientation_flag, movable=False)
            if opts.get("brush") is not None:
                self.band.setBrush(opts["brush"])
            self.band.setZValue(50)
            self.plot.addItem(self.band)

    def set_locked(self, value: float) -> None:
        self.locked_value = float(value)
        if self.locked_line is not None:
            self.locked_line.setValue(self.locked_value)

    def set_cursor(self, value: float) -> None:
        self.cursor_value = float(value)
        if self.cursor_line is not None:
            self.cursor_line.setValue(self.cursor_value)

    def set_extent(self, extent) -> None:  # Compatibility stub (nothing to do for InfiniteLine)
        self.extent = tuple(extent)

    def set_band_region(self, lower: float, upper: float) -> None:
        if not self.show_band or self.band is None:
            return
        low, high = sorted((float(lower), float(upper)))
        self._band_region = (low, high)
        self.band.setRegion(self._band_region)