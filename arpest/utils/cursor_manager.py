"""
Cursor management for interactive plots.

Handles cursor position, cut position, and update notifications using
an event-based system instead of flags.
"""

from __future__ import annotations

from typing import Callable, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class CursorState:
    """Immutable cursor state."""
    x_idx: int
    y_idx: int
    x_value: float
    y_value: float


class CursorManager:
    """Manages cursor and cut positions with event-based updates."""
    
    def __init__(self, x_values: np.ndarray, y_values: np.ndarray):
        self.x_values = x_values
        self.y_values = y_values
        
        # Initial positions (center)
        mid_x = len(x_values) // 2
        mid_y = len(y_values) // 2
        
        self._cursor = CursorState(
            x_idx=mid_x,
            y_idx=mid_y,
            x_value=x_values[mid_x],
            y_value=y_values[mid_y]
        )
        
        self._cut = CursorState(
            x_idx=mid_x,
            y_idx=mid_y,
            x_value=x_values[mid_x],
            y_value=y_values[mid_y]
        )
        
        # Event callbacks
        self._cursor_callbacks: list[Callable[[CursorState], None]] = []
        self._cut_callbacks: list[Callable[[CursorState], None]] = []
        
        # Drag state
        self.dragging = False
    
    @property
    def cursor(self) -> CursorState:
        """Current cursor position."""
        return self._cursor
    
    @property
    def cut(self) -> CursorState:
        """Current cut position."""
        return self._cut
    
    def on_cursor_change(self, callback: Callable[[CursorState], None]) -> None:
        """Register callback for cursor position changes."""
        self._cursor_callbacks.append(callback)
    
    def on_cut_change(self, callback: Callable[[CursorState], None]) -> None:
        """Register callback for cut position changes."""
        self._cut_callbacks.append(callback)
    
    def update_cursor(self, x: float, y: float) -> bool:
        """Update cursor position from data coordinates.
        
        Returns:
            True if position changed, False otherwise.
        """
        x_idx = np.searchsorted(self.x_values, x)
        x_idx = np.clip(x_idx, 0, len(self.x_values) - 1)
        
        y_idx = np.searchsorted(self.y_values, y)
        y_idx = np.clip(y_idx, 0, len(self.y_values) - 1)
        
        # Check if position actually changed
        if x_idx == self._cursor.x_idx and y_idx == self._cursor.y_idx:
            return False
        
        self._cursor = CursorState(
            x_idx=x_idx,
            y_idx=y_idx,
            x_value=self.x_values[x_idx],
            y_value=self.y_values[y_idx]
        )
        
        # Notify listeners
        for callback in self._cursor_callbacks:
            callback(self._cursor)
        
        # If dragging, also update cut
        if self.dragging:
            self._update_cut_from_cursor()
        
        return True
    
    def set_cut(self, x: float, y: float) -> bool:
        """Set cut position from data coordinates.
        
        Returns:
            True if position changed, False otherwise.
        """
        x_idx = np.searchsorted(self.x_values, x)
        x_idx = np.clip(x_idx, 0, len(self.x_values) - 1)
        
        y_idx = np.searchsorted(self.y_values, y)
        y_idx = np.clip(y_idx, 0, len(self.y_values) - 1)
        
        if x_idx == self._cut.x_idx and y_idx == self._cut.y_idx:
            return False
        
        self._cut = CursorState(
            x_idx=x_idx,
            y_idx=y_idx,
            x_value=self.x_values[x_idx],
            y_value=self.y_values[y_idx]
        )
        
        # Notify listeners
        for callback in self._cut_callbacks:
            callback(self._cut)
        
        return True
    
    def _update_cut_from_cursor(self) -> None:
        """Update cut to match cursor position."""
        if (self._cut.x_idx == self._cursor.x_idx and 
            self._cut.y_idx == self._cursor.y_idx):
            return
        
        self._cut = CursorState(
            x_idx=self._cursor.x_idx,
            y_idx=self._cursor.y_idx,
            x_value=self._cursor.x_value,
            y_value=self._cursor.y_value
        )
        
        # Notify listeners
        for callback in self._cut_callbacks:
            callback(self._cut)
    
    def start_drag(self) -> None:
        """Start drag operation."""
        self.dragging = True
    
    def end_drag(self) -> None:
        """End drag operation."""
        self.dragging = False
    
    def update_axes(self, x_values: np.ndarray, y_values: np.ndarray) -> None:
        """Update coordinate arrays (when data changes)."""
        self.x_values = x_values
        self.y_values = y_values
        
        # Recompute values for current indices
        self._cursor = CursorState(
            x_idx=self._cursor.x_idx,
            y_idx=self._cursor.y_idx,
            x_value=x_values[self._cursor.x_idx],
            y_value=y_values[self._cursor.y_idx]
        )
        
        self._cut = CursorState(
            x_idx=self._cut.x_idx,
            y_idx=self._cut.y_idx,
            x_value=x_values[self._cut.x_idx],
            y_value=y_values[self._cut.y_idx]
        )

    def _nearest_index(self, values: np.ndarray, target: float) -> int:
        """Return index of the closest entry in a 1D array."""
        if values.size == 0:
            return 0
        diffs = np.abs(values - target)
        # np.nanargmin gracefully skips NaNs if present
        idx = int(np.nanargmin(diffs))
        return max(0, min(idx, values.size - 1))
