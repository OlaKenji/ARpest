"""Interactive curve-fitting widget for captured EDC/MDC traces."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Iterable, Optional
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
    QStackedLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from .....operations.fit import (
    FitComponentConfig,
    FitParameterConfig,
    FitResult,
    available_fit_functions,
    perform_curve_fit,
)
from ..history import ViewCaptureEntry
from .....visualization.analysis_canvas import CurveDisplayData
from ..history import CurveCaptureEntry
from .base import AnalysisModule, AnalysisModuleContext


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
    capture_id: str
    fit_range: tuple[float, float]


@dataclass
class _BatchFitEntry:
    """Stores results from a batch MDC fit."""

    id: str
    label: str
    view_id: str
    energies: np.ndarray
    r_squared: np.ndarray
    components: list["_BatchComponentResult"]


@dataclass
class _BatchComponentResult:
    """One component traced across the batch energies."""

    component_id: str
    label: str
    centers: np.ndarray
    center_errors: np.ndarray
    gammas: np.ndarray
    gamma_errors: np.ndarray
    amplitudes: np.ndarray
    amplitude_errors: np.ndarray


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

    def set_display_label(self, label: str | None) -> None:
        self.label_edit.setText(label or self.spec.label)

    def set_parameters(self, metadata: dict[str, dict[str, float | bool | None]] | None) -> None:
        if not metadata:
            return
        for name, meta in metadata.items():
            row = self._rows.get(name)
            if row is None:
                continue
            value = meta.get("value")
            if value is not None:
                row.value.setValue(float(value))
            fixed = meta.get("fixed")
            if fixed is not None:
                row.fixed.setChecked(bool(fixed))
            lower = meta.get("lower")
            upper = meta.get("upper")
            row.lower.setText("" if lower is None else str(lower))
            row.upper.setText("" if upper is None else str(upper))


class FittingModule(AnalysisModule):
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

    title = "Fitting"
    wrap_in_scroll = True

    def __init__(self, context: AnalysisModuleContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(context, parent)
        self.canvas = context.canvas
        self.capture_history = context.capture_history
        self._function_specs = available_fit_functions()
        self._function_lookup = {spec.id: spec for spec in self._function_specs}
        self._component_widgets: list[_FitComponentWidget] = []
        self._component_counter = 1
        self._active_curve: CurveCaptureEntry | None = None
        self._fit_histories: dict[str, list[_FitHistoryEntry]] = {}
        self._selected_result_ids: dict[str, str | None] = {}
        self._result_counter = 1
        self._batch_results: list[_BatchFitEntry] = []
        self._view_entries: list[ViewCaptureEntry] = []
        self._selected_view_entry: ViewCaptureEntry | None = None
        self._mode = "1d"
        self._selected_batch_id: str | None = None

        self._build_ui()
        self.capture_history.entries_changed.connect(self._refresh_view_entries)
        self._refresh_view_entries()
        context.register_curve_selection_callback(self._on_external_curve_selected)
        context.register_view_selection_callback(self._on_external_view_selected)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

        intro = QLabel("Select a captured image from the capture history.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("1D fit (EDC/MDC)")
        self.mode_combo.addItem("2D batch MDC")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        mode_group = QGroupBox("Fit controls")
        mode_group_layout = QVBoxLayout()
        mode_group_layout.setContentsMargins(8, 8, 8, 8)
        self.mode_stack = QStackedLayout()
        mode_container = QWidget()
        mode_container.setLayout(self.mode_stack)

        fit_controls = QWidget()
        fit_layout = QVBoxLayout()
        fit_layout.setContentsMargins(0, 0, 0, 0)
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
        fit_layout.addLayout(region_row)

        action_row = QHBoxLayout()
        self.fit_btn = QPushButton("Fit curve")
        self.fit_btn.clicked.connect(self._run_fit)
        action_row.addWidget(self.fit_btn)
        action_row.addStretch()
        fit_layout.addLayout(action_row)
        fit_controls.setLayout(fit_layout)

        batch_controls = QWidget()
        batch_layout = QVBoxLayout()
        batch_layout.setContentsMargins(0, 0, 0, 0)
        batch_layout.setSpacing(6)

        self.batch_source_label = QLabel("Select a captured 2D view in the history list.")
        self.batch_source_label.setWordWrap(True)
        batch_layout.addWidget(self.batch_source_label)

        energy_row = QHBoxLayout()
        self.batch_energy_label = QLabel("Y range:")
        energy_row.addWidget(self.batch_energy_label)
        self.batch_energy_min = QDoubleSpinBox()
        self.batch_energy_min.setDecimals(6)
        self.batch_energy_min.setRange(-1e9, 1e9)
        self.batch_energy_min.setEnabled(False)
        self.batch_energy_min.setFixedWidth(90)
        self.batch_energy_max = QDoubleSpinBox()
        self.batch_energy_max.setDecimals(6)
        self.batch_energy_max.setRange(-1e9, 1e9)
        self.batch_energy_max.setEnabled(False)
        self.batch_energy_max.setFixedWidth(90)
        energy_row.addWidget(self.batch_energy_min)
        energy_row.addWidget(QLabel("to"))
        energy_row.addWidget(self.batch_energy_max)
        batch_layout.addLayout(energy_row)

        step_row = QHBoxLayout()
        step_row.addWidget(QLabel("Energy step:"))
        self.batch_energy_step = QDoubleSpinBox()
        self.batch_energy_step.setDecimals(6)
        self.batch_energy_step.setRange(1e-6, 1e9)
        self.batch_energy_step.setEnabled(False)
        self.batch_energy_step.setFixedWidth(90)
        step_row.addWidget(self.batch_energy_step)
        step_row.addStretch()
        batch_layout.addLayout(step_row)

        integration_row = QHBoxLayout()
        self.batch_integration_label = QLabel("Y integration (±):")
        integration_row.addWidget(self.batch_integration_label)
        self.batch_energy_integration = QDoubleSpinBox()
        self.batch_energy_integration.setDecimals(6)
        self.batch_energy_integration.setRange(0.0, 1e9)
        self.batch_energy_integration.setEnabled(False)
        self.batch_energy_integration.setFixedWidth(90)
        integration_row.addWidget(self.batch_energy_integration)
        self.batch_integration_unit = QLabel("")
        integration_row.addWidget(self.batch_integration_unit)
        integration_row.addStretch()
        batch_layout.addLayout(integration_row)

        mdc_row = QHBoxLayout()
        self.batch_mdc_label = QLabel("X fit range:")
        mdc_row.addWidget(self.batch_mdc_label)
        self.batch_mdc_min = QDoubleSpinBox()
        self.batch_mdc_min.setDecimals(6)
        self.batch_mdc_min.setRange(-1e9, 1e9)
        self.batch_mdc_min.setEnabled(False)
        self.batch_mdc_min.setFixedWidth(90)
        self.batch_mdc_max = QDoubleSpinBox()
        self.batch_mdc_max.setDecimals(6)
        self.batch_mdc_max.setRange(-1e9, 1e9)
        self.batch_mdc_max.setEnabled(False)
        self.batch_mdc_max.setFixedWidth(90)
        mdc_row.addWidget(self.batch_mdc_min)
        mdc_row.addWidget(QLabel("to"))
        mdc_row.addWidget(self.batch_mdc_max)
        batch_layout.addLayout(mdc_row)

        run_row = QHBoxLayout()
        self.batch_fit_btn = QPushButton("Run batch MDC fit")
        self.batch_fit_btn.clicked.connect(self._run_batch_fit)
        run_row.addWidget(self.batch_fit_btn)
        run_row.addStretch()
        batch_layout.addLayout(run_row)
        batch_controls.setLayout(batch_layout)

        self.mode_stack.addWidget(fit_controls)
        self.mode_stack.addWidget(batch_controls)
        mode_group_layout.addWidget(mode_container)
        mode_group.setLayout(mode_group_layout)
        layout.addWidget(mode_group)

        components_group = QGroupBox("Fit model components")
        components_layout = QVBoxLayout()
        components_layout.setSpacing(6)

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
        components_layout.addLayout(builder_row)

        self.components_area = QVBoxLayout()
        self.components_area.setSpacing(8)

        container = QWidget()
        container.setLayout(self.components_area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(container)
        scroll.setMinimumHeight(180)
        components_layout.addWidget(scroll)

        components_group.setLayout(components_layout)
        layout.addWidget(components_group)

        results_group = QGroupBox("Fit results")
        results_layout = QVBoxLayout()
        results_layout.setSpacing(6)
        results_layout.addWidget(QLabel("Fit components and parameters:"))
        self.results_tree = QTreeWidget()
        self.results_tree.setColumnCount(5)
        self.results_tree.setHeaderLabels(["Result / Component", "Parameter", "Value", "Error", "Actions"])
        self.results_tree.setFixedHeight(120)
        self.results_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_tree.itemSelectionChanged.connect(self._on_results_selection_changed)
        self.results_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.results_tree.itemClicked.connect(self._on_result_item_clicked)
        self.results_tree.itemDoubleClicked.connect(self._on_result_item_clicked)
        results_layout.addWidget(self.results_tree)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #555555;")
        results_layout.addWidget(self.status_label)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()
        self.setLayout(layout)
        self.setMaximumWidth(480)

    def _on_mode_changed(self, index: int) -> None:
        self._mode = "1d" if index == 0 else "2d"
        self.mode_stack.setCurrentIndex(index)
        if self._mode == "1d":
            self._set_results_headers_1d()
            self._refresh_results_view()
        else:
            self._set_results_headers_batch()
            self._refresh_batch_results()

    def _set_results_headers_1d(self) -> None:
        self.results_tree.setHeaderLabels(["Result / Component", "Parameter", "Value", "Error", "Actions"])

    def _set_results_headers_batch(self) -> None:
        self._set_results_headers_1d()

    def _clear_batch_results_view(self) -> None:
        self.results_tree.clear()
        self.status_label.setText("No batch results yet.")

    # ------------------------------------------------------------------
    # Curve selection / history integration
    # ------------------------------------------------------------------
    def _on_external_curve_selected(self, entry: CurveCaptureEntry | None) -> None:
        if entry is None:
            self._active_curve = None
            self.region_min_spin.setEnabled(False)
            self.region_max_spin.setEnabled(False)
            if self._mode == "1d":
                self._refresh_results_view()
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
        if self._mode == "1d":
            self._refresh_results_view()

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
        self._remove_all_components(preserve_history=True)
        self._component_counter = 1

    def _remove_component(self, component_id: str) -> None:
        for idx, widget in enumerate(self._component_widgets):
            if widget.component_id == component_id:
                self.components_area.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
                self._component_widgets.pop(idx)
                return

    def _remove_all_components(self, *, preserve_history: bool) -> None:
        while self._component_widgets:
            widget = self._component_widgets.pop()
            self.components_area.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        if not preserve_history:
            self._component_counter = 1
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

    def _current_capture_id(self) -> str | None:
        return self._active_curve.id if self._active_curve is not None else None

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

    # ------------------------------------------------------------------
    # Batch MDC fitting
    # ------------------------------------------------------------------
    def _refresh_view_entries(self) -> None:
        entries = self.capture_history.view_entries()
        self._view_entries = [entry for entry in entries if entry.dataset.is_2d]
        if not self._view_entries and self._selected_view_entry is None:
            self._clear_batch_controls()

    def _clear_batch_controls(self) -> None:
        for widget in (
            self.batch_energy_min,
            self.batch_energy_max,
            self.batch_energy_step,
            self.batch_energy_integration,
            self.batch_mdc_min,
            self.batch_mdc_max,
        ):
            widget.setEnabled(False)
        self.batch_source_label.setText("Select a captured 2D view in the history list.")
        self.batch_energy_label.setText("Y range:")
        self.batch_mdc_label.setText("X fit range:")
        self.batch_integration_label.setText("Y integration (±):")
        self.batch_integration_unit.setText("")

    def _on_external_view_selected(self, entry: ViewCaptureEntry | None) -> None:
        if entry is None or not entry.dataset.is_2d:
            self._selected_view_entry = None
            self._clear_batch_controls()
            return
        self._selected_view_entry = entry
        self._apply_batch_view(entry)
        self.batch_source_label.setText(
            f"Using selected 2D capture")

    def _apply_batch_view(self, entry: ViewCaptureEntry) -> None:
        dataset = entry.dataset
        if not dataset.is_2d:
            self._clear_batch_controls()
            return
        x_vals = np.asarray(dataset.x_axis.values, dtype=float)
        y_vals = np.asarray(dataset.y_axis.values, dtype=float)
        if x_vals.size == 0 or y_vals.size == 0:
            self._clear_batch_controls()
            return

        for widget in (
            self.batch_energy_min,
            self.batch_energy_max,
            self.batch_energy_step,
            self.batch_energy_integration,
            self.batch_mdc_min,
            self.batch_mdc_max,
        ):
            widget.setEnabled(True)

        y_min = float(np.nanmin(y_vals))
        y_max = float(np.nanmax(y_vals))
        if y_min > y_max:
            y_min, y_max = y_max, y_min
        self.batch_energy_min.setRange(y_min, y_max)
        self.batch_energy_max.setRange(y_min, y_max)
        self.batch_energy_min.setValue(y_min)
        self.batch_energy_max.setValue(y_max)

        y_range = y_max - y_min
        y_step = y_range / 10 if np.isfinite(y_range) and y_range > 0 else 1.0
        if y_step <= 0 or not np.isfinite(y_step):
            y_step = 1.0
        self.batch_energy_step.setValue(y_step)
        self.batch_energy_integration.setValue(0.0)

        x_min = float(np.nanmin(x_vals))
        x_max = float(np.nanmax(x_vals))
        if x_min > x_max:
            x_min, x_max = x_max, x_min
        self.batch_mdc_min.setRange(x_min, x_max)
        self.batch_mdc_max.setRange(x_min, x_max)
        self.batch_mdc_min.setValue(x_min)
        self.batch_mdc_max.setValue(x_max)

        y_label = self._axis_label(dataset.y_axis, "Y")
        x_label = self._axis_label(dataset.x_axis, "X")
        self.batch_energy_label.setText(f"{y_label} range:")
        self.batch_mdc_label.setText(f"{x_label} fit range:")
        self.batch_integration_label.setText(f"{y_label} integration (±):")
        unit = getattr(dataset.y_axis, "unit", "") or ""
        self.batch_integration_unit.setText(unit)

    def _run_batch_fit(self) -> None:
        entry = self._selected_view_entry
        if entry is None:
            QMessageBox.information(self, "No selection", "Select a 2D capture from the history list first.")
            return
        dataset = entry.dataset
        if not dataset.is_2d:
            QMessageBox.warning(self, "Unsupported", "Batch MDC fitting requires a 2D dataset.")
            return

        components = self._collect_components()
        if not components:
            QMessageBox.information(self, "Components required", "Add at least one component to fit.")
            return
        lorentz_components = [comp for comp in components if comp.function_id == "lorentzian"]
        if not lorentz_components:
            QMessageBox.warning(self, "Lorentzian required", "Add at least one Lorentzian component for MDC fits.")
            return

        x_vals = np.asarray(dataset.x_axis.values, dtype=float)
        y_vals = np.asarray(dataset.y_axis.values, dtype=float)
        intensity = np.asarray(dataset.intensity, dtype=float)

        y_min = float(self.batch_energy_min.value())
        y_max = float(self.batch_energy_max.value())
        if y_min > y_max:
            y_min, y_max = y_max, y_min
        y_step = float(self.batch_energy_step.value())
        if y_step <= 0:
            QMessageBox.warning(self, "Invalid step", "Energy step must be > 0.")
            return
        integration_half = float(self.batch_energy_integration.value())
        if integration_half < 0:
            QMessageBox.warning(self, "Invalid integration", "Integration must be ≥ 0.")
            return
        fit_range = (self.batch_mdc_min.value(), self.batch_mdc_max.value())

        y_targets = np.arange(y_min, y_max + 0.5 * y_step, y_step)
        y_indices = [int(np.argmin(np.abs(y_vals - target))) for target in y_targets]
        energies: list[float] = []
        r2_values: list[float] = []
        component_keys: list[tuple[str, str]] = []
        for comp in lorentz_components:
            key = comp.component_id or comp.label or "lorentzian"
            label = comp.label or "Lorentzian"
            component_keys.append((key, label))
        component_buffers: dict[str, dict[str, list[float]]] = {}
        for key, _ in component_keys:
            component_buffers[key] = {
                "center": [],
                "center_err": [],
                "gamma": [],
                "gamma_err": [],
                "amplitude": [],
                "amplitude_err": [],
            }

        for idx in y_indices:
            if integration_half > 0:
                center_val = y_vals[idx]
                mask = (y_vals >= center_val - integration_half) & (y_vals <= center_val + integration_half)
                if not np.any(mask):
                    continue
                mdc = np.nanmean(intensity[mask, :], axis=0)
            else:
                mdc = intensity[idx, :]
            try:
                result = perform_curve_fit(
                    x_vals,
                    mdc,
                    components,
                    fit_range=fit_range,
                )
            except ValueError:
                continue
            energies.append(float(y_vals[idx]))
            components_by_key: dict[str, FitComponentResult] = {}
            for comp in result.components:
                if comp.function_id != "lorentzian":
                    continue
                key = comp.component_id or comp.label or "lorentzian"
                components_by_key[key] = comp
            for key, _label in component_keys:
                comp = components_by_key.get(key)
                if comp is None:
                    buffer = component_buffers[key]
                    buffer["center"].append(np.nan)
                    buffer["center_err"].append(np.nan)
                    buffer["gamma"].append(np.nan)
                    buffer["gamma_err"].append(np.nan)
                    buffer["amplitude"].append(np.nan)
                    buffer["amplitude_err"].append(np.nan)
                    continue
                meta = comp.metadata or {}
                buffer = component_buffers[key]
                buffer["center"].append(float(comp.parameters.get("center", np.nan)))
                buffer["gamma"].append(float(comp.parameters.get("gamma", np.nan)))
                buffer["amplitude"].append(float(comp.parameters.get("amplitude", np.nan)))
                buffer["center_err"].append(float(meta.get("center", {}).get("error", np.nan) or np.nan))
                buffer["gamma_err"].append(float(meta.get("gamma", {}).get("error", np.nan) or np.nan))
                buffer["amplitude_err"].append(float(meta.get("amplitude", {}).get("error", np.nan) or np.nan))
            r2_values.append(float(result.r_squared) if result.r_squared is not None else np.nan)

        if not energies:
            QMessageBox.information(self, "No fits", "No valid MDC fits were produced.")
            return

        components_result: list[_BatchComponentResult] = []
        for key, label in component_keys:
            buffer = component_buffers[key]
            components_result.append(
                _BatchComponentResult(
                    component_id=key,
                    label=label,
                    centers=np.asarray(buffer["center"]),
                    center_errors=np.asarray(buffer["center_err"]),
                    gammas=np.asarray(buffer["gamma"]),
                    gamma_errors=np.asarray(buffer["gamma_err"]),
                    amplitudes=np.asarray(buffer["amplitude"]),
                    amplitude_errors=np.asarray(buffer["amplitude_err"]),
                )
            )

        batch_entry = _BatchFitEntry(
            id=str(uuid4()),
            label=f"Batch MDC ({len(energies)} slices)",
            view_id=entry.id,
            energies=np.asarray(energies),
            r_squared=np.asarray(r2_values),
            components=components_result,
        )
        self._batch_results.insert(0, batch_entry)
        self._selected_batch_id = batch_entry.id
        self._refresh_batch_results()
        self.canvas.display_dataset(entry.dataset, colormap=entry.colormap, integration_radius=entry.integration_radius)
        palette = self._component_colors or ["#ff8800"]
        series = []
        for idx, comp in enumerate(batch_entry.components):
            color = palette[idx % len(palette)]
            series.append(
                {
                    "x_values": comp.centers,
                    "y_values": batch_entry.energies,
                    "color": color,
                    "size": 6,
                    "symbol": "o",
                }
            )
        if series:
            self.canvas.set_overlay_series(series)

    def _refresh_batch_results(self) -> None:
        self._set_results_headers_batch()
        self.results_tree.blockSignals(True)
        self.results_tree.clear()
        created_items: dict[str, QTreeWidgetItem] = {}
        for batch in self._batch_results:
            label = f"{batch.label} ({len(batch.energies)} slices)"
            parent = QTreeWidgetItem([label, "R²", f"{np.nanmean(batch.r_squared):.4f}", "", ""])
            parent.setData(0, Qt.UserRole, batch.id)
            for idx, energy in enumerate(batch.energies):
                energy_label = f"Energy {energy:.6g}"
                energy_item = QTreeWidgetItem([energy_label, "", "", "", ""])
                for comp_index, comp in enumerate(batch.components):
                    comp_label = comp.label or f"Component {comp_index + 1}"
                    comp_item = QTreeWidgetItem([comp_label, "", "", "", ""])
                    center = comp.centers[idx]
                    center_err = comp.center_errors[idx]
                    gamma = comp.gammas[idx]
                    gamma_err = comp.gamma_errors[idx]
                    amp = comp.amplitudes[idx]
                    amp_err = comp.amplitude_errors[idx]
                    comp_item.addChild(
                        QTreeWidgetItem(
                            [
                                "",
                                "Center",
                                f"{center:.6g}",
                                f"{center_err:.3g}" if np.isfinite(center_err) else "—",
                                "",
                            ]
                        )
                    )
                    comp_item.addChild(
                        QTreeWidgetItem(
                            [
                                "",
                                "Gamma",
                                f"{gamma:.6g}",
                                f"{gamma_err:.3g}" if np.isfinite(gamma_err) else "—",
                                "",
                            ]
                        )
                    )
                    comp_item.addChild(
                        QTreeWidgetItem(
                            [
                                "",
                                "Amplitude",
                                f"{amp:.6g}",
                                f"{amp_err:.3g}" if np.isfinite(amp_err) else "—",
                                "",
                            ]
                        )
                    )
                    energy_item.addChild(comp_item)
                r2 = batch.r_squared[idx]
                energy_item.addChild(
                    QTreeWidgetItem(
                        [
                            "",
                            "R²",
                            f"{r2:.4f}" if np.isfinite(r2) else "—",
                            "",
                            "",
                        ]
                    )
                )
                parent.addChild(energy_item)
            remove_btn = QPushButton("Remove")
            remove_btn.setProperty("class", "danger")
            remove_btn.clicked.connect(lambda _, entry_id=batch.id: self._remove_batch_entry(entry_id))
            self.results_tree.addTopLevelItem(parent)
            self.results_tree.setItemWidget(parent, 4, remove_btn)
            created_items[batch.id] = parent
        self.results_tree.blockSignals(False)
        if not created_items:
            self._clear_batch_results_view()
            return
        selected_id = self._selected_batch_id or next(iter(created_items))
        if selected_id in created_items:
            item = created_items[selected_id]
            self.results_tree.setCurrentItem(item)
            self._activate_batch_entry(item)
        else:
            self._selected_batch_id = None
            self.results_tree.clearSelection()

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
        capture_id = self._current_capture_id()
        if capture_id is None:
            return
        description = ", ".join(component.label for component in result.components if component.label)
        label = f"Model #{self._result_counter}"
        if description:
            label = f"{label} ({description})"
        fit_range = (self.region_min_spin.value(), self.region_max_spin.value())
        entry = _FitHistoryEntry(
            id=str(uuid4()),
            label=label,
            result=result,
            capture_id=capture_id,
            fit_range=fit_range,
        )
        history = self._fit_histories.setdefault(capture_id, [])
        history.insert(0, entry)
        self._result_counter += 1
        self._selected_result_ids[capture_id] = entry.id
        self._refresh_results_view()
        self._update_status_for_result(result)
        if self._active_curve is not None:
            self._plot_fit_result(self._active_curve, result)
        self._apply_fit_range(entry.fit_range)
        self._rebuild_components_from_result(result)

    def _refresh_results_view(self) -> None:
        if self._mode != "1d":
            return
        capture_id = self._current_capture_id()
        self.results_tree.blockSignals(True)
        self.results_tree.clear()
        created_items: dict[str, QTreeWidgetItem] = {}
        if capture_id is not None:
            for entry in self._fit_histories.get(capture_id, []):
                r_squared = entry.result.r_squared
                r2_display = f"{r_squared:.4f}" if r_squared is not None else "n/a"
                parent = QTreeWidgetItem([entry.label, "R²", r2_display, "", ""])
                parent.setData(0, Qt.UserRole, entry.id)
                for component in entry.result.components:
                    component_item = QTreeWidgetItem([component.label, "", "", "", ""])
                    for name, value in component.parameters.items():
                        meta = (component.metadata or {}).get(name, {})
                        error_value = meta.get("error")
                        if error_value is None or not np.isfinite(error_value):
                            error_text = "—"
                        else:
                            error_text = f"{error_value:.3g}"
                        component_item.addChild(QTreeWidgetItem(["", name, f"{value:.6g}", error_text, ""]))
                    parent.addChild(component_item)
                remove_btn = QPushButton("Remove")
                remove_btn.setProperty("class", "danger")
                remove_btn.clicked.connect(
                    lambda _, cap_id=entry.capture_id, entry_id=entry.id: self._remove_fit_entry(cap_id, entry_id)
                )
                self.results_tree.addTopLevelItem(parent)
                self.results_tree.setItemWidget(parent, 4, remove_btn)
                created_items[entry.id] = parent
        self.results_tree.blockSignals(False)

        if capture_id is None or not created_items:
            self.results_tree.clearSelection()
            self._status_label_no_result()
            self._plot_data_only()
            return

        selected_id = self._selected_result_ids.get(capture_id)
        if selected_id and selected_id in created_items:
            item = created_items[selected_id]
            self.results_tree.setCurrentItem(item)
            self._activate_result_item(item)
        else:
            self.results_tree.clearSelection()
            self._status_label_no_result()
            self._plot_data_only()

    def _remove_fit_entry(self, capture_id: str, entry_id: str) -> None:
        history = self._fit_histories.get(capture_id)
        if not history:
            return
        history = [entry for entry in history if entry.id != entry_id]
        if history:
            self._fit_histories[capture_id] = history
        else:
            self._fit_histories.pop(capture_id, None)
        selected_id = self._selected_result_ids.get(capture_id)
        if selected_id == entry_id:
            self._selected_result_ids[capture_id] = history[0].id if history else None
        if capture_id == self._current_capture_id():
            self._refresh_results_view()

    def _find_fit_entry(self, capture_id: str | None, entry_id: str | None) -> _FitHistoryEntry | None:
        if not capture_id or not entry_id:
            return None
        for entry in self._fit_histories.get(capture_id, []):
            if entry.id == entry_id:
                return entry
        return None

    def _on_results_selection_changed(self) -> None:
        if self._mode == "2d":
            items = self.results_tree.selectedItems()
            if not items:
                return
            item = items[0]
            self._activate_batch_entry(item)
            return
        if self._mode != "1d":
            return
        items = self.results_tree.selectedItems()
        if not items:
            self._selected_result_id = None
            self._plot_data_only()
            return
        item = items[0]
        self._activate_result_item(item)

    def _on_result_item_clicked(self, item: QTreeWidgetItem) -> None:
        if self._mode == "2d":
            if item is None:
                return
            self.results_tree.setCurrentItem(item)
            self._activate_batch_entry(item)
            return
        if self._mode != "1d":
            return
        if item is None:
            return
        self.results_tree.setCurrentItem(item)
        self._activate_result_item(item)

    def _activate_result_item(self, item: QTreeWidgetItem) -> None:
        if self._mode != "1d":
            return
        capture_id = self._current_capture_id()
        parent = item
        while parent.parent() is not None:
            parent = parent.parent()
        entry_id = parent.data(0, Qt.UserRole)
        if not entry_id:
            return
        entry = self._find_fit_entry(capture_id, entry_id)
        if entry is None:
            return
        if capture_id is not None:
            self._selected_result_ids[capture_id] = entry_id
        if self._active_curve is not None:
            self._plot_fit_result(self._active_curve, entry.result)
        self._apply_fit_range(entry.fit_range)
        self._rebuild_components_from_result(entry.result)

    def _remove_batch_entry(self, entry_id: str) -> None:
        self._batch_results = [entry for entry in self._batch_results if entry.id != entry_id]
        if self._selected_batch_id == entry_id:
            self._selected_batch_id = self._batch_results[0].id if self._batch_results else None
        self._refresh_batch_results()

    def _activate_batch_entry(self, item: QTreeWidgetItem) -> None:
        if self._mode != "2d":
            return
        parent = item
        while parent.parent() is not None:
            parent = parent.parent()
        entry_id = parent.data(0, Qt.UserRole)
        if not entry_id:
            return
        entry = next((e for e in self._batch_results if e.id == entry_id), None)
        if entry is None:
            return
        self._selected_batch_id = entry_id
        view_entry = self.capture_history.get_entry(entry.view_id)
        if not isinstance(view_entry, ViewCaptureEntry):
            return
        self.canvas.display_dataset(
            view_entry.dataset,
            colormap=view_entry.colormap,
            integration_radius=view_entry.integration_radius,
        )
        palette = self._component_colors or ["#ff8800"]
        series = []
        for idx, comp in enumerate(entry.components):
            color = palette[idx % len(palette)]
            series.append(
                {
                    "x_values": comp.centers,
                    "y_values": entry.energies,
                    "color": color,
                    "size": 6,
                    "symbol": "o",
                }
            )
        if series:
            self.canvas.set_overlay_series(series)

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
        capture_id = self._current_capture_id()
        if capture_id:
            self._fit_histories.pop(capture_id, None)
            self._selected_result_ids[capture_id] = None
        self.results_tree.clear()
        self.status_label.clear()
        self._plot_data_only()

    def serialize_state(self) -> dict:
        return {
            "fit_histories": copy.deepcopy(self._fit_histories),
            "selected_result_ids": dict(self._selected_result_ids),
            "result_counter": self._result_counter,
        }

    def apply_state(self, state: dict | None, available_capture_ids: Iterable[str]) -> None:
        available_ids = {capture_id for capture_id in available_capture_ids if capture_id}
        self._fit_histories.clear()
        self._selected_result_ids.clear()
        self.results_tree.clear()
        self.status_label.clear()
        self._result_counter = 1
        if not state:
            self._plot_data_only()
            return
        histories = state.get("fit_histories") or {}
        selected_ids = state.get("selected_result_ids") or {}
        try:
            self._result_counter = max(1, int(state.get("result_counter", 1)))
        except (TypeError, ValueError):
            self._result_counter = 1
        for capture_id, entries in histories.items():
            if capture_id not in available_ids:
                continue
            sanitized: list[_FitHistoryEntry] = []
            for entry in entries:
                if isinstance(entry, _FitHistoryEntry):
                    sanitized.append(entry)
                elif isinstance(entry, dict):
                    try:
                        sanitized.append(_FitHistoryEntry(**entry))
                    except TypeError:
                        continue
            if sanitized:
                self._fit_histories[capture_id] = sanitized
        for capture_id, entries in self._fit_histories.items():
            selected = selected_ids.get(capture_id)
            if selected and any(entry.id == selected for entry in entries):
                self._selected_result_ids[capture_id] = selected
            else:
                self._selected_result_ids[capture_id] = entries[0].id if entries else None
        self._refresh_results_view()

    def _apply_fit_range(self, fit_range: tuple[float, float] | None) -> None:
        if fit_range is None or self._active_curve is None:
            return
        if not (self.region_min_spin.isEnabled() and self.region_max_spin.isEnabled()):
            return
        axis_min = self.region_min_spin.minimum()
        axis_max = self.region_max_spin.maximum()
        lower = max(axis_min, min(axis_max, float(fit_range[0])))
        upper = max(axis_min, min(axis_max, float(fit_range[1])))
        if upper < lower:
            lower, upper = upper, lower
        self.region_min_spin.setValue(lower)
        self.region_max_spin.setValue(upper)

    @staticmethod
    def _axis_label(axis, fallback: str) -> str:
        name = getattr(axis, "name", None) or fallback
        unit = getattr(axis, "unit", "") or ""
        return f"{name} ({unit})" if unit else str(name)

    def _rebuild_components_from_result(self, result: FitResult) -> None:
        self._remove_all_components(preserve_history=True)
        for component in result.components:
            spec = self._function_lookup.get(component.function_id)
            if spec is None:
                continue
            widget = _FitComponentWidget(spec, self._component_counter)
            self._component_counter += 1
            widget.removed.connect(self._remove_component)
            widget.set_display_label(component.label)
            widget.set_parameters(component.metadata)
            self._component_widgets.append(widget)
            self.components_area.addWidget(widget)
