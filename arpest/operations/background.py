"""Background subtraction helpers (EDC/MDC variants)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from ..models import Dataset


BACKGROUND_MODES = {"EDC", "MDC", "EDC_MIN", "MDC_MIN"}


def subtract_background(
    dataset: Dataset,
    mode: str,
    min_points: int = 5,
    edc_curves: Any = None,
    mdc_curves: Any = None,
) -> Dataset:
    """Subtract the selected background using either plotted curves or dataset-derived references."""
    if dataset.intensity.ndim < 2:
        raise ValueError("Background subtraction requires at least 2D data.")

    mode_key = (mode or "").upper()
    if mode_key not in BACKGROUND_MODES:
        raise ValueError("Unsupported background mode.")

    min_points = max(1, int(min_points))
    values = dataset.intensity.astype(float, copy=False)

    if mode_key == "EDC":
        curves = _normalize_curve_dict(edc_curves)
        if not curves:
            curves = _default_edc_curves(dataset, values)
        corrected = _apply_curves(values, dataset, curves)
    elif mode_key == "MDC":
        curves = _normalize_curve_dict(mdc_curves)
        if not curves:
            curves = _default_mdc_curves(dataset, values)
        corrected = _apply_curves(values, dataset, curves)
    elif mode_key == "EDC_MIN":
        corrected = values.copy()
        for axis_key in _edc_axis_keys(dataset):
            corrected = _subtract_minima_along_axis(corrected, dataset, axis_key, min_points)
    elif mode_key == "MDC_MIN":
        corrected = values.copy()
        for axis_key in _mdc_axis_keys(dataset):
            corrected = _subtract_minima_along_axis(corrected, dataset, axis_key, min_points)
    else:  # pragma: no cover - safeguarded by BACKGROUND_MODES
        raise ValueError("Unsupported background mode.")

    new_dataset = dataset.copy()
    new_dataset.intensity = corrected
    new_dataset.validate()
    return new_dataset


def _normalize_curve_dict(curves: Any) -> dict[str, np.ndarray]:
    """Return axis-keyed curves regardless of input structure."""
    result: dict[str, np.ndarray] = {}
    if curves is None:
        return result

    items: Sequence[tuple[Any, Any]] | None = None
    if isinstance(curves, Mapping):
        items = list(curves.items())
    elif isinstance(curves, Sequence):
        temp: list[tuple[Any, Any]] = []
        for entry in curves:
            if isinstance(entry, Mapping):
                temp.append((entry.get("axis"), entry.get("values")))
            elif isinstance(entry, Sequence) and len(entry) == 2:
                temp.append((entry[0], entry[1]))
        items = temp

    if items is None:
        return result

    for axis_key, values in items:
        if values is None or axis_key is None:
            continue
        axis = str(axis_key).lower()
        array = np.asarray(values, dtype=float)
        if array.ndim == 0:
            continue
        array = np.nan_to_num(array, nan=0.0)
        result[axis] = array
    return result


def _apply_curves(values: np.ndarray, dataset: Dataset, curves: Mapping[str, np.ndarray]) -> np.ndarray:
    """Subtract axis-aligned curves from the dataset intensity."""
    corrected = values.copy()
    for axis_key, curve in curves.items():
        axis_index = _axis_key_to_index(dataset, axis_key)
        flat = np.ravel(curve)
        axis_len = corrected.shape[axis_index]
        if flat.size != axis_len:
            raise ValueError(f"Curve length mismatch for axis {axis_key.upper()}: expected {axis_len}, got {flat.size}.")
        shaped = _reshape_for_axis(flat, corrected.ndim, axis_index)
        corrected = corrected - shaped
    return corrected


def _default_edc_curves(dataset: Dataset, values: np.ndarray) -> dict[str, np.ndarray]:
    axis_key = _edc_axis_keys(dataset)[0]
    axis_index = _axis_key_to_index(dataset, axis_key)
    curve = _mean_over_other_axes(values, axis_index)
    return {axis_key: curve}


def _default_mdc_curves(dataset: Dataset, values: np.ndarray) -> dict[str, np.ndarray]:
    curves: dict[str, np.ndarray] = {}
    for axis_key in _mdc_axis_keys(dataset):
        axis_index = _axis_key_to_index(dataset, axis_key)
        curves[axis_key] = _mean_over_other_axes(values, axis_index)
    return curves


def _edc_axis_keys(dataset: Dataset) -> list[str]:
    """EDCs vary along the energy axis (y for 2D, z for 3D+)."""
    return ["z"] if dataset.intensity.ndim >= 3 else ["y"]


def _mdc_axis_keys(dataset: Dataset) -> list[str]:
    """MDCs span in-plane axes; 3D data includes both x and y angles."""
    axes = ["x"]
    if dataset.intensity.ndim >= 3:
        axes.append("y")
    return axes


def _mean_over_other_axes(values: np.ndarray, axis_index: int) -> np.ndarray:
    axes = tuple(i for i in range(values.ndim) if i != axis_index)
    curve = np.nanmean(values, axis=axes)
    return np.nan_to_num(curve, nan=0.0)


def _subtract_minima_along_axis(
    values: np.ndarray,
    dataset: Dataset,
    axis_key: str,
    count: int,
) -> np.ndarray:
    axis_index = _axis_key_to_index(dataset, axis_key)
    axis_len = values.shape[axis_index]
    take = max(1, min(int(count), axis_len))
    sorted_vals = np.sort(values, axis=axis_index)
    slicer = [slice(None)] * values.ndim
    slicer[axis_index] = slice(0, take)
    subset = sorted_vals[tuple(slicer)]
    offsets = np.nanmean(subset, axis=axis_index, keepdims=True)
    offsets = np.nan_to_num(offsets, nan=0.0)
    return values - offsets


def _axis_key_to_index(dataset: Dataset, axis_key: str) -> int:
    key = axis_key.lower()
    if key == "y":
        return 0
    if key == "x":
        if dataset.intensity.ndim < 2:
            raise ValueError("Dataset does not contain an x-axis.")
        return 1
    if key == "z":
        if dataset.intensity.ndim < 3:
            raise ValueError("Dataset does not contain a z-axis.")
        return 2
    if key == "w":
        if dataset.intensity.ndim < 4:
            raise ValueError("Dataset does not contain a w-axis.")
        return 3
    raise ValueError(f"Unknown axis key '{axis_key}'.")


def _reshape_for_axis(curve: np.ndarray, ndim: int, axis_index: int) -> np.ndarray:
    shape = [1] * ndim
    shape[axis_index] = curve.shape[0]
    return curve.reshape(shape)
