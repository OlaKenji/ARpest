"""Analysis tab housing reusable visualization canvas and modules."""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....models import Axis, Dataset, FileStack
from ....visualization.analysis_canvas import AnalysisCanvas, CurveDisplayData
from .history import CaptureEntry, CaptureHistoryModel, CurveCaptureEntry, ViewCaptureEntry
from .widgets import FittingModule, OverplotModule


class AnalysisPanel(QWidget):
    """Container for analysis modules and the shared visualization canvas."""

    def __init__(
        self,
        get_file_stack: Callable[[], FileStack | None],
        canvas: AnalysisCanvas,
        capture_view_callback: Callable[[str | None], tuple[Dataset, str, int]],
        context_providers: dict[str, Callable[[], object]] | None = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.canvas = canvas
        self._capture_view_callback = capture_view_callback
        self.context_providers = context_providers or {}
        self.capture_history = CaptureHistoryModel()
        self.capture_history.entries_changed.connect(self._refresh_history_view)
        self._curve_selection_callbacks: list[Callable[[CurveCaptureEntry | None], None]] = []
        self._current_curve_selection: CurveCaptureEntry | None = None
        self._history_curve_palette = [
            "#1f77b4",
            "#d62728",
            "#2ca02c",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
        ]

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        description = QLabel(
            "Capture images from the active dataset to analyse them. "
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        panel_row = QHBoxLayout()
        panel_row.addWidget(QLabel("Capture panel:"))
        self.capture_top_left_btn = QPushButton("Top-left")
        self.capture_top_left_btn.setToolTip("Capture the top-left view (Fermi map / primary image).")
        self.capture_top_left_btn.clicked.connect(lambda: self._capture_named_view("top_left"))
        panel_row.addWidget(self.capture_top_left_btn)

        self.capture_top_right_btn = QPushButton("Top-right")
        self.capture_top_right_btn.setToolTip("Capture the top-right cut (Band @ X).")
        self.capture_top_right_btn.clicked.connect(lambda: self._capture_named_view("top_right"))
        panel_row.addWidget(self.capture_top_right_btn)

        self.capture_bottom_left_btn = QPushButton("Bottom-left")
        self.capture_bottom_left_btn.setToolTip("Capture the bottom-left cut (Band @ Y).")
        self.capture_bottom_left_btn.clicked.connect(lambda: self._capture_named_view("bottom_left"))
        panel_row.addWidget(self.capture_bottom_left_btn)
        panel_row.addStretch()
        layout.addLayout(panel_row)

        curve_row = QHBoxLayout()
        curve_row.addWidget(QLabel("Capture curves:"))
        self.capture_edc_btn = QPushButton("Current EDC")
        self.capture_edc_btn.setToolTip("Capture the current EDC trace (energy distribution curve).")
        self.capture_edc_btn.clicked.connect(lambda: self._capture_curves("current_mdc_curves", "EDC"))
        curve_row.addWidget(self.capture_edc_btn)

        self.capture_mdc_btn = QPushButton("Current MDC")
        self.capture_mdc_btn.setToolTip("Capture the current MDC trace (momentum distribution curve).")
        self.capture_mdc_btn.clicked.connect(lambda: self._capture_curves("current_edc_curves", "MDC"))
        curve_row.addWidget(self.capture_mdc_btn)
        curve_row.addStretch()
        layout.addLayout(curve_row)

        history_header = QHBoxLayout()
        history_label = QLabel("Capture history:")
        history_label.setStyleSheet("font-weight: bold;")
        history_header.addWidget(history_label)
        self.remove_history_btn = QPushButton("Remove selected")
        self.remove_history_btn.setEnabled(False)
        self.remove_history_btn.clicked.connect(self._remove_selected_history_items)
        history_header.addWidget(self.remove_history_btn)        
        
        self.clear_canvas_btn = QPushButton("Clear canvas")
        self.clear_canvas_btn.clicked.connect(lambda: self.canvas.clear("No analysis data yet."))
        history_header.addWidget(self.clear_canvas_btn)
        history_header.addStretch()
        layout.addLayout(history_header)

        self.history_tree = QTreeWidget()
        self.history_tree.setColumnCount(3)
        self.history_tree.setHeaderLabels(["Type", "Dataset", "Source"])
        header = self.history_tree.header()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        policy = self.history_tree.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Fixed)
        policy.setHorizontalPolicy(QSizePolicy.Expanding)
        self.history_tree.setSizePolicy(policy)
        self.history_tree.setFixedHeight(100)
        layout.addWidget(self.history_tree)
        self.history_tree.itemSelectionChanged.connect(self._on_history_selection_changed)
        self._refresh_history_view()
        self._notify_curve_selection(None)

        self.modules_tab = QTabWidget()
        self.modules_tab.setTabPosition(QTabWidget.North)
        self.modules_tab.setDocumentMode(True)

        self.overplot_module = OverplotModule(canvas=self.canvas, capture_history=self.capture_history)

        self.modules_tab.addTab(self.overplot_module, "Overplot")

        self.fitting_module = FittingModule(
            get_file_stack=self.get_file_stack,
            context_providers=self.context_providers,
            canvas=self.canvas,
            register_curve_selection_callback=self.register_curve_selection_listener,
        )
        fitting_scroll = QScrollArea()
        fitting_scroll.setWidgetResizable(True)
        fitting_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        fitting_scroll.setWidget(self.fitting_module)
        self.modules_tab.addTab(fitting_scroll, "Fitting")
        layout.addWidget(self.modules_tab)

        self.setLayout(layout)

    def _on_capture_view_clicked(self) -> None:
        self._capture_with_feedback(None)

    def _capture_named_view(self, view_id: str) -> None:
        self._capture_with_feedback(view_id)

    def _capture_with_feedback(self, view_id: Optional[str]) -> None:
        try:
            dataset, colormap, integration_radius = self._capture_view_callback(view_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Capture failed", str(exc))
            return
        self._record_view_capture(view_id, dataset, colormap, integration_radius)

    def _capture_curves(self, context_key: str, kind: str) -> None:
        stack = self.get_file_stack()
        if stack is None:
            QMessageBox.warning(self, "No dataset", "Select a dataset before capturing curves.")
            return

        provider = self.context_providers.get(context_key)
        if provider is None:
            QMessageBox.warning(self, "Unavailable", "The current visualization does not provide this data.")
            return

        try:
            raw_curves = provider()
        except Exception:
            raw_curves = None
        if not raw_curves:
            QMessageBox.information(self, "Nothing to capture", "No curve data is available right now.")
            return

        dataset = stack.current_state
        dataset_label = self._dataset_label(stack)
        added = False
        new_entries: list[CurveCaptureEntry] = []
        for axis_key, values in raw_curves.items():
            axis = self._axis_from_key(dataset, axis_key)
            if axis is None:
                continue
            entry = self.capture_history.add_curve_capture(
                dataset_label=dataset_label,
                kind=kind,
                axis_name=axis.name,
                axis_unit=axis.unit,
                axis_values=axis.values,
                intensity=np.asarray(values, dtype=float),
            )
            new_entries.append(entry)
            added = True

        if not added:
            QMessageBox.information(
                self,
                "Unsupported",
                "Could not determine axis information for the captured curve.",
            )
            return

        self._display_curve_entries(new_entries)

    def _record_view_capture(
        self,
        view_id: Optional[str],
        dataset: Dataset,
        colormap: str,
        integration_radius: int,
    ) -> None:
        stack = self.get_file_stack()
        dataset_label = self._dataset_label(stack)
        view_label = self._describe_view(view_id)
        self.capture_history.add_view_capture(
            dataset_label=dataset_label,
            dataset=dataset,
            view_id=view_id,
            view_label=view_label,
            colormap=colormap,
            integration_radius=integration_radius,
        )

    def _refresh_history_view(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        self.history_tree.clear()
        for entry in self.capture_history.entries():
            item = QTreeWidgetItem()
            if isinstance(entry, ViewCaptureEntry):
                item.setText(0, "Figure")
                item.setText(2, entry.view_label)
                tooltip = f"Captured {entry.timestamp:%Y-%m-%d %H:%M:%S} UTC"
            elif isinstance(entry, CurveCaptureEntry):
                item.setText(0, f"{entry.kind} curve")
                item.setText(2, entry.label)
                tooltip = (
                    f"{entry.label} captured {entry.timestamp:%Y-%m-%d %H:%M:%S} UTC"
                )
            else:
                tooltip = ""
            item.setText(1, entry.dataset_label)
            item.setToolTip(0, tooltip)
            item.setToolTip(1, entry.dataset_label)
            item.setData(0, Qt.UserRole, entry.id)
            self.history_tree.addTopLevelItem(item)
        if hasattr(self, "remove_history_btn"):
            self.remove_history_btn.setEnabled(False)

    def _on_history_selection_changed(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        items = self.history_tree.selectedItems()
        has_selection = bool(items)
        if hasattr(self, "remove_history_btn"):
            self.remove_history_btn.setEnabled(has_selection)
        if not items:
            self._notify_curve_selection(None)
            return
        entry_ids = [item.data(0, Qt.UserRole) for item in items if item.data(0, Qt.UserRole)]
        if not entry_ids:
            self._notify_curve_selection(None)
            return

        view_entries: list[ViewCaptureEntry] = []
        curve_entries: list[CurveCaptureEntry] = []
        for entry_id in entry_ids:
            entry = self.capture_history.get_entry(entry_id)
            if isinstance(entry, ViewCaptureEntry):
                view_entries.append(entry)
            elif isinstance(entry, CurveCaptureEntry):
                curve_entries.append(entry)

        selected_curve = curve_entries[0] if curve_entries else None

        if view_entries:
            entry = view_entries[0]
            self.canvas.display_dataset(
                entry.dataset,
                colormap=entry.colormap,
                integration_radius=entry.integration_radius,
            )
            self._notify_curve_selection(selected_curve)
            return

        if curve_entries:
            self._display_curve_entries(curve_entries)
        else:
            self.canvas.clear("No curves captured yet.")
        self._notify_curve_selection(selected_curve)

    def _remove_selected_history_items(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        items = self.history_tree.selectedItems()
        if not items:
            return
        entry_ids = [item.data(0, Qt.UserRole) for item in items if item.data(0, Qt.UserRole)]
        if not entry_ids:
            return
        self.capture_history.remove_entries(entry_ids)

    def _display_curve_entries(self, entries: list[CurveCaptureEntry]) -> None:
        curve_data = [
            CurveDisplayData(
                axis_values=entry.axis_values,
                intensity=entry.intensity,
                label=f"{entry.dataset_label} – {entry.label}",
                axis_label=f"{entry.axis_name} ({entry.axis_unit})"
                if entry.axis_unit
                else entry.axis_name,
                color=self._history_curve_palette[idx % len(self._history_curve_palette)],
            )
            for idx, entry in enumerate(entries)
        ]
        if curve_data:
            self.canvas.display_curves(curve_data)

    def register_curve_selection_listener(
        self, callback: Callable[[CurveCaptureEntry | None], None]
    ) -> None:
        self._curve_selection_callbacks.append(callback)
        callback(self._current_curve_selection)

    def _notify_curve_selection(self, entry: CurveCaptureEntry | None) -> None:
        self._current_curve_selection = entry
        for callback in self._curve_selection_callbacks:
            callback(entry)

    def serialize_state(self) -> dict:
        selected_id = self._current_curve_selection.id if self._current_curve_selection else None
        return {
            "capture_entries": self.capture_history.entries(),
            "selected_entry_id": selected_id,
            "fitting": self.fitting_module.serialize_state(),
        }

    def apply_state(self, state: dict | None) -> None:
        if not state:
            self.capture_history.set_entries([])
            self.fitting_module.apply_state(None, set())
            if hasattr(self, "history_tree"):
                self.history_tree.clearSelection()
            return
        entries = list(state.get("capture_entries") or [])
        self.capture_history.set_entries(entries)
        available_ids = {entry.id for entry in entries if isinstance(entry, CaptureEntry)}
        self.fitting_module.apply_state(state.get("fitting"), available_ids)
        selected_id = state.get("selected_entry_id")
        if selected_id:
            self._select_history_entry(selected_id)
        elif hasattr(self, "history_tree"):
            self.history_tree.clearSelection()

    def _select_history_entry(self, entry_id: str) -> None:
        if not hasattr(self, "history_tree"):
            return
        for idx in range(self.history_tree.topLevelItemCount()):
            item = self.history_tree.topLevelItem(idx)
            if item.data(0, Qt.UserRole) == entry_id:
                self.history_tree.setCurrentItem(item)
                return
        self.history_tree.clearSelection()

    def _describe_view(self, view_id: Optional[str]) -> str:
        mapping = {
            None: "Full figure",
            "top_left": "Top-left panel",
            "top_right": "Top-right panel",
            "bottom_left": "Bottom-left panel",
        }
        return mapping.get(view_id, view_id or "Unknown view")

    def _dataset_label(self, stack: FileStack | None) -> str:
        if stack is None:
            return "Unknown dataset"
        return f"{stack.filename} [{stack.current_name}]"

    def _axis_from_key(self, dataset: Dataset, key: str) -> Axis | None:
        key_lower = key.lower().split("_", 1)[0]
        if key_lower == "x":
            return dataset.x_axis
        if key_lower == "y":
            return dataset.y_axis
        if key_lower == "z":
            return dataset.z_axis
        if key_lower == "w":
            return dataset.w_axis
        return None
