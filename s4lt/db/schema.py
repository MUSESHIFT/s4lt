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
    category TEXT
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
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a database connection with recommended settings."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    """Initialize database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
