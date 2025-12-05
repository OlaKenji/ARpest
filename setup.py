"""
Setup script for ARpest.

This file is needed for editable installs with older pip versions.
Modern pip (>=21.3) can use pyproject.toml alone.
"""

from setuptools import setup, find_packages

setup(
    name="arpest",
    version="1.0.1",
    packages=find_packages(),
    python_requires=">=3.7.13",
    install_requires=[
        "numpy>=1.21.6",
        "matplotlib>=3.5.3",
        "scipy>=1.7.3",
        "h5py>=3.6.0",
        "pyqtgraph>=0.12.1",
        # PyQt5 should be installed separately
    ],
)
