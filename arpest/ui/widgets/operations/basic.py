"""UI widgets for basic dataset operations."""

from __future__ import annotations

import numpy as np
from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from .base import OperationWidget
from ....models import Dataset
from ....operations.basic import crop_dataset, modify_axes, normalize_dataset, scale_dataset


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

class ModifyAxesOperationWidget(OperationWidget):
    title = "Modify axes"
    category = "Arithmetic"
    description = "Add, subtarct, multipy or divide on axes"

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        desc = QLabel("Add, subtract, multiply or divide on both axes.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._multiplier_values = [0.0, 1.0, np.pi, 2 * np.pi]
        self._multiplier_labels = ["0", "1", "π", "2π"]
        self._axis_controls = {}

        layout.addLayout(self._build_axis_row("x"))
        layout.addLayout(self._build_axis_row("y"))

        buttons_row = QHBoxLayout()
        for op_name, text in [
            ("add", "Add"),
            ("subtract", "Sub"),
            ("multiply", "Mul"),
            ("divide", "Div"),
        ]:
            btn = QPushButton(text)
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda _, op=op_name: self._apply_operation_with(op))
            buttons_row.addWidget(btn)
        layout.addLayout(buttons_row)

        self.setLayout(layout)
        self.setMaximumWidth(320)
        self._pending_operation: str | None = None

    def _build_axis_row(self, axis: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)
        label = QLabel(f"{axis.upper()} axis:")
        label.setFixedWidth(60)
        input_spin = QDoubleSpinBox()
        input_spin.setDecimals(6)
        input_spin.setRange(-1e9, 1e9)
        input_spin.setSingleStep(0.1)
        input_spin.setFixedWidth(85)
        input_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        mult_label = QLabel("×")
        mult_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        mult_button = QPushButton("1")
        mult_button.setCheckable(False)
        mult_button.setFixedWidth(50)
        mult_button.clicked.connect(lambda _, a=axis: self._cycle_multiplier(a))

        self._axis_controls[axis] = {
            "spin": input_spin,
            "button": mult_button,
            "index": 1,
        }

        row.addWidget(label)
        row.addWidget(input_spin)
        row.addWidget(mult_label)
        row.addWidget(mult_button)
        return row

    def _cycle_multiplier(self, axis: str) -> None:
        control = self._axis_controls[axis]
        control["index"] = (control["index"] + 1) % len(self._multiplier_values)
        idx = control["index"]
        control["button"].setText(self._multiplier_labels[idx])

    def _apply_operation_with(self, operation: str) -> None:
        self._pending_operation = operation
        self._trigger_apply()

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        if not self._pending_operation:
            raise ValueError("No operation selected.")

        def compute_value(axis: str) -> float | None:
            control = self._axis_controls[axis]
            value = float(control["spin"].value())
            multiplier = self._multiplier_values[control["index"]]
            result = value * multiplier
            return result

        x_value = compute_value("x")
        y_value = compute_value("y")

        result = modify_axes(dataset, x_value, y_value, operation=self._pending_operation)
        return result, f"{self._pending_operation} axes"

class CropOperationWidget(OperationWidget):
    title = "Crop data"
    category = "General"
    description = "Crop the data"

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        desc = QLabel("Crop the data.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        range_min, range_max = -1e9, 1e9
        decimals = 3
        step = 0.1

        self.y_start_spin = QDoubleSpinBox()
        self.y_start_spin.setRange(range_min, range_max)
        self.y_start_spin.setDecimals(decimals)
        self.y_start_spin.setSingleStep(step)

        self.y_end_spin = QDoubleSpinBox()
        self.y_end_spin.setRange(range_min, range_max)
        self.y_end_spin.setDecimals(decimals)
        self.y_end_spin.setSingleStep(step)

        self.x_start_spin = QDoubleSpinBox()
        self.x_start_spin.setRange(range_min, range_max)
        self.x_start_spin.setDecimals(decimals)
        self.x_start_spin.setSingleStep(step)

        self.x_end_spin = QDoubleSpinBox()
        self.x_end_spin.setRange(range_min, range_max)
        self.x_end_spin.setDecimals(decimals)
        self.x_end_spin.setSingleStep(step)

        self.y_start_spin.setFixedWidth(70)
        self.y_end_spin.setFixedWidth(70)
        self.x_start_spin.setFixedWidth(70)
        self.x_end_spin.setFixedWidth(70)

        y_row = QHBoxLayout()
        y_label = QLabel("Y range:")
        y_label.setFixedWidth(60)
        y_row.addWidget(y_label)
        y_row.addWidget(self.y_start_spin)
        y_row.addWidget(QLabel("to"))
        y_row.addWidget(self.y_end_spin)
        layout.addLayout(y_row)

        x_row = QHBoxLayout()
        x_label = QLabel("X range:")
        x_label.setFixedWidth(60)
        x_row.addWidget(x_label)
        x_row.addWidget(self.x_start_spin)
        x_row.addWidget(QLabel("to"))
        x_row.addWidget(self.x_end_spin)
        layout.addLayout(x_row)

        populate_btn = QPushButton("Use Data Limits")
        populate_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        populate_btn.clicked.connect(self._populate_from_dataset)
        layout.addWidget(populate_btn)

        apply_btn = QPushButton("Apply Crop")
        apply_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        apply_btn.clicked.connect(self._trigger_apply)
        layout.addWidget(apply_btn)

        self.setLayout(layout)
        self.setMaximumWidth(320)
        self._populate_from_dataset()

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        y_start = float(self.y_start_spin.value())
        y_end = float(self.y_end_spin.value())
        x_start = float(self.x_start_spin.value())
        x_end = float(self.x_end_spin.value())
        result = crop_dataset(dataset, x_start, x_end, y_start, y_end)
        return result, f"cropped y[{y_start:.2f}, {y_end:.2f}] x[{x_start:.2f}, {x_end:.2f}]"

    def _populate_from_dataset(self) -> None:
        file_stack = self.get_file_stack()
        if file_stack is None:
            return

        dataset = file_stack.current_state
        y_vals = np.asarray(dataset.y_axis.values, dtype=float)
        x_vals = np.asarray(dataset.x_axis.values, dtype=float)
        self.y_start_spin.setValue(float(np.nanmin(y_vals)))
        self.y_end_spin.setValue(float(np.nanmax(y_vals)))
        self.x_start_spin.setValue(float(np.nanmin(x_vals)))
        self.x_end_spin.setValue(float(np.nanmax(x_vals)))
