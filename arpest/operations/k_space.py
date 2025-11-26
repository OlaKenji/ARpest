from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
)

from ..models import AxisType, Dataset, Axis
from ..utils.cursor_manager import CursorState
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
        """Populate UI defaults using currently selected dataset, if any."""
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
            # Automatically sync when a new dataset is encountered.
            self._update_dataset_summary(dataset, sync_parameters=True)

        context = self._build_context(dataset)
        if context.mode is KSpaceConversionMode.MAP_2D:
            return self._convert_2d_map(dataset, context)
        if context.mode is KSpaceConversionMode.VOLUME_3D:
            return self._convert_3d_volume(dataset, context)
        if context.mode is KSpaceConversionMode.PHOTON_SCAN:
            return self._convert_photon_scan(dataset, context)

        raise ValueError("Unsupported dataset dimensionality for k-space conversion.")

    def _update_dataset_summary(self, dataset: Dataset, sync_parameters: bool) -> None:
        """Update descriptive text and optionally sync parameter controls."""
        if dataset is None:
            self.dataset_info_label.setText("No dataset selected.")
            self.mode_hint_label.setText("Mode: unavailable.")
            self._last_dataset_id = None
            return

        mode = self._determine_mode(dataset)
        axis_lines = [
            f"X-axis: {dataset.x_axis.name} ({dataset.x_axis.unit})",
            f"Y-axis: {dataset.y_axis.name} ({dataset.y_axis.unit})",
        ]
        if dataset.z_axis is not None:
            axis_lines.append(f"Z-axis: {dataset.z_axis.name} ({dataset.z_axis.unit})")
        if dataset.w_axis is not None:
            axis_lines.append(f"W-axis: {dataset.w_axis.name} ({dataset.w_axis.unit})")

        measurement = dataset.measurement

        self.mode_hint_label.setText(f"Mode: {mode.describe()}")

        hv_default = self._default_photon_energy(dataset, mode)
        angle_x_default, angle_y_default = self._default_angle_offsets(dataset)

        if sync_parameters:
            if hv_default is not None:
                self.photon_energy_spin.setValue(hv_default)
            if measurement.work_function is not None:
                self.work_function_spin.setValue(measurement.work_function)
            if angle_x_default is not None:
                self.angle_offset_x_spin.setValue(angle_x_default)
            if angle_y_default is not None:
                self.angle_offset_y_spin.setValue(angle_y_default)
        self._last_dataset_id = id(dataset)

    def _build_context(self, dataset: Dataset) -> "KSpaceConversionContext":
        mode = self._determine_mode(dataset)
        return KSpaceConversionContext(
            mode=mode,
            photon_energy=self.photon_energy_spin.value() or dataset.measurement.photon_energy,
            work_function=self.work_function_spin.value(),
            inner_potential=self.inner_potential_spin.value(),
            angle_offset_x=self.angle_offset_x_spin.value(),
            angle_offset_y=self.angle_offset_y_spin.value(),
        )

    def _determine_mode(self, dataset: Dataset) -> "KSpaceConversionMode":
        if dataset.is_2d:
            return KSpaceConversionMode.MAP_2D

        if dataset.is_3d and dataset.z_axis is not None:
            if dataset.x_axis.axis_type is AxisType.PHOTON_ENERGY:
                return KSpaceConversionMode.PHOTON_SCAN
            return KSpaceConversionMode.VOLUME_3D

        raise ValueError("Only 2D and 3D datasets are supported for k-space conversion.")

    def _default_photon_energy(self,dataset: Dataset,mode: "KSpaceConversionMode") -> float | None:
        """Determine the photon energy value to populate the UI with."""
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
        """Use the current cursor to guess the gamma (angle) position for both axes."""
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

    def _convert_2d_map(self, dataset: Dataset, context: "KSpaceConversionContext") -> tuple[Dataset, str]:
        new_dataset = dataset.copy()

        work_func = context.work_function
        hv = context.photon_energy

        k0 = 0.5124 * np.sqrt(hv - work_func)
        #alpha is the polar or theta -> SIS
        #beta is the tilt -> SIS

        # Angle to radian conversion
        pos1 = context.angle_offset_y       
        pos2 = context.angle_offset_x    
        dalpha,dbeta = -pos1,-pos2#the offsets

        alpha, beta = new_dataset.y_axis.values, np.array([new_dataset.measurement.chi])

        a = (alpha + dalpha)*np.pi/180
        b = (beta + dbeta)*np.pi/180

        nkx = len(alpha)
        nky = len(beta)

        theta_k = beta * np.pi / 180.0
        cos_theta = np.cos(theta_k)
        sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta * np.pi / 180.0)

        kx_grid = np.empty((nkx, nky))
        ky_grid = np.empty((nkx, nky))
        for i in range(nkx):
            kx_grid[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * np.sin(dbeta * np.pi / 180.0)
            ky_grid[i] = cos_theta * np.sin(a[i])

        mid_alpha = nkx // 2
        mid_beta = nky // 2
        kx_values = kx_grid[mid_alpha, :] * k0
        ky_values = ky_grid[:, mid_beta] * k0

        #new_dataset.x_axis = Axis(kx_values, AxisType.K_PARALLEL, "k_x", "Å⁻¹")
        new_dataset.y_axis = Axis(ky_values, AxisType.K_PARALLEL, "k_y", "Å⁻¹")
        new_dataset.validate()

        return new_dataset, "k space"        

    def _convert_3d_volume(self, dataset: Dataset, context: "KSpaceConversionContext") -> tuple[Dataset, str]:
        new_dataset = dataset.copy()

        work_func = context.work_function
        hv = context.photon_energy

        k0 = 0.5124 * np.sqrt(hv - work_func)
        #alpha is the polar or theta -> SIS
        #beta is the tilt -> SIS

        # Angle to radian conversion
        pos1 = context.angle_offset_y       
        pos2 = context.angle_offset_x    
        dalpha,dbeta = -pos1,-pos2#the offsets

        alpha, beta = new_dataset.y_axis.values, new_dataset.x_axis.values

        a = (alpha + dalpha)*np.pi/180
        b = (beta + dbeta)*np.pi/180

        nkx = len(alpha)
        nky = len(beta)

        theta_k = beta * np.pi / 180.0
        cos_theta = np.cos(theta_k)
        sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta * np.pi / 180.0)

        kx_grid = np.empty((nkx, nky))
        ky_grid = np.empty((nkx, nky))
        for i in range(nkx):
            kx_grid[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * np.sin(dbeta * np.pi / 180.0)
            ky_grid[i] = cos_theta * np.sin(a[i])

        mid_alpha = nkx // 2
        mid_beta = nky // 2
        kx_values = kx_grid[mid_alpha, :] * k0
        ky_values = ky_grid[:, mid_beta] * k0

        new_dataset.x_axis = Axis(kx_values, AxisType.K_PERPENDICULAR, "k_x", "Å⁻¹")
        new_dataset.y_axis = Axis(ky_values, AxisType.K_PARALLEL, "k_y", "Å⁻¹")
        new_dataset.validate()

        return new_dataset, "k space"    

    def _convert_photon_scan(self, dataset: Dataset, context: "KSpaceConversionContext") -> tuple[Dataset, str]:
        new_dataset = dataset.copy()
        ky_grid, kz_grid = self._compute_photon_scan_grids(new_dataset, context)        
        ky_axis, kz_axis = self._build_k_axes_from_grid(new_dataset, ky_grid, kz_grid)

        resampled_intensity = self._resample_photon_scan_intensity(new_dataset.intensity, ky_grid, kz_grid, ky_axis, kz_axis)

        new_dataset.intensity = resampled_intensity
        new_dataset.x_axis = Axis(kz_axis, AxisType.K_PERPENDICULAR, "k_z", "Å⁻¹")
        new_dataset.y_axis = Axis(ky_axis, AxisType.K_PARALLEL, "k_y", "Å⁻¹")
        new_dataset.validate()

        return new_dataset, "k space"

    def _convert2k(self,hv, new_dataset, context):
        W = context.work_function
        k0 = 0.5124 * np.sqrt(hv - W)
        #alpha is the polar or theta -> SIS
        #beta is the tilt -> SIS

        # Angle to radian conversion
        pos1 = context.angle_offset_y       
        pos2 = context.angle_offset_x    
        dalpha,dbeta = -pos1,-pos2#the offsets

        alpha, beta = new_dataset.y_axis.values, np.array([new_dataset.measurement.chi])

        a = (alpha + dalpha)*np.pi/180
        b = (beta + dbeta)*np.pi/180

        nkx = len(alpha)
        nky = len(beta)

        theta_k = beta * np.pi / 180.0
        cos_theta = np.cos(theta_k)
        sin_theta_cos_beta = np.sin(theta_k) * np.cos(dbeta * np.pi / 180.0)

        kx_grid = np.empty((nkx, nky))
        ky_grid = np.empty((nkx, nky))
        for i in range(nkx):
            kx_grid[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * np.sin(dbeta * np.pi / 180.0)
            ky_grid[i] = cos_theta * np.sin(a[i])

        mid_alpha = nkx // 2
        mid_beta = nky // 2
        kx_values = kx_grid[mid_alpha, :] * k0
        ky_values = ky_grid[:, mid_beta] * k0

        return ky_values

    def _compute_photon_scan_grids(self, dataset: Dataset, context: "KSpaceConversionContext") -> tuple[np.ndarray, np.ndarray]:
        hv_values = np.asarray(dataset.x_axis.values, dtype=float)
        ky_values = [self._convert2k(hv, dataset, context) for hv in hv_values]

        ky_grid = np.transpose(np.asarray(ky_values, dtype=float))

        q = 1.60218e-19
        m = 9.1093837e-31
        hbar = 6.62607015e-34 / (2 * np.pi)
        V = context.inner_potential * q
        W = context.work_function
        Eb = 0.0

        theta_rad = np.deg2rad(np.asarray(dataset.y_axis.values, dtype=float))
        cos_sq = np.cos(theta_rad) ** 2
        Ek = np.maximum(hv_values - W - Eb, 0.0) * q
        kz_terms = np.outer(cos_sq, Ek) + V
        kz_grid = 1e-10 * np.sqrt(2 * m * kz_terms) / hbar

        return ky_grid, kz_grid

    def _build_k_axes_from_grid(self, dataset: Dataset, ky_grid: np.ndarray, kz_grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        ky_len = ky_grid.shape[0]
        kz_len = kz_grid.shape[1]

        ky_axis = np.linspace(float(np.nanmin(ky_grid)), float(np.nanmax(ky_grid)), ky_len)
        kz_axis = np.linspace(float(np.nanmin(kz_grid)), float(np.nanmax(kz_grid)), kz_len)

        if dataset.y_axis.values[0] > dataset.y_axis.values[-1]:
            ky_axis = ky_axis[::-1]
        if dataset.x_axis.values[0] > dataset.x_axis.values[-1]:
            kz_axis = kz_axis[::-1]

        return ky_axis, kz_axis

    def _resample_photon_scan_intensity(self, intensity: np.ndarray, ky_grid: np.ndarray, kz_grid: np.ndarray, ky_axis: np.ndarray, kz_axis: np.ndarray) -> np.ndarray:
        if intensity.ndim != 3:
            raise ValueError("Photon scan conversion expects a 3D dataset.")

        ky_len = len(ky_axis)
        kz_len = len(kz_axis)
        nz = intensity.shape[2]

        ky_resampled = np.empty((ky_len, ky_grid.shape[1], nz), dtype=float)
        for hv_idx in range(ky_grid.shape[1]):
            ky_source = ky_grid[:, hv_idx]
            values = intensity[:, hv_idx, :]
            ky_resampled[:, hv_idx, :] = self._vectorized_interp(ky_source, values, ky_axis)

        regridded = np.empty((ky_len, kz_len, nz), dtype=float)
        for ky_idx in range(ky_len):
            kz_source = kz_grid[ky_idx, :]
            values = ky_resampled[ky_idx, :, :]
            regridded[ky_idx, :, :] = self._vectorized_interp(kz_source, values, kz_axis)

        return regridded

    def _vectorized_interp(self, source_axis: np.ndarray, source_values: np.ndarray, target_axis: np.ndarray) -> np.ndarray:
        source_axis = np.asarray(source_axis, dtype=float)
        source_values = np.asarray(source_values, dtype=float)
        target_axis = np.asarray(target_axis, dtype=float)

        if source_axis.ndim != 1:
            raise ValueError("Interpolation source axis must be 1D.")
        if source_values.shape[0] != source_axis.size:
            raise ValueError("Source values must align with source axis length.")

        if source_axis.size == 1:
            row = source_values[0]
            return np.broadcast_to(row, (target_axis.size,) + row.shape)

        order = np.argsort(source_axis)
        x = source_axis[order]
        y = source_values[order]

        # Clamp targets to avoid extrapolation artifacts.
        t = np.clip(target_axis, x[0], x[-1])
        idx = np.searchsorted(x, t, side="left")
        idx = np.clip(idx, 1, x.size - 1)

        x0 = x[idx - 1]
        x1 = x[idx]
        denom = np.where(x1 == x0, 1.0, x1 - x0)
        weight = (t - x0) / denom

        y0 = y[idx - 1]
        y1 = y[idx]
        return ((1 - weight)[:, None] * y0) + (weight[:, None] * y1)

class KSpaceConversionMode(Enum):
    MAP_2D = auto()
    VOLUME_3D = auto()
    PHOTON_SCAN = auto()

    def describe(self) -> str:
        if self is KSpaceConversionMode.MAP_2D:
            return "2D angle-energy map"
        if self is KSpaceConversionMode.VOLUME_3D:
            return "3D volume (angle-angle-energy)"
        if self is KSpaceConversionMode.PHOTON_SCAN:
            return "Photon-energy scan (kz mapping)"
        return "Unknown"

@dataclass
class KSpaceConversionContext:
    mode: KSpaceConversionMode
    photon_energy: float
    work_function: float
    inner_potential: float
    angle_offset_x: float
    angle_offset_y: float
