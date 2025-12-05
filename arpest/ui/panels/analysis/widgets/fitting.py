"""Placeholder fitting module for future curve/surface fitting tools."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from .....models import FileStack
from .....visualization.analysis_canvas import AnalysisCanvas


class FittingModule(QWidget):
    """Scaffold for upcoming fitting features."""

    def __init__(
        self,
        *,
        get_file_stack: Callable[[], FileStack | None],
        canvas: AnalysisCanvas,
        context_providers: dict[str, Callable[[], object]],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.canvas = canvas
        self.context_providers = context_providers

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(
            QLabel(
                "Fitting tools will appear here. Capture EDC/MDC data and configure fitting models "
            )
        )

        self.setLayout(layout)
