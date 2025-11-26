"""State history widget for a FileStack."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ...models import FileStack


class StateHistoryWidget(QWidget):
    """Displays and selects states within a FileStack."""

    state_selected = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._file_stack: Optional[FileStack] = None
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_row_changed)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def set_file_stack(self, file_stack: Optional[FileStack]) -> None:
        """Assign a file stack and refresh the list."""
        self._file_stack = file_stack
        self.refresh()

    def refresh(self) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if self._file_stack is not None:
            for idx, name, is_current in self._file_stack.get_state_info():
                item = QListWidgetItem(f"{idx}: {name}")
                self.list_widget.addItem(item)
                if is_current:
                    self.list_widget.setCurrentRow(idx)
        self.list_widget.blockSignals(False)

    def _on_row_changed(self, row: int) -> None:
        if row >= 0 and self._file_stack is not None:
            self.state_selected.emit(row)
