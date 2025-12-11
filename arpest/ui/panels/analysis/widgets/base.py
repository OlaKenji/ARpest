"""Shared primitives for analysis modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from typing_extensions import Protocol

from PyQt5.QtWidgets import QWidget

from .....models import FileStack
from .....visualization.analysis_canvas import AnalysisCanvas
from ..history import CaptureHistoryModel, CurveCaptureEntry

CurveSelectionCallback = Callable[[CurveCaptureEntry or None], None]

class CurveSelectionRegistrar(Protocol):
    """Protocol describing the capture history selection hook."""

    def __call__(self, callback: CurveSelectionCallback) -> None: ...


@dataclass()
class AnalysisModuleContext:
    """Container exposing shared tooling for analysis modules."""

    canvas: AnalysisCanvas
    capture_history: CaptureHistoryModel
    get_file_stack: Callable[[], FileStack or None]
    context_providers: dict[str, Callable[[], object]]
    register_curve_selection_callback: CurveSelectionRegistrar


class AnalysisModule(QWidget):
    """Base widget for modules hosted in the analysis panel."""

    title: str = "Module"
    wrap_in_scroll: bool = False

    def __init__(self, context: AnalysisModuleContext, parent: QWidget or None = None) -> None:
        super().__init__(parent)
        self.context = context
