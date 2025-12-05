"""Analysis tab housing reusable visualization canvas and modules."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ....models import FileStack
from ....visualization.analysis_canvas import AnalysisCanvas
from .widgets import FittingModule, OverplotModule


class AnalysisPanel(QWidget):
    """Container for analysis modules and the shared visualization canvas."""

    def __init__(
        self,
        get_file_stack: Callable[[], FileStack | None],
        canvas: AnalysisCanvas,
        capture_view_callback: Callable[[str | None], bool],
        context_providers: dict[str, Callable[[], object]] | None = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.get_file_stack = get_file_stack
        self.canvas = canvas
        self._capture_view_callback = capture_view_callback
        self.context_providers = context_providers or {}

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        description = QLabel(
            "Capture slices or curves from the active dataset and analyse them here. "
            "When this tab is active, the main canvas on the left shows the captured data."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        capture_row = QHBoxLayout()
        self.capture_view_btn = QPushButton("Capture current figure")
        self.capture_view_btn.clicked.connect(self._on_capture_view_clicked)
        self.clear_canvas_btn = QPushButton("Clear canvas")
        self.clear_canvas_btn.clicked.connect(lambda: self.canvas.clear("No analysis data yet."))
        capture_row.addWidget(self.capture_view_btn)
        capture_row.addWidget(self.clear_canvas_btn)
        capture_row.addStretch()
        layout.addLayout(capture_row)

        panel_row = QHBoxLayout()
        panel_row.addWidget(QLabel("Capture panel:"))
        self.capture_top_left_btn = QPushButton("Top-left")
        self.capture_top_left_btn.setToolTip("Capture the top-left view (Fermi map / primary image).")
        self.capture_top_left_btn.clicked.connect(lambda: self._capture_named_view("top_left"))
        panel_row.addWidget(self.capture_top_left_btn)

        self.capture_top_right_btn = QPushButton("Top-right")
        self.capture_top_right_btn.setToolTip("Capture the top-right cut (Band @ X).")
        self.capture_top_right_btn.clicked.connect(lambda: self._capture_named_view("top_right"))
        panel_row.addWidget(self.capture_top_right_btn)

        self.capture_bottom_left_btn = QPushButton("Bottom-left")
        self.capture_bottom_left_btn.setToolTip("Capture the bottom-left cut (Band @ Y).")
        self.capture_bottom_left_btn.clicked.connect(lambda: self._capture_named_view("bottom_left"))
        panel_row.addWidget(self.capture_bottom_left_btn)
        panel_row.addStretch()
        layout.addLayout(panel_row)

        self.modules_tab = QTabWidget()
        self.modules_tab.setTabPosition(QTabWidget.North)
        self.modules_tab.setDocumentMode(True)

        self.overplot_module = OverplotModule(
            get_file_stack=self.get_file_stack,
            context_providers=self.context_providers,
            canvas=self.canvas,
        )

        self.modules_tab.addTab(self.overplot_module, "Overplot")

        self.fitting_module = FittingModule(
            get_file_stack=self.get_file_stack,
            context_providers=self.context_providers,
            canvas=self.canvas,
        )
        self.modules_tab.addTab(self.fitting_module, "Fitting")
        layout.addWidget(self.modules_tab)

        self.setLayout(layout)

    def _on_capture_view_clicked(self) -> None:
        self._capture_with_feedback(None)

    def _capture_named_view(self, view_id: str) -> None:
        self._capture_with_feedback(view_id)

    def _capture_with_feedback(self, view_id: Optional[str]) -> None:
        try:
            success = self._capture_view_callback(view_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Capture failed", str(exc))
            return
        if not success:
            QMessageBox.warning(
                self,
                "Capture failed",
                "Unable to capture the current figure. Ensure a dataset is loaded and try again.",
            )
