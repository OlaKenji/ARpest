"""Registry for analysis modules displayed in the analysis panel."""

from __future__ import annotations

from typing import List, Type

from .base import AnalysisModule
from .fitting import FittingModule
from .overplot import OverplotModule


def get_registered_analysis_modules() -> List[Type[AnalysisModule]]:
    """Return the ordered list of analysis modules."""
    return [
        OverplotModule,
        FittingModule,
    ]
