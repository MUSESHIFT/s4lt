"""Desktop application launcher - entry point for PyInstaller."""

import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from s4lt.logging import setup_logging, setup_cleanup_handlers, get_log_file
from s4lt.desktop.app import DesktopApp, Server
from s4lt.desktop.tray import TrayIcon


# Global references to prevent garbage collection
_app: Optional[DesktopApp] = None
_tray: Optional[TrayIcon] = None


def cleanup() -> None:
    """Clean up resources on exit."""
    global _app, _tray

    logging.info("Cleaning up resources...")

    # Stop tray icon first
    if _tray:
        try:
            _tray.stop()
            logging.info("Tray icon stopped")
        except Exception as e:
            logging.warning(f"Error stopping tray: {e}")
        _tray = None

    # Then stop the app
    if _app:
        try:
            _app.quit()
            logging.info("App stopped")
        except Exception as e:
            logging.warning(f"Error stopping app: {e}")
        _app = None


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

    log_file = get_log_file()
    if log_file and log_file.exists():
        try:
            subprocess.Popen(["xdg-open", str(log_file)])
        except FileNotFoundError:
            logging.warning("Could not open log file: xdg-open not found")


def on_settings() -> None:
    """Handle 'Settings' menu action."""
    logging.info("Opening settings...")
    if _app:
        _app.show()


def on_quit() -> None:
    """Handle 'Quit' menu action."""
    logging.info("Quitting S4LT...")
    cleanup()
    sys.exit(0)


def on_window_close() -> None:
    """Handle window close - minimize to tray."""
    logging.info("Minimizing to tray")
    if _app:
        _app.hide()


def run_headless(host: str = "127.0.0.1", port: int = 8040) -> None:
    """Run only the web server without GUI components."""
    server = Server(host=host, port=port)

    def signal_handler(sig, frame):
        print("\nShutting down...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    log_file = get_log_file()
    logging.info("Starting S4LT in headless mode")
    server.start()
    print(f"Server running at http://{host}:{port}")
    if log_file:
        print(f"Log file: {log_file}")
    print("Press Ctrl+C to stop")

    signal.pause()


def main() -> None:
    """Main entry point for the desktop application."""
    global _app, _tray

    parser = argparse.ArgumentParser(description="S4LT - Sims 4 Linux Toolkit")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run only the web server without GUI (for headless servers)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8040,
        help="Port to bind to (default: 8040)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Set up logging first
    log_file = setup_logging(debug=args.debug)

    if args.headless:
        run_headless(host=args.host, port=args.port)
        return

    logging.info("Starting S4LT Desktop Application")
    logging.info(f"Log file: {log_file}")

    # Set up cleanup handlers for crash recovery
    setup_cleanup_handlers(cleanup)

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
        cleanup()
        sys.exit(1)

    logging.info("S4LT shut down cleanly")


if __name__ == "__main__":
    main()
