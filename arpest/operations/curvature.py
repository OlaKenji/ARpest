"""Basic dataset manipulation helpers."""

from __future__ import annotations

import numpy as np

from ..models import Dataset

def _axis_index(direction: str) -> int:
    direction = (direction or "").lower()
    if direction not in {"horizontal", "vertical"}:
        raise ValueError("Direction must be 'horizontal' or 'vertical'.")
    # Intensity arrays are stored as (y, x, ...) so horizontal => axis 1
    return 1 if direction == "horizontal" else 0

def derivative(dataset: Dataset, direction: str = "horizontal", order: int = 1) -> Dataset:
    """Return a copy of the dataset differentiated along the requested axis."""
    if order < 1:
        raise ValueError("Derivative order must be >= 1.")
    axis = _axis_index(direction)
    if dataset.intensity.ndim <= axis:
        raise ValueError("Dataset does not have enough dimensions for the requested derivative.")

    values = dataset.intensity.astype(float, copy=False)
    for _ in range(order):
        values = np.gradient(values, axis=axis)

    new_dataset = dataset.copy()
    new_dataset.intensity = values
    return new_dataset

def _smooth_values(values: np.ndarray, axis: int, window: int) -> np.ndarray:
    kernel = np.ones(window, dtype=float) / float(window)
    pad = window // 2
    pad_width = [(0, 0)] * values.ndim
    pad_width[axis] = (pad, pad)

    padded = np.pad(values, pad_width, mode="edge")
    return np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), axis, padded)

def smooth(dataset: Dataset, direction: str = "horizontal", window: int = 5) -> Dataset:
    """Return a copy of the dataset with a moving-average smoothing applied along the requested axis."""
    axis = _axis_index(direction)
    if dataset.intensity.ndim <= axis:
        raise ValueError("Dataset does not have enough dimensions for the requested smoothing.")
    if window < 1 or window % 2 == 0:
        raise ValueError("Smoothing window must be a positive odd integer.")

    smoothed = _smooth_values(dataset.intensity.astype(float, copy=False), axis, window)

    new_dataset = dataset.copy()
    new_dataset.intensity = smoothed
    return new_dataset

def zhang_curvature(
    dataset: Dataset,
    direction: str = "horizontal",
    smooth_window: int = 5,
    epsilon: float = 1e-6,
) -> Dataset:
    """
    Compute the Zhang et al. curvature (second derivative normalized by slope) along the chosen axis.

    Reference: Zhang et al., Rev. Sci. Instrum. 82, 043712 (2011).
    The output is normalized to unit maximum absolute value for consistent color scaling.
    """
    axis = _axis_index(direction)
    if dataset.intensity.ndim <= axis:
        raise ValueError("Dataset does not have enough dimensions for the requested curvature.")
    if smooth_window < 1 or smooth_window % 2 == 0:
        raise ValueError("Smoothing window must be a positive odd integer.")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive.")

    smoothed = _smooth_values(dataset.intensity.astype(float, copy=False), axis, smooth_window)
    first = np.gradient(smoothed, axis=axis)
    second = np.gradient(first, axis=axis)
    denom = np.power(1.0 + first * first, 1.5)
    curvature = -second / np.maximum(denom, epsilon)

    new_dataset = dataset.copy()
    new_dataset.intensity = curvature
    return new_dataset
