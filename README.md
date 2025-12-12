# ARpest

**A**ngle **R**esolved **P**hotoemission **E**lectron **S**pectroscopy **T**ool

A modern, interactive GUI application for analysing ARPES (Angle-Resolved Photoemission Spectroscopy) data from multiple synchrotron beamlines. Coding or scripting is not needed.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

### Core Capabilities
- **Multi-beamline support**: Load data from Diamond Light Source (I05) and MAX IV (Bloch)
- **Multiple file formats**: `.nxs`, `.zip`, `.ibw`
- **2D, 3D & 4D visualisation**: Single cuts and photon energy/deflector angle scans
- **Interactive visualisation**: Real-time cursor tracking with live EDC/MDC updates
- **Proces the data**: Convert to k-space, correct the Fermi level based on a reference measurent etc.
- **State management**: Undo/redo functionality with complete processing history
- **Analyse the data**: Fit the process data
- **Tabbed interface**: Work with multiple datasets simultaneously
- **Save dataset**: Save and comeback where you where

### Performance
- Optimized rendering for smooth visualisation
- Fast numpy slicing for data extraction
- In-place data updates 

---

## Installation

### Requirements
- Python 3.7 or higher
- PyQt5
- NumPy
- SciPy
- h5py
- igor
- pyqtgraph

### Quick Install

```bash
# Install ARpest from PyPI
pip install arpest

# Launch the GUI
arpest
```

## Usage

### Basic Workflow

1. **Launch the application**:
   ```bash
   arpest
   ```

2. **Configure settings**:
   - Click ⚙️ **Settings** to set default data directory
   - Choose preferred colormap
   - Settings persist between sessions

3. **Load data**:
   - Click the 📂 **Open File** button in the toolbar
   - Select your ARPES data file (`.nxs`, `.h5`, `.zip`, or `.ibw`)

4. **Interactive visualisation**:
   - **Click & drag**: Continuously update cuts in real-time
   - **3D data**: Use energy slider to navigate through different energy slices

5. **Analyse and process the data**:
   - **Apply data processing**: Convert to k-space, correct the Fermi level based on a reference measurent and more
   - **Analyse by fitting the processed data**: Fit EDC/MDC curves

### Supported Beamlines

#### Diamond Light Source - I05
#### MAX IV - Bloch

## Roadmap

- [ ] Additional beamline support (SLS, SOLEIL, etc.)
- [ ] Additional analysis methods

---
## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---
## License

This project is licensed under the MIT License.

---
## Citation

If you use ARpest in your research, please cite:

```bibtex
@software{arpest2025,
  author = {Ola Kenji Forslund},
  title = {ARpest: Interactive ARPES Data Analysis Tool},
  year = {2025},
  url = {https://github.com/OlaKenji/arpest}
}
```

---

## Screenshots

### 3D Fermi Surface Mapping

![3D Analysis](docs/images/3d_analysis.png)

*Fermi surface with momentum cuts. Data from Phys. Rev. Lett. **134**, 126602 (<https://doi.org/10.1103/PhysRevLett.134.126602>)*.


---