"""Widget that exports currently visible panels and curves to JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .base import OperationWidget
from ......models import Axis, Dataset
from ......operations.export import curve_to_json_payload, dataset_to_json_payload


@dataclass
class _PanelCapture:
    dataset: Dataset
    view_id: str


@dataclass
class _CurveCapture:
    axis: Axis
    intensity: np.ndarray
    kind: str


@dataclass
class _CapturedEntry:
    label: str
    kind: str
    details: str
    payload: _PanelCapture | _CurveCapture


class ExportWidget(OperationWidget):
    title = "Export captured data"
    category = "Export"
    description = (
        "Capture the visible panels or current MDC/EDC and export them into a "
        "single JSON file without altering the dataset state."
    )

    def __init__(self, *args, **kwargs) -> None:
        self._entries: list[_CapturedEntry] = []
        super().__init__(*args, **kwargs)

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        description = QLabel(
            "Capture the current panels (top-left/top-right/bottom-left) or the "
            "current MDC/EDC curves, inspect them in the table, then export all "
            "listed entries into a single JSON document."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        view_buttons = QHBoxLayout()
        #view_buttons.addWidget(QLabel("Capture:"))
        for key, label in (
            ("panel_dataset_top_left", "T-left"),
            ("panel_dataset_top_right", "T-right"),
            ("panel_dataset_bottom_left", "B-left"),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, k=key, l=label: self._capture_panel(k, l))
            view_buttons.addWidget(btn)
        view_buttons.addStretch()
        layout.addLayout(view_buttons)

        curve_buttons = QHBoxLayout()
        edc_btn = QPushButton("EDC")
        edc_btn.clicked.connect(lambda: self._capture_curves("current_edc_curves", "EDC"))
        mdc_btn = QPushButton("MDC")
        mdc_btn.clicked.connect(lambda: self._capture_curves("current_mdc_curves", "MDC"))
        curve_buttons.addWidget(edc_btn)
        curve_buttons.addWidget(mdc_btn)
        curve_buttons.addStretch()
        layout.addLayout(curve_buttons)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Label", "Kind", "Details", "Source"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(False)
        layout.addWidget(self.table)

        action_row = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_entries)
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_entries)
        action_row.addStretch()
        action_row.addWidget(clear_btn)
        action_row.addWidget(export_btn)
        layout.addLayout(action_row)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Capture helpers
    # ------------------------------------------------------------------
    def _capture_panel(self, context_key: str, label: str) -> None:
        dataset = self._get_context_value(context_key)
        if dataset is None:
            QMessageBox.information(self, "Unavailable", "No data is available for that panel right now.")
            return

        dataset_copy = dataset.copy()
        entry_label = f"{self._dataset_label()}_{label.replace(' ', '').lower()}"
        details = entry_label
        payload = _PanelCapture(dataset=dataset_copy, view_id=label)
        self._entries.append(_CapturedEntry(entry_label, "Panel", details, payload))
        self._refresh_table()

    def _capture_curves(self, context_key: str, label: str) -> None:
        stack = self.get_file_stack()
        if stack is None:
            QMessageBox.warning(self, "No dataset", "Select a dataset before capturing curves.")
            return

        raw_curves = self._get_context_value(context_key)
        if not raw_curves:
            QMessageBox.information(self, "Unavailable", f"No {label} data is available right now.")
            return

        dataset = stack.current_state
        added = False
        for axis_key, values in raw_curves.items():
            axis = self._axis_from_key(dataset, axis_key)
            if axis is None:
                continue
            axis_copy = Axis(axis.values.copy(), axis.axis_type, axis.name, axis.unit)
            intensity = np.asarray(values, dtype=float)
            if intensity.size != len(axis_copy.values):
                continue
            axis_part = axis_key.upper()
            entry_label = f"{self._dataset_label()}_{label.lower()}_{axis_part.lower()}"
            details = f"{entry_label} ({intensity.size} pts)"
            payload = _CurveCapture(axis=axis_copy, intensity=intensity, kind=label)
            self._entries.append(_CapturedEntry(entry_label, "Curve", details, payload))
            added = True

        if not added:
            QMessageBox.information(self, "Unsupported", "Could not determine axis information for the captured curve.")
            return

        self._refresh_table()

    # ------------------------------------------------------------------
    # Table management
    # ------------------------------------------------------------------
    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.label))
            self.table.setItem(row, 1, QTableWidgetItem(entry.kind))
            self.table.setItem(row, 2, QTableWidgetItem(entry.details))
            source = "Panel" if isinstance(entry.payload, _PanelCapture) else entry.payload.kind
            self.table.setItem(row, 3, QTableWidgetItem(source))

    def _clear_entries(self) -> None:
        if not self._entries:
            return
        self._entries.clear()
        self.table.setRowCount(0)

    # ------------------------------------------------------------------
    # Export logic
    # ------------------------------------------------------------------
    def _export_entries(self) -> None:
        if not self._entries:
            QMessageBox.information(self, "Nothing to export", "Capture at least one panel or curve first.")
            return

        start_path = self._get_context_value("start_path") or str(Path.home())
        target_dir = QFileDialog.getExistingDirectory(
            self,
            "Export captured data",
            str(start_path),
        )
        if not target_dir:
            return

        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        exported = 0
        used_names: set[str] = set()
        for index, entry in enumerate(self._entries, start=1):
            base_name = self._sanitize_filename(entry.label) or f"entry_{index}"
            candidate = base_name
            counter = 1
            while candidate in used_names:
                counter += 1
                candidate = f"{base_name}_{counter}"
            used_names.add(candidate)

            try:
                if isinstance(entry.payload, _PanelCapture):
                    payload = dataset_to_json_payload(entry.payload.dataset, label=entry.label)
                else:
                    payload = curve_to_json_payload(
                        entry.payload.axis,
                        entry.payload.intensity,
                        label=entry.label,
                        curve_kind=entry.payload.kind,
                    )
            except Exception as exc:  # pragma: no cover - UI feedback path
                QMessageBox.warning(self, "Export issues", f"{entry.label}: {exc}")
                return

            output_file = target_path / f"{candidate}.json"
            with output_file.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            exported += 1

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved {exported} entr{'y' if exported == 1 else 'ies'} to {target_path}.",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _dataset_label(self) -> str:
        stack = self.get_file_stack()
        if stack is None:
            return "dataset"
        base = Path(stack.filename or "dataset").stem
        state = stack.current_name or "state"
        return f"{base}_{state}"

    def _axis_from_key(self, dataset: Dataset, key: str) -> Axis | None:
        lookup = key.lower().split("_", 1)[0]
        if lookup == "x":
            return dataset.x_axis
        if lookup == "y":
            return dataset.y_axis
        if lookup == "z":
            return dataset.z_axis
        if lookup == "w":
            return dataset.w_axis
        return None

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        safe_chars = [c if ("0" <= c <= "9") or ("a" <= c.lower() <= "z") or c in {"-", "_"} else "_" for c in name]
        sanitized = "".join(safe_chars).strip("._")
        return sanitized

    # This widget performs actions directly and does not create history states,
    # but OperationWidget requires an implementation.
    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:  # pragma: no cover - UI only
        return dataset, "export"
