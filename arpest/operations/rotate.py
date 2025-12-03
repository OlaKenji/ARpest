"""Dataset rotation helpers."""

from __future__ import annotations

from typing import Tuple

import numpy as np

from ..models import Dataset


def rotate_dataset(
    dataset: Dataset,
    angle_degrees: float,
    center_x: float | None = None,
    center_y: float | None = None,
    fill_value: float = np.nan,
) -> Dataset:
    """
    Rotate the dataset in the x/y plane using bilinear interpolation.

    Args:
        dataset: Dataset to rotate. The first two axes (y, x) must be defined.
        angle_degrees: Rotation angle in degrees, counter-clockwise.
        center_x: X coordinate of the rotation centre. Defaults to axis mid-point.
        center_y: Y coordinate of the rotation centre. Defaults to axis mid-point.
        fill_value: Value assigned outside the original domain (default NaN).
    """
    if dataset.intensity.ndim < 2:
        raise ValueError("Rotate operation requires at least a 2D dataset.")

    x_axis = np.asarray(dataset.x_axis.values, dtype=float)
    y_axis = np.asarray(dataset.y_axis.values, dtype=float)
    if x_axis.size < 2 or y_axis.size < 2:
        raise ValueError("Rotate operation requires axes with at least 2 points.")
    if not np.isfinite(angle_degrees):
        raise ValueError("Rotation angle must be a finite number.")

    cx = float(center_x) if center_x is not None else float(np.nanmean(x_axis))
    cy = float(center_y) if center_y is not None else float(np.nanmean(y_axis))
    theta = np.deg2rad(float(angle_degrees))

    x_grid, y_grid = np.meshgrid(x_axis, y_axis)
    rotated_x, rotated_y = _rotate_points(x_grid, y_grid, theta, cx, cy)
    x_min, x_max = float(np.nanmin(rotated_x)), float(np.nanmax(rotated_x))
    y_min, y_max = float(np.nanmin(rotated_y)), float(np.nanmax(rotated_y))
    if not (np.isfinite(x_min) and np.isfinite(x_max) and np.isfinite(y_min) and np.isfinite(y_max)):
        raise ValueError("Rotation produced invalid bounds; check axis values.")

    x_new = np.linspace(x_min, x_max, x_axis.size)
    y_new = np.linspace(y_min, y_max, y_axis.size)
    if x_axis[-1] < x_axis[0]:
        x_new = x_new[::-1]
    if y_axis[-1] < y_axis[0]:
        y_new = y_new[::-1]

    target_x, target_y = np.meshgrid(x_new, y_new)
    source_x, source_y = _rotate_points(target_x, target_y, -theta, cx, cy)

    interp_x, x_reversed = _prepare_axis_for_interpolation(x_axis)
    interp_y, y_reversed = _prepare_axis_for_interpolation(y_axis)

    values = np.asarray(dataset.intensity, dtype=float)
    if x_reversed:
        values = values[:, ::-1, ...]
    if y_reversed:
        values = values[::-1, ...]

    rotated_values = _interpolate_grid(
        interp_x,
        interp_y,
        values,
        source_x,
        source_y,
        fill_value=fill_value,
    )

    new_dataset = dataset.copy()
    new_dataset.intensity = rotated_values
    new_dataset.x_axis.values = np.asarray(x_new, dtype=float)
    new_dataset.y_axis.values = np.asarray(y_new, dtype=float)
    new_dataset.validate()
    return new_dataset


def _rotate_points(
    x: np.ndarray,
    y: np.ndarray,
    theta: float,
    cx: float,
    cy: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Rotate x/y coordinates around the provided centre."""
    sin_t = np.sin(theta)
    cos_t = np.cos(theta)
    x_shift = x - cx
    y_shift = y - cy
    x_rot = cos_t * x_shift - sin_t * y_shift + cx
    y_rot = sin_t * x_shift + cos_t * y_shift + cy
    return x_rot, y_rot


def _prepare_axis_for_interpolation(axis: np.ndarray) -> tuple[np.ndarray, bool]:
    """Return an ascending version of the axis and whether it was reversed."""
    axis = np.asarray(axis, dtype=float)
    if axis.ndim != 1 or axis.size == 0:
        raise ValueError("Axis arrays must be one-dimensional.")
    diffs = np.diff(axis)
    if np.all(diffs >= 0):
        return axis.copy(), False
    if np.all(diffs <= 0):
        return axis[::-1].copy(), True
    raise ValueError("Axis values must be monotonic for interpolation.")


def _interpolate_grid(
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    values: np.ndarray,
    x_points: np.ndarray,
    y_points: np.ndarray,
    fill_value: float = np.nan,
) -> np.ndarray:
    """
    Bilinear interpolation of `values` defined on (y_axis, x_axis) grid.
    """
    ny, nx = len(y_axis), len(x_axis)
    if nx < 2 or ny < 2:
        raise ValueError("Interpolation requires axes with at least 2 points.")

    rest_shape = values.shape[2:]
    if rest_shape:
        flat_values = values.reshape(ny, nx, -1)
    else:
        flat_values = values.reshape(ny, nx, 1)

    points_x = np.asarray(x_points, dtype=float).ravel()
    points_y = np.asarray(y_points, dtype=float).ravel()
    if points_x.size != points_y.size:
        raise ValueError("Point grids must be the same size.")

    result = np.full((points_x.size, flat_values.shape[-1]), fill_value, dtype=float)

    x_min, x_max = x_axis[0], x_axis[-1]
    y_min, y_max = y_axis[0], y_axis[-1]
    valid = (
        np.isfinite(points_x)
        & np.isfinite(points_y)
        & (points_x >= min(x_min, x_max))
        & (points_x <= max(x_min, x_max))
        & (points_y >= min(y_min, y_max))
        & (points_y <= max(y_min, y_max))
    )
    if np.any(valid):
        px = points_x[valid]
        py = points_y[valid]

        x_hi = np.searchsorted(x_axis, px, side="right")
        y_hi = np.searchsorted(y_axis, py, side="right")
        x_hi = np.clip(x_hi, 1, nx - 1)
        y_hi = np.clip(y_hi, 1, ny - 1)
        x_lo = x_hi - 1
        y_lo = y_hi - 1

        x0 = x_axis[x_lo]
        x1 = x_axis[x_hi]
        y0 = y_axis[y_lo]
        y1 = y_axis[y_hi]

        denom_x = np.where(x1 != x0, x1 - x0, 1.0)
        denom_y = np.where(y1 != y0, y1 - y0, 1.0)
        wx = np.clip((px - x0) / denom_x, 0.0, 1.0)
        wy = np.clip((py - y0) / denom_y, 0.0, 1.0)

        i00 = flat_values[y_lo, x_lo, :]
        i01 = flat_values[y_lo, x_hi, :]
        i10 = flat_values[y_hi, x_lo, :]
        i11 = flat_values[y_hi, x_hi, :]

        w00 = (1.0 - wx) * (1.0 - wy)
        w01 = wx * (1.0 - wy)
        w10 = (1.0 - wx) * wy
        w11 = wx * wy

        interpolated = (
            i00 * w00[:, None]
            + i01 * w01[:, None]
            + i10 * w10[:, None]
            + i11 * w11[:, None]
        )
        result[valid] = interpolated

    final_shape = y_points.shape + rest_shape if rest_shape else y_points.shape
    return result.reshape(final_shape)
