"""
Core data models for ARPES data representation.

This module defines the fundamental data structures used throughout the application.
All beamline loaders must convert their specific formats into these standard models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
from numpy.typing import NDArray


class AxisType(Enum):
    """Physical quantity represented by an axis."""

    ANGLE = "angle"  # Emission angle (degrees)
    ENERGY_KINETIC = "energy_ke"  # Kinetic energy (eV)
    ENERGY_BINDING = "energy_be"  # Binding energy (eV)
    PHOTON_ENERGY = "photon_hv"  # Photon energy (eV)
    K_PARALLEL = "k_parallel"  # k|| (Å⁻¹)
    K_PERPENDICULAR = "k_perp"  # k⊥ (Å⁻¹)
    TIME = "time"  # Time (s) for time-resolved measurements
    TEMPERATURE = "temperature"  # Temperature (K)
    POSITION = "position"  # Spatial position (mm/μm)
    GENERIC = "generic"  # For custom/unknown axes


@dataclass
class Axis:
    """
    Represents a single axis of data.
    
    Attributes:
        values: Array of axis values
        axis_type: Physical quantity type
        name: Display name for plots
        unit: Unit symbol for display
    """

    values: NDArray[np.floating]
    axis_type: AxisType
    name: str
    unit: str

    def __len__(self) -> int:
        """Return number of points along axis."""
        return len(self.values)

    def __post_init__(self) -> None:
        """Validate axis after initialization."""
        if not isinstance(self.values, np.ndarray):
            self.values = np.array(self.values)

    @property
    def min(self) -> float:
        """Minimum value along axis."""
        return float(np.min(self.values))

    @property
    def max(self) -> float:
        """Maximum value along axis."""
        return float(np.max(self.values))

    @property
    def range(self) -> float:
        """Range of axis values."""
        return self.max - self.min


@dataclass
class Measurement:
    """
    Experimental metadata for a measurement.
    
    Common metadata fields are defined as attributes.
    Beamline-specific metadata goes into the 'custom' dictionary.
    """

    photon_energy: float  # hv (eV)
    temperature: float  # Sample temperature (K)
    beamline: str  # Beamline/instrument identifier

    # Optional common fields
    time: Optional[str] = None
    polarization: Optional[str] = None
    work_function: Optional[float] = None
    pass_energy: Optional[float] = None
    slit_size: Optional[float] = None
    mode: Optional[float] = None
    center_energy: Optional[float] = None
    deflector: Optional[float] = None
    
    # Tilt angles - beamline loaders should normalize these names
    chi: Optional[float] = None  # Polar angle
    phi: Optional[float] = None  # Azimuthal angle
    theta: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    
    # Beamline-specific metadata
    custom: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure custom dict is initialized."""
        if self.custom is None:
            self.custom = {}

    def to_dict(self) -> dict:
        """
        Convert metadata to dictionary for display/export.
        
        Returns:
            Dictionary with all metadata fields
        """
        result = {
            "hv": self.photon_energy,
            "temperature": self.temperature,
            "beamline": self.beamline,
        }
        
        # Add optional fields if present
        if self.time is not None:
            result["time"] = self.time
        if self.polarization is not None:
            result["polarization"] = self.polarization
        if self.work_function is not None:
            result["work_function"] = self.work_function
        if self.pass_energy is not None:
            result["pass_energy"] = self.pass_energy
        if self.tilt_theta is not None:
            result["tilt_theta"] = self.tilt_theta
        if self.tilt_phi is not None:
            result["tilt_phi"] = self.tilt_phi
            
        # Add custom metadata
        result.update(self.custom)
        
        return result


