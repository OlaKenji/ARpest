"""K-space conversion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np

from ..models import Axis, AxisType, Dataset
from ..utils.constants import elementary_charge, hbar, electron_mass

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

def determine_mode(dataset: Dataset) -> KSpaceConversionMode:#called from widget
    """Determine the conversion mode supported by the dataset."""
    if dataset.is_2d:
        return KSpaceConversionMode.MAP_2D

    if dataset.is_3d and dataset.z_axis is not None:
        if dataset.x_axis.axis_type is AxisType.PHOTON_ENERGY:
            return KSpaceConversionMode.PHOTON_SCAN
        return KSpaceConversionMode.VOLUME_3D

    raise ValueError("Only 2D and 3D datasets are supported for k-space conversion.")


def convert_dataset(dataset: Dataset, context: KSpaceConversionContext) -> tuple[Dataset, str]:#called from widget
    """Convert dataset to k-space according to the provided context."""
    mode = context.mode
    if mode is KSpaceConversionMode.MAP_2D:
        return _convert_2d_map(dataset, context)
    if mode is KSpaceConversionMode.VOLUME_3D:
        return _convert_3d_volume(dataset, context)
    if mode is KSpaceConversionMode.PHOTON_SCAN:
        return _convert_photon_scan(dataset, context)

    raise ValueError("Unsupported conversion mode.")

#2D
def _convert_2d_map(dataset: Dataset, context: KSpaceConversionContext) -> tuple[Dataset, str]:
    new_dataset = dataset.copy()
    k0 = _wavevector_prefactor(context.photon_energy, context.work_function)

    dalpha = -context.angle_offset_y
    dbeta = -context.angle_offset_x

    alpha = np.asarray(new_dataset.y_axis.values, dtype=float)
    beta_value = new_dataset.measurement.chi or 0.0
    beta = np.array([beta_value], dtype=float)

    a = np.deg2rad(alpha + dalpha)
    b = np.deg2rad(beta + dbeta)

    nkx = len(alpha)
    nky = len(beta)

    theta_k = np.deg2rad(beta)
    cos_theta = np.cos(theta_k)
    sin_theta_cos_beta = np.sin(theta_k) * np.cos(np.deg2rad(dbeta))

    kx_grid = np.empty((nkx, nky))
    ky_grid = np.empty((nkx, nky))
    for i in range(nkx):
        kx_grid[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * np.sin(np.deg2rad(dbeta))
        ky_grid[i] = cos_theta * np.sin(a[i])

    mid_alpha = nkx // 2
    mid_beta = nky // 2
    ky_values = ky_grid[:, mid_beta] * k0

    new_dataset.y_axis = Axis(ky_values, AxisType.K_PARALLEL, "k_y", "Å⁻¹")
    new_dataset.validate()
    return new_dataset, "k space"

#3D
def _convert_3d_volume(dataset: Dataset, context: KSpaceConversionContext) -> tuple[Dataset, str]:
    new_dataset = dataset.copy()
    k0 = _wavevector_prefactor(context.photon_energy, context.work_function)

    dalpha = -context.angle_offset_y
    dbeta = -context.angle_offset_x

    alpha = np.asarray(new_dataset.y_axis.values, dtype=float)
    beta = np.asarray(new_dataset.x_axis.values, dtype=float)

    a = np.deg2rad(alpha + dalpha)
    b = np.deg2rad(beta + dbeta)

    nkx = len(alpha)
    nky = len(beta)

    theta_k = np.deg2rad(beta)
    cos_theta = np.cos(theta_k)
    sin_theta_cos_beta = np.sin(theta_k) * np.cos(np.deg2rad(dbeta))

    kx_grid = np.empty((nkx, nky))
    ky_grid = np.empty((nkx, nky))
    for i in range(nkx):
        kx_grid[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * np.sin(np.deg2rad(dbeta))
        ky_grid[i] = cos_theta * np.sin(a[i])

    kx_grid *= k0
    ky_grid *= k0

    ky_axis = _build_regular_axis_from_grid(ky_grid, nkx, new_dataset.y_axis.values)
    kx_axis = _build_regular_axis_from_grid(kx_grid, nky, new_dataset.x_axis.values)

    resampled_intensity = _resample_volume_intensity(new_dataset.intensity, ky_grid, kx_grid, ky_axis, kx_axis)

    new_dataset.intensity = resampled_intensity
    new_dataset.x_axis = Axis(kx_axis, AxisType.K_PERPENDICULAR, "k_x", "Å⁻¹")
    new_dataset.y_axis = Axis(ky_axis, AxisType.K_PARALLEL, "k_y", "Å⁻¹")
    new_dataset.validate()
    return new_dataset, "k space"

def _build_regular_axis_from_grid(grid: np.ndarray, target_len: int, original_axis_values: np.ndarray) -> np.ndarray:
    axis = np.linspace(float(np.nanmin(grid)), float(np.nanmax(grid)), target_len)
    if original_axis_values[0] > original_axis_values[-1]:
        axis = axis[::-1]
    return axis

def _resample_volume_intensity(
    intensity: np.ndarray,
    ky_grid: np.ndarray,
    kx_grid: np.ndarray,
    ky_axis: np.ndarray,
    kx_axis: np.ndarray,
) -> np.ndarray:
    if intensity.ndim != 3:
        raise ValueError("3D volume conversion expects a 3D dataset.")

    ky_len = len(ky_axis)
    kx_len = len(kx_axis)
    nz = intensity.shape[2]

    ky_resampled = np.empty((ky_len, kx_grid.shape[1], nz), dtype=float)
    kx_resampled = np.empty((ky_len, kx_grid.shape[1]), dtype=float)

    for beta_idx in range(kx_grid.shape[1]):
        ky_source = ky_grid[:, beta_idx]
        values = intensity[:, beta_idx, :]
        ky_resampled[:, beta_idx, :] = _vectorized_interp(ky_source, values, ky_axis)

        kx_column = kx_grid[:, beta_idx]
        kx_interp = _vectorized_interp(ky_source, kx_column[:, None], ky_axis)
        kx_resampled[:, beta_idx] = kx_interp[:, 0]

    regridded = np.empty((ky_len, kx_len, nz), dtype=float)
    for ky_idx in range(ky_len):
        kx_source = kx_resampled[ky_idx, :]
        values = ky_resampled[ky_idx, :, :]
        regridded[ky_idx, :, :] = _vectorized_interp(kx_source, values, kx_axis)

    return regridded

#photn energy scan
def _convert_photon_scan(dataset: Dataset, context: KSpaceConversionContext) -> tuple[Dataset, str]:
    new_dataset = dataset.copy()
    ky_grid, kz_grid = _compute_photon_scan_grids(new_dataset, context)
    ky_axis, kz_axis = _build_k_axes_from_grid(new_dataset, ky_grid, kz_grid)

    resampled_intensity = _resample_photon_scan_intensity(new_dataset.intensity, ky_grid, kz_grid, ky_axis, kz_axis)

    new_dataset.intensity = resampled_intensity
    new_dataset.x_axis = Axis(kz_axis, AxisType.K_PERPENDICULAR, "k_z", "Å⁻¹")
    new_dataset.y_axis = Axis(ky_axis, AxisType.K_PARALLEL, "k_y", "Å⁻¹")
    new_dataset.validate()
    return new_dataset, "k space"

def _wavevector_prefactor(photon_energy: float, work_function: float) -> float:
    hv = float(photon_energy)
    work_func = float(work_function)
    diff = max(hv - work_func, 0.0)
    return 0.5124 * np.sqrt(diff)

def _convert_to_ky_values(hv: float, dataset: Dataset, context: KSpaceConversionContext) -> np.ndarray:
    k0 = _wavevector_prefactor(hv, context.work_function)

    dalpha = -context.angle_offset_y
    dbeta = -context.angle_offset_x

    alpha = np.asarray(dataset.y_axis.values, dtype=float)
    beta_value = dataset.measurement.chi or 0.0
    beta = np.array([beta_value], dtype=float)

    a = np.deg2rad(alpha + dalpha)
    b = np.deg2rad(beta + dbeta)

    nkx = len(alpha)
    nky = len(beta)

    theta_k = np.deg2rad(beta)
    cos_theta = np.cos(theta_k)
    sin_theta_cos_beta = np.sin(theta_k) * np.cos(np.deg2rad(dbeta))

    kx_grid = np.empty((nkx, nky))
    ky_grid = np.empty((nkx, nky))
    for i in range(nkx):
        kx_grid[i] = sin_theta_cos_beta + cos_theta * np.cos(a[i]) * np.sin(np.deg2rad(dbeta))
        ky_grid[i] = cos_theta * np.sin(a[i])

    mid_alpha = nkx // 2
    mid_beta = nky // 2
    return ky_grid[:, mid_beta] * k0

def _compute_photon_scan_grids(dataset: Dataset, context: KSpaceConversionContext) -> tuple[np.ndarray, np.ndarray]:
    hv_values = np.asarray(dataset.x_axis.values, dtype=float)
    ky_values = [_convert_to_ky_values(hv, dataset, context) for hv in hv_values]
    ky_grid = np.transpose(np.asarray(ky_values, dtype=float))

    V = context.inner_potential * elementary_charge
    W = context.work_function
    Eb = 0.0  # the binding energy

    theta_rad = np.deg2rad(np.asarray(dataset.y_axis.values, dtype=float))
    cos_sq = np.cos(theta_rad) ** 2
    Ek = np.maximum(hv_values - W - Eb, 0.0) * elementary_charge
    kz_terms = np.outer(cos_sq, Ek) + V
    kz_grid = 1e-10 * np.sqrt(2 * electron_mass * kz_terms) / hbar

    return ky_grid, kz_grid

def _build_k_axes_from_grid(
    dataset: Dataset, ky_grid: np.ndarray, kz_grid: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    ky_len = ky_grid.shape[0]
    kz_len = kz_grid.shape[1]

    ky_axis = np.linspace(float(np.nanmin(ky_grid)), float(np.nanmax(ky_grid)), ky_len)
    kz_axis = np.linspace(float(np.nanmin(kz_grid)), float(np.nanmax(kz_grid)), kz_len)

    if dataset.y_axis.values[0] > dataset.y_axis.values[-1]:
        ky_axis = ky_axis[::-1]
    if dataset.x_axis.values[0] > dataset.x_axis.values[-1]:
        kz_axis = kz_axis[::-1]

    return ky_axis, kz_axis

def _create_validity_mask(
    ky_grid: np.ndarray,
    kz_grid: np.ndarray,
    ky_axis: np.ndarray,
    kz_axis: np.ndarray,
) -> np.ndarray:
    """
    Create a mask that indicates which points in the rectangular grid
    fall within the original curved boundary of the data.
    """
    ky_len = len(ky_axis)
    kz_len = len(kz_axis)
    
    # Create 2D mesh of target coordinates
    kz_mesh, ky_mesh = np.meshgrid(kz_axis, ky_axis)
    
    # Initialize mask as False (invalid)
    mask = np.zeros((ky_len, kz_len), dtype=bool)
    
    # For each ky value in the target grid, find the valid kz range
    for ky_idx, ky_target in enumerate(ky_axis):
        # Find the closest ky indices in the original grid
        ky_diffs = np.abs(ky_grid - ky_target)
        closest_ky_idx = np.argmin(ky_diffs, axis=0)
        
        # Get the kz values at this ky for each photon energy
        kz_at_ky = np.array([kz_grid[closest_ky_idx[hv_idx], hv_idx] 
                              for hv_idx in range(kz_grid.shape[1])])
        
        # Find valid kz range (min and max from original curved boundary)
        kz_min = np.min(kz_at_ky)
        kz_max = np.max(kz_at_ky)
        
        # Mark points in this ky row that fall within the valid kz range
        mask[ky_idx, :] = (kz_axis >= kz_min) & (kz_axis <= kz_max)
    
    return mask

def _resample_photon_scan_intensity(
    intensity: np.ndarray,
    ky_grid: np.ndarray,
    kz_grid: np.ndarray,
    ky_axis: np.ndarray,
    kz_axis: np.ndarray,
) -> np.ndarray:
    if intensity.ndim != 3:
        raise ValueError("Photon scan conversion expects a 3D dataset.")

    ky_len = len(ky_axis)
    kz_len = len(kz_axis)
    nz = intensity.shape[2]

    # First interpolation: resample along ky for each photon energy
    ky_resampled = np.empty((ky_len, ky_grid.shape[1], nz), dtype=float)
    for hv_idx in range(ky_grid.shape[1]):
        ky_source = ky_grid[:, hv_idx]
        values = intensity[:, hv_idx, :]
        ky_resampled[:, hv_idx, :] = _vectorized_interp(ky_source, values, ky_axis)

    # Second interpolation: resample along kz for each ky
    regridded = np.empty((ky_len, kz_len, nz), dtype=float)
    for ky_idx in range(ky_len):
        kz_source = kz_grid[ky_idx, :]
        values = ky_resampled[ky_idx, :, :]
        regridded[ky_idx, :, :] = _vectorized_interp(kz_source, values, kz_axis)

    # Create validity mask to preserve curved boundaries
    mask = _create_validity_mask(ky_grid, kz_grid, ky_axis, kz_axis)
    
    # Apply mask: set invalid regions to NaN
    mask_3d = mask[:, :, np.newaxis]  # Broadcast mask to 3D
    regridded = np.where(mask_3d, regridded, np.nan)

    return regridded


# Common interpolation function
def _vectorized_interp(
    source_axis: np.ndarray, source_values: np.ndarray, target_axis: np.ndarray
) -> np.ndarray:
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

    t = np.clip(target_axis, x[0], x[-1])
    idx = np.searchsorted(x, t, side="left")
    idx = np.clip(idx, 1, x.size - 1)

    x0 = x[idx - 1]
    x1 = x[idx]
    denom = np.where(x1 == x0, 1.0, x1 - x0)
    weight = (t - x0) / denom

    y0 = y[idx - 1]
    y1 = y[idx]
    reshape_shape = (t.size,) + (1,) * (y.ndim - 1)
    w0 = (1 - weight).reshape(reshape_shape)
    w1 = weight.reshape(reshape_shape)
    return (w0 * y0) + (w1 * y1)
