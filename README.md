# ARpest

**A**ngle-**R**esolved **P**hotoemission **E**lectron **S**pectroscopy **T**ool

A modern, interactive Python application for analysing ARPES (Angle-Resolved Photoemission Spectroscopy) data from multiple synchrotron beamlines.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

### Core Capabilities
- **Multi-beamline support**: Load data from Diamond Light Source (I05) and MAX IV (Bloch)
- **Multiple file formats**: `.nxs`, `.h5`, `.zip`, `.ibw`
- **2D & 3D visualisation**: Single cuts and photon energy/deflector angle scans
- **Interactive analysis**: Real-time cursor tracking with live EDC/MDC updates
- **State management**: Undo/redo functionality with complete processing history
- **Tabbed interface**: Work with multiple datasets simultaneously
- **Save dataset**: Save and comeback where you where

### Performance
- Optimized rendering for smooth visualisation
- Fast numpy slicing for data extraction
- In-place data updates (no memory reallocation)
- Efficient rendering for large datasets

---

## Installation

### Requirements
- Python 3.9 or higher
- PyQt5
- NumPy
- SciPy
- h5py
- igor (optional, for `.ibw` files)
- pyqtgraph

### Quick Install

```bash
# Clone the repository
git clone https://github.com/OlaKenji/ARpest.git
cd arpest

# Install dependencies
pip install PyQt5 numpy matplotlib scipy h5py igor, pyqtgraph

# Run the application
python run.py
```

## Usage

### Basic Workflow

1. **Launch the application**:
   ```bash
   python run.py
   ```

2. **Load data**:
   - Click the 📂 **Open File** button in the toolbar
   - Select your ARPES data file (`.nxs`, `.h5`, `.zip`, or `.ibw`)

3. **Interactive analysis**:
   - **Apply data processing**: Convert to k-space, correct the Fermi level based on a reference measurent and more
   - **Click & drag**: Continuously update cuts in real-time
   - **3D data**: Use energy slider to navigate through different energy slices

4. **Configure settings**:
   - Click ⚙️ **Settings** to set default data directory
   - Choose preferred colormap
   - Settings persist between sessions

### Supported Beamlines

#### Diamond Light Source - I05
#### MAX IV - Bloch

## Roadmap

- [ ] Additional beamline support (SLS, SOLEIL, etc.)
- [ ] Additional Data processing operations
- [ ] Export processed data
- [ ] Analysis plugins system

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

This project is licensed under the MIT License - see the LICENSE file for details.

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

### 2D Single Cut Analysis
![2D Analysis](docs/images/2d_analysis.png)
*Interactive band structure visualization with EDC and MDC*

### 3D Fermi Surface Mapping
![3D Analysis](docs/images/3d_analysis.png)
*Fermi surface with momentum cuts*

---