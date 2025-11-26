#!/usr/bin/env python3
"""
Launcher script for ARpest.

This can be run from anywhere: python run.py
"""

import sys
from pathlib import Path

# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent.resolve()

# Add to path if not already there
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Now import
try:
    from arpest.app import main
except ImportError as e:
    print(f"Error importing ARpest: {e}")
    print(f"Script directory: {SCRIPT_DIR}")
    print(f"Python path: {sys.path}")
    print("\nMake sure you have installed dependencies:")
    print("  pip install PyQt5 numpy matplotlib scipy h5py")
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())

