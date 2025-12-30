"""Desktop application with embedded webview."""

import logging
import sys
import threading
import socket
import time
from pathlib import Path
from typing import Optional

import webview
import uvicorn

from s4lt.web import create_app


logger = logging.getLogger(__name__)


def get_asset_path(filename: str) -> Optional[Path]:
    """Get path to an asset file, works in both dev and frozen (PyInstaller) mode."""
    # For PyInstaller frozen apps
    if getattr(sys, 'frozen', False):
        bundle_dir = Path(sys._MEIPASS)
        asset_path = bundle_dir / "assets" / filename
        if asset_path.exists():
            return asset_path
        asset_path = bundle_dir / filename
        if asset_path.exists():
            return asset_path

    # Development mode - try relative to package
    locations = [
        Path(__file__).parent.parent.parent / "assets" / filename,
        Path(__file__).parent.parent / "assets" / filename,
        Path("/usr/share/icons") / filename,
        Path.home() / ".local/share/icons" / filename,
    ]

    for path in locations:
        if path.exists():
            return path
    return None


class Server:
    """Uvicorn server running in a background thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8040):
        self.host = host
        self.port = port
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the server in a background thread."""
        config = uvicorn.Config(
            app=create_app(),
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)

        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()

        # Wait for server to be ready
        self._wait_for_ready()

    def _wait_for_ready(self, timeout: float = 10.0) -> None:
        """Wait until server is accepting connections."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection((self.host, self.port), timeout=0.5):
                    return
            except (socket.error, ConnectionRefusedError):
                time.sleep(0.1)
        raise TimeoutError("Server failed to start")

    def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.should_exit = True

    def restart(self) -> None:
        """Restart the server."""
        self.stop()
        time.sleep(0.5)
        self.start()

    @property
    def url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"


class DesktopApp:
    """Main desktop application."""

    def __init__(self):
        self.server = Server()
        self.window: Optional[webview.Window] = None
        self._on_close_callback: Optional[callable] = None
        self._window_shown = False

    def set_on_close_callback(self, callback: callable) -> None:
        """Set callback for when window is closed (minimize to tray)."""
        self._on_close_callback = callback

    def start(self) -> None:
        """Start the desktop application."""
        # Start the backend server
        logger.info("Starting backend server...")
        self.server.start()
        logger.info(f"Server started at {self.server.url}")

        # Create the webview window
        self.window = webview.create_window(
            title="S4LT - Sims 4 Linux Toolkit",
            url=self.server.url,
            width=1200,
            height=800,
            resizable=True,
            min_size=(800, 600),
        )

        # Handle window close - minimize to tray instead of quitting
        def on_closing():
            if self._on_close_callback:
                self._on_close_callback()
                return False  # Prevent default close, we'll hide instead
            return True

        self.window.events.closing += on_closing

        # Ensure window is shown and focused when it loads
        def on_loaded():
            logger.info("Window loaded, ensuring visibility")
            self._ensure_window_visible()

        self.window.events.loaded += on_loaded

    def _ensure_window_visible(self) -> None:
        """Ensure the window is visible and focused."""
        if self.window and not self._window_shown:
            try:
                self.window.show()
                self.window.restore()
                self.window.on_top = True  # Temporarily bring to front
                time.sleep(0.1)
                self.window.on_top = False  # Allow normal stacking
                self._window_shown = True
                logger.info("Window shown successfully")
            except Exception as e:
                logger.warning(f"Failed to ensure window visibility: {e}")

    def run(self) -> None:
        """Run the webview event loop (blocking)."""
        # Start webview - window should open immediately
        logger.info("Starting webview event loop")
        webview.start()

    def show(self) -> None:
        """Show the window."""
        if self.window:
            try:
                self.window.show()
                self.window.restore()
                # Bring to front
                self.window.on_top = True
                time.sleep(0.05)
                self.window.on_top = False
                logger.info("Window shown from tray")
            except Exception as e:
                logger.warning(f"Error showing window: {e}")

    def hide(self) -> None:
        """Hide the window."""
        if self.window:
            try:
                self.window.hide()
                logger.info("Window hidden to tray")
            except Exception as e:
                logger.warning(f"Error hiding window: {e}")

    def quit(self) -> None:
        """Quit the application."""
        logger.info("Quitting desktop app")
        self.server.stop()
        if self.window:
            try:
                self.window.destroy()
            except Exception as e:
                logger.warning(f"Error destroying window: {e}")
