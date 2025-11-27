"""Operations panel for datasets."""

from __future__ import annotations

from typing import Callable, List, Type

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QScrollArea,
    QFrame,
)

from ...models import FileStack, Dataset
from .operations.base import OperationWidget


class OperationsPanel(QWidget):
    """Container widget that groups available operations by category."""

    def __init__(
        self,
        get_file_stack: Callable[[], FileStack],
        apply_callback: Callable[[FileStack, Dataset, str], None],
        operation_classes: List[Type[OperationWidget]],
        context_providers: dict[str, Callable[[], object]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.apply_callback = apply_callback
        self.operation_classes = operation_classes
        self.context_providers = context_providers or {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Organize operations by category
        category_widgets: dict[str, QVBoxLayout] = {}

        for op_cls in self.operation_classes:
            category = getattr(op_cls, "category", "General")
            if category not in category_widgets:
                container = QFrame()
                vbox = QVBoxLayout()
                vbox.setContentsMargins(4, 4, 4, 4)
                vbox.setSpacing(8)
                container.setLayout(vbox)

                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                scroll.setWidget(container)
                self.tabs.addTab(scroll, category)
                category_widgets[category] = vbox

            widget = op_cls(
                self.get_file_stack,
                self.apply_callback,
                context_providers=self.context_providers,
            )
            category_widgets[category].addWidget(widget)

        # add stretch to each tab layout
        for vbox in category_widgets.values():
            vbox.addStretch()
