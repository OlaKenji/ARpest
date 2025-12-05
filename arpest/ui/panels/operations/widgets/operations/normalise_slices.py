"""Widget for the per-slice normalisation operation."""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout

from .base import OperationWidget
from ......models import Dataset
from ......operations.normalise_slices import normalise_slices


class NormaliseSlicesOperationWidget(OperationWidget):
    title = "Normalise scan slices"
    category = "Operate"
    description = "Normalise each slice of a 3D dataset along the scan axis."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        desc = QLabel(
            "Normalise the intensity of every slice along the scan axis"
            " so their integrated intensity matches."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        apply_btn = QPushButton("Normalise slices")
        apply_btn.clicked.connect(self._trigger_apply)
        layout.addWidget(apply_btn)
        self.setLayout(layout)

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        result = normalise_slices(dataset)
        return result, "normalised slices"
