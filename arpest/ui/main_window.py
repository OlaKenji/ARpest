"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QFileDialog,
    QMainWindow,
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
import numpy as np

from ..models import FileStack, Dataset, Axis, AxisType
from ..operations import get_registered_operations
from ..utils.config import Config
from ..utils.colour_map import add_colour_map
from ..utils.cursor.cursor_manager import CursorState
from ..utils.session import (
    SESSION_FILE_EXTENSION,
    SESSION_FORMAT_VERSION,
    SessionData,
    SessionTabState,
    ensure_session_extension,
    is_session_file,
    load_session,
    save_session,
)
from .widgets.file_catalog import FileCatalogWidget
from .widgets.operations_panel import OperationsPanel
from .widgets.state_history import StateHistoryWidget
from .widgets.analysis_panel import AnalysisPanel

from ..visualization.figure_2d import Figure2D
from ..visualization.figure_3d import Figure3D
from ..visualization.analysis_canvas import AnalysisCanvas

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
        
        add_colour_map()
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
        overview_layout.setSpacing(6)
        overview_tab.setLayout(overview_layout)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        load_button = QPushButton("Load Data")
        load_button.setToolTip("Load additional data into this catalog")
        load_button.clicked.connect(self._on_load_data_clicked)
        button_row.addWidget(load_button)

        remove_button = QPushButton("Remove Data")
        remove_button.setToolTip("Remove selected datasets from the catalog")
        remove_button.clicked.connect(self._on_remove_data_clicked)
        button_row.addWidget(remove_button)

        combine_button = QPushButton("Combine Data")
        combine_button.setToolTip("Average selected datasets (needs ≥ 2 selections)")
        combine_button.clicked.connect(self._on_combine_data_clicked)
        button_row.addWidget(combine_button)
        button_row.addStretch()
        overview_layout.addLayout(button_row)

        catalog_label = QLabel("Loaded Files:")
        catalog_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        overview_layout.addWidget(catalog_label)

        self.file_catalog = FileCatalogWidget(self.file_stacks)
        self.file_catalog.file_selected.connect(self._on_file_selected)
        self.file_catalog.setMaximumHeight(200)
        self.file_catalog.setMinimumWidth(250)
        overview_layout.addWidget(self.file_catalog)
        self.file_catalog.select_index(self.current_index)

        metadata_label = QLabel("Metadata:")
        metadata_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        overview_layout.addWidget(metadata_label)

        meta_info = self._format_metadata(self.file_stacks[self.current_index])
        self.meta_text = QLabel(meta_info)
        self.meta_text.setStyleSheet("font-size: 10px; padding: 5px; background: #f9f9f9;")
        self.meta_text.setWordWrap(True)
        overview_layout.addWidget(self.meta_text)

        data_info = self._format_data_info(self.file_stacks[self.current_index])
        self.data_text = QLabel(data_info)
        self.data_text.setStyleSheet("font-size: 10px; padding: 5px; background: #f9f9f9;")
        self.data_text.setWordWrap(True)
        overview_layout.addWidget(self.data_text)

        colormap_row = QHBoxLayout()
        colormap_label = QLabel("Colour Map:")
        colormap_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        colormap_row.addWidget(colormap_label)
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(self.available_colormaps)
        self.colormap_combo.setCurrentText(self.current_colormap)
        self.colormap_combo.currentTextChanged.connect(self._on_colormap_changed)
        colormap_row.addWidget(self.colormap_combo)
        overview_layout.addLayout(colormap_row)

        scale_label = QLabel("Colour Scale:")
        scale_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        overview_layout.addWidget(scale_label)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(6)
        self.color_scale_slider = QSlider(Qt.Horizontal)
        self.color_scale_slider.setRange(1, 100)
        self.color_scale_slider.setEnabled(False)
        self.color_scale_slider.setToolTip("Adjust relative vmax while keeping vmin fixed.")
        self.color_scale_slider.valueChanged.connect(self._on_color_scale_slider_changed)
        slider_row.addWidget(self.color_scale_slider)
        overview_layout.addLayout(slider_row)

        manual_row = QHBoxLayout()
        self.vmin_input = QLineEdit()
        self.vmin_input.setPlaceholderText("vmin")
        self.vmin_input.setFixedWidth(80)
        self.vmin_input.editingFinished.connect(self._on_manual_limit_edited)
        manual_row.addWidget(QLabel("Min:"))
        manual_row.addWidget(self.vmin_input)

        self.vmax_input = QLineEdit()
        self.vmax_input.setPlaceholderText("vmax")
        self.vmax_input.setFixedWidth(80)
        self.vmax_input.editingFinished.connect(self._on_manual_limit_edited)
        manual_row.addWidget(QLabel("Max:"))
        manual_row.addWidget(self.vmax_input)
        manual_row.addStretch()
        overview_layout.addLayout(manual_row)

        integration_label = QLabel("Integration Range:")
        integration_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        overview_layout.addWidget(integration_label)

        integration_row = QHBoxLayout()
        self.integration_slider = QSlider(Qt.Horizontal)
        self.integration_slider.setRange(1, 15)
        self.integration_slider.setValue(self.integration_radius + 1)
        self.integration_slider.setToolTip("Average cuts over (2N-1) pixels around the cursor.")
        self.integration_slider.valueChanged.connect(self._on_integration_slider_changed)
        integration_row.addWidget(self.integration_slider)
        self.integration_value_label = QLabel(self._format_integration_label())
        integration_row.addWidget(self.integration_value_label)
        integration_row.addStretch()
        overview_layout.addLayout(integration_row)

        if self.file_stacks:
            self._update_color_scale_controls(self.file_stacks[self.current_index])

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
    ) -> bool:
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
        return True

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
            try:
                self._capture_current_view_for_analysis(set_tab=False)
            except ValueError:
                pass
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
        return SessionTabState(
            title=title,
            file_stacks=list(self.file_stacks),
            current_index=self.current_index,
            colormap=self.current_colormap,
            color_limits=self._current_color_limits,
            integration_radius=self.integration_radius,
            cursor_states=list(self._cursor_states),
            cut_states=list(self._cut_states),
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


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Contains tabbed interface for multiple datasets.
    """

    def __init__(self, config: Config):
        """
        Initialize main window.
        
        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.loaders = [BlochLoader(), I05Loader()]  # data loaders
        
        self._setup_ui()
        self._create_actions()
        self._create_menus()
        
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("ARpest 2.0")
        self.resize(*self.config.window_size)
        
        # Create toolbar
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        
        # Open button in toolbar
        open_action = toolbar.addAction("📂 Open File")
        open_action.triggered.connect(self._open_files)
        open_action.setToolTip("Open ARPES data file (Ctrl+O)")

        save_action = toolbar.addAction("💾 Save Dataset")
        save_action.triggered.connect(self._save_session)
        save_action.setToolTip("Save current dataset tab (Ctrl+S)")
        
        # Add separator
        toolbar.addSeparator()
        
        # Settings button
        settings_action = toolbar.addAction("⚙️ Settings")
        settings_action.triggered.connect(self._open_settings)
        settings_action.setToolTip("Configure default paths and settings")
        
        # Central widget with tab system
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)
        
        # Add welcome tab
        self._add_welcome_tab()
        
        # Status bar
        self.statusBar().showMessage("Ready - Click 📂 Open File or use File → Open (Ctrl+O)")
        
    def _open_settings(self) -> None:
        """Open settings dialog."""
        from .dialogs.settings import SettingsDialog
        
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_():
            # Settings were saved
            self.statusBar().showMessage("Settings saved", 3000)
        
    def _create_actions(self) -> None:
        """Create menu actions."""
        # File actions are created in _create_menus
        pass
        
    def _create_menus(self) -> None:
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Open action
        open_action = file_menu.addAction("&Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_files)

        save_action = file_menu.addAction("&Save Dataset...")
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_session)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
    def _open_files(self) -> None:
        """Open file dialog and load selected files."""
        # Build file filter based on available loaders
        filters = []
        all_extensions = []
        
        filters = []
        all_extensions = []

        for loader in self.loaders:
            exts = " ".join(f"*{ext}" for ext in loader.extensions)
            all_extensions.extend(loader.extensions)
            filters.append(f"{loader.name} ({exts})")

        filters.append(f"ARpest Sessions (*{SESSION_FILE_EXTENSION})")
        all_extensions.append(SESSION_FILE_EXTENSION)
        
        # Add "All supported" filter
        all_exts = " ".join(f"*{ext}" for ext in set(all_extensions))
        filters.insert(0, f"All supported formats ({all_exts})")
        filters.append("All files (*.*)")
        
        filter_string = ";;".join(filters)
        
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Open ARPES Data",
            str(self.config.start_path),
            filter_string,
        )
        
        if not filenames:
            return
            
        # Show progress in status bar
        total = len(filenames)
        for idx, filename in enumerate(filenames, 1):
            path = Path(filename)
            if is_session_file(path):
                self.statusBar().showMessage(f"Loading session {idx}/{total}: {path.name}...")
                self._load_session(path)
            else:
                self.statusBar().showMessage(f"Loading file {idx}/{total}: {path.name}...")
                self._load_file(path)
            
        # Update start path and save
        if filenames:
            self.config.update_start_path(Path(filenames[0]))
            
        self.statusBar().showMessage(f"Loaded {total} item(s)", 3000)

    def _save_session(self) -> None:
        """Persist the currently selected tab state to a session file."""
        current_index = self.tabs.currentIndex()
        if current_index == -1:
            QMessageBox.information(self, "Nothing to Save", "Load data before saving.")
            return

        widget = self.tabs.widget(current_index)
        if not isinstance(widget, DatasetTab):
            QMessageBox.information(self, "Nothing to Save", "Select a dataset tab before saving.")
            return

        title = self.tabs.tabText(current_index)
        tab_state = widget.to_session_state(title)

        filter_string = f"ARpest Session (*{SESSION_FILE_EXTENSION})"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Dataset",
            str(self.config.start_path),
            filter_string,
        )

        if not filename:
            return

        path = ensure_session_extension(Path(filename))

        session = SessionData(version=SESSION_FORMAT_VERSION, tabs=[tab_state])
        try:
            save_session(path, session)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not save session:\n{exc}")
            return

        self.config.update_start_path(path)
        self.statusBar().showMessage(f"Saved dataset to {path.name}", 3000)
            
    def _load_file(self, filepath: Path) -> None:
        """
        Load a single file.
        
        Args:
            filepath: Path to file to load
        """
        # Find appropriate loader
        loader = None
        for l in self.loaders:
            if l.can_load(filepath):
                loader = l
                break
                
        if loader is None:
            QMessageBox.warning(
                self,
                "Unknown Format",
                f"Could not find a loader for {filepath.name}",
            )
            return
            
        # Load the file
        self.statusBar().showMessage(f"Loading {filepath.name}...")
        dataset = loader.load(filepath)
        
        # Create file stack
        file_stack = FileStack(
            filename=str(filepath),
            raw_data=dataset,
        )
        
        self._remove_welcome_tab_if_present()
        
        # Create new tab
        tab = DatasetTab(filepath.name, file_stack, self, loaders=self.loaders, config=self.config)
        self.tabs.addTab(tab, filepath.stem)
        self.tabs.setCurrentWidget(tab)
        
        self.statusBar().showMessage(f"Loaded {filepath.name}", 3000)        

    def _load_session(self, filepath: Path) -> None:
        """
        Restore a previously saved session.
        
        Args:
            filepath: Path to the session file.
        """
        try:
            session = load_session(filepath)
        except Exception as exc:
            QMessageBox.critical(self, "Load Failed", f"Could not load session:\n{exc}")
            return

        if not session.tabs:
            QMessageBox.information(self, "Empty Session", "This session does not contain any tabs.")
            return

        if session.version > SESSION_FORMAT_VERSION:
            QMessageBox.warning(
                self,
                "Newer Session Format",
                "This session was created with a newer version of ARpest. "
                "Attempting to load anyway.",
            )

        self._remove_welcome_tab_if_present()

        valid_state: SessionTabState | None = None
        for state in session.tabs:
            if state.file_stacks:
                valid_state = state
                break

        if valid_state is None:
            QMessageBox.warning(self, "Session Load", "This session does not contain any datasets.")
            return

        try:
            tab = DatasetTab(
                valid_state.title or filepath.name,
                parent=self,
                loaders=self.loaders,
                config=self.config,
                session_state=valid_state,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Session Load",
                f"Failed to restore dataset: {exc}",
            )
            return

        default_title = Path(valid_state.file_stacks[0].filename).stem or filepath.stem
        tab_title = valid_state.title or default_title
        self.tabs.addTab(tab, tab_title)
        self.tabs.setCurrentWidget(tab)

        if len(session.tabs) > 1:
            QMessageBox.information(
                self,
                "Partial Load",
                "This file contained multiple datasets; only the first was loaded.",
            )

        self.statusBar().showMessage(f"Loaded dataset from {filepath.name}", 3000)
    
    def _close_tab(self, index: int) -> None:
        """
        Close a tab.
        
        Args:
            index: Index of tab to close
        """
        self.tabs.removeTab(index)
        
        # Add welcome tab back if no tabs left
        if self.tabs.count() == 0:
            self._add_welcome_tab()
    
    def _add_welcome_tab(self) -> None:
        """Add welcome tab with instructions."""
        welcome_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title = QLabel("Welcome to ARpest 2.0")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "🚀 Get started by opening ARPES data:\n\n"
            "• Click the '📂 Open File' button in the toolbar\n"
            "• Or use File → Open (Ctrl+O)\n"
            "• Or drag and drop files here (coming soon)\n\n"
            "📁 Configure your default data directory:\n"
            "• Click the '⚙️ Settings' button\n\n"
            "Supported formats:\n"
            "• Bloch/MAX IV: .zip files\n"
            "• I05/Diamond: .nxs, .h5 files"
        )
        instructions.setStyleSheet("font-size: 14px; padding: 20px; color: #666;")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        
        # Large open button
        open_btn = QPushButton("📂 Open ARPES Data")
        open_btn.setStyleSheet(
            "font-size: 16px; padding: 15px 30px; background-color: #4CAF50; "
            "color: white; border: none; border-radius: 5px;"
        )
        open_btn.clicked.connect(self._open_files)
        layout.addWidget(open_btn)
        
        welcome_widget.setLayout(layout)
        self.tabs.addTab(welcome_widget, "Welcome")
        self.tabs.setTabsClosable(False)  # Don't allow closing welcome tab
    
    def _remove_welcome_tab_if_present(self) -> None:
        """Remove the welcome tab if it's currently displayed."""
        if self.tabs.count() > 0 and self.tabs.tabText(0) == "Welcome":
            self.tabs.removeTab(0)
            self.tabs.setTabsClosable(True)
