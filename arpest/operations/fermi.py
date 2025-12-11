"""Core Fermi level correction routines."""

from __future__ import annotations

import numpy as np

from ..models import Dataset
from ..utils.functions.fermi_dirac_ditribution import fit_fermi_dirac

DEFAULT_WORK_FUNCTION = 4.38
DEFAULT_POLY_ORDER = 3

def correct_fermi_level_2d(
    dataset: Dataset,
    reference: Dataset,
    *,
    initial_fermi_guess: float | None = None,
    work_function: float | None = DEFAULT_WORK_FUNCTION,
    fit_stride: int = 1,
    poly_order: int = DEFAULT_POLY_ORDER,
) -> tuple[Dataset, np.ndarray]:
    """
    Apply a per-EDC Fermi level correction using a 2D gold reference.

    Args:
        dataset: Dataset to correct (must be 2D)
        reference: Gold reference dataset with matching pixel count (2D)
        initial_fermi_guess: Optional manual EF guess to seed the first fit
        work_function: Work function estimate (only used if no manual guess is provided)
        fit_stride: Number of neighboring EDCs to average per Fermi fit
        poly_order: Polynomial order used to interpolate EF values between fitted points

    Returns:
        Tuple of (corrected_dataset, fitted_fermi_levels)
    """
    gold = reference.intensity
    n_pixels, _ = gold.shape
    energies = reference.x_axis.values
    dataset_intensity = dataset.intensity

    if dataset_intensity.shape[0] != n_pixels:
        raise ValueError("Reference and dataset must have the same number of EDC pixels.")

    temperature = (
        getattr(dataset.measurement, "temperature", None)
        or getattr(reference.measurement, "temperature", None)
        or 10.0
    )
    e_guess = _resolve_initial_guess(
        dataset,
        energies,
        initial_fermi_guess=initial_fermi_guess,
        work_function=work_function,
    )

    fermi_levels = _fit_reference_fermi_levels(
        gold,
        energies,
        temperature,
        e_guess,
        fit_stride=fit_stride,
        poly_order=poly_order,
    )

    corrected_intensity, corrected_axis = shift_edcs_to_common_axis(dataset_intensity, dataset.x_axis.values,fermi_levels)

    new_dataset = dataset.copy()
    new_dataset.intensity = corrected_intensity
    new_dataset.x_axis.values = corrected_axis
    new_dataset.validate()

    return new_dataset, fermi_levels

