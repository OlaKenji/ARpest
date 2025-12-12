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
)

from ..core.loaders import BlochLoader, I05Loader

from ..models import FileStack
from ..utils.config import Config
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
from .dataset_tab import DatasetTab

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
        self.setWindowTitle("ARpest")
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
        title = QLabel("Welcome to ARpest")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Get started by opening ARPES data:\n"
            "• Click the '📂 Open File' button in the toolbar\n"
            "• Or use File → Open (Ctrl+O)\n\n"
            "Configure your default data directory:\n"
            "• Click the '⚙️ Settings' button\n\n"
            "Supported formats:\n"
            "• Bloch/MAX IV: .zip, .ibw files\n"
            "• I05/Diamond: .nxs files"
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
