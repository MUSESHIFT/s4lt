"""Database schema and initialization."""

import sqlite3
from pathlib import Path

SCHEMA = """
-- Mod packages
CREATE TABLE IF NOT EXISTS mods (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    hash TEXT NOT NULL,
    resource_count INTEGER,
    scan_time REAL,
    broken INTEGER DEFAULT 0,
    error_message TEXT,
    category TEXT,
    subcategory TEXT,
    thumbnail_path TEXT,
    enabled INTEGER DEFAULT 1,
    created_at REAL,
    modified_at REAL
);

-- Resources inside packages
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    mod_id INTEGER NOT NULL REFERENCES mods(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    instance_id INTEGER NOT NULL,
    type_name TEXT,
    name TEXT,
    compressed_size INTEGER,
    uncompressed_size INTEGER
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_resources_tgi ON resources(type_id, group_id, instance_id);
CREATE INDEX IF NOT EXISTS idx_resources_mod ON resources(mod_id);
CREATE INDEX IF NOT EXISTS idx_mods_hash ON mods(hash);
CREATE INDEX IF NOT EXISTS idx_mods_path ON mods(path);
CREATE INDEX IF NOT EXISTS idx_mods_category ON mods(category);
CREATE INDEX IF NOT EXISTS idx_mods_enabled ON mods(enabled);

-- Config storage
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Profiles for mod configurations
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at REAL NOT NULL,
    is_auto INTEGER DEFAULT 0
);

-- Mods in each profile
CREATE TABLE IF NOT EXISTS profile_mods (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    mod_path TEXT NOT NULL,
    enabled INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_profile_mods_profile ON profile_mods(profile_id);

-- Detected conflicts
CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    resource_type INTEGER,
    resource_type_name TEXT,
    instance_id INTEGER,
    group_id INTEGER,
    packages TEXT NOT NULL,
    description TEXT,
    resolved INTEGER DEFAULT 0,
    resolution TEXT,
    created_at REAL
);

CREATE INDEX IF NOT EXISTS idx_conflicts_resolved ON conflicts(resolved);
CREATE INDEX IF NOT EXISTS idx_conflicts_severity ON conflicts(severity);

-- Tray items (saved Sims, lots, rooms)
CREATE TABLE IF NOT EXISTS tray_items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    thumbnail_path TEXT,
    cc_references TEXT,
    missing_cc_count INTEGER DEFAULT 0,
    last_checked REAL,
    created_at REAL
);

CREATE INDEX IF NOT EXISTS idx_tray_items_type ON tray_items(type);
CREATE INDEX IF NOT EXISTS idx_tray_items_missing ON tray_items(missing_cc_count);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a database connection with recommended settings."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Get column names for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply schema migrations for existing databases."""
    # Migration: Add new columns to mods table
    mods_columns = _get_table_columns(conn, "mods")
    migrations = [
        ("mods", "category", "TEXT"),
        ("mods", "subcategory", "TEXT"),
        ("mods", "thumbnail_path", "TEXT"),
        ("mods", "enabled", "INTEGER DEFAULT 1"),
    ]
    for table, column, col_type in migrations:
        if column not in mods_columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def init_db(db_path: Path) -> None:
    """Initialize database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)

    # Check if mods table exists (existing database)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='mods'"
    )
    table_exists = cursor.fetchone() is not None

    if table_exists:
        # Apply migrations first for existing databases
        _apply_migrations(conn)

    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
