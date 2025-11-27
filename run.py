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
from arpest.app import main

if __name__ == "__main__":
    sys.exit(main())

