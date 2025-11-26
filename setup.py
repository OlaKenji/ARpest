"""
Setup script for ARpest.

This file is needed for editable installs with older pip versions.
Modern pip (>=21.3) can use pyproject.toml alone.
"""

from setuptools import setup, find_packages

setup(
    name="arpest",
    version="2.0.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "scipy>=1.11.0",
        "h5py>=3.0.0",
        # PyQt5 or PyQt6 should be installed separately
    ],
)
