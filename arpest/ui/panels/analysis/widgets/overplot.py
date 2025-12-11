"""Overplot module for visualizing captured EDC/MDC curves."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from .....visualization.analysis_canvas import CurveDisplayData
from ..history import CurveCaptureEntry
from .base import AnalysisModule, AnalysisModuleContext


@dataclass
class _CurveEntry:
    capture: CurveCaptureEntry
    color: str

    @property
    def label(self) -> str:
        return f"{self.capture.dataset_label} – {self.capture.label}"


class OverplotModule(AnalysisModule):
    """Overlay captured EDC/MDC curves sourced from the shared history."""

    _color_palette = [
        "#1f77b4",
        "#d62728",
        "#2ca02c",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    title = "Overplot"

    def __init__(self, context: AnalysisModuleContext, parent: Optional["QWidget"] = None) -> None:
        super().__init__(context, parent)
        self.canvas = context.canvas
        self.capture_history = context.capture_history
        self._curves: list[_CurveEntry] = []
        self._color_index = 0
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        instructions = QLabel(
            "Select captured curves from the history below and plot them directly on the analysis canvas."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        history_label = QLabel("Captured curves:")
        layout.addWidget(history_label)

        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.history_list)

        action_row = QHBoxLayout()
        self.plot_selection_btn = QPushButton("Plot selection")
        self.plot_selection_btn.clicked.connect(self._plot_selected_from_history)
        self.clear_btn = QPushButton("Clear plot")
        self.clear_btn.clicked.connect(self._clear_curves)

        action_row.addWidget(self.plot_selection_btn)
        action_row.addStretch()
        action_row.addWidget(self.clear_btn)
        layout.addLayout(action_row)

        self.setLayout(layout)

        self.capture_history.entries_changed.connect(self._refresh_history_list)
        self.history_list.itemSelectionChanged.connect(self._plot_selected_from_history)
        self._refresh_history_list()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def _plot_selected_from_history(self) -> None:
        items = self.history_list.selectedItems()
        if not items:
            return
        self._curves.clear()
        self._color_index = 0
        for item in items:
            entry_id = item.data(Qt.UserRole)
            entry = self.capture_history.get_entry(entry_id)
            if not isinstance(entry, CurveCaptureEntry):
                continue
            self._curves.append(_CurveEntry(capture=entry, color=self._next_color()))

        if self._curves:
            self._update_canvas()
        else:
            self.canvas.clear("Select captured curves to display.")

    def _clear_curves(self) -> None:
        self._curves.clear()
        self._color_index = 0
        self.canvas.clear("No curves captured yet.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _refresh_history_list(self) -> None:
        self.history_list.clear()
        for entry in self.capture_history.curve_entries():
            label = f"{entry.dataset_label} – {entry.label}"
            item = QListWidgetItem(label)
            item.setToolTip(label)
            item.setData(Qt.UserRole, entry.id)
            self.history_list.addItem(item)

    def _update_canvas(self) -> None:
        if not self._curves:
            self.canvas.clear("No curves captured yet.")
            return
        curve_data = [
            CurveDisplayData(
                axis_values=curve.capture.axis_values,
                intensity=curve.capture.intensity,
                label=curve.label,
                axis_label=f"{curve.capture.axis_name} ({curve.capture.axis_unit})"
                if curve.capture.axis_unit
                else curve.capture.axis_name,
                color=curve.color,
            )
            for curve in self._curves
        ]
        self.canvas.display_curves(curve_data)

    def _next_color(self) -> str:
        color = self._color_palette[self._color_index % len(self._color_palette)]
        self._color_index += 1
        return color
