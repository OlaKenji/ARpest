"""Core Fermi level correction routines."""

from __future__ import annotations

import numpy as np

from ..models import Dataset
from ..utils.functions.fermi_dirac_ditribution import fit_fermi_dirac

DEFAULT_WORK_FUNCTION_EV = 4.38

def correct_fermi_level_2d(
    dataset: Dataset,
    reference: Dataset,
    work_function: float = DEFAULT_WORK_FUNCTION_EV,
) -> tuple[Dataset, np.ndarray]:
    """
    Apply a per-EDC Fermi level correction using a 2D gold reference.

    Args:
        dataset: Dataset to correct (must be 2D)
        reference: Gold reference dataset with matching pixel count (2D)
        work_function: Work function estimate for initial EF guess

    Returns:
        Tuple of (corrected_dataset, fitted_fermi_levels)
    """
    gold = reference.intensity
    n_pixels, _ = gold.shape
    energies = reference.x_axis.values
    dataset_intensity = dataset.intensity

    if dataset_intensity.shape[0] != n_pixels:
        raise ValueError("Reference and dataset must have the same number of EDC pixels.")

    temperature = dataset.measurement.temperature or reference.measurement.temperature or 10.0
    hv = dataset.measurement.photon_energy
    e_guess = hv - work_function

    params: list[np.ndarray] = []
    for edc in gold:
        length = int(len(edc) * 0.75)
        p, _ = fit_fermi_dirac(
            energies[length:-1],
            edc[length:-1],
            e_guess,
            T=temperature,
        )
        params.append(p)
        e_guess = p[0]

    param_array = np.asarray(params)
    fermi_levels = param_array[:, 0]

    corrected_intensity, corrected_axis = shift_edcs_to_common_axis(
        dataset_intensity,
        dataset.x_axis.values,
        fermi_levels,
    )

    new_dataset = dataset.copy()
    new_dataset.intensity = corrected_intensity
    new_dataset.x_axis.values = corrected_axis
    new_dataset.validate()

    return new_dataset, fermi_levels

def shift_edcs_to_common_axis(
    intensity: np.ndarray,
    energies: np.ndarray,
    fermi_levels: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
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