"""Dataset tab widget encapsulating per-file-stack UI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QSplitter,
    QComboBox,
    QSlider,
    QLineEdit,
    QStackedLayout,
)

from ..core.loaders import BlochLoader, I05Loader
from ..models import FileStack, Dataset, Axis, AxisType
from ..operations import get_registered_operations
from ..utils.config import Config
from ..utils.cursor.cursor_manager import CursorState
from ..utils.session import SessionTabState
from .panels.analysis.panel import AnalysisPanel
from .panels.operations.panel import OperationsPanel
from .panels.operations.widgets.state_history import StateHistoryWidget
from .panels.overview.panel import OverviewPanel
from ..visualization.analysis_canvas import AnalysisCanvas
from ..visualization.figure_2d import Figure2D
from ..visualization.figure_3d import Figure3D

class DatasetTab(QWidget):
    """
    Tab for a single dataset with multiple files.
    
    Each tab contains:
    - File catalog (list of loaded files)
    - Figure displays
    - Operations panel
    - Metadata logbook
    """

    def __init__(
        self,
        filename: str,
        file_stack: Optional[FileStack] = None,
        parent: Optional[QWidget] = None,
        loaders: Optional[list] = None,
        config: Optional[Config] = None,
        session_state: Optional[SessionTabState] = None,
    ):
        """
        Initialize dataset tab.
        
        Args:
            filename: Name to display in tab
            file_stack: FileStack to display (required unless restoring session)
            parent: Parent widget
            session_state: Optional previously saved session data
        """
        super().__init__(parent)
        self.filename = filename
        self.file_stacks: list[FileStack] = []
        self.loaders = loaders or []
        self.config = config
        self.figure = None
        self.left_layout: Optional[QVBoxLayout] = None
        self.visual_stack: Optional[QStackedLayout] = None
        self.figure_container: Optional[QWidget] = None
        self.figure_container_layout: Optional[QVBoxLayout] = None
        self.meta_text: Optional[QLabel] = None
        self.data_text: Optional[QLabel] = None
        self.state_history: Optional[StateHistoryWidget] = None
        self.analysis_panel: Optional[AnalysisPanel] = None
        self.analysis_canvas: Optional[AnalysisCanvas] = None
        self.side_tabs: Optional[QTabWidget] = None
        self._analysis_tab_index: Optional[int] = None
        self.colormap_combo: Optional[QComboBox] = None
        self.color_scale_slider: Optional[QSlider] = None
        self.vmin_input: Optional[QLineEdit] = None
        self.vmax_input: Optional[QLineEdit] = None
        self.integration_slider: Optional[QSlider] = None
        self.integration_value_label: Optional[QLabel] = None
        self._cursor_states: list[Optional[CursorState]] = []
        self._cut_states: list[Optional[CursorState]] = []
        
        colours = ['arpest', 'RdYlBu_r', 'terrain','binary', 'binary_r'] + sorted(['RdBu_r','Spectral_r','bwr','coolwarm', 'twilight_shifted','twilight_shifted_r', 'PiYG', 'gist_ncar','gist_ncar_r', 'gist_stern','gnuplot2', 'hsv', 'hsv_r', 'magma', 'magma_r', 'seismic', 'seismic_r','turbo', 'turbo_r'])        
        self.available_colormaps = colours
        self.current_colormap = self.available_colormaps[0]
        self._base_color_limits: tuple[Optional[float], Optional[float]] = (None, None)
        self._current_color_limits: tuple[Optional[float], Optional[float]] = (None, None)
        self.integration_radius = 0
        self._pending_color_limits: Optional[tuple[Optional[float], Optional[float]]] = None

        if session_state is not None:
            if not session_state.file_stacks:
                raise ValueError("Session state does not contain any file stacks.")
            self.file_stacks = list(session_state.file_stacks)
            self.current_index = max(0, min(session_state.current_index, len(self.file_stacks) - 1))
            if session_state.colormap in self.available_colormaps:
                self.current_colormap = session_state.colormap
            self.integration_radius = max(0, int(session_state.integration_radius))
            self._pending_color_limits = session_state.color_limits
        else:
            if file_stack is None:
                raise ValueError("file_stack must be provided when no session state is given.")
            self.file_stacks = [file_stack]
            self.current_index = 0

        stack_count = len(self.file_stacks)
        self._cursor_states = [None] * stack_count
        self._cut_states = [None] * stack_count

        if session_state is not None:
            saved_cursors = getattr(session_state, "cursor_states", []) or []
            saved_cuts = getattr(session_state, "cut_states", []) or []
            for idx in range(min(len(saved_cursors), stack_count)):
                self._cursor_states[idx] = saved_cursors[idx]
            for idx in range(min(len(saved_cuts), stack_count)):
                self._cut_states[idx] = saved_cuts[idx]
        
        self._setup_ui()
        if session_state is not None and getattr(session_state, "analysis_state", None):
            self.analysis_panel.apply_state(session_state.analysis_state)
        self._apply_pending_visual_state()
        
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QSplitter, QLabel
        from PyQt5.QtCore import Qt
        
        # Main horizontal layout
        main_layout = QHBoxLayout()
        
        # Left side: Figure visualization
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout = left_layout

        self.visual_stack = QStackedLayout()
        self.figure_container = QWidget()
        self.figure_container_layout = QVBoxLayout()
        self.figure_container_layout.setContentsMargins(0, 0, 0, 0)
        self.figure_container.setLayout(self.figure_container_layout)

        self.analysis_canvas = AnalysisCanvas()

        self.visual_stack.addWidget(self.figure_container)
        self.visual_stack.addWidget(self.analysis_canvas)
        left_layout.addLayout(self.visual_stack)

        left_widget.setLayout(left_layout)
        self._display_file_stack(self.file_stacks[self.current_index])
        if self.visual_stack is not None and self.figure_container is not None:
            self.visual_stack.setCurrentWidget(self.figure_container)
        
        # Right side tabs
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget.setLayout(right_layout)
        right_widget.setMaximumWidth(380)

        side_tabs = QTabWidget()
        side_tabs.setTabPosition(QTabWidget.North)
        side_tabs.setElideMode(Qt.ElideRight)
        right_layout.addWidget(side_tabs)
        self.side_tabs = side_tabs

        # overview tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout()
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_tab.setLayout(overview_layout)

        self.overview_panel = OverviewPanel(
            file_stacks=self.file_stacks,
            on_load_clicked=self._on_load_data_clicked,
            on_remove_clicked=self._on_remove_data_clicked,
            on_combine_clicked=self._on_combine_data_clicked,
            on_file_selected=self._on_file_selected,
        )
        overview_layout.addWidget(self.overview_panel)
        self.file_catalog = self.overview_panel.file_catalog
        self.file_catalog.select_index(self.current_index)

        self.meta_text = self.overview_panel.meta_text
        self.data_text = self.overview_panel.data_text

        self.colormap_combo = self.overview_panel.colormap_combo
        self.colormap_combo.clear()
        self.colormap_combo.addItems(self.available_colormaps)
        self.colormap_combo.setCurrentText(self.current_colormap)
        self.colormap_combo.currentTextChanged.connect(self._on_colormap_changed)

        self.color_scale_slider = self.overview_panel.color_scale_slider
        self.color_scale_slider.setEnabled(False)
        self.color_scale_slider.setToolTip("Adjust relative vmax while keeping vmin fixed.")
        self.color_scale_slider.valueChanged.connect(self._on_color_scale_slider_changed)

        self.vmin_input = self.overview_panel.vmin_input
        self.vmin_input.editingFinished.connect(self._on_manual_limit_edited)
        self.vmax_input = self.overview_panel.vmax_input
        self.vmax_input.editingFinished.connect(self._on_manual_limit_edited)

        self.integration_slider = self.overview_panel.integration_slider
        self.integration_slider.setValue(self.integration_radius + 1)
        self.integration_slider.setToolTip("Average cuts over (2N-1) pixels around the cursor.")
        self.integration_slider.valueChanged.connect(self._on_integration_slider_changed)
        self.integration_value_label = self.overview_panel.integration_value_label
        self.integration_value_label.setText(self._format_integration_label())

        if self.file_stacks:
            current_stack = self.file_stacks[self.current_index]
            self.meta_text.setText(self._format_metadata(current_stack))
            self.data_text.setText(self._format_data_info(current_stack))
            self._update_color_scale_controls(current_stack)

        overview_layout.addStretch()
        side_tabs.addTab(overview_tab, "Overview")

        # Operations tab
        operations_tab = QWidget()
        operations_layout = QVBoxLayout()
        operations_tab.setLayout(operations_layout)

        history_header = QHBoxLayout()
        history_label = QLabel("States:")
        history_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        history_header.addWidget(history_label)
        delete_state_btn = QPushButton("Remove State")
        delete_state_btn.setToolTip("Remove selected state (raw cannot be removed)")
        delete_state_btn.clicked.connect(self._on_remove_state_clicked)
        history_header.addWidget(delete_state_btn)
        history_header.addStretch()
        operations_layout.addLayout(history_header)

        self.state_history = StateHistoryWidget()
        self.state_history.state_selected.connect(self._on_state_selected)
        operations_layout.addWidget(self.state_history)
        self._update_state_history_widget(self.file_stacks[self.current_index])

        self.operations_panel = OperationsPanel(
            get_file_stack=self._current_file_stack,
            apply_callback=self._on_operation_result,
            operation_classes=get_registered_operations(),
            context_providers={
                "cut_state": self._current_cut_state,
                "photon_energy_cursor": self._current_photon_energy_value,
                "available_loaders": self._available_loaders,
                "start_path": self._current_start_path,
                "current_edc_curves": self._current_edc_curves,
                "current_mdc_curves": self._current_mdc_curves,
                "panel_dataset_top_left": lambda: self._export_dataset_for_operations("top_left"),
                "panel_dataset_top_right": lambda: self._export_dataset_for_operations("top_right"),
                "panel_dataset_bottom_left": lambda: self._export_dataset_for_operations("bottom_left"),
            },
        )
        operations_layout.addWidget(self.operations_panel)
        operations_layout.addStretch()

        side_tabs.addTab(operations_tab, "Operations")

        # Analysis tab
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        analysis_tab.setLayout(analysis_layout)

        self.analysis_panel = AnalysisPanel(
            get_file_stack=self._current_file_stack,
            canvas=self.analysis_canvas,
            capture_view_callback=lambda view=None: self._capture_current_view_for_analysis(view=view),
            context_providers={
                "current_edc_curves": self._current_edc_curves,
                "current_mdc_curves": self._current_mdc_curves,
            },
        )
        analysis_layout.addWidget(self.analysis_panel)
        side_tabs.addTab(analysis_tab, "Analysis")
        self._analysis_tab_index = side_tabs.indexOf(analysis_tab)
        side_tabs.currentChanged.connect(self._on_side_tab_changed)
        self._on_side_tab_changed(side_tabs.currentIndex())
        
        # Use splitter to allow resizing
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)  # Left side gets more space
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def _apply_pending_visual_state(self) -> None:
        """Reapply saved colour limits after widgets are initialized."""
        if self._pending_color_limits is None:
            return
        self._current_color_limits = self._pending_color_limits
        self._sync_color_limit_inputs(update_slider=True)
        self._apply_color_limits()
        self._pending_color_limits = None

    def _capture_current_visual_state(self, index: Optional[int] = None) -> None:
        """Persist cursor/cut positions for the specified file stack index."""
        if self.figure is None or not self.file_stacks:
            return
        idx = self.current_index if index is None else index
        if not (0 <= idx < len(self._cursor_states)):
            return

        get_cursor = getattr(self.figure, "get_cursor_state", None)
        if callable(get_cursor):
            self._cursor_states[idx] = get_cursor()
        get_cut = getattr(self.figure, "get_cut_state", None)
        if callable(get_cut):
            self._cut_states[idx] = get_cut()

    def _apply_saved_cursor_state(self, index: int) -> None:
        """Restore previously saved cursor/cut positions for the given index."""
        if self.figure is None or not (0 <= index < len(self._cursor_states)):
            return
        set_cursor = getattr(self.figure, "set_cursor_state", None)
        if callable(set_cursor):
            set_cursor(self._cursor_states[index])
        set_cut = getattr(self.figure, "set_cut_state", None)
        if callable(set_cut):
            set_cut(self._cut_states[index])
    
    def _format_metadata(self, file_stack: FileStack) -> str:
        """Format metadata for display."""
        dataset = file_stack.current_state
        meta = dataset.measurement

        info = f"Beamline: {meta.beamline}\n"
        info += f"Photon Energy: {meta.photon_energy:.2f} eV\n"
        info += f"Temperature: {meta.temperature} K\n"
        
        info += f"Count time: {meta.time}\n"             
        info += f"χ: {meta.chi:.2f}°\n"        
        info += f"φ: {meta.phi:.2f}°\n"
        info += f"θ: {meta.theta:.2f}°\n"            
        info += f"x: {meta.x:.2f}\n"            
        info += f"y: {meta.y:.2f}\n"            
        info += f"z: {meta.z:.2f}\n"                                                        
        info += f"Polarisation: {meta.polarization}\n"        
        info += f"Slit size: {meta.slit_size:.2f}\n"                
        info += f"Mode: {meta.mode}\n"        
        info += f"Center energy: {meta.center_energy} eV\n"                
        info += f"Pass energy: {meta.pass_energy} eV\n"            
        info += f"Deflector: {meta.deflector}°\n"                             
        return info

    def _current_file_stack(self) -> FileStack:
        return self.file_stacks[self.current_index]

    def _available_loaders(self) -> list:
        """Expose loader list to operation widgets."""
        return list(self.loaders or [])

    def _current_start_path(self) -> str:
        """Return the preferred directory for file dialogs."""
        if self.config is not None and getattr(self.config, "start_path", None):
            return str(self.config.start_path)
        return str(Path.home())

    def _current_cut_state(self):
        """Return the static cut position from the active figure, if available."""
        figure = self.figure
        if figure is None:
            return None
        cursor_mgr = getattr(figure, "cursor_mgr", None)
        if cursor_mgr is None:
            return None
        return cursor_mgr.cut

    def _current_photon_energy_value(self) -> float | None:
        """Return the photon energy represented by the current figure context."""
        figure = self.figure
        if figure is not None:
            z_cursor = getattr(figure, "curves_z_cursor", None)
            if z_cursor is not None:
                try:
                    return float(z_cursor)
                except (TypeError, ValueError):
                    pass

        file_stack = self._current_file_stack()
        if file_stack is None:
            return None
        dataset = file_stack.current_state

        if dataset.z_axis is not None and dataset.z_axis.axis_type is AxisType.PHOTON_ENERGY:
            values = dataset.z_axis.values
            if len(values) > 0:
                return float(values[len(values) // 2])

        return dataset.measurement.photon_energy

    def _current_edc_curves(self):
        figure = self.figure
        if figure is None:
            return None
        getter = getattr(figure, "get_current_edc_curves", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None

    def _current_mdc_curves(self):
        figure = self.figure
        if figure is None:
            return None
        getter = getattr(figure, "get_current_mdc_curves", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None

    def _export_dataset_for_operations(self, view: Optional[str]):
        try:
            return self._export_dataset_for_analysis(view)
        except ValueError:
            return None

    def _display_file_stack(self, file_stack: FileStack, previous_index: Optional[int] = None) -> None:
        """Create or replace the figure widget for the selected file stack."""
        if self.figure_container_layout is None:
            return
        if previous_index is None:
            previous_index = self.current_index
        if self.figure is not None:
            self._capture_current_visual_state(previous_index)

        new_figure = (
            Figure2D(
                file_stack,
                colormap=self.current_colormap,
                integration_radius=self.integration_radius,
            )
            if file_stack.current_state.is_2d
            else Figure3D(
                file_stack,
                colormap=self.current_colormap,
                integration_radius=self.integration_radius,
            )
        )

        if self.figure is not None:
            self.figure_container_layout.removeWidget(self.figure)
            self.figure.setParent(None)
            self.figure.deleteLater()

        self.figure = new_figure
        self.figure_container_layout.addWidget(self.figure)
        self._apply_colormap_to_current_figure()
        self._apply_integration_radius_to_current_figure()
        self._update_color_scale_controls(file_stack)
        self._apply_saved_cursor_state(self.current_index)

    def _update_info_panels(self, file_stack: FileStack) -> None:
        """Refresh metadata/data info labels for the given file stack."""
        if self.meta_text is not None:
            self.meta_text.setText(self._format_metadata(file_stack))
        if self.data_text is not None:
            self.data_text.setText(self._format_data_info(file_stack))
        self._update_state_history_widget(file_stack)

    def _update_state_history_widget(self, file_stack: FileStack) -> None:
        if self.state_history is not None:
            self.state_history.set_file_stack(file_stack)

    def _capture_current_view_for_analysis(
        self, view: Optional[str] = None, *, set_tab: bool = True
    ) -> tuple[Dataset, str, int]:
        if self.analysis_canvas is None:
            raise ValueError("Analysis canvas is not available.")
        dataset = self._export_dataset_for_analysis(view)
        self.analysis_canvas.display_dataset(
            dataset,
            colormap=self.current_colormap,
            integration_radius=self.integration_radius,
        )
        if (
            set_tab
            and self.side_tabs is not None
            and self._analysis_tab_index is not None
        ):
            self.side_tabs.setCurrentIndex(self._analysis_tab_index)
        return dataset, self.current_colormap, self.integration_radius

    def _export_dataset_for_analysis(self, view: Optional[str]) -> Dataset:
        if not self.file_stacks:
            raise ValueError("No dataset is loaded.")
        if self.figure is None:
            raise ValueError("No figure is currently active.")

        exporter = getattr(self.figure, "export_panel_dataset", None)
        dataset: Optional[Dataset] = None
        if callable(exporter):
            try:
                dataset = exporter(view)
            except Exception as exc:
                raise ValueError(f"Could not capture the current figure: {exc}") from exc
        elif view is None:
            fallback = getattr(self.figure, "export_display_dataset", None)
            if callable(fallback):
                dataset = fallback()

        if dataset is None:
            raise ValueError("The current figure cannot provide the requested view.")
        return dataset

    def _on_side_tab_changed(self, index: int) -> None:
        if (
            self.visual_stack is None
            or self.analysis_canvas is None
            or self.figure_container is None
        ):
            return
        if self._analysis_tab_index is not None and index == self._analysis_tab_index:
            self.visual_stack.setCurrentWidget(self.analysis_canvas)
        else:
            self.visual_stack.setCurrentWidget(self.figure_container)

    def _on_operation_result(self, file_stack: FileStack, dataset: Dataset, state_name: str) -> None:
        """Persist an operation result as a new state and refresh UI."""
        self._capture_current_visual_state()
        file_stack.add_state(dataset, state_name)
        self.file_catalog.refresh()
        self._display_file_stack(file_stack)
        self._update_info_panels(file_stack)

    def _on_file_selected(self, index: int) -> None:
        """Handle selection change in the file catalog."""
        if index < 0 or index >= len(self.file_stacks) or index == self.current_index:
            return

        previous_index = self.current_index
        self.current_index = index
        file_stack = self.file_stacks[index]
        self._display_file_stack(file_stack, previous_index=previous_index)
        self._update_info_panels(file_stack)
        self._update_state_history_widget(file_stack)

    def _on_state_selected(self, state_index: int) -> None:
        """Jump to state within current file stack."""
        file_stack = self._current_file_stack()
        if file_stack is None:
            return
        self._capture_current_visual_state()
        try:
            file_stack.goto_state(state_index)
        except IndexError:
            return
        self._display_file_stack(file_stack)
        self._update_info_panels(file_stack)
        self.file_catalog.refresh()

    def _on_remove_state_clicked(self) -> None:
        """Delete the currently selected state from the history."""
        file_stack = self._current_file_stack()
        if file_stack is None or self.state_history is None:
            return

        row = self.state_history.list_widget.currentRow()
        if row <= 0:
            QMessageBox.information(self, "Cannot Remove", "Raw state cannot be removed.")
            return

        self._capture_current_visual_state()
        if not file_stack.delete_state(row):
            QMessageBox.warning(self, "Remove Failed", "Unable to delete selected state.")
            return

        self._update_state_history_widget(file_stack)
        self.file_catalog.refresh()
        self._display_file_stack(file_stack)
        self._update_info_panels(file_stack)

    def _on_load_data_clicked(self) -> None:
        """Launch file dialog to load additional data into this catalog."""
        if not self.loaders:
            QMessageBox.warning(self, "No Loaders", "No data loaders are configured.")
            return

        filter_string = self._build_file_filter_string()
        start_path = str(self.config.start_path) if self.config else ""

        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Load Additional Data",
            start_path,
            filter_string,
        )

        if not filenames:
            return

        new_indices = []
        for filename in filenames:
            path = Path(filename)
            loader = next((l for l in self.loaders if l.can_load(path)), None)
            if loader is None:
                QMessageBox.warning(self, "Unknown Format", f"No loader available for {path.name}")
                continue

            dataset = loader.load(path)
            file_stack = FileStack(filename=str(path), raw_data=dataset)
            self.file_stacks.append(file_stack)
            self._cursor_states.append(None)
            self._cut_states.append(None)
            new_indices.append(len(self.file_stacks) - 1)

        if new_indices:
            if self.config:
                self.config.update_start_path(Path(filenames[0]))
            self.file_catalog.refresh()
            self.file_catalog.select_index(new_indices[-1])

    def _on_remove_data_clicked(self) -> None:
        """Remove selected file stacks from the catalog."""
        indices = self.file_catalog.get_selected_indices()
        if not indices:
            QMessageBox.information(self, "No Selection", "Select at least one dataset to remove.")
            return

        if len(self.file_stacks) - len(indices) < 1:
            QMessageBox.warning(self, "Cannot Remove", "At least one dataset must remain loaded.")
            return

        for idx in sorted(indices, reverse=True):
            del self.file_stacks[idx]
            del self._cursor_states[idx]
            del self._cut_states[idx]

        self.file_catalog.refresh()
        self.current_index = min(self.current_index, len(self.file_stacks) - 1)
        self.current_index = max(0, self.current_index)
        self.file_catalog.select_index(self.current_index)
        current_stack = self.file_stacks[self.current_index]
        self._display_file_stack(current_stack)
        self._update_info_panels(current_stack)

    def _on_combine_data_clicked(self) -> None:
        """Combine multiple selected datasets into a new averaged dataset."""
        indices = self.file_catalog.get_selected_indices()
        if len(indices) < 2:
            QMessageBox.information(self, "Need Multiple Selections", "Select at least two datasets to combine.")
            return

        datasets = [self.file_stacks[i].current_state for i in indices]
        compatible, reason = self._datasets_are_compatible(datasets)
        if not compatible:
            QMessageBox.warning(self, "Incompatible Data", reason or "Selected datasets cannot be combined.")
            return

        combined_dataset = self._combine_datasets(datasets)
        combined_names = ", ".join(Path(self.file_stacks[i].filename).name for i in indices)
        combined_dataset.filename = f"Combined[{combined_names}]"
        combined_dataset.measurement.custom = combined_dataset.measurement.custom.copy()
        combined_dataset.measurement.custom["combined_from"] = combined_names

        combined_stack = FileStack(filename=combined_dataset.filename, raw_data=combined_dataset)
        combined_stack.state_names[0] = "combined"
        self.file_stacks.append(combined_stack)
        self._cursor_states.append(None)
        self._cut_states.append(None)
        self.file_catalog.refresh()
        self.file_catalog.select_index(len(self.file_stacks) - 1)

    def _apply_colormap_to_current_figure(self) -> None:
        """Apply the currently selected colormap to the active figure widget."""
        if self.figure is None:
            return
        set_cmap = getattr(self.figure, "set_colormap", None)
        if callable(set_cmap):
            set_cmap(self.current_colormap)

    def _apply_integration_radius_to_current_figure(self) -> None:
        """Apply integration radius to the active figure."""
        if self.figure is None:
            return
        setter = getattr(self.figure, "set_integration_radius", None)
        if callable(setter):
            setter(self.integration_radius)

    def _update_color_scale_controls(self, file_stack: FileStack) -> None:
        """Initialize colour-scale controls for the provided file stack."""
        dataset = file_stack.current_state
        data = getattr(dataset, "intensity", None)
        if data is None:
            self._disable_color_scale_controls()
            return

        arr = np.asarray(data)
        finite_mask = np.isfinite(arr)
        if not finite_mask.any():
            self._disable_color_scale_controls()
            return

        finite_vals = arr[finite_mask]
        base_min = float(finite_vals.min())
        base_max = float(finite_vals.max())
        if np.isclose(base_min, base_max):
            base_max = base_min + 1.0

        self._base_color_limits = (base_min, base_max)
        self._current_color_limits = (base_min, base_max)

        if self.color_scale_slider is not None:
            self.color_scale_slider.setEnabled(True)
            self.color_scale_slider.blockSignals(True)
            self.color_scale_slider.setValue(100)
            self.color_scale_slider.blockSignals(False)

        if self.vmin_input is not None:
            self.vmin_input.setEnabled(True)
        if self.vmax_input is not None:
            self.vmax_input.setEnabled(True)

        self._sync_color_limit_inputs()
        self._apply_color_limits()

    def _disable_color_scale_controls(self) -> None:
        """Disable colour-scale controls when no valid data is available."""
        self._base_color_limits = (None, None)
        self._current_color_limits = (None, None)
        if self.color_scale_slider is not None:
            self.color_scale_slider.blockSignals(True)
            self.color_scale_slider.setValue(100)
            self.color_scale_slider.blockSignals(False)
            self.color_scale_slider.setEnabled(False)
        if self.vmin_input is not None:
            self.vmin_input.blockSignals(True)
            self.vmin_input.clear()
            self.vmin_input.blockSignals(False)
            self.vmin_input.setEnabled(False)
        if self.vmax_input is not None:
            self.vmax_input.blockSignals(True)
            self.vmax_input.clear()
            self.vmax_input.blockSignals(False)
            self.vmax_input.setEnabled(False)

    def _format_color_value(self, value: Optional[float]) -> str:
        if value is None or np.isnan(value):
            return ""
        return f"{value:.4g}"

    def _format_integration_label(self) -> str:
        width = self.integration_radius * 2 + 1
        return f"Width: {width} px"

    def _update_integration_label(self) -> None:
        if self.integration_value_label is not None:
            self.integration_value_label.setText(self._format_integration_label())

    def _sync_color_limit_inputs(self, update_slider: bool = False) -> None:
        """Keep line edits (and optionally slider) aligned with current limits."""
        vmin, vmax = self._current_color_limits
        if self.vmin_input is not None:
            self.vmin_input.blockSignals(True)
            self.vmin_input.setText(self._format_color_value(vmin))
            self.vmin_input.blockSignals(False)
        if self.vmax_input is not None:
            self.vmax_input.blockSignals(True)
            self.vmax_input.setText(self._format_color_value(vmax))
            self.vmax_input.blockSignals(False)

        if update_slider and self.color_scale_slider is not None:
            base_min, base_max = self._base_color_limits
            if base_min is None or base_max is None or vmax is None:
                return
            span = base_max - base_min
            if span <= 0:
                return
            ratio = np.clip((float(vmax) - base_min) / span, 0.0, 1.0)
            slider_value = int(round(ratio * 100))
            self.color_scale_slider.blockSignals(True)
            self.color_scale_slider.setValue(slider_value)
            self.color_scale_slider.blockSignals(False)

    def _on_color_scale_slider_changed(self, value: int) -> None:
        """Adjust vmax using the slider while keeping vmin fixed."""
        base_min, base_max = self._base_color_limits
        if base_min is None or base_max is None:
            return
        span = base_max - base_min
        if span <= 0:
            return

        ratio = np.clip(value / 100.0, 0.0, 1.0)
        new_max = base_min + span * ratio
        current_min = self._current_color_limits[0]
        if current_min is None:
            current_min = base_min
        if current_min is not None:
            new_max = max(new_max, current_min + 1e-9)

        self._current_color_limits = (current_min, new_max)
        self._sync_color_limit_inputs()
        self._apply_color_limits()

    def _on_integration_slider_changed(self, value: int) -> None:
        """Handle integration range adjustments."""
        radius = max(0, int(value) - 1)
        if radius == self.integration_radius:
            return
        self.integration_radius = radius
        self._update_integration_label()
        self._apply_integration_radius_to_current_figure()

    def _on_manual_limit_edited(self) -> None:
        """Handle manual vmin/vmax edits from the line edits."""
        sender = self.sender()
        base_min, base_max = self._base_color_limits
        current_min, current_max = self._current_color_limits
        if sender is None or base_min is None or base_max is None:
            return

        def _parse(text: str) -> Optional[float]:
            stripped = text.strip()
            if stripped == "":
                return None
            try:
                return float(stripped)
            except ValueError:
                return None

        if sender is self.vmin_input:
            new_min = _parse(self.vmin_input.text()) if self.vmin_input is not None else None
            if new_min is None:
                new_min = base_min
            if current_max is not None and new_min is not None:
                new_min = min(new_min, current_max - 1e-9)
            current_min = new_min
            self._current_color_limits = (current_min, current_max)
            self._sync_color_limit_inputs(update_slider=False)
            self._apply_color_limits()
        elif sender is self.vmax_input:
            new_max = _parse(self.vmax_input.text()) if self.vmax_input is not None else None
            if new_max is None:
                new_max = base_max
            if current_min is not None and new_max is not None:
                new_max = max(new_max, current_min + 1e-9)
            current_max = new_max
            self._current_color_limits = (current_min, current_max)
            self._sync_color_limit_inputs(update_slider=True)
            self._apply_color_limits()

    def _apply_color_limits(self) -> None:
        """Push the selected colour limits onto the active figure."""
        if self.figure is None:
            return
        vmin, vmax = self._current_color_limits
        set_limits = getattr(self.figure, "set_color_limits", None)
        if callable(set_limits):
            set_limits(vmin, vmax)

    def _on_colormap_changed(self, colormap: str) -> None:
        """Handle colour map selection changes."""
        if not colormap or colormap == self.current_colormap:
            return
        self.current_colormap = colormap
        self._apply_colormap_to_current_figure()

    def _combine_datasets(self, datasets: list) -> Dataset:
        """Average intensity data across datasets (assumes already compatible)."""
        first = datasets[0]
        combined = first.copy()
        accum = np.zeros_like(first.intensity, dtype=np.float64)
        for ds in datasets:
            accum += ds.intensity
        accum /= len(datasets)
        combined.intensity = accum
        return combined

    def _datasets_are_compatible(self, datasets: list[Dataset]) -> tuple[bool, Optional[str]]:
        """Check that datasets share shape and axes."""
        first = datasets[0]
        for ds in datasets[1:]:
            if ds.intensity.shape != first.intensity.shape:
                return False, "Datasets must share identical intensity shapes."
            if not self._axes_match(first.x_axis, ds.x_axis):
                return False, "X-axis mismatch between selected datasets."
            if not self._axes_match(first.y_axis, ds.y_axis):
                return False, "Y-axis mismatch between selected datasets."
            if not self._axes_match(first.z_axis, ds.z_axis):
                return False, "Z-axis mismatch between selected datasets."
            if not self._axes_match(first.w_axis, ds.w_axis):
                return False, "W-axis mismatch between selected datasets."
        return True, None

    @staticmethod
    def _axes_match(a: Optional[Axis], b: Optional[Axis]) -> bool:
        """Return True if both axes are equivalent (or both None)."""
        if (a is None) != (b is None):
            return False
        if a is None:
            return True
        return (
            a.axis_type == b.axis_type
            and a.unit == b.unit
            and len(a.values) == len(b.values)
            and np.allclose(a.values, b.values)
        )

    def _build_file_filter_string(self) -> str:
        """Build QFileDialog filter string based on available loaders."""
        filters = []
        all_extensions = []
        for loader in self.loaders:
            exts = " ".join(f"*{ext}" for ext in loader.extensions)
            all_extensions.extend(loader.extensions)
            filters.append(f"{loader.name} ({exts})")

        all_exts = " ".join(f"*{ext}" for ext in set(all_extensions))
        filters.insert(0, f"All supported formats ({all_exts})")
        filters.append("All files (*.*)")
        return ";;".join(filters)

    def to_session_state(self, title: str) -> SessionTabState:
        """Serialize this tab to a SessionTabState."""
        self._capture_current_visual_state()
        analysis_state = None
        if self.analysis_panel is not None:
            analysis_state = self.analysis_panel.serialize_state()
        return SessionTabState(
            title=title,
            file_stacks=list(self.file_stacks),
            current_index=self.current_index,
            colormap=self.current_colormap,
            color_limits=self._current_color_limits,
            integration_radius=self.integration_radius,
            cursor_states=list(self._cursor_states),
            cut_states=list(self._cut_states),
            analysis_state=analysis_state,
        )
    
    def _format_data_info(self, file_stack: FileStack) -> str:
        """Format data information for display."""
        dataset = file_stack.current_state
        
        info = f"Dimensions: {dataset.ndim}D\n"
        info += f"Shape: {dataset.shape}\n\n"
        
        info += f"X: {dataset.x_axis.name}\n"
        info += f"  Range: {dataset.x_axis.min:.2f} to {dataset.x_axis.max:.2f} {dataset.x_axis.unit}\n"
        info += f"  Points: {len(dataset.x_axis)}\n\n"
        
        info += f"Y: {dataset.y_axis.name}\n"
        info += f"  Range: {dataset.y_axis.min:.2f} to {dataset.y_axis.max:.2f} {dataset.y_axis.unit}\n"
        info += f"  Points: {len(dataset.y_axis)}\n"
        
        if dataset.z_axis and len(dataset.z_axis) > 1:
            info += f"\nZ: {dataset.z_axis.name}\n"
            info += f"  Range: {dataset.z_axis.min:.2f} to {dataset.z_axis.max:.2f} {dataset.z_axis.unit}\n"
            info += f"  Points: {len(dataset.z_axis)}\n"
        
        return info
