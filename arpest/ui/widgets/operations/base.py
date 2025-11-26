"""Base classes for processing operation widgets."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Callable, Optional

from PyQt5.QtWidgets import QGroupBox, QMessageBox

from ....models import Dataset, FileStack


class OperationWidget(QGroupBox):
    """Abstract widget representing a single operation."""

    category: str = "General"
    title: str = "Operation"
    description: str = ""

    def __init__(
        self,
        get_file_stack: Callable[[], Optional[FileStack]],
        apply_callback: Callable[[FileStack, Dataset, str], None],
        context_providers: Optional[dict[str, Callable[[], Any]]] = None,
        parent=None,
    ) -> None:
        super().__init__(self.title, parent)
        self.get_file_stack = get_file_stack
        self.apply_callback = apply_callback
        self.context_providers = context_providers or {}
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI layout; subclasses should extend."""
        self.setToolTip(self.description)
        self._build_ui()

    def _build_ui(self) -> None:
        """Create child widgets."""
        raise NotImplementedError

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        """Return the processed dataset and state name."""
        raise NotImplementedError

    def _trigger_apply(self) -> None:
        """Handle apply button invoked by subclasses."""
        file_stack = self.get_file_stack()
        if file_stack is None:
            QMessageBox.warning(self, "No dataset", "No dataset is currently selected.")
            return

        dataset = file_stack.current_state
        try:
            new_dataset, state_name = self._apply_operation(dataset)
        except ValueError as exc:
            QMessageBox.warning(self, "Operation failed", str(exc))
            return

        self.apply_callback(file_stack, new_dataset, state_name)

    def _get_context_value(self, key: str) -> Any | None:
        """Safely evaluate a context provider if available."""
        provider = self.context_providers.get(key)
        if provider is None:
            return None
        try:
            return provider()
        except Exception:
            return None
