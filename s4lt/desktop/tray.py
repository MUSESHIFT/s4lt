"""System tray functionality using pystray."""

import logging
import sys
import threading
from pathlib import Path
from typing import Optional, Callable

from PIL import Image
import pystray
from pystray import MenuItem as Item


logger = logging.getLogger(__name__)


def get_asset_path(filename: str) -> Optional[Path]:
    """Get path to an asset file, works in both dev and frozen (PyInstaller) mode."""
    # For PyInstaller frozen apps
    if getattr(sys, 'frozen', False):
        # Running as frozen executable
        bundle_dir = Path(sys._MEIPASS)
        asset_path = bundle_dir / "assets" / filename
        if asset_path.exists():
            return asset_path
        # Also try directly in bundle
        asset_path = bundle_dir / filename
        if asset_path.exists():
            return asset_path

    # Development mode - try relative to package
    locations = [
        Path(__file__).parent.parent.parent / "assets" / filename,
        Path(__file__).parent.parent / "assets" / filename,
        Path("/usr/share/icons/hicolor/32x32/apps") / filename,
        Path("/usr/share/icons") / filename,
        Path.home() / ".local/share/icons" / filename,
    ]

    for path in locations:
        if path.exists():
            logger.debug(f"Found asset at: {path}")
            return path

    logger.warning(f"Asset not found: {filename}")
    return None


class TrayIcon:
    """System tray icon with menu."""

    def __init__(
        self,
        on_open: Callable[[], None],
        on_restart: Callable[[], None],
        on_logs: Callable[[], None],
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        self.on_open = on_open
        self.on_restart = on_restart
        self.on_logs = on_logs
        self.on_settings = on_settings
        self.on_quit = on_quit

        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _load_icon(self) -> Image.Image:
        """Load the tray icon image."""
        # Try to find icon file
        for filename in ["s4lt-icon-32.png", "s4lt-icon.png", "s4lt.png"]:
            path = get_asset_path(filename)
            if path:
                try:
                    img = Image.open(path)
                    # Ensure RGBA for proper transparency
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    # Resize to 32x32 if needed
                    if img.size != (32, 32):
                        img = img.resize((32, 32), Image.Resampling.LANCZOS)
                    logger.info(f"Loaded tray icon from: {path}")
                    return img
                except Exception as e:
                    logger.warning(f"Failed to load icon from {path}: {e}")
                    continue

        # Fallback: create S4LT branded icon (green with white diamond)
        logger.info("Creating fallback tray icon")
        img = Image.new("RGBA", (32, 32), color=(0, 0, 0, 0))
        pixels = img.load()
        # Create a green diamond shape
        for y in range(32):
            for x in range(32):
                # Diamond shape
                if abs(x - 16) + abs(y - 16) < 14:
                    pixels[x, y] = (34, 197, 94, 255)  # Green
                elif abs(x - 16) + abs(y - 16) < 16:
                    pixels[x, y] = (22, 163, 74, 255)  # Darker green border
        return img

    def _create_menu(self) -> pystray.Menu:
        """Create the tray menu."""
        return pystray.Menu(
            Item("Open S4LT", lambda: self.on_open(), default=True),
            Item("Restart Server", lambda: self.on_restart()),
            pystray.Menu.SEPARATOR,
            Item("View Logs", lambda: self.on_logs()),
            Item("Settings", lambda: self.on_settings()),
            pystray.Menu.SEPARATOR,
            Item("Quit", lambda: self._quit()),
        )

    def _quit(self) -> None:
        """Handle quit from tray menu."""
        self.on_quit()
        if self._icon:
            self._icon.stop()

    def start(self) -> None:
        """Start the tray icon in a background thread."""
        icon_image = self._load_icon()
        menu = self._create_menu()

        self._icon = pystray.Icon(
            name="s4lt",
            icon=icon_image,
            title="S4LT - Sims 4 Linux Toolkit",
            menu=menu,
        )

        # Run in background thread
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the tray icon."""
        if self._icon:
            self._icon.stop()

    def update_icon(self, icon_path: Path) -> None:
        """Update the tray icon image."""
        if self._icon and icon_path.exists():
            self._icon.icon = Image.open(icon_path)
