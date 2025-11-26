"""
ARpest application entry point.

This module initializes and runs the main PyQt5 application.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from arpest.ui.main_window import MainWindow
from arpest.utils.config import Config


class ARpestApp:
    """Main ARpest application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("ARpest")
        self.app.setOrganizationName("ARpest")
        
        # Load configuration
        self.config = Config()
        
        # Create main window
        self.window = MainWindow(self.config)
        
    def run(self) -> int:
        """
        Run the application.
        
        Returns:
            Exit code (0 for success)
        """
        self.window.show()
        return self.app.exec_()


def main() -> int:
    """
    Main entry point for ARpest application.
    
    Returns:
        Exit code (0 for success)
    """
    app = ARpestApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
