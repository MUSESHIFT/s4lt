"""Desktop application launcher - entry point for PyInstaller."""

import logging
import sys
from pathlib import Path
from typing import Optional

from s4lt.desktop.app import DesktopApp
from s4lt.desktop.tray import TrayIcon


# Global references to prevent garbage collection
_app: Optional[DesktopApp] = None
_tray: Optional[TrayIcon] = None


def setup_logging() -> None:
    """Set up logging to file and console."""
    log_dir = Path.home() / ".local" / "share" / "s4lt" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "s4lt.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


def on_open() -> None:
    """Handle 'Open S4LT' menu action."""
    if _app:
        _app.show()


def on_restart() -> None:
    """Handle 'Restart Server' menu action."""
    if _app:
        logging.info("Restarting server...")
        _app.server.restart()
        logging.info("Server restarted")


def on_logs() -> None:
    """Handle 'View Logs' menu action."""
    import subprocess

    log_file = Path.home() / ".local" / "share" / "s4lt" / "logs" / "s4lt.log"
    if log_file.exists():
        # Try to open with default text editor
        try:
            subprocess.Popen(["xdg-open", str(log_file)])
        except FileNotFoundError:
            logging.warning("Could not open log file: xdg-open not found")


def on_settings() -> None:
    """Handle 'Settings' menu action."""
    # TODO: Implement settings dialog
    logging.info("Settings not yet implemented")
    if _app:
        _app.show()


def on_quit() -> None:
    """Handle 'Quit' menu action."""
    logging.info("Quitting S4LT...")
    if _app:
        _app.quit()


def on_window_close() -> None:
    """Handle window close - minimize to tray."""
    logging.info("Minimizing to tray")
    if _app:
        _app.hide()


def main() -> None:
    """Main entry point for the desktop application."""
    global _app, _tray

    setup_logging()
    logging.info("Starting S4LT Desktop Application")

    try:
        # Create the desktop app
        _app = DesktopApp()
        _app.set_on_close_callback(on_window_close)

        # Create the tray icon
        _tray = TrayIcon(
            on_open=on_open,
            on_restart=on_restart,
            on_logs=on_logs,
            on_settings=on_settings,
            on_quit=on_quit,
        )

        # Start tray icon first (runs in background thread)
        _tray.start()
        logging.info("Tray icon started")

        # Start and run the app (this blocks until quit)
        _app.start()
        logging.info("Desktop app started")
        _app.run()

    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        sys.exit(1)

    logging.info("S4LT shut down cleanly")


if __name__ == "__main__":
    main()
