"""File catalog widget for displaying loaded files."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from .....models import FileStack


class FileCatalogWidget(QWidget):
    """
    Widget displaying list of loaded files and their states.
    
    Signals:
        file_selected: Emitted when a file is selected (index)
    """

    file_selected = pyqtSignal(int)

    def __init__(
        self, file_stacks: list[FileStack], parent: Optional[QWidget] = None
    ):
        """
        Initialize file catalog.
        
        Args:
            file_stacks: List of FileStack objects to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.file_stacks = file_stacks
        
        self._setup_ui()
        self._populate_list()
        
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # No margins
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        self.list_widget.setAlternatingRowColors(True)  # Better visual
        layout.addWidget(self.list_widget)
        
        self.setLayout(layout)
        
    def _populate_list(self) -> None:
        """Populate list with file stacks."""
        self.list_widget.clear()
        
        for file_stack in self.file_stacks:
            # Display filename and current state
            text = f"{Path(file_stack.filename).name} [{file_stack.current_name}]"
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)
            
    def _on_selection_changed(self, index: int) -> None:
        """
        Handle selection change.
        
        Args:
            index: Index of selected item
        """
        if index >= 0:
            self.file_selected.emit(index)
            
    def refresh(self) -> None:
        """Refresh the list display."""
        self._populate_list()

    def select_index(self, index: int) -> None:
        """Select a specific item in the list."""
        if 0 <= index < self.list_widget.count():
            self.list_widget.setCurrentRow(index)
        else:
            self.list_widget.clearSelection()

    def get_selected_indices(self) -> list[int]:
        """Return sorted list of selected indices."""
        indices = [index.row() for index in self.list_widget.selectedIndexes()]
        return sorted(set(i for i in indices if i >= 0))
            
    def add_file_stack(self, file_stack: FileStack) -> None:
        """
        Add a new file stack to the catalog.
        
        Args:
            file_stack: FileStack to add
        """
        self.file_stacks.append(file_stack)
        self.refresh()
