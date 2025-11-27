"""UI widget for k-space conversion."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ....models import AxisType, Dataset
from ....operations.k_space import (
    KSpaceConversionContext,
    KSpaceConversionMode,
    convert_dataset,
    determine_mode,
)
from ....utils.cursor.cursor_manager import CursorState
from .base import OperationWidget


class KSpaceOperationWidget(OperationWidget):
    title = "Convert to k-space"
    category = "KSpace"
    description = "Convert to k space, with cursor position assumed as Gamma."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.dataset_info_label = QLabel("No dataset selected.")
        self.dataset_info_label.setWordWrap(True)
        layout.addWidget(self.dataset_info_label)

        params_group = QGroupBox("Conversion Parameters")
        params_form = QFormLayout()

        self.photon_energy_spin = QDoubleSpinBox()
        self.photon_energy_spin.setRange(0.0, 5000.0)
        self.photon_energy_spin.setDecimals(3)
        self.photon_energy_spin.setSuffix(" eV")
        self.photon_energy_spin.setValue(0.0)
        params_form.addRow("Photon energy:", self.photon_energy_spin)

        self.work_function_spin = QDoubleSpinBox()
        self.work_function_spin.setRange(0.0, 10.0)
        self.work_function_spin.setDecimals(3)
        self.work_function_spin.setSuffix(" eV")
        self.work_function_spin.setValue(4.5)
        params_form.addRow("Work function:", self.work_function_spin)

        self.inner_potential_spin = QDoubleSpinBox()
        self.inner_potential_spin.setRange(0.0, 100.0)
        self.inner_potential_spin.setDecimals(3)
        self.inner_potential_spin.setSuffix(" eV")
        self.inner_potential_spin.setValue(12.0)
        params_form.addRow("Inner potential:", self.inner_potential_spin)

        self.angle_offset_x_spin = QDoubleSpinBox()
        self.angle_offset_x_spin.setRange(-90.0, 90.0)
        self.angle_offset_x_spin.setDecimals(3)
        self.angle_offset_x_spin.setSuffix(" deg")
        self.angle_offset_x_spin.setValue(0.0)
        params_form.addRow("Angle offset (X):", self.angle_offset_x_spin)

        self.angle_offset_y_spin = QDoubleSpinBox()
        self.angle_offset_y_spin.setRange(-90.0, 90.0)
        self.angle_offset_y_spin.setDecimals(3)
        self.angle_offset_y_spin.setSuffix(" deg")
        self.angle_offset_y_spin.setValue(0.0)
        params_form.addRow("Angle offset (Y):", self.angle_offset_y_spin)

        params_group.setLayout(params_form)
        layout.addWidget(params_group)

        self.mode_hint_label = QLabel("Mode: waiting for dataset.")
        self.mode_hint_label.setWordWrap(True)
        layout.addWidget(self.mode_hint_label)

        button_row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh from dataset")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        button_row.addWidget(self.refresh_btn)
        button_row.addStretch()
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        button_row.addWidget(self.convert_btn)
        layout.addLayout(button_row)

        layout.addStretch()
        self.setLayout(layout)
        self._last_dataset_id: int | None = None
        self._init_from_current_dataset()

    def _init_from_current_dataset(self) -> None:
        file_stack = self.get_file_stack()
        if file_stack is None:
            return
        dataset = file_stack.current_state
        self._update_dataset_summary(dataset, sync_parameters=True)

    def _on_refresh_clicked(self) -> None:
        file_stack = self.get_file_stack()
        if file_stack is None:
            self.dataset_info_label.setText("No dataset selected.")
            self.mode_hint_label.setText("Mode: unavailable.")
            return
        self._update_dataset_summary(file_stack.current_state, sync_parameters=True)

    def _on_convert_clicked(self) -> None:
        file_stack = self.get_file_stack()
        if file_stack is not None:
            self._update_dataset_summary(file_stack.current_state, sync_parameters=False)
        self._trigger_apply()

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        if dataset is None:
            raise ValueError("No dataset available for conversion.")

        if self._last_dataset_id != id(dataset):
            self._update_dataset_summary(dataset, sync_parameters=True)

        context = self._build_context(dataset)
        return convert_dataset(dataset, context)

    def _update_dataset_summary(self, dataset: Dataset, sync_parameters: bool) -> None:
        if dataset is None:
            self.dataset_info_label.setText("No dataset selected.")
            self.mode_hint_label.setText("Mode: unavailable.")
            self._last_dataset_id = None
            return

        mode = determine_mode(dataset)
        axis_lines = [
            f"X-axis: {dataset.x_axis.name} ({dataset.x_axis.unit})",
            f"Y-axis: {dataset.y_axis.name} ({dataset.y_axis.unit})",
        ]
        if dataset.z_axis is not None:
            axis_lines.append(f"Z-axis: {dataset.z_axis.name} ({dataset.z_axis.unit})")
        if dataset.w_axis is not None:
            axis_lines.append(f"W-axis: {dataset.w_axis.name} ({dataset.w_axis.unit})")

        self.dataset_info_label.setText("\n".join(axis_lines))
        self.mode_hint_label.setText(f"Mode: {mode.describe()}")

        hv_default = self._default_photon_energy(dataset, mode)
        angle_x_default, angle_y_default = self._default_angle_offsets(dataset)

        if sync_parameters:
            if hv_default is not None:
                self.photon_energy_spin.setValue(hv_default)
            if dataset.measurement.work_function is not None:
                self.work_function_spin.setValue(dataset.measurement.work_function)
            if angle_x_default is not None:
                self.angle_offset_x_spin.setValue(angle_x_default)
            if angle_y_default is not None:
                self.angle_offset_y_spin.setValue(angle_y_default)
        self._last_dataset_id = id(dataset)

    def _build_context(self, dataset: Dataset) -> KSpaceConversionContext:
        mode = determine_mode(dataset)
        return KSpaceConversionContext(
            mode=mode,
            photon_energy=self.photon_energy_spin.value() or dataset.measurement.photon_energy,
            work_function=self.work_function_spin.value(),
            inner_potential=self.inner_potential_spin.value(),
            angle_offset_x=self.angle_offset_x_spin.value(),
            angle_offset_y=self.angle_offset_y_spin.value(),
        )

    def _default_photon_energy(
        self, dataset: Dataset, mode: KSpaceConversionMode
    ) -> float | None:
        measurement_hv = dataset.measurement.photon_energy
        if mode is not KSpaceConversionMode.PHOTON_SCAN:
            return measurement_hv

        context_value = self._get_context_value("photon_energy_cursor")
        if context_value is not None:
            try:
                return float(context_value)
            except (TypeError, ValueError):
                pass

        if dataset.z_axis is not None and len(dataset.z_axis.values) > 0:
            mid = len(dataset.z_axis.values) // 2
            return float(dataset.z_axis.values[mid])

        return measurement_hv

    def _default_angle_offsets(self, dataset: Dataset) -> tuple[float | None, float | None]:
        cut_state: CursorState | None = self._get_context_value("cut_state")
        state = cut_state
        if state is None:
            return (None, None)

        x_default: float | None = None
        y_default: float | None = None

        if dataset.x_axis.axis_type is AxisType.ANGLE:
            x_default = float(state.x_value)
        if dataset.y_axis.axis_type is AxisType.ANGLE:
            y_default = float(state.y_value)

        return (x_default, y_default)
