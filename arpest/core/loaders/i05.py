"""
I05 beamline data loader (Diamond Light Source).

Loads HDF5 (.nxs) files from the I05 beamline and converts
them to the standard Dataset format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union
from dateutil import parser
import h5py
import numpy as np
from numpy.typing import NDArray

from ...models import Axis, AxisType, Dataset, Measurement
from .base import BaseLoader
from datetime import timedelta  # probably already imported elsewhere


def start_step_n(start: float, step: float, n: int) -> NDArray[np.floating]:
    """
    Create array from start, step, and number of points.
    
    Args:
        start: Starting value
        step: Step size
        n: Number of points
        
    Returns:
        Array of n points starting at start with step size step
    """
    end = start + n * step
    return np.linspace(start, end, n)


class I05Loader(BaseLoader):
    """
    Loader for I05 beamline (Diamond Light Source) data.
    
    Supports .nxs (NeXus HDF5) files.
    """

    @property
    def name(self) -> str:
        """Human-readable name."""
        return "I05 (Diamond)"

    @property
    def extensions(self) -> list[str]:
        """Supported file extensions."""
        return [".nxs", ".h5"]

    def can_load(self, filepath: Union[str, Path]) -> bool:
        """
        Check if file is an I05 beamline file.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if this is an I05 file
        """
        filepath = Path(filepath)
        
        # Check extension first
        if filepath.suffix.lower() not in self.extensions:
            return False

        # Try to open as HDF5 and check structure
        try:
            with h5py.File(filepath, "r") as f:
                # Check for characteristic I05/Diamond structure
                return "/entry1/instrument/analyser" in f
        except (OSError, KeyError):
            return False

    def load(self, filepath: Union[str, Path]) -> Dataset:
        """
        Load I05 beamline data.
        
        Args:
            filepath: Path to .nxs file
            
        Returns:
            Dataset with standardized format
            
        Raises:
            ValueError: If file format is invalid
        """
        filepath = Path(filepath)
        
        print("\n" + "="*60)
        print(f"I05 LOADER: Loading {filepath.name}")
        print("="*60)
        
        with h5py.File(filepath, "r") as infile:
            # Extract intensity data
            data = np.array(infile["/entry1/analyser/data"])
            print(f"[1] Raw data from HDF5:")
            print(f"    Shape: {data.shape}")
            print(f"    Dtype: {data.dtype}")
            print(f"    Dimensions: {data.ndim}D")
            
            # Get dimensions and axes
            xscale, yscale, zscale, is_photon_energy_scan = self._extract_axes(infile, data)
            
            print(f"\n[2] Extracted axes:")
            print(f"    xscale: {len(xscale)} points (angle)")
            print(f"    yscale: {len(yscale)} points (energy)")
            print(f"    zscale: {len(zscale)} points (photon energy)")        
            
            # Handle different data shapes
            print(f"\n[3] Processing data shape...")
            
            # Extract metadata
            measurement = self._extract_metadata(infile)            

            # Check if single cut (original code: if data.shape[2] == 1)
            is_single_cut = (data.shape[0] == 1) or (data.ndim == 3 and data.shape[2] == 1)
            
            if data.ndim == 3 and data.shape[0] == 1:
                print(f"    Detected single cut stored as 3D: {data.shape}")
                data = data.squeeze(axis=0)
                print(f"    Squeezed to 2D: {data.shape}")
                
                # For single cuts, data needs to be transposed
                # Original code does: data = data.T
                # After squeeze, shape is (n_angle, n_energy) but we want (n_energy, n_angle)
                if is_single_cut:
                    data = data.T
                    print(f"    Transposed single cut to: {data.shape}")
            
            # Now determine if 2D or 3D based on actual data dimensions
            if data.ndim == 2 or len(zscale) == 1:  # 2D data
                # Extract metadata
                print(f"\n[4] Creating 2D Dataset...")
                dataset = self._create_2d_dataset(
                    data, xscale, yscale, measurement, filepath
                )
            elif data.ndim == 3:  # 3D data (data.ndim == 3 and len(zscale) > 1)
                print(f"\n[4] Creating 3D Dataset...")
                print(f"    Data shape: {data.shape}")
                print(f"    Expected: ({len(zscale)}, {len(yscale)}, {len(xscale)})")
                dataset = self._create_3d_dataset(
                    data, yscale, xscale, zscale, measurement, filepath, is_photon_energy_scan
                )
            else:#4D data
                spatial_axes = self._extract_spatial_scan_axes(infile)
                if len(spatial_axes) < 2:
                    raise ValueError("Unable to determine spatial scan axes for 4D dataset.")
                (axis_a_name, axis_a_values), (axis_b_name, axis_b_values) = spatial_axes[:2]
                dataset = self._create_4d_dataset(
                    data,
                    axis_a_values,
                    axis_b_values,
                    zscale,
                    xscale,
                    measurement,
                    filepath,
                    axis_a_name=axis_a_name,
                    axis_b_name=axis_b_name,
                )
            
            print(f"\n[5] Final Dataset:")
            print(f"    Dimensions: {dataset.ndim}D")
            print(f"    Intensity shape: {dataset.intensity.shape}")
            print(f"    X-axis: {len(dataset.x_axis)} points")
            print(f"    Y-axis: {len(dataset.y_axis)} points")
            if dataset.z_axis:
                print(f"    Z-axis: {len(dataset.z_axis)} points")
            
            print("="*60)
            print("I05 LOADER: Success!")
            print("="*60 + "\n")
            
            return dataset
                
    def _extract_axes(
        self, infile: h5py.File, data: NDArray
    ) -> tuple[NDArray, NDArray, NDArray]:
        """Extract axis arrays from HDF5 file."""
        # Get axis scale information
        is_photon_energy_scan = False
        try:
            # Energy axis (kinetic energy)
            energies = np.array(infile["/entry1/analyser/energies"])
            
            # Handle 2D energy arrays (sometimes happens)
            if len(energies.shape) == 2:
                energies = energies[0]
                print(f"    DEBUG: Squeezed 2D energies array to 1D")
            
            # Angle axis
            angles = np.array(infile["/entry1/analyser/angles"])
            
            print(f"    DEBUG: Raw arrays - energies={len(energies)}, angles={len(angles)}")
            
            original_shape = data.shape
            print(f"    DEBUG: Original data shape: {original_shape}")
            
            # Determine if this is a single cut or a scan
            # Single cut: data.shape is (1, n_energy, n_angle) or similar
            # Scan: data.shape is (n_scan, n_energy, n_angle) or similar
            
            is_single_cut = (original_shape[0] == 1) or (len(original_shape) == 3 and original_shape[2] == 1)
            
            if is_single_cut:
                # Single cut: swap axes assignment
                print(f"    DEBUG: Detected single cut")
                xscale = energies
                yscale = angles
                
                # Z-axis is just the single photon energy
                try:
                    zscale = np.array(infile["/entry1/instrument/monochromator/energy"])
                    if np.isscalar(zscale):
                        zscale = np.array([zscale])
                except KeyError:
                    zscale = np.array([0.0])
                    
            else:
                # Full scan: need to extract scan axis
                print(f"    DEBUG: Detected full scan")
                xscale = angles
                yscale, is_photon_energy_scan = self._extract_scan_axis(infile, data)

                
                
                # Z-axis: extract from scan command
                zscale = energies
                print(f"    DEBUG: Extracted scan axis with {len(zscale)} points")
                
        except KeyError as e:
            raise ValueError(f"Missing required axis data: {e}")
            
        print(f"    DEBUG: Final assignment - xscale={len(xscale)}, yscale={len(yscale)}, zscale={len(zscale)}")
        return xscale, yscale, zscale, is_photon_energy_scan

    def _extract_scan_axis(self, infile: h5py.File, data: NDArray) -> NDArray:
        """
        Extract scan axis from scan command.
        
        Parses the scan command to determine what was scanned (deflector angle, etc.)
        """
        try:
            command = infile['entry1/scan_command'][()].decode("utf-8")
            print(f"    DEBUG: Scan command: {command}")
            
            n_points = data.shape[0]  # First dimension is scan dimension
            
            # Parse different scan types
            tokens = command.split()
            
            # Special case for 'pathgroup'
            if len(tokens) > 1 and tokens[1] == 'pathgroup':
                # Extract points from ([value, x, y], [value, x, y], ...)
                points_str = command.split('(')[-1].split(')')[0]
                tuples = points_str.split('[')[1:]
                scan_values = []
                for t in tuples:
                    point = t.split(',')[0]
                    scan_values.append(float(point))
                return np.array(scan_values), False
            
            # Special case for 'scan_group'
            elif len(tokens) > 1 and tokens[1] == 'scan_group':
                # Similar parsing
                points = command.split('((')[-1].split('))')[0]
                points = ' (' + points + ')'#changed here from '((' + points + '))'
                
                xscale = []
                for s in list(points.split(",")):
                    if s[1] == '(':
                        xscale.append(float(s[2:-2]))
                return np.array(xscale), True
            
            # Standard scan: "scan motor start stop step"
            else:
                # Extract numeric parameters
                numbers = []
                for token in tokens:
                    try:
                        numbers.append(float(token))
                    except ValueError:
                        continue
                
                if len(numbers) >= 3:
                    start, stop, step = numbers[:3]
                    # Generate axis
                    return np.arange(start, stop + 0.5 * step, step)[:n_points], False
            
            # Fallback: create default scan axis
            print(f"    DEBUG: Could not parse scan command, using default")
            return np.arange(n_points, dtype=float), False
            
        except (KeyError, ValueError, IndexError) as e:
            print(f"    DEBUG: Error parsing scan command: {e}, using default")
            # Fallback: create default axis
            n_points = data.shape[0]
            return np.arange(n_points, dtype=float)

    def _extract_angle_axis(self, infile: h5py.File, data: NDArray) -> NDArray:
        """
        Extract angle axis from scan command or defaults.
        
        I05 stores the scan command as a string that needs parsing.
        """
        # Squeeze data to get actual 2D shape
        data_squeezed = data.squeeze() if data.ndim == 3 else data
        
        # Try to get actual angles from file first
        try:
            angles = np.array(infile["/entry1/analyser/angles"])
            print(f"    DEBUG: Found angles array with {len(angles)} points")
            return angles
        except KeyError:
            pass
        
        try:
            # Try to get scan command
            scan_cmd = str(np.array(infile["/entry1/scan_command"]))
            
            # Parse the command - typically like "scan pgm_energy 100 200 0.5"
            # Look for angle scan
            if "thetax" in scan_cmd.lower() or "theta" in scan_cmd.lower():
                tokens = scan_cmd.split()
                # Find the numeric parameters (start, stop, step)
                numbers = []
                for token in tokens:
                    try:
                        numbers.append(float(token))
                    except ValueError:
                        continue
                        
                if len(numbers) >= 3:
                    start, stop, step = numbers[:3]
                    # Determine which dimension is angle
                    energies_len = len(np.array(infile["/entry1/analyser/energies"]))
                    if data_squeezed.shape[0] == energies_len:
                        n_points = data_squeezed.shape[1]  # Angle is second dimension
                    else:
                        n_points = data_squeezed.shape[0]  # Angle is first dimension
                    return np.arange(start, stop + 0.5 * step, step)[:n_points]
                    
        except (KeyError, ValueError, IndexError):
            pass
            
        # Fallback: create default angle array based on data shape
        energies_len = len(np.array(infile["/entry1/analyser/energies"]))
        if data_squeezed.shape[0] == energies_len:
            n_angles = data_squeezed.shape[1]
        else:
            n_angles = data_squeezed.shape[0]
        
        print(f"    DEBUG: Creating default angle array with {n_angles} points")
        return np.arange(n_angles, dtype=float)

    def _extract_spatial_scan_axes(self, infile: h5py.File) -> list[tuple[str, NDArray]]:
        """Parse scan command to obtain spatial scan axes (e.g., SAX, SAY)."""
        command = self._read_hdf5_string(infile["/entry1/scan_command"])
        tokens = command.replace(",", " ").split()
        axes: list[tuple[str, NDArray]] = []
        idx = 1
        while idx + 3 < len(tokens):
            axis_name = tokens[idx]
            axis_lower = axis_name.lower()
            if axis_lower in {"analyser", "analyzer", "detector"}:
                break
            try:
                start = float(tokens[idx + 1])
                stop = float(tokens[idx + 2])
                step = float(tokens[idx + 3])
            except (ValueError, IndexError):
                break
            values = np.arange(start, stop + step * 0.5, step)
            axes.append((axis_lower, values))
            idx += 4
        print(f"    DEBUG: Spatial scan axes parsed: {[name for name, _ in axes]}")
        return axes

    def _read_hdf5_string(self, x):
        value = x[()]                  # read the dataset
        if isinstance(value, np.ndarray):
            value = value.item()       # convert 0-D array → Python scalar
        if isinstance(value, bytes):
            value = value.decode("utf-8")  # decode if needed
        return value

    def _extract_metadata(self, infile: h5py.File) -> Measurement:
        """Extract metadata from HDF5 file."""
            # Required metadata
        photon_energy = float(
            np.array(infile["/entry1/instrument/monochromator/energy"])[0]
        )

        # Try to get temperature
        temperature =np.array(infile['/entry1/sample/'+'temperature'])[0]

        # Get manipulator angles (tilt)
        chi = None
        tilt_phi = None
        theta = None
        x = None
        y = None
        z = None
        manipulator_arrays: dict[str, np.ndarray] = {}
        try:
            manipulator = infile["/entry1/instrument/manipulator"]
            for position in np.array(manipulator):
                raw = np.array(manipulator[position])
                flat = raw.ravel()
                if flat.size == 0:
                    continue
                value = float(flat[0])
                pos_lower = position.lower()

                if raw.size > 1:
                    manipulator_arrays[pos_lower] = raw

                if "satilt" in pos_lower:
                    chi = value
                elif "sapolar" in pos_lower:
                    tilt_phi = value
                elif "saazimuth" in pos_lower:
                    theta = value
                elif "sax" in pos_lower:
                    x = value
                elif "say" in pos_lower:
                    y = value
                elif "saz" in pos_lower:
                    z = value
        except (KeyError, IndexError):
            pass
            
        # Extract additional metadata into custom dict
        custom = {}
        
        # Timestamp
        start = self._read_hdf5_string(infile['/entry1/start_time'])
        end   = self._read_hdf5_string(infile['/entry1/end_time'])

        total_time = parser.parse(end) - parser.parse(start)            
        count_time = str(total_time - timedelta(microseconds=total_time.microseconds))
        
        # Analyser settings
        analyser = infile["/entry1/instrument/analyser"]
        for key in analyser:                
            try:
                custom[f"analyser_{key}"] = str(np.array(analyser[key]))
            except:
                pass

        for key, values in manipulator_arrays.items():
            custom[f"manipulator_{key}"] = values

        deflector = custom.get('analyser_deflector_x', None)
        mode = custom.get('analyser_acquisition_mode', None)
        center_energy = custom.get('analyser_kinetic_energy_center', None)
        pass_energy = custom.get('analyser_pass_energy', None)

        polarisation = np.array(infile['/entry1/instrument/insertion_device/beam/final_polarisation_label']).astype(str)[0]
        slit_size = np.array(infile['/entry1/instrument/monochromator/exit_slit_size/'])[0]

        return Measurement(
            time = count_time,
            photon_energy=photon_energy,
            temperature=temperature,
            beamline="I05 (Diamond)",
            chi=chi,
            phi=tilt_phi,
            theta=theta,
            x=x,
            y=y,
            z=z,
            polarization = polarisation,
            slit_size = slit_size,
            mode = mode,
            center_energy = center_energy,
            pass_energy = pass_energy,
            deflector = deflector,
            custom=custom,
        )
            

    def _create_2d_dataset(
        self,
        data: NDArray,
        xscale: NDArray,
        yscale: NDArray,
        measurement: Measurement,
        filepath: Path,
    ) -> Dataset:
        """Create a 2D Dataset."""
        print(f"\n    [_create_2d_dataset]")
        print(f"      Input data shape: {data.shape}")
        print(f"      yscale (energy): {len(yscale)} points")
        print(f"      xscale (angle): {len(xscale)} points")
        print(f"      Expected: ({len(yscale)}, {len(xscale)})")
        
        # Data shape should be (n_energy, n_angle)
        # But might be transposed, so check
        
        # Expected: data is (n_energy, n_angle)
        if data.shape[0] == len(yscale) and data.shape[1] == len(xscale):
            # Correct orientation
            print(f"      ✓ Data orientation correct")
        elif data.shape[1] == len(yscale) and data.shape[0] == len(xscale):
            # Transposed - fix it
            data = data.T
            print(f"      ↻ Transposed to {data.shape}")
        else:
            # Try to guess best fit
            print(f"      ⚠ Shape mismatch, attempting auto-fix...")
            if data.shape[0] == len(xscale):
                data = data.T
                print(f"      ↻ Transposed to {data.shape}")
            
        return Dataset(
            x_axis=Axis(
                values=xscale,
                axis_type=AxisType.ENERGY_KINETIC,
               name="Kinetic Energy",
                unit="eV",                

            ),
            y_axis=Axis(
                values=yscale,
                axis_type=AxisType.ANGLE,
                 name="Angle",
                unit="°",
            ),
            intensity=data,
            measurement=measurement,
            filename=filepath.name,
        )

    def _create_3d_dataset(
        self,
        data: NDArray,
        xscale: NDArray,
        yscale: NDArray,
        zscale: NDArray,
        measurement: Measurement,
        filepath: Path,
        is_photon_energy_scan: bool = False,
    ) -> Dataset:
        """Create a 3D Dataset."""
        print(f"\n    [_create_3d_dataset]")
        print(f"      Input data shape: {data.shape}")
        print(f"      xscale (angle): {len(xscale)} points")
        print(f"      yscale (energy): {len(yscale)} points")
        print(f"      zscale (scan): {len(zscale)} points")
        
        # Data from I05 comes as (n_scan, n_angle, n_energy)
        # We need it as (n_angle, n_energy, n_scan) for Dataset
        # Which is: (xscale, yscale, zscale)
        
        # Expected shape
        expected_shape = (len(xscale), len(yscale), len(zscale))
        print(f"      Expected: {expected_shape}")
        
        # Transpose: (n_scan, n_angle, n_energy) -> (n_angle, n_energy, n_scan)
        # That's: (0, 1, 2) -> (1, 2, 0)
        expected_shape = (len(yscale), len(xscale), len(zscale))
        print(f"      Target: x=scan ({len(xscale)} pts, horizontal), y=angle ({len(yscale)} pts, vertical)")
        print(f"      Expected shape: {expected_shape} (angle, scan, energy)")
        
        # Transpose: (n_scan, n_angle, n_energy) -> (n_angle, n_scan, n_energy)
        # That's: (0, 1, 2) -> (1, 0, 2)
        data = np.transpose(data, (1, 0, 2))#for polar and deflector scan
        if is_photon_energy_scan:
            data = np.flip(data, axis = 1)        #for photo energy sacn
            x_axis_type = AxisType.PHOTON_ENERGY
            xscale = np.flip(xscale)
        else:
            x_axis_type = AxisType.ANGLE
            
        return Dataset(
            x_axis=Axis(
                values=xscale,
                axis_type = x_axis_type,
                name="Scan axis",
                unit="a.u.",
            ),
            y_axis=Axis(
                values=yscale,
                axis_type=AxisType.ANGLE,
                name="Angle",
                unit="°",
            ),
            z_axis=Axis(
                values=zscale,
                axis_type=AxisType.ENERGY_KINETIC,
                name="Kinetic Energy",
                unit="eV",
            ),
            intensity=data,
            measurement=measurement,
            filename=filepath.name,
        )

    def _create_4d_dataset(
        self,
        data: NDArray,
        scan_axis_a: NDArray,
        scan_axis_b: NDArray,
        energy_scale: NDArray,
        angle_scale: NDArray,
        measurement: Measurement,
        filepath: Path,
        *,
        axis_a_name: str = "sax",
        axis_b_name: str = "saz",
    ) -> Dataset:
        """Create a 4D Dataset for spatial scans (x, y, energy, angle)."""
        print(f"\n    [_create_4d_dataset]")
        print(f"      Raw data shape: {data.shape}")
        print(f"      Scan axis A '{axis_a_name}': {len(scan_axis_a)} points")
        print(f"      Scan axis B '{axis_b_name}': {len(scan_axis_b)} points")
        print(f"      Angle axis: {len(angle_scale)} points")
        print(f"      Energy axis: {len(energy_scale)} points")

        if data.ndim != 4:
            raise ValueError(f"Expected 4D intensity data, received {data.ndim}D.")

        expected_shape = (
            len(scan_axis_a),
            len(scan_axis_b),
            len(angle_scale),
            len(energy_scale),
        )
        if data.shape != expected_shape:
            raise ValueError(
                f"4D data shape mismatch. Got {data.shape}, expected {expected_shape} "
                "(scan_a, scan_b, angle, energy)."
            )

        intensity = np.transpose(data, (1, 0, 3, 2))
        print(f"      Transposed intensity shape: {intensity.shape} (y, x, energy, angle)")

        x_axis = Axis(
            values=scan_axis_a,
            axis_type=AxisType.POSITION,
            name=f"{axis_a_name.upper()} position",
            unit="mm",
        )
        y_axis = Axis(
            values=scan_axis_b,
            axis_type=AxisType.POSITION,
            name=f"{axis_b_name.upper()} position",
            unit="mm",
        )
        z_axis = Axis(
            values=energy_scale,
            axis_type=AxisType.ENERGY_KINETIC,
            name="Kinetic Energy",
            unit="eV",
        )
        w_axis = Axis(
            values=angle_scale,
            axis_type=AxisType.ANGLE,
            name="Analyzer angle",
            unit="°",
        )

        dataset = Dataset(
            x_axis=x_axis,
            y_axis=y_axis,
            z_axis=z_axis,
            w_axis=w_axis,
            intensity=intensity,
            measurement=measurement,
            filename=filepath.name,
        )
        dataset.validate()
        return dataset
