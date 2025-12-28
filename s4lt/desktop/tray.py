"""System tray functionality using pystray."""

import threading
from pathlib import Path
from typing import Optional, Callable

from PIL import Image
import pystray
from pystray import MenuItem as Item


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
        # Try multiple locations for the icon
        locations = [
            Path(__file__).parent.parent.parent / "assets" / "s4lt-icon-32.png",
            Path(__file__).parent.parent.parent / "assets" / "s4lt-icon.png",
            Path("/usr/share/icons/hicolor/32x32/apps/s4lt.png"),
            Path.home() / ".local/share/icons/s4lt.png",
        ]

        for path in locations:
            if path.exists():
                return Image.open(path)

        # Fallback: create a simple green square
        img = Image.new("RGB", (32, 32), color=(34, 197, 94))
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
