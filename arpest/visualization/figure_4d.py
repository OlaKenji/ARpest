"""
High-performance 4D visualization based on PyQtGraph.

"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from matplotlib import cm
from PyQt5.QtCore import QObject, QEvent, Qt, QPointF, QRectF
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from ..models import Dataset, FileStack
from ..utils.cursor.cursor_manager import CursorManager, CursorState
from ..utils.cursor.cursor_helpers import DragMode, DragState
from ..utils.cursor.pg_line_cursor import PGLineCursor

class Figure4D(QWidget):
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

        self.view = pg.GraphicsLayoutWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self._setup_plots()
        self._plot_band_and_curves()

        self.cursor_mgr.on_cursor_change(self._on_cursor_changed)
        self.cursor_mgr.on_cut_change(self._on_cut_changed)

        self._event_filter = _GraphicsViewEventFilter(self)
        self.view.viewport().installEventFilter(self._event_filter)
        self.view.viewport().setMouseTracking(True)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _setup_plots(self) -> None:
        pass

  