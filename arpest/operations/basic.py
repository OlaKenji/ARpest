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
