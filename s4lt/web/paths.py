"""Path utilities for PyInstaller compatibility."""

import sys
from pathlib import Path


def get_web_root() -> Path:
    """Get the web module root directory, works in both dev and frozen mode."""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)
        return bundle_dir / "s4lt" / "web"
    else:
        # Running in development
        return Path(__file__).parent


def get_static_dir() -> Path:
    """Get the static files directory."""
    return get_web_root() / "static"


def get_templates_dir() -> Path:
    """Get the templates directory."""
    return get_web_root() / "templates"
