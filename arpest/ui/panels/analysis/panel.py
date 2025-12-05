"""Analysis tab housing reusable visualization canvas and modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ....models import Axis, Dataset, FileStack
from ....visualization.analysis_canvas import AnalysisCanvas, CurveDisplayData


class AnalysisPanel(QWidget):
    """Container for analysis modules and the shared visualization canvas."""

    def __init__(
        self,
        get_file_stack: Callable[[], FileStack | None],
        canvas: AnalysisCanvas,
        capture_view_callback: Callable[[str | None], bool],
        context_providers: dict[str, Callable[[], object]] | None = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.canvas = canvas
        self._capture_view_callback = capture_view_callback
        self.context_providers = context_providers or {}

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        description = QLabel(
            "Capture slices or curves from the active dataset and analyse them here. "
            "When this tab is active, the main canvas on the left shows the captured data."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        capture_row = QHBoxLayout()
        self.capture_view_btn = QPushButton("Capture current figure")
        self.capture_view_btn.clicked.connect(self._on_capture_view_clicked)
        self.clear_canvas_btn = QPushButton("Clear canvas")
        self.clear_canvas_btn.clicked.connect(lambda: self.canvas.clear("No analysis data yet."))
        capture_row.addWidget(self.capture_view_btn)
        capture_row.addWidget(self.clear_canvas_btn)
        capture_row.addStretch()
        layout.addLayout(capture_row)

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

        self.modules_tab = QTabWidget()
        self.modules_tab.setTabPosition(QTabWidget.North)
        self.modules_tab.setDocumentMode(True)

        self.overplot_module = OverplotModule(
            get_file_stack=self.get_file_stack,
            context_providers=self.context_providers,
            canvas=self.canvas,
        )

        self.modules_tab.addTab(self.overplot_module, "Overplot")
        layout.addWidget(self.modules_tab)

        self.setLayout(layout)

    def _on_capture_view_clicked(self) -> None:
        self._capture_with_feedback(None)

    def _capture_named_view(self, view_id: str) -> None:
        self._capture_with_feedback(view_id)

    def _capture_with_feedback(self, view_id: Optional[str]) -> None:
        try:
            success = self._capture_view_callback(view_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Capture failed", str(exc))
            return
        if not success:
            QMessageBox.warning(
                self,
                "Capture failed",
                "Unable to capture the current figure. Ensure a dataset is loaded and try again.",
            )


@dataclass
class _CurveEntry:
    kind: str  # "EDC" or "MDC"
    axis: Axis
    intensity: np.ndarray
    dataset_label: str
    color: str

    @property
    def label(self) -> str:
        return f"{self.dataset_label} – {self.kind} ({self.axis.name})"


class OverplotModule(QWidget):
    """Simple module that overlays captured EDC/MDC curves."""

    _color_palette = [
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

    def __init__(
        self,
        *,
        get_file_stack: Callable[[], FileStack | None],
        context_providers: dict[str, Callable[[], object]],
        canvas: AnalysisCanvas,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.context_providers = context_providers
        self.canvas = canvas
        self._curves: list[_CurveEntry] = []
        self._color_index = 0

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        instructions = QLabel(
            "Use the buttons below to capture the current EDC or MDC from the active dataset. "
            "Captured curves are overplotted on the analysis canvas for comparison."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        button_row = QHBoxLayout()
        self.add_edc_btn = QPushButton("Add current EDC")
        self.add_mdc_btn = QPushButton("Add current MDC")
        self.remove_btn = QPushButton("Remove selected")
        self.clear_btn = QPushButton("Clear all")

        self.add_edc_btn.clicked.connect(lambda: self._capture_curves("current_mdc_curves", "EDC"))
        self.add_mdc_btn.clicked.connect(lambda: self._capture_curves("current_edc_curves", "MDC"))
        self.remove_btn.clicked.connect(self._remove_selected)
        self.clear_btn.clicked.connect(self._clear_curves)

        button_row.addWidget(self.add_edc_btn)
        button_row.addWidget(self.add_mdc_btn)
        button_row.addStretch()
        button_row.addWidget(self.remove_btn)
        button_row.addWidget(self.clear_btn)
        layout.addLayout(button_row)

        self.curve_list = QListWidget()
        self.curve_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.curve_list, stretch=1)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
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
        added = False
        for axis_key, values in raw_curves.items():
            axis = self._axis_from_key(dataset, axis_key)
            if axis is None:
                continue
            curve = _CurveEntry(
                kind=kind,
                axis=axis,
                intensity=np.asarray(values, dtype=float),
                dataset_label=f"{stack.filename} [{stack.current_name}]",
                color=self._next_color(),
            )
            self._curves.append(curve)
            added = True

        if not added:
            QMessageBox.information(self, "Unsupported", "Could not determine axis information for the captured curve.")
            return

        self._refresh_list()
        self._update_canvas()

    def _remove_selected(self) -> None:
        selected_indexes = sorted(
            {self.curve_list.row(item) for item in self.curve_list.selectedItems()},
            reverse=True,
        )
        for idx in selected_indexes:
            if 0 <= idx < len(self._curves):
                self._curves.pop(idx)
        self._refresh_list()
        self._update_canvas()

    def _clear_curves(self) -> None:
        self._curves.clear()
        self._color_index = 0
        self._refresh_list()
        self.canvas.clear("No curves captured yet.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _refresh_list(self) -> None:
        self.curve_list.clear()
        for curve in self._curves:
            item = QListWidgetItem(curve.label)
            item.setToolTip(curve.label)
            self.curve_list.addItem(item)

    def _update_canvas(self) -> None:
        curve_data = [
            CurveDisplayData(
                axis_values=curve.axis.values,
                intensity=curve.intensity,
                label=curve.label,
                axis_label=f"{curve.axis.name} ({curve.axis.unit})",
                color=curve.color,
            )
            for curve in self._curves
        ]
        self.canvas.display_curves(curve_data)

    def _next_color(self) -> str:
        color = self._color_palette[self._color_index % len(self._color_palette)]
        self._color_index += 1
        return color

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
