"""UI widget for curvature-inspired operations (directional smoothing/derivative)."""

from __future__ import annotations

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from .base import OperationWidget
from ....models import Dataset
from ....operations.curvature import derivative, smooth, zhang_curvature


class CurvatureOperationWidget(OperationWidget):
    title = "Curvature operations"
    category = "Operate"
    description = "Smooth data, take a directional derivative, or compute Zhang curvature along a chosen axis."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        desc = QLabel(
            "Toggle the direction, then smooth the dataset, take its first derivative, or compute Zhang curvature along that axis."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._direction = "horizontal"
        self.direction_button = QPushButton(self._direction_label())
        self.direction_button.clicked.connect(self._toggle_direction)
        layout.addWidget(self.direction_button)

        window_row = QHBoxLayout()
        window_row.addWidget(QLabel("Window:"))
        self.window_spin = QSpinBox()
        self.window_spin.setRange(3, 51)
        self.window_spin.setSingleStep(2)
        self.window_spin.setValue(5)
        self.window_spin.setFixedWidth(70)
        window_row.addWidget(self.window_spin)
        window_row.addStretch()
        layout.addLayout(window_row)

        button_row = QHBoxLayout()
        button_specs = [
            ("Smooth", "smooth"),
            ("Derivative", "derivative"),
            ("Curvature", "curvature"),
        ]
        for label, op in button_specs:
            btn = QPushButton(label)
            btn.setFixedWidth(90)
            btn.clicked.connect(lambda _, action=op: self._apply_operation_with(action))
            button_row.addWidget(btn)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.setLayout(layout)
        self._pending_operation: str | None = None
        self.setMaximumWidth(360)

    def _direction_label(self) -> str:
        return f"Direction: {self._direction}"

    def _toggle_direction(self) -> None:
        self._direction = "vertical" if self._direction == "horizontal" else "horizontal"
        self.direction_button.setText(self._direction_label())

    def _apply_operation_with(self, operation: str) -> None:
        self._pending_operation = operation
        self._trigger_apply()

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        if dataset.intensity.ndim < 2:
            raise ValueError("Curvature operations require at least 2D datasets.")

        operation = self._pending_operation
        self._pending_operation = None
        if operation is None:
            raise ValueError("Select an operation to run.")

        window = int(self.window_spin.value())

        if operation == "smooth":
            result = smooth(dataset, direction=self._direction, window=window)
            label = f"smoothed {self._direction} [window size: {window}]"
        elif operation == "derivative":
            result = derivative(dataset, direction=self._direction, order=1)
            label = f"first derivative {self._direction}"
        elif operation == "curvature":
            result = zhang_curvature(dataset, direction=self._direction, smooth_window=window)
            label = f"Zhang curvature {self._direction} [window size: {window}]"
        else:
            raise ValueError("Unknown operation requested.")

        return result, label
