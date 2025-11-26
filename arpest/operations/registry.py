"""Operation registry."""

from __future__ import annotations

from typing import List, Type

from .base import OperationWidget
from .basic import NormalizeOperationWidget, ScaleOperationWidget
from .k_space import KSpaceOperationWidget

def get_registered_operations() -> List[Type[OperationWidget]]:
    """Return the list of available operation widgets."""
    return [
        NormalizeOperationWidget,
        ScaleOperationWidget,
        KSpaceOperationWidget,
    ]
