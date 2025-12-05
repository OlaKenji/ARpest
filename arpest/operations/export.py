"""Utilities for converting datasets and curves into JSON-friendly payloads."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..models import Axis, Dataset


def dataset_to_json_payload(dataset: Dataset, *, label: str) -> dict[str, Any]:
    """Convert a dataset slice into a JSON-serializable dictionary."""

    def _axis_payload(axis: Axis | None) -> dict[str, Any] | None:
        if axis is None:
            return None
        return {
            "name": axis.name,
            "unit": axis.unit,
            "type": axis.axis_type.value,
            "values": np.asarray(axis.values, dtype=float).tolist(),
        }

    measurement = dataset.measurement
    payload: dict[str, Any] = {
        "label": label,
        "kind": "panel",
        "shape": list(dataset.intensity.shape),
        "intensity": np.asarray(dataset.intensity, dtype=float).tolist(),
        "axes": {
            "x": _axis_payload(dataset.x_axis),
            "y": _axis_payload(dataset.y_axis),
            "z": _axis_payload(dataset.z_axis),
            "w": _axis_payload(dataset.w_axis),
        },
        "metadata": {
            "photon_energy": measurement.photon_energy,
            "temperature": measurement.temperature,
            "beamline": measurement.beamline,
        },
        "source_file": dataset.filename,
    }
    return payload


def curve_to_json_payload(
    axis: Axis,
    intensity: np.ndarray,
    *,
    label: str,
    curve_kind: str,
) -> dict[str, Any]:
    """Convert a 1D curve into a JSON-serializable dictionary."""

    axis_values = np.asarray(axis.values, dtype=float)
    curve_values = np.asarray(intensity, dtype=float)
    if axis_values.size != curve_values.size:
        raise ValueError("Axis and intensity lengths do not match for export.")

    return {
        "label": label,
        "kind": "curve",
        "curve_type": curve_kind,
        "axis": {
            "name": axis.name,
            "unit": axis.unit,
            "type": axis.axis_type.value,
            "values": axis_values.tolist(),
        },
        "intensity": curve_values.tolist(),
    }
