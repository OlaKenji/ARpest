"""
Base loader interface for beamline-specific data loaders.

All beamline loaders must inherit from BaseLoader and implement
the load() method to convert beamline-specific formats into
the standard Dataset model.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from ...models import Dataset


class BaseLoader(ABC):
    """
    Abstract base class for beamline data loaders.
    
    Each beamline has its own data format. Loaders convert these
    formats into the unified Dataset model.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the beamline/instrument."""
        pass

    @property
    @abstractmethod
    def extensions(self) -> list[str]:
        """Supported file extensions (e.g., ['.txt', '.dat'])."""
        pass

    @abstractmethod
    def can_load(self, filepath: Union[str, Path]) -> bool:
        """
        Check if this loader can handle the given file.
        
        This should be a quick check (e.g., file extension, magic bytes,
        header inspection) without fully parsing the file.
        
        Args:
            filepath: Path to file to check
            
        Returns:
            True if this loader can handle the file
        """
        pass

    @abstractmethod
    def load(self, filepath: Union[str, Path]) -> Dataset:
        """
        Load data from file and convert to standard Dataset.
        
        This is where the beamline-specific parsing happens.
        The loader must:
        1. Read the file
        2. Extract axes, intensity data, and metadata
        3. Normalize naming conventions (e.g., tilt angles)
        4. Return a valid Dataset
        
        Args:
            filepath: Path to file to load
            
        Returns:
            Dataset object with standardized format
            
        Raises:
            ValueError: If file format is invalid
            IOError: If file cannot be read
        """
        pass

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} Loader"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"<{self.__class__.__name__}: {self.name} ({', '.join(self.extensions)})>"
