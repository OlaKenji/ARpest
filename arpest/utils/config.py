"""Configuration management for ARpest."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """
    Application configuration.
    
    Attributes:
        window_size: Main window size (width, height)
        start_path: Initial directory for file dialogs
        default_colormap: Default matplotlib colormap
        figure_dpi: DPI for matplotlib figures
    """

    # Window settings
    window_size: tuple[int, int] = (1920, 1080)
    
    # File browser
    start_path: Path = Path.home()
    
    # Visualization defaults
    default_colormap: str = "arpest"
    figure_dpi: int = 100
    
    # Figure positions and sizes (can be adjusted)
    figure_width: float = 4.4
    figure_height: float = 4.3
    
    def __post_init__(self) -> None:
        """Ensure start_path is a Path object and load saved config."""
        if isinstance(self.start_path, str):
            self.start_path = Path(self.start_path)
            
        # Try to load saved configuration
        self.load()
            
    def update_start_path(self, filepath: Path) -> None:
        """
        Update start path based on a loaded file.
        
        Args:
            filepath: Path to file that was loaded
        """
        if filepath.is_file():
            self.start_path = filepath.parent
        else:
            self.start_path = filepath
            
        # Auto-save when path changes
        self.save()
    
    @staticmethod
    def get_config_path() -> Path:
        """Get path to configuration file."""
        # Save in user's home directory
        config_dir = Path.home() / ".arpest"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.json"
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            config_path = self.get_config_path()
            
            # Convert to dict
            config_dict = {
                "window_size": list(self.window_size),
                "start_path": str(self.start_path),
                "default_colormap": self.default_colormap,
                "figure_dpi": self.figure_dpi,
                "figure_width": self.figure_width,
                "figure_height": self.figure_height,
            }
            
            # Save as JSON
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
    
    def load(self) -> None:
        """Load configuration from file."""
        try:
            config_path = self.get_config_path()
            
            if not config_path.exists():
                return
                
            # Load from JSON
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            
            # Update attributes
            if "window_size" in config_dict:
                self.window_size = tuple(config_dict["window_size"])
            if "start_path" in config_dict:
                self.start_path = Path(config_dict["start_path"])
            if "default_colormap" in config_dict:
                self.default_colormap = config_dict["default_colormap"]
            if "figure_dpi" in config_dict:
                self.figure_dpi = config_dict["figure_dpi"]
            if "figure_width" in config_dict:
                self.figure_width = config_dict["figure_width"]
            if "figure_height" in config_dict:
                self.figure_height = config_dict["figure_height"]
                
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
