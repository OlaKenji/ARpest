"""Basic dataset manipulation helpers."""

from __future__ import annotations

import numpy as np

from ..models import Dataset


def normalize_dataset(dataset: Dataset) -> Dataset:
    """Return a copy of the dataset with intensity normalized to unit max."""
    new_dataset = dataset.copy()
    max_val = np.nanmax(np.abs(new_dataset.intensity))
    if max_val == 0 or np.isnan(max_val):
        raise ValueError("Cannot normalize: dataset has zero or undefined intensity.")
    new_dataset.intensity = new_dataset.intensity / max_val
    return new_dataset

def scale_dataset(dataset: Dataset, factor: float) -> Dataset:
    """Return a copy of the dataset with intensity scaled by the factor."""
    new_dataset = dataset.copy()
    new_dataset.intensity = new_dataset.intensity * float(factor)
    return new_dataset

def modify_axes(dataset: Dataset, factor: float) -> Dataset:
    """Return a copy of the dataset with intensity scaled by the factor."""
    new_dataset = dataset.copy()
    
    return new_dataset

def crop_dataset(dataset: Dataset, x_min: float, x_max: float, y_min: float, y_max: float) -> Dataset:
    """
    Return a cropped copy of the dataset using absolute axis bounds.

    Args:
        x_min: Lower bound along the x-axis.
        x_max: Upper bound along the x-axis.
        y_min: Lower bound along the y-axis.
        y_max: Upper bound along the y-axis.
    """
    if np.isnan(x_min) or np.isnan(x_max) or np.isnan(y_min) or np.isnan(y_max):
        raise ValueError("Crop bounds must be finite numbers.")

    new_dataset = dataset.copy()
    if len(new_dataset.x_axis) == 0 or len(new_dataset.y_axis) == 0:
        raise ValueError("Cannot crop dataset with empty axes.")

    def _index_bounds(axis_values: np.ndarray, start_val: float, end_val: float) -> tuple[int, int]:
        low = min(start_val, end_val)
        high = max(start_val, end_val)
        axis_min = float(np.nanmin(axis_values))
        axis_max = float(np.nanmax(axis_values))

        low = max(low, axis_min)
        high = min(high, axis_max)
        if low >= high:
            raise ValueError(
                f"Crop bounds [{start_val}, {end_val}] do not overlap axis range [{axis_min}, {axis_max}]."
            )

        mask = (axis_values >= low) & (axis_values <= high)
        indices = np.where(mask)[0]
        if indices.size == 0:
            raise ValueError("Crop bounds yield an empty selection.")

        start_idx = int(indices[0])
        end_idx = int(indices[-1]) + 1
        return start_idx, end_idx

    y_vals = np.asarray(new_dataset.y_axis.values, dtype=float)
    x_vals = np.asarray(new_dataset.x_axis.values, dtype=float)
    y_start_idx, y_end_idx = _index_bounds(y_vals, y_min, y_max)
    x_start_idx, x_end_idx = _index_bounds(x_vals, x_min, x_max)

    slices = [
        slice(y_start_idx, y_end_idx),
        slice(x_start_idx, x_end_idx),
    ]
    slices.extend([slice(None)] * (new_dataset.intensity.ndim - 2))
    new_dataset.intensity = new_dataset.intensity[tuple(slices)]
    new_dataset.y_axis.values = new_dataset.y_axis.values[y_start_idx:y_end_idx].copy()
    new_dataset.x_axis.values = new_dataset.x_axis.values[x_start_idx:x_end_idx].copy()
    new_dataset.validate()
    return new_dataset


def modify_axes(
    dataset: Dataset,
    x_value: float | None = None,
    y_value: float | None = None,
    operation: str = "add",
) -> Dataset:
    """
    Return a copy of the dataset with its axes modified arithmetically.

    Args:
        x_value: Numeric value to apply to the x-axis (None to skip).
        y_value: Numeric value to apply to the y-axis (None to skip).
        operation: One of {"add", "subtract", "multiply", "divide"}.
    """
    if x_value is None and y_value is None:
        raise ValueError("Provide at least one axis value to modify.")
    if operation not in {"add", "subtract", "multiply", "divide"}:
        raise ValueError("operation must be add, subtract, multiply, or divide.")

    def apply_op(values: np.ndarray, value: float) -> np.ndarray:
        if operation == "add":
            return values + value
        if operation == "subtract":
            return values - value
        if operation == "multiply":
            return values * value
        if operation == "divide":
            if value == 0:
                raise ValueError("Cannot divide axis by zero.")
            return values / value
        raise ValueError("Unsupported operation.")

    new_dataset = dataset.copy()
    if x_value is not None:
        new_dataset.x_axis.values = apply_op(np.asarray(new_dataset.x_axis.values, dtype=float), float(x_value))
    if y_value is not None:
        new_dataset.y_axis.values = apply_op(np.asarray(new_dataset.y_axis.values, dtype=float), float(y_value))
    new_dataset.validate()
    return new_dataset

def modify_intensity(
    dataset: Dataset,
    reference_dataset: Dataset,
    operation: str,
) -> Dataset:
    """Combine dataset intensity with a reference dataset using an arithmetic operation."""
    if operation not in {"add", "subtract", "multiply", "divide"}:
        raise ValueError("operation must be add, subtract, multiply, or divide.")

    target_shape = dataset.intensity.shape
    reference_shape = reference_dataset.intensity.shape
    if target_shape != reference_shape:
        raise ValueError(
            "Reference dataset must have the same intensity shape as the current dataset "
            f"(got {reference_shape}, expected {target_shape})."
        )

    new_dataset = dataset.copy()
    reference_values = np.asarray(reference_dataset.intensity)

    if operation == "add":
        new_dataset.intensity = new_dataset.intensity + reference_values
    elif operation == "subtract":
        new_dataset.intensity = new_dataset.intensity - reference_values
    elif operation == "multiply":
        new_dataset.intensity = new_dataset.intensity * reference_values
    elif operation == "divide":
        if np.any(reference_values == 0):
            raise ValueError("Cannot divide by reference dataset containing zero intensity values.")
        new_dataset.intensity = new_dataset.intensity / reference_values

    new_dataset.validate()
    return new_dataset
