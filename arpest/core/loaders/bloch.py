"""
Bloch beamline data loader (MAX IV).

Loads ZIP files from the Bloch beamline at MAX IV and converts
them to the standard Dataset format.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Union

import numpy as np
from numpy.typing import NDArray

from ...models import Axis, AxisType, Dataset, Measurement
from .base import BaseLoader

def start_step_n(start: float, step: float, n: int) -> NDArray[np.floating]:
    """
    Create array from start, step, and number of points.
    
    Args:
        start: Starting value
        step: Step size
        n: Number of points
        
    Returns:
        Array of n points
    """
    end = start + n * step
    return np.linspace(start, end, n)


class BlochLoader(BaseLoader):
    """
    Loader for Bloch beamline (MAX IV) data.
    
    Supports .zip files containing spectrum data.
    """

    @property
    def name(self) -> str:
        """Human-readable name."""
        return "Bloch (MAX IV)"

    @property
    def extensions(self) -> list[str]:
        """Supported file extensions."""
        return [".zip", ".ibw"]

    def can_load(self, filepath: Union[str, Path]) -> bool:
        """
        Check if file is a Bloch beamline file (ZIP or IBW).
        
        Args:
            filepath: Path to check
            
        Returns:
            True if this is a Bloch file
        """
        filepath = Path(filepath)
        
        if filepath.suffix.lower() == ".zip":
            # Check if it contains Bloch-specific files
            try:
                with zipfile.ZipFile(filepath, 'r') as z:
                    files = z.namelist()
                    # Bloch files have viewer.ini and Spectrum_*.ini
                    return 'viewer.ini' in files and any('Spectrum_' in f for f in files)
            except (zipfile.BadZipFile, OSError):
                return False
        elif filepath.suffix.lower() == ".ibw":
            # IBW files from Bloch can be loaded
            return True
        
        return False

    def load(self, filepath: Union[str, Path]) -> Dataset:
        """
        Load Bloch beamline data from ZIP or IBW file.
        
        Args:
            filepath: Path to .zip or .ibw file
            
        Returns:
            Dataset with standardized format
            
        Raises:
            ValueError: If file format is invalid
        """
        filepath = Path(filepath)
        
        if filepath.suffix.lower() == ".zip":
            return self._load_zip(filepath)
        elif filepath.suffix.lower() == ".ibw":
            return self._load_ibw(filepath)
        else:
            raise ValueError(f"Unsupported file type: {filepath.suffix}")
    
    def _load_ibw(self, filepath: Path) -> Dataset:
        """Load IBW file from Bloch beamline."""
        try:
            from igor import binarywave
        except ImportError:
            raise ValueError(
                "igor package required for IBW files. Install with: pip install igor"
            )
        
        print("\n" + "="*60)
        print(f"BLOCH LOADER (IBW): Loading {filepath.name}")
        print("="*60)
        
        wave = binarywave.load(str(filepath))['wave']
        data = np.array([wave['wData']])
        
        print(f"[1] Raw data from IBW:")
        print(f"    Shape: {data.shape}")
        
        # Get header
        header = wave['wave_header']
        nDim = header['nDim']
        steps = header['sfA']
        starts = header['sfB']
        
        print(f"[2] Header dimensions: {nDim}")
        print(f"    Steps: {steps[:3]}")
        print(f"    Starts: {starts[:3]}")
        
        # Parse metadata from note
        note = wave['note'].decode('ASCII').split('\r')
        M2 = {}
        for line in note:
            try:
                name, val = line.split('=')
                M2[name] = val
            except ValueError:
                continue
        
        is_spatial_scan = len(data.shape) == 5

        def _safe_float(value: str | None) -> float | None:
            try:
                return float(value) if value not in (None, "") else None
            except (TypeError, ValueError):
                return None

        # Extract metadata
        metadata = {}
        for key, name, dtype in self._meta_keys():
            try:
                if name == 'hv' or name == 'tilt':
                    metadata[name] = float(M2.get(key, 0))
                else:
                    metadata[name] = M2.get(key, '')
            except (KeyError, ValueError):
                pass
        
        # Create measurement
        measurement = Measurement(
            time=M2.get('Time'),
            photon_energy=float(M2['Excitation Energy']),
            temperature=None,  # Not in IBW files
            beamline="Bloch (MAX IV)",
            pass_energy=_safe_float(M2.get('Pass Energy')),
            deflector=_safe_float(M2.get('ThetaY')),
            x=None if is_spatial_scan else _safe_float(M2.get('X')),
            y=None if is_spatial_scan else _safe_float(M2.get('Y')),
            z=_safe_float(M2.get('Z')),
            phi=_safe_float(M2.get('A')),
            theta=_safe_float(M2.get('P')),
            chi=_safe_float(M2.get('T')),
            mode=M2.get('Acquisition Mode'),
            center_energy=_safe_float(M2.get('Center Energy')),
            slit_size=None,
            custom=metadata,
        )
        
        # Determine if 2D or 3D based on data shape
        print(f"[3] Processing data...")

        if len(data.shape) == 5:  # 4D scan (spatial map)
            print("    Detected 4D data (spatial map)")
            data = data[0]
            print(f"    After squeeze: {data.shape}")

            n_energy, n_angle, n_y, n_x = data.shape
            print(f"    Dimensions: energy={n_energy}, angle={n_angle}, y={n_y}, x={n_x}")

            energy_axis = start_step_n(starts[0], steps[0], n_energy)
            angle_axis = start_step_n(starts[1], steps[1], n_angle)
            y_axis_values = start_step_n(starts[2], steps[2], n_y)
            x_axis_values = start_step_n(starts[3], steps[3], n_x)

            print(f"[4] 4D axes:")
            print(f"    x positions: {len(x_axis_values)} points")
            print(f"    y positions: {len(y_axis_values)} points")
            print(f"    energy axis: {len(energy_axis)} points")
            print(f"    angle axis: {len(angle_axis)} points")

            # Rearrange to Dataset order (y, x, energy, angle)
            data = np.transpose(data, (2, 3, 0, 1))
            print(f"    Data shape after reorder: {data.shape}")

            x_axis = Axis(
                x_axis_values,
                AxisType.POSITION,
                "X position",
                "mm",
            )
            y_axis = Axis(
                y_axis_values,
                AxisType.POSITION,
                "Y position",
                "mm",
            )
            z_axis = Axis(
                energy_axis,
                AxisType.ENERGY_KINETIC,
                "Kinetic Energy",
                "eV",
            )
            w_axis = Axis(
                angle_axis,
                AxisType.ANGLE,
                "Angle",
                "°",
            )

            dataset = Dataset(
                x_axis=x_axis,
                y_axis=y_axis,
                z_axis=z_axis,
                w_axis=w_axis,
                intensity=data,
                measurement=measurement,
                filename=filepath.name,
            )
            dataset.validate()

        elif len(data.shape) == 4:  # 3D scan (hv scan)
            print(f"    Detected 3D data (photon energy scan)")
            # Data shape is (1, n_energy, n_angle, n_hv)
            # Remove the leading singleton dimension from IGOR
            data = data[0]
            print(f"    After squeeze: {data.shape}")
            
            # Dimensions from header
            n_energy = int(nDim[0])
            n_angle = int(nDim[1])
            n_hv = int(nDim[2])
            
            print(f"    Header says: n_energy={n_energy}, n_angle={n_angle}, n_hv={n_hv}")
            
            # Construct axes
            energy_axis = start_step_n(starts[0], steps[0], n_energy)
            angle_axis = start_step_n(starts[1], steps[1], n_angle)
            
            # Z-scale: photon energies from metadata
            # Extract from M2['Point 1'], M2['Point 2'], etc.
            zscale_list = []
            for i in range(1, n_hv + 1):  # Use actual n_hv from data
                key = f'Point {i}'
                if key in M2:
                    val_str = M2[key].replace(" eV", "").strip()
                    try:
                        zscale_list.append(float(val_str))
                    except ValueError:
                        pass
            
            if len(zscale_list) == n_hv:
                zscale = np.array(zscale_list)
            else:
                # Fallback
                print(f"    WARNING: Could not extract {n_hv} photon energies, found {len(zscale_list)}")
                zscale = np.arange(n_hv, dtype=float)
            
            print(f"[4] 3D axes:")
            print(f"    angle_axis: {len(angle_axis)} points")
            print(f"    energy_axis: {len(energy_axis)} points")
            print(f"    zscale (photon energy): {len(zscale)} points")
            
            # Reorder to Dataset convention: (y=angle, x=hv, z=energy)
            data = np.transpose(data, (1, 2, 0))
            print(f"    Data shape after reorder: {data.shape}")
            print(f"    Expected: ({len(angle_axis)}, {len(zscale)}, {len(energy_axis)})")
            
            dataset = Dataset(
                x_axis=Axis(zscale, AxisType.PHOTON_ENERGY, "Photon Energy", "eV"),
                y_axis=Axis(angle_axis, AxisType.ANGLE, "Angle", "°"),
                z_axis=Axis(energy_axis, AxisType.ENERGY_KINETIC, "Kinetic Energy", "eV"),
                intensity=data,
                measurement=measurement,
                filename=filepath.name,
            )
            
        else:  # 2D data
            print(f"    Detected 2D data")
            data = np.swapaxes(data, 1, 2)  # Energy on x, angle on y
            
            # Construct axes
            xscale = start_step_n(starts[0], steps[0], nDim[0])
            yscale = start_step_n(starts[1], steps[1], nDim[1])
            
            # Squeeze data
            data = data.squeeze()
            
            print(f"[4] 2D axes:")
            print(f"    yscale (angle): {len(yscale)} points")
            print(f"    xscale (energy): {len(xscale)} points")
            print(f"    Final shape: {data.shape}")
            
            dataset = Dataset(
                y_axis=Axis(yscale, AxisType.ANGLE, "Angle", "°"),
                x_axis=Axis(xscale, AxisType.ENERGY_KINETIC, "Kinetic Energy", "eV"),
                intensity=data,
                measurement=measurement,
                filename=filepath.name,
            )
        
        print("="*60)
        print("BLOCH LOADER (IBW): Success!")
        print("="*60 + "\n")
        
        return dataset
            
    def _load_zip(self, filepath: Path) -> Dataset:
        """
        Load Bloch beamline data from ZIP file.
        
        Args:
            filepath: Path to .zip file
            
        Returns:
            Dataset with standardized format
            
        Raises:
            ValueError: If file format is invalid
        """
        print("\n" + "="*60)
        print(f"BLOCH LOADER (ZIP): Loading {filepath.name}")
        print("="*60)
        
        with zipfile.ZipFile(filepath, 'r') as z:
            # Get file ID from viewer.ini
            with z.open('viewer.ini') as viewer:
                file_id = self._read_viewer(viewer)
            print(f"[1] File ID: {file_id}")
            
            # Load metadata from spectrum ini
            with z.open(f'Spectrum_{file_id}.ini') as metadata_file:
                spectrum_meta = self._read_metadata(metadata_file, self._spectrum_keys())
            
            print(f"[2] Spectrum metadata:")
            print(f"    Dimensions: ({spectrum_meta['n_y']}, {spectrum_meta['n_x']}, {spectrum_meta['n_energy']})")
            print(f"    Energy range: {spectrum_meta['first_energy']} to {spectrum_meta['last_energy']}")
            
            # Load additional metadata
            with z.open(f'{file_id}.ini') as metadata_file2:
                extra_meta = self._read_metadata(metadata_file2, self._meta_keys())
            
            # Load binary data
            with z.open(f'Spectrum_{file_id}.bin') as f:
                data_flat = np.frombuffer(f.read(), dtype='float32')
        
        print(f"[3] Binary data loaded: {len(data_flat)} values")
        
        # Reshape data
        n_y = int(spectrum_meta['n_y'])
        n_x = int(spectrum_meta['n_x'])
        n_energy = int(spectrum_meta['n_energy'])
        
        print(f"[4] Attempting reshape:")
        print(f"    n_y (dim 0): {n_y}")
        print(f"    n_x (dim 1): {n_x}")  
        print(f"    n_energy (dim 2): {n_energy}")
        print(f"    Expected total: {n_y * n_x * n_energy}")
        print(f"    Actual values: {len(data_flat)}")
        
        data = np.reshape(data_flat, (n_y, n_x, n_energy))
        print(f"    Reshaped to: {data.shape}")
        
        # Cut off unswept region
        first = int(spectrum_meta['first_energy'])
        last = int(spectrum_meta['last_energy'])
        
        print(f"[5] Energy range from metadata:")
        print(f"    first_energy: {first}")
        print(f"    last_energy: {last}")
        print(f"    Data dim 2 size: {data.shape[2]}")
        
        # Make sure indices are valid for dimension 2 (energy)
        max_index = data.shape[2] - 1
        if last > max_index:
            print(f"    WARNING: last={last} > max_index={max_index}, adjusting to {max_index}")
            last = max_index
        if first < 0:
            first = 0
        if first > last:
            print(f"    WARNING: first > last, swapping")
            first, last = last, first
            
        print(f"    Slicing [:, :, {first}:{last + 1}]")
        data = data[:, :, first:last + 1]
        print(f"[6] After cutting: {data.shape}")
        
        # Transpose to (energy, x, y)
        data = np.moveaxis(data, 2, 0)
        print(f"[7] After moveaxis(2, 0): {data.shape}")
        
        # Create axes
        xscale = start_step_n(
            spectrum_meta['start_x'],
            spectrum_meta['step_x'],
            n_x
        )
        yscale = start_step_n(
            spectrum_meta['start_y'],
            spectrum_meta['step_y'],
            n_y
        )
        
        # Create FULL energy axis first
        energies_full = start_step_n(
            spectrum_meta['start_energy'],
            spectrum_meta['step_energy'],
            n_energy
        )
        print(f"    Full energy axis: {len(energies_full)} points")
        
        # Now cut energies to match the cut data
        energies = energies_full[first:last + 1]
        
        print(f"[8] Axes created:")
        print(f"    xscale: {len(xscale)} points")
        print(f"    yscale: {len(yscale)} points")
        print(f"    energies: {len(energies)} points (cut from {len(energies_full)})")
        print(f"    Data shape after cutting: {data.shape}")
        print(f"    Expected match: data.shape[0]={data.shape[0]} == len(energies)={len(energies)}")
        
        # Create measurement metadata  
        measurement = Measurement(
            photon_energy=extra_meta['hv'],
            temperature=extra_meta.get('temperature', 300.0),
            beamline="Bloch (MAX IV)",            
            time = extra_meta['Time'],                                    
            pass_energy = float(extra_meta['Pass Energy']),
            deflector =  float(extra_meta['Deflector']),
            x=float(extra_meta['X']),
            y=float(extra_meta['Y']),
            z=float(extra_meta['Z']), 
            phi=float(extra_meta['azimuth']),
            theta=float(extra_meta['polar']),
            chi=float(extra_meta['tilt']),   
            mode = extra_meta['Acquisition Mode'],  
            center_energy = float(extra_meta['Center Energy']),    
            slit_size = float(extra_meta['exit_slit_h']),
            custom=extra_meta     

        )
        
        # Determine if 2D or 3D
        print(f"[9] Determining dimensionality...")
        if len(yscale) == 1:  # 2D data
            print(f"    2D data detected (yscale length = 1)")
            # Transpose to (x, energy)
            data_2d = np.transpose(data, (1, 2, 0)).squeeze()
            print(f"    Final 2D shape: {data_2d.shape}")
            
            dataset = Dataset(
                x_axis=Axis(energies, AxisType.ENERGY_KINETIC, "Kinetic Energy", "eV"),
                y_axis=Axis(xscale, AxisType.ANGLE, "Angle", "°"),
                intensity=data_2d,
                measurement=measurement,
                filename=filepath.name,
            )
        else:  # 3D data
            print(f"    3D data detected")
            # Data after moveaxis is: (energy, y, x) = (972, 49, 740)
            # Transpose to: (y, x, energy) = (49, 740, 972)
            # But Dataset expects: (y_axis, x_axis, z_axis)
            
            # Current data shape: (energy, y, x) = (972, 49, 740)
            # We want: (y, x, energy) = (49, 740, 972)
            data_3d = np.transpose(data, (1, 2, 0))
            print(f"    Transposed from {data.shape} to {data_3d.shape}")
            
            # Now data is (y, x, energy) = (49, 740, 972)
            # So: y_axis=yscale (49), x_axis=xscale (740), z_axis=energies (972)
            
            dataset = Dataset(
                x_axis=Axis(xscale, AxisType.ANGLE, "Angle X", "°"),
                y_axis=Axis(yscale, AxisType.ANGLE, "Angle Y", "°"),
                z_axis=Axis(energies, AxisType.ENERGY_KINETIC, "Kinetic Energy", "eV"),
                intensity=data_3d,
                measurement=measurement,
                filename=filepath.name,
            )
            
            print(f"    Dataset shape check:")
            print(f"      intensity: {data_3d.shape}")
            print(f"      expected: ({len(yscale)}, {len(xscale)}, {len(energies)})")
        
        print("="*60)
        print("BLOCH LOADER (ZIP): Success!")
        print("="*60 + "\n")
        
        return dataset
            

    @staticmethod
    def _read_viewer(viewer) -> str:
        """Extract file ID from viewer.ini."""
        for line in viewer.readlines():
            l = line.decode('UTF-8')
            if l.startswith('name'):
                return l.split('=')[1].split()[0]
        raise ValueError("Could not find file ID in viewer.ini")

    def _read_metadata(self, metadata_file, keys):
        """
        Read metadata from INI file.
        
        Args:
            metadata_file: File object
            keys: List of (key_name, output_name, dtype) tuples
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        for raw_line in metadata_file.readlines():
            line = raw_line.decode('utf-8').strip()
            if not line or '=' not in line:
                continue            

            key, value = [part.strip() for part in line.split('=', 1)]
            if key == 'Comments':
                metadata.update(self._parse_comment_metadata(value))
                continue
            
            for meta_key, name, dtype in keys:
                if key == meta_key:
                    if dtype is str:
                        cleaned_value = value
                    else:
                        cleaned_value = value.split()[0]
                    try:
                        metadata[name] = dtype(cleaned_value)
                    except ValueError:
                        pass
        return metadata

    @staticmethod
    def _parse_comment_metadata(comment_text: str) -> dict:
        """Extract exit slit sizes and temperature details from comments."""
        metadata: dict = {}
        text = comment_text.replace('\r', ' ').strip()

        exit_slit_match = re.search(
            r"Exit slit h x v\s*=*\s*([0-9.]+)\s*x\s*([0-9.]+)",
            text,
            re.IGNORECASE,
        )
        if exit_slit_match:
            h_val, v_val = exit_slit_match.groups()
            metadata['exit_slit'] = f"{h_val} x {v_val}"
            metadata['exit_slit_h'] = float(h_val)
            metadata['exit_slit_v'] = float(v_val)

        temp_match = re.search(
            r"sample\s+estimated\s+at\s*([0-9.]+)\s*K",
            text,
            re.IGNORECASE,
        )
        if temp_match:
            metadata['temperature'] = float(temp_match.group(1))

        return metadata

    @staticmethod
    def _spectrum_keys():
        """Keys for Spectrum_*.ini file."""
        return [
            ('width', 'n_energy', int),
            ('height', 'n_x', int),
            ('depth', 'n_y', int),
            ('first_full', 'first_energy', int),
            ('last_full', 'last_energy', int),
            ('widthoffset', 'start_energy', float),
            ('widthdelta', 'step_energy', float),
            ('heightoffset', 'start_x', float),
            ('heightdelta', 'step_x', float),
            ('depthoffset', 'start_y', float),
            ('depthdelta', 'step_y', float),
        ]

    @staticmethod
    def _meta_keys():
        """Keys for main metadata file."""
        return [
            ('Date', 'Date', str),
            ('Time', 'Time', str),
            ('Excitation Energy', 'hv', float),
            ('A', 'azimuth', float),
            ('P', 'polar', float),
            ('T', 'tilt', float),
            ('X', 'X', float),
            ('Y', 'Y', float),
            ('Z', 'Z', float),
            ('ThetaY', 'Deflector', float),
            ('Pass Energy', 'Pass Energy', int),
            ('Number of Sweeps', 'Number of Sweeps', int),
            ('Acquisition Mode', 'Acquisition Mode', str),
            ('Center Energy', 'Center Energy', float),
            ('Low Energy', 'Low Energy', float),
            ('High Energy', 'High Energy', float),
            ('Energy Step', 'Energy Step', float),
        ]
