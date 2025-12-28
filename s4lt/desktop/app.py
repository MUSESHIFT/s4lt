"""Desktop application with embedded webview."""

import threading
import socket
import time
from pathlib import Path
from typing import Optional

import webview
import uvicorn

from s4lt.web import create_app


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

    def set_on_close_callback(self, callback: callable) -> None:
        """Set callback for when window is closed (minimize to tray)."""
        self._on_close_callback = callback

    def start(self) -> None:
        """Start the desktop application."""
        # Start the backend server
        self.server.start()

        # Get icon path
        icon_path = self._get_icon_path()

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

    def run(self) -> None:
        """Run the webview event loop (blocking)."""
        webview.start()

    def show(self) -> None:
        """Show the window."""
        if self.window:
            self.window.show()
            self.window.restore()

    def hide(self) -> None:
        """Hide the window."""
        if self.window:
            self.window.hide()

    def quit(self) -> None:
        """Quit the application."""
        self.server.stop()
        if self.window:
            self.window.destroy()

    def _get_icon_path(self) -> Optional[Path]:
        """Get the path to the application icon."""
        # Try multiple locations
        locations = [
            Path(__file__).parent.parent.parent / "assets" / "s4lt-icon.png",
            Path("/usr/share/icons/s4lt.png"),
            Path.home() / ".local/share/icons/s4lt.png",
        ]
        for path in locations:
            if path.exists():
                return path
        return None
