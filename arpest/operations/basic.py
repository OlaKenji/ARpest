"""Basic data operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
)

from ..models import Dataset, AxisType
from ..utils.cursor_manager import CursorState
from .base import OperationWidget

class NormalizeOperationWidget(OperationWidget):
    title = "Normalize Intensity"
    category = "General"
    description = "Scale intensity so the maximum absolute value becomes 1."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Normalize dataset to unit maximum intensity."))
        apply_btn = QPushButton("Normalize")
        apply_btn.clicked.connect(self._trigger_apply)
        layout.addWidget(apply_btn)
        self.setLayout(layout)

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        new_dataset = dataset.copy()
        max_val = np.nanmax(np.abs(new_dataset.intensity))
        if max_val == 0 or np.isnan(max_val):
            raise ValueError("Cannot normalize: dataset has zero or undefined intensity.")
        new_dataset.intensity = new_dataset.intensity / max_val
        return new_dataset, "normalized"

class ScaleOperationWidget(OperationWidget):
    title = "Scale Intensity"
    category = "Arithmetic"
    description = "Multiply intensity by a chosen factor."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        desc = QLabel("Multiply intensity by the selected factor.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        row = QHBoxLayout()
        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(0.01, 1000.0)
        self.factor_spin.setSingleStep(0.1)
        self.factor_spin.setValue(1.0)
        row.addWidget(QLabel("Factor:"))
        row.addWidget(self.factor_spin)
        layout.addLayout(row)

        apply_btn = QPushButton("Apply Scale")
        apply_btn.clicked.connect(self._trigger_apply)
        layout.addWidget(apply_btn)
        self.setLayout(layout)

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        factor = float(self.factor_spin.value())
        new_dataset = dataset.copy()
        new_dataset.intensity = new_dataset.intensity * factor
        return new_dataset, f"scaled x{factor:.2f}"

