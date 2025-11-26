"""UI widgets for basic dataset operations."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .base import OperationWidget
from ....models import Dataset
from ....operations.basic import normalize_dataset, scale_dataset


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
        result = normalize_dataset(dataset)
        return result, "normalized"


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
        result = scale_dataset(dataset, factor)
        return result, f"scaled x{factor:.2f}"
