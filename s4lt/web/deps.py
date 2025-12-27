"""Dependency injection for web routes."""

import sqlite3
from pathlib import Path
from typing import Generator

from s4lt.config.settings import get_settings, DATA_DIR, DB_PATH
from s4lt.db.schema import init_db


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection dependency."""
    init_db(DB_PATH)
    # Use check_same_thread=False for async FastAPI routes
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_mods_path() -> Path | None:
    """Get mods path from settings."""
    settings = get_settings()
    return settings.mods_path


def get_tray_path() -> Path | None:
    """Get tray path from settings."""
    settings = get_settings()
    return settings.tray_path