@dataclass
class Dataset:
    """
    Core data structure for ARPES measurements.
    
    This is the unified format that all beamline loaders must produce.
    Supports 2D, 3D, and 4D data in a modular way.
    
    Attributes:
        x_axis: Primary axis (typically angle or energy)
        y_axis: Secondary axis (typically energy or angle)
        intensity: 2D/3D/4D intensity array
        measurement: Experimental metadata
        z_axis: Third axis (e.g., photon energy for constant-energy maps)
        w_axis: Fourth axis (e.g., temperature, time, position)
        filename: Original filename
    """

    # Required fields first
    x_axis: Axis
    y_axis: Axis
    intensity: NDArray[np.floating] = field(repr=False)
    measurement: Measurement
    
    # Optional fields
    z_axis: Optional[Axis] = None
    w_axis: Optional[Axis] = None
    filename: str = ""

    @property
    def ndim(self) -> int:
        """Number of dimensions (2, 3, or 4)."""
        if self.w_axis is not None:
            return 4
        elif self.z_axis is not None:
            return 3
        else:
            return 2

    @property
    def is_2d(self) -> bool:
        """Check if dataset is 2D."""
        return self.ndim == 2

    @property
    def is_3d(self) -> bool:
        """Check if dataset is 3D."""
        return self.ndim == 3

    @property
    def is_4d(self) -> bool:
        """Check if dataset is 4D."""
        return self.ndim == 4

    @property
    def shape(self) -> tuple[int, ...]:
        """Shape of intensity array."""
        return self.intensity.shape

    @property
    def axes(self) -> list[Axis]:
        """Get list of all axes (in order: x, y, z, w)."""
        result = [self.x_axis, self.y_axis]
        if self.z_axis is not None:
            result.append(self.z_axis)
        if self.w_axis is not None:
            result.append(self.w_axis)
        return result

    def validate(self) -> bool:
        """
        Validate data consistency.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If shape mismatch detected
        """
        # Build expected shape based on ACTUAL data dimensions, not axis presence
        # A z_axis with length 1 still means 2D data
        ndim = self.intensity.ndim
        
        if ndim == 2:
            expected_shape = (len(self.y_axis), len(self.x_axis))
        elif ndim == 3:
            expected_shape = (len(self.y_axis), len(self.x_axis), len(self.z_axis))
        elif ndim == 4:
            expected_shape = (
                len(self.y_axis),
                len(self.x_axis),
                len(self.z_axis),
                len(self.w_axis),
            )
        else:
            raise ValueError(f"Unsupported data dimensionality: {ndim}")

        if self.intensity.shape != expected_shape:
            raise ValueError(
                f"Shape mismatch: intensity shape {self.intensity.shape} "
                f"does not match axes shape {expected_shape}"
            )

        return True

    def get_slice_2d(
        self, z_index: Optional[int] = None, w_index: Optional[int] = None
    ) -> tuple[NDArray, Axis, Axis]:
        """
        Extract a 2D slice from 3D or 4D data.
        
        Args:
            z_index: Index along z-axis (for 3D/4D data)
            w_index: Index along w-axis (for 4D data)
            
        Returns:
            Tuple of (2D intensity array, x_axis, y_axis)
        """
        if self.is_2d:
            return self.intensity, self.x_axis, self.y_axis
        elif self.is_3d:
            if z_index is None:
                z_index = len(self.z_axis) // 2
            return self.intensity[:, :, z_index], self.x_axis, self.y_axis
        else:  # 4D
            if z_index is None:
                z_index = len(self.z_axis) // 2
            if w_index is None:
                w_index = len(self.w_axis) // 2
            return self.intensity[:, :, z_index, w_index], self.x_axis, self.y_axis

    def copy(self) -> Dataset:
        """
        Create a deep copy of the dataset.
        
        Returns:
            New Dataset instance with copied data
        """
        return Dataset(
            x_axis=Axis(
                self.x_axis.values.copy(),
                self.x_axis.axis_type,
                self.x_axis.name,
                self.x_axis.unit,
            ),
            y_axis=Axis(
                self.y_axis.values.copy(),
                self.y_axis.axis_type,
                self.y_axis.name,
                self.y_axis.unit,
            ),
            intensity=self.intensity.copy(),
            measurement=Measurement(
                photon_energy=self.measurement.photon_energy,
                temperature=self.measurement.temperature,
                beamline=self.measurement.beamline,
                time=self.measurement.time,
                polarization=self.measurement.polarization,
                work_function=self.measurement.work_function,
                pass_energy=self.measurement.pass_energy,
                chi=self.measurement.chi,
                phi=self.measurement.phi,
                theta=self.measurement.theta,
                x=self.measurement.x,
                y=self.measurement.y,
                z=self.measurement.z,
                slit_size=self.measurement.slit_size,
                mode=self.measurement.mode,
                center_energy=self.measurement.center_energy,
                deflector=self.measurement.deflector,
                custom=self.measurement.custom.copy(),
            ),
            z_axis=Axis(
                self.z_axis.values.copy(),
                self.z_axis.axis_type,
                self.z_axis.name,
                self.z_axis.unit,
            )
            if self.z_axis
            else None,
            w_axis=Axis(
                self.w_axis.values.copy(),
                self.w_axis.axis_type,
                self.w_axis.name,
                self.w_axis.unit,
            )
            if self.w_axis
            else None,
            filename=self.filename,
        )
