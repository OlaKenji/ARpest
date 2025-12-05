"""Normalisation helpers for higher dimensional datasets."""

from __future__ import annotations

import numpy as np

from ..models import Dataset


def normalise_slices(dataset: Dataset) -> Dataset:
    """Normalise each slice along the scan axis of a 3D dataset.

    The integrated intensity of every slice (summed over the x/y axes) is
    scaled to 1.0 so that intensity variations caused by different numbers of
    sweeps or changing flux are reduced.
    """

    if not dataset.is_3d or dataset.z_axis is None:
        raise ValueError("Normalise slices requires a 3D dataset with a scan axis.")

    data = np.asarray(dataset.intensity, dtype=float)
    if data.ndim != 3:
        raise ValueError(
            "Normalise slices only supports datasets with three intensity dimensions."
        )

    per_slice_total = np.nansum(np.abs(data), axis=(0,2))

    # Sum absolute intensities over (y, x) for every scan slice to avoid
    # cancellations from negative values.
    #per_slice_total = np.nansum(np.abs(data), axis=(0, 1))
    valid_mask = np.isfinite(per_slice_total) & (per_slice_total > 0)
    if not np.any(valid_mask):
        raise ValueError(
            "Cannot normalise slices because every scan slice has zero total intensity."
        )

    # Build scaling array; leave zero-intensity slices unchanged.
    scale = np.ones_like(per_slice_total, dtype=float)
    scale[valid_mask] = 1.0 / per_slice_total[valid_mask]

    new_dataset = dataset.copy()
    new_dataset.intensity = data * scale.reshape((1, -1, 1))
    new_dataset.validate()
    return new_dataset


# Provide US spelling alias for backwards compatibility.
normalize_slices = normalise_slices
