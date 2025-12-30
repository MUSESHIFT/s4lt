"""Comprehensive logging system for S4LT."""

import atexit
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Global log file path for access by error handlers
_log_file: Optional[Path] = None


def get_log_dir() -> Path:
    """Get the log directory path."""
    log_dir = Path.home() / ".local" / "share" / "s4lt" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file() -> Optional[Path]:
    """Get the current log file path."""
    return _log_file


def setup_logging(debug: bool = False) -> Path:
    """
    Set up comprehensive logging to file and console.

    Args:
        debug: If True, enable debug level logging to console

    Returns:
        Path to the log file
    """
    global _log_file

    log_dir = get_log_dir()
    _log_file = log_dir / f"s4lt-{datetime.now().strftime('%Y-%m-%d')}.log"

    # Clear existing handlers
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    # File handler - detailed with line numbers
    file_handler = logging.FileHandler(_log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    ))
    root.addHandler(file_handler)

    # Console handler - info only (or debug if requested)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    root.addHandler(console_handler)

    # Set up global exception handler
    sys.excepthook = _handle_exception

    logging.info(f"S4LT logging initialized. Log file: {_log_file}")

    return _log_file


def _handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler that logs uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupts
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )


def setup_cleanup_handlers(cleanup_func):
    """
    Set up handlers to ensure cleanup on crash/exit.

    Args:
        cleanup_func: Function to call on cleanup
    """
    # Register atexit handler
    atexit.register(cleanup_func)

    # Register signal handlers
    def signal_handler(sig, frame):
        logging.info(f"Received signal {sig}, cleaning up...")
        cleanup_func()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # SIGHUP for terminal hangup
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)


def get_recent_logs(lines: int = 100) -> list[str]:
    """
    Get recent log entries.

    Args:
        lines: Number of lines to return

    Returns:
        List of recent log lines
    """
    if not _log_file or not _log_file.exists():
        return []

    try:
        with open(_log_file, 'r') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except Exception as e:
        logging.warning(f"Failed to read log file: {e}")
        return []


def get_system_info() -> dict:
    """Get system information for debugging."""
    import platform

    info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "s4lt_version": "unknown",
        "log_file": str(_log_file) if _log_file else None,
        "log_dir": str(get_log_dir()),
    }

    # Get S4LT version
    try:
        from s4lt import __version__
        info["s4lt_version"] = __version__
    except ImportError:
        pass

    # Get Qt version if available
    try:
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        info["qt_version"] = QT_VERSION_STR
        info["pyqt_version"] = PYQT_VERSION_STR
    except ImportError:
        info["qt_version"] = "not installed"
        info["pyqt_version"] = "not installed"

    # Check for frozen (PyInstaller) mode
    info["frozen"] = getattr(sys, 'frozen', False)
    if info["frozen"]:
        info["meipass"] = getattr(sys, '_MEIPASS', None)

    return info
