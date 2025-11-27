"""
Shared helpers for managing cursor overlays and drag state in visualization figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Optional, Sequence

from matplotlib.patches import Rectangle


class DragMode(Enum):
    """Which region of a figure is currently being dragged."""
    NONE = auto()
    FERMI = auto()
    CUT_Y = auto()
    CUT_X = auto()
    ENERGY = auto()


@dataclass
class DragState:
    """Shared drag state tracking the active mode and anchor coordinates."""
    mode: DragMode = DragMode.NONE
    anchor_x: Optional[float] = None
    anchor_y: Optional[float] = None

    def start(
        self,
        mode: DragMode,
        *,
        anchor_x: Optional[float] = None,
        anchor_y: Optional[float] = None,
    ) -> None:
        self.mode = mode
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y

    def stop(self) -> None:
        self.mode = DragMode.NONE
        self.anchor_x = None
        self.anchor_y = None

    def is_mode(self, mode: DragMode) -> bool:
        return self.mode is mode


class LineCursor:
    """Utility pairing solid (locked) and dashed (hover) cursor lines on an axis."""

    def __init__(
        self,
        axis,
        *,
        orientation: str,
        extent: Sequence[float],
        locked_value: float,
        cursor_value: Optional[float] = None,
        solid_kwargs: Optional[Dict] = None,
        dashed_kwargs: Optional[Dict] = None,
        show_locked: bool = True,
        show_cursor: bool = True,
        show_band: bool = False,
        band_kwargs: Optional[Dict] = None,
    ) -> None:
        if orientation not in {"vertical", "horizontal"}:
            raise ValueError("orientation must be 'vertical' or 'horizontal'")

        self.axis = axis
        self.orientation = orientation
        self.extent = tuple(extent)
        self.locked_value = locked_value
        self.cursor_value = locked_value if cursor_value is None else cursor_value
        self.show_locked = show_locked
        self.show_cursor = show_cursor

        solid_defaults = {"color": "red", "linestyle": "-", "linewidth": 1.5, "alpha": 0.9}
        dashed_defaults = {"color": "gray", "linestyle": "--", "linewidth": 1, "alpha": 0.8}
        solid_kwargs = {**solid_defaults, **(solid_kwargs or {})}
        dashed_kwargs = {**dashed_defaults, **(dashed_kwargs or {})}

        locked_data = self._data_for_value(self.locked_value)
        cursor_data = self._data_for_value(self.cursor_value)

        self.solid = None
        self.dashed = None
        self.band = None
        self.band_region = (self.locked_value, self.locked_value)
        self.show_band = show_band
        self._band_kwargs = band_kwargs or {"color": "red", "alpha": 0.15, "zorder": 1.0}

        if show_locked:
            (self.solid,) = axis.plot(*locked_data, **solid_kwargs)
        if show_cursor:
            (self.dashed,) = axis.plot(*cursor_data, **dashed_kwargs)
        if self.show_band:
            self._create_band()

    def _data_for_value(self, value: float):
        if self.orientation == "vertical":
            return ([value, value], list(self.extent))
        return (list(self.extent), [value, value])

    def _extent_bounds(self) -> tuple[float, float]:
        return (min(self.extent), max(self.extent))

    def _create_band(self) -> None:
        extent_min, extent_max = self._extent_bounds()
        if self.orientation == "vertical":
            height = extent_max - extent_min
            self.band = Rectangle(
                (self.locked_value, extent_min),
                0.0,
                height,
                **self._band_kwargs,
            )
        else:
            width = extent_max - extent_min
            self.band = Rectangle(
                (extent_min, self.locked_value),
                width,
                0.0,
                **self._band_kwargs,
            )
        self.axis.add_patch(self.band)

    def _position_band(self) -> None:
        if self.band is None:
            return
        low, high = self.band_region
        extent_min, extent_max = self._extent_bounds()
        if self.orientation == "vertical":
            self.band.set_x(low)
            self.band.set_width(max(high - low, 0.0))
            self.band.set_y(extent_min)
            self.band.set_height(extent_max - extent_min)
        else:
            self.band.set_x(extent_min)
            self.band.set_width(extent_max - extent_min)
            self.band.set_y(low)
            self.band.set_height(max(high - low, 0.0))

    def _set_line_position(self, line, value: float, extent=None) -> None:
        if line is None:
            return
        if extent is None:
            extent = self.extent
        if self.orientation == "vertical":
            line.set_xdata([value, value])
            line.set_ydata(extent)
        else:
            line.set_xdata(extent)
            line.set_ydata([value, value])

    def set_locked(self, value: float) -> None:
        self.locked_value = value
        self._set_line_position(self.solid, value)

    def set_cursor(self, value: float) -> None:
        self.cursor_value = value
        self._set_line_position(self.dashed, value)

    def set_extent(self, extent: Sequence[float]) -> None:
        self.extent = tuple(extent)
        self._set_line_position(self.solid, self.locked_value, self.extent)
        self._set_line_position(self.dashed, self.cursor_value, self.extent)
        if self.show_band:
            self._position_band()

    def set_band_region(self, lower: float, upper: float) -> None:
        """Set the span (in axis units) covered by the solid cursor."""
        if not self.show_band:
            return
        low, high = sorted((float(lower), float(upper)))
        self.band_region = (low, high)
        self._position_band()

    def artists(self):
        artists = []
        if self.band is not None:
            artists.append(self.band)
        artists.extend(line for line in (self.solid, self.dashed) if line is not None)
        return artists
