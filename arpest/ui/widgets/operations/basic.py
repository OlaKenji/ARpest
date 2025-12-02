"""UI widgets for basic dataset operations."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from PyQt5.QtWidgets import (
    QFileDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from .base import OperationWidget
from ....core.loaders import BaseLoader
from ....models import Dataset
from ....operations.basic import crop_dataset, modify_axes, normalize_dataset, scale_dataset, modify_intensity
from ....utils.session import SESSION_FILE_EXTENSION, load_session
from ....operations.basic import crop_dataset, modify_axes, normalize_dataset, scale_dataset, modify_intensity


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
    category = "General"
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

class ModifyByDataOperationWidget(OperationWidget):
    title = "Modify data"
    category = "Operate"
    description = "Combine dataset intensity with a reference dataset using an arithmetic operation."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        desc = QLabel("Combine dataset intensity with a reference dataset using an arithmetic operation.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.reference_path_label = QLabel("No reference dataset loaded.")
        self.reference_path_label.setWordWrap(True)
        layout.addWidget(self.reference_path_label)

        self.reference_meta_label = QLabel("")
        self.reference_meta_label.setWordWrap(True)
        layout.addWidget(self.reference_meta_label)

        load_btn = QPushButton("Load reference data…")
        load_btn.clicked.connect(self._on_load_reference_clicked)
        layout.addWidget(load_btn)

        buttons_row = QHBoxLayout()
        self._operation_buttons: list[QPushButton] = []
        for op_name, text in [
            ("add", "Add"),
            ("subtract", "Sub"),
            ("multiply", "Mul"),
            ("divide", "Div"),
        ]:
            btn = QPushButton(text)
            btn.setEnabled(False)
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda _, op=op_name: self._apply_operation_with(op))
            buttons_row.addWidget(btn)
            self._operation_buttons.append(btn)
        layout.addLayout(buttons_row)

        layout.addStretch()
        self.setLayout(layout)

        self._reference_dataset: Dataset | None = None
        self._reference_path: Path | None = None
        self._last_reference_dir: Path | None = None
        self._pending_operation: str | None = None

    def _set_operation_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._operation_buttons:
            btn.setEnabled(enabled)

    def _on_load_reference_clicked(self) -> None:
        loaders = self._available_loaders()
        if not loaders:
            self.reference_meta_label.setText(
                f"No raw data loaders available; only saved datasets (*{SESSION_FILE_EXTENSION}) can be loaded."
            )

        start_dir = self._start_path()
        if self._last_reference_dir is not None:
            start_dir = str(self._last_reference_dir)

        filter_entries: list[str] = []
        all_exts: list[str] = []
        for loader in loaders:
            if not loader.extensions:
                continue
            patterns = " ".join(f"*{ext}" for ext in loader.extensions)
            filter_entries.append(f"{loader.name} ({patterns})")
            all_exts.extend(loader.extensions)

        all_exts.append(SESSION_FILE_EXTENSION)
        unique_patterns = " ".join(sorted({f"*{ext}" for ext in all_exts}))
        filter_entries.insert(0, f"All supported ({unique_patterns})")
        filter_entries.insert(1, f"Saved datasets (*{SESSION_FILE_EXTENSION})")
        filter_entries.append("All files (*.*)")

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select reference dataset",
            start_dir,
            ";;".join(filter_entries),
        )
        if not filename:
            return

        path = Path(filename)
        try:
            dataset = self._load_reference_dataset(path, loaders)
        except ValueError as exc:
            self.reference_path_label.setText("Failed to load reference dataset.")
            self.reference_meta_label.setText(str(exc))
            self._reference_dataset = None
            self._reference_path = None
            self._set_operation_buttons_enabled(False)
            return

        self._reference_dataset = dataset
        self._reference_path = path
        self._last_reference_dir = path.parent
        self.reference_path_label.setText(f"Reference: {path.name}")
        self.reference_meta_label.setText(f"{dataset.ndim}D dataset with grid {dataset.shape}")
        self._set_operation_buttons_enabled(True)

    def _apply_operation_with(self, operation: str) -> None:
        self._pending_operation = operation
        self._trigger_apply()

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        if self._reference_dataset is None:
            raise ValueError("Load a reference dataset before applying an operation.")

        operation = self._pending_operation
        self._pending_operation = None
        if operation is None:
            raise ValueError("Select an operation to apply.")

        result = modify_intensity(dataset, self._reference_dataset, operation)
        verb = {
            "add": "added reference intensity",
            "subtract": "subtracted reference intensity",
            "multiply": "multiplied by reference intensity",
            "divide": "divided by reference intensity",
        }.get(operation, "modified by reference")
        return result, verb

    def _available_loaders(self) -> list[BaseLoader]:
        loaders = self._get_context_value("available_loaders")
        if isinstance(loaders, list):
            return loaders
        return []

    def _start_path(self) -> str:
        path = self._get_context_value("start_path")
        if isinstance(path, (str, Path)):
            return str(path)
        return str(Path.home())

    def _load_reference_dataset(self, path: Path, loaders: Iterable[BaseLoader]) -> Dataset:
        if path.suffix == SESSION_FILE_EXTENSION:
            return self._load_session_reference(path)

        for loader in loaders:
            try:
                if loader.can_load(path):
                    return loader.load(path)
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError(f"Failed to load {path.name} with {loader.name}: {exc}") from exc
        raise ValueError(f"No loader available for {path.name}")

    def _load_session_reference(self, path: Path) -> Dataset:
        try:
            session = load_session(path)
        except Exception as exc:
            raise ValueError(f"Could not read {path.name}: {exc}") from exc

        if not session.tabs:
            raise ValueError("Session does not contain any datasets.")

        tab_state = session.tabs[0]
        if not tab_state.file_stacks:
            raise ValueError("Session does not contain any file stacks.")

        stack_index = max(0, min(tab_state.current_index, len(tab_state.file_stacks) - 1))
        file_stack = tab_state.file_stacks[stack_index]
        if not file_stack.states:
            dataset = file_stack.raw_data
        else:
            state_index = max(0, min(file_stack.current_index, len(file_stack.states) - 1))
            dataset = file_stack.states[state_index]

        return dataset
