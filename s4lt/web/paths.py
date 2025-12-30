"""Path utilities for PyInstaller compatibility."""

import os
import sys
from pathlib import Path


def get_web_root() -> Path:
    """Get the web module root directory, works in both dev and frozen mode."""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)

        # Try primary location (PyInstaller 5.x+ with COLLECT)
        primary = bundle_dir / "s4lt" / "web"
        if primary.exists():
            return primary

        # Fallback: check relative to executable for one-folder builds
        exe_dir = Path(sys.executable).parent
        fallback_paths = [
            exe_dir / "_internal" / "s4lt" / "web",
            exe_dir / "s4lt" / "web",
            bundle_dir.parent / "s4lt" / "web",
        ]

        for path in fallback_paths:
            if path.exists():
                return path

        # Last resort: search for static directory
        for search_root in [bundle_dir, exe_dir, bundle_dir.parent]:
            for root, dirs, files in os.walk(search_root):
                if "static" in dirs and "templates" in dirs:
                    candidate = Path(root)
                    if (candidate / "static").exists() and (candidate / "templates").exists():
                        return candidate

        # Return primary even if not found (will error with useful path info)
        return primary
    else:
        # Running in development
        return Path(__file__).parent


def get_static_dir() -> Path:
    """Get the static files directory."""
    return get_web_root() / "static"


def get_templates_dir() -> Path:
    """Get the templates directory."""
    return get_web_root() / "templates"
