"""Operation widget registry."""

from __future__ import annotations

from typing import List, Type

from .base import OperationWidget
from .basic import NormalizeOperationWidget, ScaleOperationWidget, CropOperationWidget, ModifyAxesOperationWidget, ModifyByDataOperationWidget
from .fermi_level import FermiLevelCorrectionWidget
from .k_space import KSpaceOperationWidget
from .curvature import CurvatureOperationWidget
from .background import BackgroundOperationWidget

def get_registered_operations() -> List[Type[OperationWidget]]:
    """Return the list of available operation widgets."""
    return [
        NormalizeOperationWidget,
        ScaleOperationWidget,
        FermiLevelCorrectionWidget,
        KSpaceOperationWidget,
        CropOperationWidget,
        ModifyAxesOperationWidget,
        ModifyByDataOperationWidget,
        CurvatureOperationWidget,
        BackgroundOperationWidget,
    ]