def shift_edcs_to_common_axis(intensity: np.ndarray, energies: np.ndarray, fermi_levels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Shift each EDC independently and resample onto a common energy axis.

    Args:
        intensity: Array of shape (n_pixels, n_energy)
        energies: Original energy axis
        fermi_levels: Estimated EF for each EDC (length n_pixels)

    Returns:
        Tuple of (shifted_intensity, shared_axis)
    """
    if intensity.shape[0] != len(fermi_levels):
        raise ValueError("Number of Fermi entries does not match dataset rows.")

    energies = np.asarray(energies, dtype=float)
    if energies.ndim != 1 or energies.size < 2:
        raise ValueError("Energy axis must contain at least two points.")

    spacing = np.diff(energies)
    valid_spacing = np.abs(spacing[spacing != 0])
    step = float(np.median(valid_spacing)) if valid_spacing.size else 1.0

    shifted_min = float(energies.min() - np.max(fermi_levels))
    shifted_max = float(energies.max() - np.min(fermi_levels))
    if shifted_max <= shifted_min:
        shifted_max = shifted_min + step

    num_points = int(np.ceil((shifted_max - shifted_min) / step)) + 1
    target_axis = shifted_min + np.arange(num_points) * step

    corrected = np.full((intensity.shape[0], num_points), np.nan, dtype=float)
    ascending = energies[0] < energies[-1]

    for idx, (curve, ef) in enumerate(zip(intensity, fermi_levels)):
        xp = energies - ef
        yp = curve
        if not ascending:
            xp = xp[::-1]
            yp = yp[::-1]
        corrected[idx] = np.interp(
            target_axis,
            xp,
            yp,
            left=np.nan,
            right=np.nan,
        )

    return corrected, target_axis

def correct_fermi_level_3d_same(
    dataset: Dataset,
    reference: Dataset,
    *,
    initial_fermi_guess: float | None = None,
    work_function: float | None = DEFAULT_WORK_FUNCTION,
    fit_stride: int = 1,
    poly_order: int = DEFAULT_POLY_ORDER,
) -> tuple[Dataset, np.ndarray]:
    """
    Shift each EDC independently and resample onto a common energy axis for each scan angle.

    Args:
        dataset: Dataset to correct (3D)
        reference: Gold reference dataset with matching pixel count (2D)
        initial_fermi_guess: Optional manual EF guess to seed the first fit
        work_function: Work function estimate (used when no manual guess is provided)
        fit_stride: Number of neighboring EDCs to average per Fermi fit
        poly_order: Polynomial order used to interpolate EF values between fitted points

    Returns:
        Tuple of (corrected_dataset, fitted_fermi_levels)
    """
    gold = reference.intensity
    n_pixels, _ = gold.shape
    energies = reference.x_axis.values
    dataset_intensity = dataset.intensity

    if dataset_intensity.shape[0] != n_pixels:
        raise ValueError("Reference and dataset must have the same number of EDC pixels.")

    temperature = (
        getattr(dataset.measurement, "temperature", None)
        or getattr(reference.measurement, "temperature", None)
        or 10.0
    )
    e_guess = _resolve_initial_guess(
        dataset,
        energies,
        initial_fermi_guess=initial_fermi_guess,
        work_function=work_function,
    )
    fermi_levels = _fit_reference_fermi_levels(
        gold,
        energies,
        temperature,
        e_guess,
        fit_stride=fit_stride,
        poly_order=poly_order,
    )

    corrected_intensity, corrected_axis = shift_edcs_to_common_axis_3d_same(dataset_intensity, dataset.z_axis.values, fermi_levels)

    new_dataset = dataset.copy()
    new_dataset.intensity = corrected_intensity
    if new_dataset.z_axis is None:
        raise ValueError("3D dataset must define a z-axis for the energy dimension.")
    new_dataset.z_axis.values = corrected_axis
    new_dataset.validate()

    return new_dataset, fermi_levels

def shift_edcs_to_common_axis_3d_same(intensity: np.ndarray, energies: np.ndarray, fermi_levels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Shift each EDC independently and resample onto a common energy axis for each scan angle.

    Args:
        intensity: Array of shape (n_pixels, n_scans, n_energy)
        energies: Original energy axis
        fermi_levels: Estimated EF for each EDC (length n_pixels)

    Returns:
        Tuple of (shifted_intensity, shared_axis)
    """

    if intensity.ndim != 3:
        raise ValueError("Expected a 3D intensity array (pixels × scans × energy).")

    n_pixels, n_scans, _ = intensity.shape
    if len(fermi_levels) != n_pixels:
        raise ValueError("Length of fermi_levels must match the first dimension of intensity.")

    reshaped = intensity.reshape(n_pixels * n_scans, intensity.shape[2])
    repeated_fermi = np.repeat(np.asarray(fermi_levels, dtype=float), n_scans)

    corrected_flat, target_axis = shift_edcs_to_common_axis(reshaped, energies, repeated_fermi)
    corrected = corrected_flat.reshape(n_pixels, n_scans, corrected_flat.shape[1])

    return corrected, target_axis

def correct_fermi_level_3d(
    dataset: Dataset,
    reference: Dataset,
    work_function: float = DEFAULT_WORK_FUNCTION,
) -> tuple[Dataset, np.ndarray]:
    """
    Apply a per-EDC Fermi level correction using a 3D gold reference.

    Args:
        dataset: Dataset to correct (3D)
        reference: Gold reference dataset with matching pixel count (2D)
        work_function: Work function estimate for initial EF guess

    Returns:
        Tuple of (corrected_dataset, fitted_fermi_levels)
    """
    pass

def _resolve_initial_guess(
    dataset: Dataset,
    energies: np.ndarray,
    *,
    initial_fermi_guess: float | None,
    work_function: float | None,
) -> float:
    """Return the initial EF guess to seed the first Fermi fit."""
    if initial_fermi_guess is not None:
        return float(initial_fermi_guess)

    photon_energy = getattr(dataset.measurement, "photon_energy", None)
    if photon_energy is not None and work_function is not None:
        return float(photon_energy - work_function)

    return float(np.median(energies))

def _fit_reference_fermi_levels(
    gold_reference: np.ndarray,
    energies: np.ndarray,
    temperature: float,
    e_guess: float,
    *,
    fit_stride: int,
    poly_order: int,
) -> np.ndarray:
    """Fit the Fermi edge on block-averaged EDCs and interpolate across all pixels."""
    if fit_stride < 1:
        raise ValueError("fit_stride must be at least 1.")

    n_pixels = gold_reference.shape[0]
    stride = min(int(fit_stride), n_pixels)

    block_levels: list[float] = []
    block_positions: list[float] = []
    guess = e_guess
    for start in range(0, n_pixels, stride):
        stop = min(start + stride, n_pixels)
        block = gold_reference[start:stop]
        if block.size == 0:
            continue
        averaged_edc = np.nanmean(block, axis=0)
        length = int(len(averaged_edc) * 0.75)
        energies_slice = energies[length:-1]
        edc_slice = averaged_edc[length:-1]
        p, _ = fit_fermi_dirac(energies_slice, edc_slice, guess, T=temperature)
        ef = float(p[0])
        block_levels.append(ef)
        block_positions.append(start + (stop - start) / 2.0)
        guess = ef

    if not block_levels:
        raise ValueError("Failed to fit any Fermi edges from the reference dataset.")

    block_levels_array = np.asarray(block_levels, dtype=float)
    block_positions_array = np.asarray(block_positions, dtype=float)
    deg = max(0, min(int(poly_order), len(block_levels_array) - 1))

    if deg == 0:
        fitted = np.full(n_pixels, block_levels_array[0], dtype=float)
    else:
        coeffs = np.polyfit(block_positions_array, block_levels_array, deg=deg)
        fitted = np.polyval(coeffs, np.arange(n_pixels, dtype=float))
    return fitted
