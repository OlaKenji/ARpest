"""Overplot module for visualizing captured EDC/MDC curves."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .....models import Axis, Dataset, FileStack
from .....visualization.analysis_canvas import AnalysisCanvas, CurveDisplayData


@dataclass
class _CurveEntry:
    kind: str  # "EDC" or "MDC"
    axis: Axis
    intensity: np.ndarray
    dataset_label: str
    color: str

    @property
    def label(self) -> str:
        return f"{self.dataset_label} – {self.kind} ({self.axis.name})"


class OverplotModule(QWidget):
    """Simple module that overlays captured EDC/MDC curves."""

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

    def __init__(
        self,
        *,
        get_file_stack: Callable[[], FileStack | None],
        context_providers: dict[str, Callable[[], object]],
        canvas: AnalysisCanvas,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.context_providers = context_providers
        self.canvas = canvas
        self._curves: list[_CurveEntry] = []
        self._color_index = 0

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        instructions = QLabel(
            "Use the buttons below to capture the current EDC or MDC from the active dataset. "
            "Captured curves are overplotted on the analysis canvas for comparison."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        button_row = QHBoxLayout()
        self.add_edc_btn = QPushButton("Add current EDC")
        self.add_mdc_btn = QPushButton("Add current MDC")
        self.remove_btn = QPushButton("Remove selected")
        self.clear_btn = QPushButton("Clear all")

        self.add_edc_btn.clicked.connect(lambda: self._capture_curves("current_mdc_curves", "EDC"))
        self.add_mdc_btn.clicked.connect(lambda: self._capture_curves("current_edc_curves", "MDC"))
        self.remove_btn.clicked.connect(self._remove_selected)
        self.clear_btn.clicked.connect(self._clear_curves)

        button_row.addWidget(self.add_edc_btn)
        button_row.addWidget(self.add_mdc_btn)
        button_row.addStretch()
        button_row.addWidget(self.remove_btn)
        button_row.addWidget(self.clear_btn)
        layout.addLayout(button_row)

        self.curve_list = QListWidget()
        self.curve_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.curve_list, stretch=1)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def _capture_curves(self, context_key: str, kind: str) -> None:
        stack = self.get_file_stack()
        if stack is None:
            QMessageBox.warning(self, "No dataset", "Select a dataset before capturing curves.")
            return

        provider = self.context_providers.get(context_key)
        if provider is None:
            QMessageBox.warning(self, "Unavailable", "The current visualization does not provide this data.")
            return

        try:
            raw_curves = provider()
        except Exception:
            raw_curves = None
        if not raw_curves:
            QMessageBox.information(self, "Nothing to capture", "No curve data is available right now.")
            return

        dataset = stack.current_state
        added = False
        for axis_key, values in raw_curves.items():
            axis = self._axis_from_key(dataset, axis_key)
            if axis is None:
                continue
            curve = _CurveEntry(
                kind=kind,
                axis=axis,
                intensity=np.asarray(values, dtype=float),
                dataset_label=f"{stack.filename} [{stack.current_name}]",
                color=self._next_color(),
            )
            self._curves.append(curve)
            added = True

        if not added:
            QMessageBox.information(self, "Unsupported", "Could not determine axis information for the captured curve.")
            return

        self._refresh_list()
        self._update_canvas()

    def _remove_selected(self) -> None:
        selected_indexes = sorted(
            {self.curve_list.row(item) for item in self.curve_list.selectedItems()},
            reverse=True,
        )
        for idx in selected_indexes:
            if 0 <= idx < len(self._curves):
                self._curves.pop(idx)
        self._refresh_list()
        self._update_canvas()

    def _clear_curves(self) -> None:
        self._curves.clear()
        self._color_index = 0
        self._refresh_list()
        self.canvas.clear("No curves captured yet.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _refresh_list(self) -> None:
        self.curve_list.clear()
        for curve in self._curves:
            item = QListWidgetItem(curve.label)
            item.setToolTip(curve.label)
            self.curve_list.addItem(item)

    def _update_canvas(self) -> None:
        curve_data = [
            CurveDisplayData(
                axis_values=curve.axis.values,
                intensity=curve.intensity,
                label=curve.label,
                axis_label=f"{curve.axis.name} ({curve.axis.unit})",
                color=curve.color,
            )
            for curve in self._curves
        ]
        self.canvas.display_curves(curve_data)

    def _next_color(self) -> str:
        color = self._color_palette[self._color_index % len(self._color_palette)]
        self._color_index += 1
        return color

    def _axis_from_key(self, dataset: Dataset, key: str) -> Axis | None:
        key_lower = key.lower().split("_", 1)[0]
        if key_lower == "x":
            return dataset.x_axis
        if key_lower == "y":
            return dataset.y_axis
        if key_lower == "z":
            return dataset.z_axis
        if key_lower == "w":
            return dataset.w_axis
        return None
