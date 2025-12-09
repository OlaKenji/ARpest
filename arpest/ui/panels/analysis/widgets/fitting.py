"""Interactive curve-fitting widget for captured EDC/MDC traces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
from uuid import uuid4

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from .....models import FileStack
from .....operations.fit import (
    FitComponentConfig,
    FitParameterConfig,
    FitResult,
    available_fit_functions,
    perform_curve_fit,
)
from .....visualization.analysis_canvas import AnalysisCanvas, CurveDisplayData
from ..history import CurveCaptureEntry


@dataclass
class _ParameterRow:
    """Holds the widgets controlling a single parameter."""

    value: QDoubleSpinBox
    fixed: QCheckBox
    lower: QLineEdit
    upper: QLineEdit


@dataclass
class _FitHistoryEntry:
    """Stores one fit result along with metadata for the UI."""

    id: str
    label: str
    result: FitResult


class _FitComponentWidget(QGroupBox):
    """Editor allowing tuning of one fit component."""

    removed = pyqtSignal(str)

    def __init__(self, spec, index: int) -> None:
        super().__init__(spec.label)
        self.spec = spec
        self.component_id = f"{spec.id}_{index}"
        self._rows: dict[str, _ParameterRow] = {}

        layout = QVBoxLayout()
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(QLabel(f"{spec.label} component"))
        header.addStretch()
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("class", "danger")
        remove_btn.clicked.connect(lambda: self.removed.emit(self.component_id))
        header.addWidget(remove_btn)
        layout.addLayout(header)

        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("Display label:"))
        self.label_edit = QLineEdit(f"{spec.label} #{index}")
        label_row.addWidget(self.label_edit)
        layout.addLayout(label_row)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        for param in spec.parameters:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            value_spin = QDoubleSpinBox()
            value_spin.setDecimals(6)
            value_spin.setRange(-1e9, 1e9)
            value_spin.setSingleStep(0.1)
            value_spin.setValue(param.default)

            fixed_box = QCheckBox("Fix")

            lower_edit = QLineEdit()
            lower_edit.setPlaceholderText("Lower")
            if param.lower is not None:
                lower_edit.setPlaceholderText(str(param.lower))

            upper_edit = QLineEdit()
            upper_edit.setPlaceholderText("Upper")
            if param.upper is not None:
                upper_edit.setPlaceholderText(str(param.upper))

            row_layout.addWidget(value_spin)
            row_layout.addWidget(fixed_box)
            row_layout.addWidget(lower_edit)
            row_layout.addWidget(upper_edit)

            self._rows[param.name] = _ParameterRow(
                value=value_spin,
                fixed=fixed_box,
                lower=lower_edit,
                upper=upper_edit,
            )
            form.addRow(f"{param.label}:", row_widget)

        layout.addLayout(form)
        self.setLayout(layout)

    def display_label(self) -> str:
        text = self.label_edit.text().strip()
        return text or self.spec.label

    def parameter_configs(self) -> dict[str, FitParameterConfig]:
        configs: dict[str, FitParameterConfig] = {}
        for param in self.spec.parameters:
            row = self._rows[param.name]
            lower = self._parse_bound(row.lower.text())
            upper = self._parse_bound(row.upper.text())
            configs[param.name] = FitParameterConfig(
                name=param.name,
                value=row.value.value(),
                fixed=row.fixed.isChecked(),
                lower=lower,
                upper=upper,
            )
        return configs

    @staticmethod
    def _parse_bound(text: str) -> float | None:
        stripped = text.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None


class FittingModule(QWidget):
    """Allows fitting captured curves with configurable components."""

    _component_colors = [
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
        canvas: AnalysisCanvas,
        context_providers: dict[str, Callable[[], object]],
        register_curve_selection_callback: Optional[
            Callable[[Callable[[CurveCaptureEntry | None], None]], None]
        ] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.canvas = canvas
        self.context_providers = context_providers
        self._function_specs = available_fit_functions()
        self._component_widgets: list[_FitComponentWidget] = []
        self._component_counter = 1
        self._active_curve: CurveCaptureEntry | None = None
        self._fit_history: list[_FitHistoryEntry] = []
        self._result_counter = 1
        self._selected_result_id: str | None = None

        self._build_ui()
        if register_curve_selection_callback is not None:
            register_curve_selection_callback(self._on_external_curve_selected)
        else:
            self._on_external_curve_selected(None)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

        intro = QLabel(
            "Select a captured EDC/MDC curve from the capture history."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        region_row = QHBoxLayout()
        region_row.addWidget(QLabel("Fit range:"))
        self.region_min_spin = QDoubleSpinBox()
        self.region_min_spin.setDecimals(6)
        self.region_min_spin.setRange(-1e9, 1e9)
        self.region_min_spin.setEnabled(False)
        self.region_max_spin = QDoubleSpinBox()
        self.region_max_spin.setDecimals(6)
        self.region_max_spin.setRange(-1e9, 1e9)
        self.region_max_spin.setEnabled(False)
        region_row.addWidget(self.region_min_spin)
        region_row.addWidget(QLabel("to"))
        region_row.addWidget(self.region_max_spin)
        region_row.addStretch()
        layout.addLayout(region_row)

        builder_row = QHBoxLayout()
        self.component_selector = QComboBox()
        for spec in self._function_specs:
            self.component_selector.addItem(spec.label, spec.id)
        builder_row.addWidget(self.component_selector)
        self.add_component_btn = QPushButton("Add")
        self.add_component_btn.clicked.connect(self._add_component)
        builder_row.addWidget(self.add_component_btn)
        clear_components_btn = QPushButton("Clear")
        clear_components_btn.clicked.connect(self._clear_components)
        builder_row.addWidget(clear_components_btn)
        builder_row.addStretch()
        layout.addLayout(builder_row)

        self.components_area = QVBoxLayout()
        self.components_area.setSpacing(8)

        container = QWidget()
        container.setLayout(self.components_area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(container)
        scroll.setMinimumHeight(180)
        layout.addWidget(scroll)

        action_row = QHBoxLayout()
        self.fit_btn = QPushButton("Fit curve")
        self.fit_btn.clicked.connect(self._run_fit)
        action_row.addWidget(self.fit_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        layout.addWidget(QLabel("Fit components and parameters:"))
        self.results_tree = QTreeWidget()
        self.results_tree.setColumnCount(4)
        self.results_tree.setHeaderLabels(["Result / Component", "Parameter", "Value", "Actions"])
        self.results_tree.setFixedHeight(120)
        self.results_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_tree.itemSelectionChanged.connect(self._on_results_selection_changed)
        self.results_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.results_tree)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #555555;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)
        self.setMaximumWidth(480)

    # ------------------------------------------------------------------
    # Curve selection / history integration
    # ------------------------------------------------------------------
    def _on_external_curve_selected(self, entry: CurveCaptureEntry | None) -> None:
        if entry is None:
            self._active_curve = None
            self.region_min_spin.setEnabled(False)
            self.region_max_spin.setEnabled(False)
            return

        self._active_curve = entry
        axis_min = float(np.min(entry.axis_values))
        axis_max = float(np.max(entry.axis_values))

        self.region_min_spin.setEnabled(True)
        self.region_max_spin.setEnabled(True)
        self.region_min_spin.setRange(axis_min, axis_max)
        self.region_max_spin.setRange(axis_min, axis_max)
        self.region_min_spin.setValue(axis_min)
        self.region_max_spin.setValue(axis_max)

    # ------------------------------------------------------------------
    # Component handling
    # ------------------------------------------------------------------
    def _add_component(self) -> None:
        if not self._function_specs:
            QMessageBox.warning(self, "Unavailable", "No fit functions defined.")
            return
        index = self.component_selector.currentIndex()
        if index < 0:
            index = 0
        spec = self._function_specs[index]
        widget = _FitComponentWidget(spec, self._component_counter)
        self._component_counter += 1
        widget.removed.connect(self._remove_component)
        self._component_widgets.append(widget)
        self.components_area.addWidget(widget)

    def _clear_components(self) -> None:
        while self._component_widgets:
            widget = self._component_widgets.pop()
            widget.setParent(None)
            widget.deleteLater()
        self._component_counter = 1

    def _remove_component(self, component_id: str) -> None:
        removed = False
        for idx, widget in enumerate(self._component_widgets):
            if widget.component_id == component_id:
                self.components_area.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
                self._component_widgets.pop(idx)
                removed = True
                break
        if removed:
            self._clear_results_history()

    def _collect_components(self) -> list[FitComponentConfig]:
        components: list[FitComponentConfig] = []
        for widget in self._component_widgets:
            configs = widget.parameter_configs()
            components.append(
                FitComponentConfig(
                    function_id=widget.spec.id,
                    parameters=configs,
                    label=widget.display_label(),
                    component_id=widget.component_id,
                )
            )
        return components

    # ------------------------------------------------------------------
    # Fitting logic
    # ------------------------------------------------------------------
    def _run_fit(self) -> None:
        entry = self._active_curve
        if entry is None:
            return
        components = self._collect_components()
        if not components:
            QMessageBox.information(self, "Components required", "Add at least one component to fit.")
            return
        fit_range = (self.region_min_spin.value(), self.region_max_spin.value())
        try:
            result = perform_curve_fit(
                entry.axis_values,
                entry.intensity,
                components,
                fit_range=fit_range,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid input", str(exc))
            return
        self._store_fit_result(result)

    def _plot_fit_result(self, entry: CurveCaptureEntry, result: FitResult) -> None:
        axis_label = f"{entry.axis_name} ({entry.axis_unit})" if entry.axis_unit else entry.axis_name
        curves = [
            CurveDisplayData(
                axis_values=entry.axis_values,
                intensity=entry.intensity,
                label=f"{entry.dataset_label} – data",
                axis_label=axis_label,
                color="#444444",
                style="solid",
                width=2,
            ),
            CurveDisplayData(
                axis_values=result.x,
                intensity=result.y_fit,
                label="Total fit",
                axis_label=axis_label,
                color="#d62728",
                style="solid",
                width=3,
            ),
        ]
        for idx, component in enumerate(result.components):
            color = self._component_colors[idx % len(self._component_colors)]
            curves.append(
                CurveDisplayData(
                    axis_values=result.x,
                    intensity=component.contribution,
                    label=component.label,
                    axis_label=axis_label,
                    color=color,
                    style="dash",
                    width=2,
                )
            )
        self.canvas.display_curves(curves)

    def _store_fit_result(self, result: FitResult) -> None:
        description = ", ".join(component.label for component in result.components if component.label)
        label = f"Model #{self._result_counter}"
        if description:
            label = f"{label} ({description})"
        entry = _FitHistoryEntry(id=str(uuid4()), label=label, result=result)
        self._fit_history.insert(0, entry)
        self._result_counter += 1
        self._selected_result_id = entry.id
        self._refresh_results_view()
        self._update_status_for_result(result)
        if self._active_curve is not None:
            self._plot_fit_result(self._active_curve, result)

    def _refresh_results_view(self) -> None:
        self.results_tree.blockSignals(True)
        self.results_tree.clear()
        for entry in self._fit_history:
            r_squared = entry.result.r_squared
            r2_display = f"{r_squared:.4f}" if r_squared is not None else "n/a"
            parent = QTreeWidgetItem([entry.label, "R²", r2_display, ""])
            parent.setData(0, Qt.UserRole, entry.id)
            for component in entry.result.components:
                component_item = QTreeWidgetItem([component.label, "", "", ""])
                for name, value in component.parameters.items():
                    component_item.addChild(QTreeWidgetItem(["", name, f"{value:.6g}", ""]))
                parent.addChild(component_item)
            remove_btn = QPushButton("Remove")
            remove_btn.setProperty("class", "danger")
            remove_btn.clicked.connect(
                lambda _, entry_id=entry.id: self._remove_fit_entry(entry_id)
            )
            self.results_tree.addTopLevelItem(parent)
            self.results_tree.setItemWidget(parent, 3, remove_btn)
            if self._selected_result_id == entry.id:
                self.results_tree.setCurrentItem(parent)
        self.results_tree.blockSignals(False)

    def _remove_fit_entry(self, entry_id: str) -> None:
        removed = None
        new_history: list[_FitHistoryEntry] = []
        for existing in self._fit_history:
            if existing.id == entry_id:
                removed = existing
            else:
                new_history.append(existing)
        if removed is None:
            return
        self._fit_history = new_history
        if self._selected_result_id == entry_id:
            self._selected_result_id = self._fit_history[0].id if self._fit_history else None
        self._refresh_results_view()
        if self._selected_result_id is not None:
            entry = self._find_fit_entry(self._selected_result_id)
            if entry and self._active_curve is not None:
                self._plot_fit_result(self._active_curve, entry.result)
        else:
            self._status_label_no_result()
            self._plot_data_only()

    def _find_fit_entry(self, entry_id: str | None) -> _FitHistoryEntry | None:
        if entry_id is None:
            return None
        for entry in self._fit_history:
            if entry.id == entry_id:
                return entry
        return None

    def _on_results_selection_changed(self) -> None:
        items = self.results_tree.selectedItems()
        if not items:
            self._selected_result_id = None
            self._plot_data_only()
            return
        item = items[0]
        parent = item
        while parent.parent() is not None:
            parent = parent.parent()
        entry_id = parent.data(0, Qt.UserRole)
        if not entry_id:
            return
        entry = self._find_fit_entry(entry_id)
        if entry is None:
            return
        self._selected_result_id = entry_id
        if self._active_curve is not None:
            self._plot_fit_result(self._active_curve, entry.result)

    def _update_status_for_result(self, result: FitResult) -> None:
        if result.success and not result.message:
            status = "Fit finished successfully."
        elif result.success:
            status = f"Fit finished with warnings: {result.message}"
        else:
            status = f"Fit used initial guesses (could not converge): {result.message or 'unknown error'}"
        self.status_label.setText(status)

    def _status_label_no_result(self) -> None:
        self.status_label.setText("No stored fit results for this curve.")

    def _plot_data_only(self) -> None:
        if not self._active_curve:
            return
        axis_label = (
            f"{self._active_curve.axis_name} ({self._active_curve.axis_unit})"
            if self._active_curve.axis_unit
            else self._active_curve.axis_name
        )
        curve = CurveDisplayData(
            axis_values=self._active_curve.axis_values,
            intensity=self._active_curve.intensity,
            label=f"{self._active_curve.dataset_label} – data",
            axis_label=axis_label,
            color="#444444",
            style="solid",
            width=2,
        )
        self.canvas.display_curves([curve])

    def _clear_results_history(self) -> None:
        self._fit_history.clear()
        self._selected_result_id = None
        self.results_tree.clear()
        self.status_label.clear()
        self._plot_data_only()
