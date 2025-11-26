"""Settings dialog for ARpest configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QDialogButtonBox,
    QGroupBox,
    QWidget,
)

from ...utils.config import Config


class SettingsDialog(QDialog):
    """
    Dialog for configuring ARpest settings.
    
    Allows user to set:
    - Default data directory
    - Default colormap
    - Window size
    """

    def __init__(self, config: Config, parent: Optional[QWidget] = None):
        """
        Initialize settings dialog.
        
        Args:
            config: Application configuration
            parent: Parent widget
        """
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("ARpest Settings")
        self.setMinimumWidth(500)
        
        self._setup_ui()
        self._load_current_settings()
        
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout()
        
        # File paths section
        paths_group = QGroupBox("File Paths")
        paths_layout = QFormLayout()
        
        # Default data directory
        dir_layout = QHBoxLayout()
        self.data_dir_edit = QLineEdit()
        self.data_dir_edit.setPlaceholderText("Select default data directory...")
        dir_layout.addWidget(self.data_dir_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_data_dir)
        dir_layout.addWidget(browse_btn)
        
        paths_layout.addRow("Default Data Directory:", dir_layout)
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # Visualization section
        viz_group = QGroupBox("Visualization")
        viz_layout = QFormLayout()
        
        # Default colormap
        self.colormap_edit = QLineEdit()
        self.colormap_edit.setPlaceholderText("e.g., RdYlBu_r, viridis, plasma")
        viz_layout.addRow("Default Colormap:", self.colormap_edit)
        
        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)
        
        # Add info label
        info_label = QLabel(
            "💡 Tip: The default data directory will be used as the starting "
            "location when you open files."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        layout.addWidget(info_label)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def _load_current_settings(self) -> None:
        """Load current settings into the form."""
        self.data_dir_edit.setText(str(self.config.start_path))
        self.colormap_edit.setText(self.config.default_colormap)
        
    def _browse_data_dir(self) -> None:
        """Open directory browser."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Default Data Directory",
            str(self.config.start_path),
        )
        
        if directory:
            self.data_dir_edit.setText(directory)
            
    def _save_settings(self) -> None:
        """Save settings and close dialog."""
        # Update config
        data_dir = self.data_dir_edit.text().strip()
        if data_dir:
            self.config.start_path = Path(data_dir)
            
        colormap = self.colormap_edit.text().strip()
        if colormap:
            self.config.default_colormap = colormap
            
        self.accept()

