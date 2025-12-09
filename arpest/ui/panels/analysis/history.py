"""Shared capture-history data structures for analysis modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional
from uuid import uuid4

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from ....models import Dataset


@dataclass(frozen=True)
class CaptureEntry:
    """Base metadata for captured content."""

    id: str
    dataset_label: str
    timestamp: datetime


@dataclass(frozen=True)
class ViewCaptureEntry(CaptureEntry):
    """Captured figure or panel dataset."""

    view_id: Optional[str]
    view_label: str
    dataset: Dataset
    colormap: str
    integration_radius: int


@dataclass(frozen=True)
class CurveCaptureEntry(CaptureEntry):
    """Captured EDC/MDC curve."""

    kind: str
    axis_name: str
    axis_unit: str
    axis_values: np.ndarray
    intensity: np.ndarray

    @property
    def label(self) -> str:
        unit = f" ({self.axis_unit})" if self.axis_unit else ""
        return f"{self.kind} – {self.axis_name}{unit}"


class CaptureHistoryModel(QObject):
    """Model storing captured datasets and curves for reuse across modules."""

    entries_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[CaptureEntry] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def entries(self) -> list[CaptureEntry]:
        return list(self._entries)

    def set_entries(self, entries: Iterable[CaptureEntry]) -> None:
        self._entries = list(entries)
        self.entries_changed.emit()

    def view_entries(self) -> list[ViewCaptureEntry]:
        return [entry for entry in self._entries if isinstance(entry, ViewCaptureEntry)]

    def curve_entries(self) -> list[CurveCaptureEntry]:
        return [entry for entry in self._entries if isinstance(entry, CurveCaptureEntry)]

    def get_entry(self, entry_id: str) -> CaptureEntry | None:
        return next((entry for entry in self._entries if entry.id == entry_id), None)

    def add_view_capture(
        self,
        *,
        dataset_label: str,
        dataset: Dataset,
        view_id: Optional[str],
        view_label: str,
        colormap: str,
        integration_radius: int,
    ) -> ViewCaptureEntry:
        entry = ViewCaptureEntry(
            id=str(uuid4()),
            dataset_label=dataset_label,
            timestamp=datetime.utcnow(),
            view_id=view_id,
            view_label=view_label,
            dataset=dataset,
            colormap=colormap,
            integration_radius=integration_radius,
        )
        self._prepend(entry)
        return entry

    def add_curve_capture(
        self,
        *,
        dataset_label: str,
        kind: str,
        axis_name: str,
        axis_unit: str,
        axis_values: np.ndarray,
        intensity: np.ndarray,
    ) -> CurveCaptureEntry:
        entry = CurveCaptureEntry(
            id=str(uuid4()),
            dataset_label=dataset_label,
            timestamp=datetime.utcnow(),
            kind=kind,
            axis_name=axis_name,
            axis_unit=axis_unit,
            axis_values=np.asarray(axis_values, dtype=float),
            intensity=np.asarray(intensity, dtype=float),
        )
        self._prepend(entry)
        return entry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepend(self, entry: CaptureEntry) -> None:
        self._entries.insert(0, entry)
        self.entries_changed.emit()

    def remove_entry(self, entry_id: str) -> bool:
        for idx, entry in enumerate(self._entries):
            if entry.id == entry_id:
                self._entries.pop(idx)
                self.entries_changed.emit()
                return True
        return False

    def remove_entries(self, entry_ids: Iterable[str]) -> int:
        removed = 0
        for entry_id in list(entry_ids):
            if self.remove_entry(entry_id):
                removed += 1
        return removed
