"""Reusable analysis canvas for 1D/2D/3D visualizations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QFrame

from ..models import Dataset, FileStack
from .figure_2d import Figure2D
from .figure_3d import Figure3D


@dataclass
class CurveDisplayData:
    """Simple container describing a 1D curve to plot."""

    axis_values: np.ndarray
    intensity: np.ndarray
    label: str
    axis_label: str
    color: str = "#1f77b4"
    intensity_label: str = "Intensity"
    style: str = "solid"
    width: int = 2


class AnalysisCanvas(QWidget):
    """Hosts either a dataset figure or an overplotted set of curves."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._frame = QFrame()
        self._frame_layout = QVBoxLayout()
        self._frame_layout.setContentsMargins(0, 0, 0, 0)
        self._frame.setLayout(self._frame_layout)
        layout.addWidget(self._frame)

        self._placeholder = QLabel("No analysis data yet.")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._frame_layout.addWidget(self._placeholder)

        self._current_widget: QWidget | None = None
        self._curve_widget: pg.PlotWidget | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def clear(self, message: str | None = None) -> None:
        """Remove the current visualization and show the placeholder."""
        self._dispose_current_widget()
        if message:
            self._placeholder.setText(message)
        self._placeholder.show()

    def display_dataset(
        self,
        dataset: Dataset,
        *,
        colormap: str = "arpest",
        integration_radius: int = 0,
    ) -> None:
        """
        Display a dataset using the existing Figure2D/Figure3D widgets.
        """
        copied = dataset.copy()
        stack = FileStack(filename=copied.filename or "analysis", raw_data=copied)

        figure: QWidget
        if copied.is_2d:
            figure = Figure2D(stack, colormap=colormap, integration_radius=integration_radius)
        else:
            figure = Figure3D(stack, colormap=colormap, integration_radius=integration_radius)

        self._set_canvas_widget(figure)

    def display_curves(self, curves: Sequence[CurveDisplayData]) -> None:
        """Render a set of 1D curves on the canvas."""
        if not curves:
            self.clear("No curves captured yet.")
            return

        plot = pg.PlotWidget()
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.setLabel("left", curves[0].intensity_label or "Intensity")
        plot.setLabel("bottom", curves[0].axis_label or "Axis")
        plot.addLegend(offset=(10, 10))
        plot.setBackground("w")
        plot.getAxis("bottom").setPen(pg.mkPen("#000000"))
        plot.getAxis("left").setPen(pg.mkPen("#000000"))

        for curve in curves:
            x = np.asarray(curve.axis_values, dtype=float)
            y = np.asarray(curve.intensity, dtype=float)
            if x.size == 0 or y.size == 0 or x.size != y.size:
                continue
            if curve.style == "dash":
                pen_style = Qt.DashLine
            elif curve.style == "dot":
                pen_style = Qt.DotLine
            else:
                pen_style = Qt.SolidLine
            pen = pg.mkPen(curve.color or "#1f77b4", width=curve.width or 2, style=pen_style)
            plot.plot(x, y, pen=pen, name=curve.label)

        self._set_canvas_widget(plot)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _set_canvas_widget(self, widget: QWidget) -> None:
        self._dispose_current_widget()
        self._placeholder.hide()
        self._frame_layout.addWidget(widget)
        self._current_widget = widget

    def _dispose_current_widget(self) -> None:
        if self._current_widget is not None:
            self._frame_layout.removeWidget(self._current_widget)
            self._current_widget.setParent(None)
            self._current_widget.deleteLater()
            self._current_widget = None
