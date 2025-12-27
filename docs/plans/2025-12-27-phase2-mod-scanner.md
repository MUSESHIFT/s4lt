# Phase 2: Mod Scanner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a mod scanner that indexes all .package files, detects conflicts and duplicates, with a rich CLI.

**Architecture:** Scanner crawls Mods folder, Indexer extracts resources using Phase 1 core, SQLite caches everything, CLI presents results with rich formatting.

**Tech Stack:** Python 3.11+, Click (CLI), Rich (formatting), SQLite, Phase 1 DBPF core

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml with new dependencies**

```toml
[project]
name = "s4lt"
version = "0.1.0"
description = "Sims 4 Linux Toolkit"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[project.scripts]
s4lt = "s4lt.cli.main:cli"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["s4lt*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

**Step 2: Install updated dependencies**

Run: `source .venv/bin/activate && pip install -e ".[dev]"`
Expected: Successfully installed click, rich

**Step 3: Verify imports work**

Run: `python -c "import click; import rich; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add -A
git commit -m "deps: add click and rich for CLI"
```

---

## Task 2: Database Schema

**Files:**
- Create: `s4lt/db/__init__.py`
- Create: `s4lt/db/schema.py`
- Create: `tests/db/__init__.py`
- Create: `tests/db/test_schema.py`

**Step 1: Create db package init**

```python
# s4lt/db/__init__.py
"""S4LT Database - SQLite storage for mod index."""

from s4lt.db.schema import init_db, get_connection

__all__ = ["init_db", "get_connection"]
```

**Step 2: Write the failing test**

```python
# tests/db/__init__.py
```

```python
# tests/db/test_schema.py
"""Tests for database schema."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection


def test_init_creates_tables():
    """init_db should create all required tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "mods" in tables
        assert "resources" in tables
        assert "config" in tables
        conn.close()


def test_mods_table_columns():
    """mods table should have required columns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute("PRAGMA table_info(mods)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "id" in columns
        assert "path" in columns
        assert "hash" in columns
        assert "mtime" in columns
        assert "size" in columns
        assert "broken" in columns
        conn.close()


def test_resources_table_columns():
    """resources table should have required columns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute("PRAGMA table_info(resources)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "mod_id" in columns
        assert "type_id" in columns
        assert "group_id" in columns
        assert "instance_id" in columns
        assert "name" in columns
        conn.close()
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/db/test_schema.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 4: Write the implementation**

```python
# s4lt/db/schema.py
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
    error_message TEXT
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
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/db/test_schema.py -v`
Expected: 3 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: database schema for mod index"
```

---

## Task 3: Database Operations

**Files:**
- Create: `s4lt/db/operations.py`
- Create: `tests/db/test_operations.py`

**Step 1: Write the failing test**

```python
# tests/db/test_operations.py
"""Tests for database operations."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import (
    upsert_mod,
    get_mod_by_path,
    delete_mod,
    insert_resource,
    get_all_mods,
    mark_broken,
)


def test_upsert_mod_insert():
    """upsert_mod should insert new mod."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(
            conn,
            path="Mods/Test/cool.package",
            filename="cool.package",
            size=1024,
            mtime=1234567890.0,
            hash="abc123",
            resource_count=5,
        )

        assert mod_id == 1
        conn.close()


def test_upsert_mod_update():
    """upsert_mod should update existing mod."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert
        mod_id1 = upsert_mod(conn, "test.package", "test.package", 100, 1.0, "hash1", 1)
        # Update
        mod_id2 = upsert_mod(conn, "test.package", "test.package", 200, 2.0, "hash2", 2)

        assert mod_id1 == mod_id2

        mod = get_mod_by_path(conn, "test.package")
        assert mod["size"] == 200
        assert mod["hash"] == "hash2"
        conn.close()


def test_get_mod_by_path():
    """get_mod_by_path should return mod or None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        assert get_mod_by_path(conn, "nonexistent.package") is None

        upsert_mod(conn, "exists.package", "exists.package", 100, 1.0, "hash", 1)
        mod = get_mod_by_path(conn, "exists.package")
        assert mod is not None
        assert mod["filename"] == "exists.package"
        conn.close()


def test_delete_mod():
    """delete_mod should remove mod and its resources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "test.package", "test.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x0333406C, 0, 123456, "Tuning", "test_tuning", 50, 100)

        delete_mod(conn, "test.package")

        assert get_mod_by_path(conn, "test.package") is None
        # Resources should cascade delete
        cursor = conn.execute("SELECT COUNT(*) FROM resources WHERE mod_id = ?", (mod_id,))
        assert cursor.fetchone()[0] == 0
        conn.close()


def test_insert_resource():
    """insert_resource should add resource to mod."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "test.package", "test.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x0333406C, 0, 123456, "Tuning", "my_tuning", 50, 100)

        cursor = conn.execute("SELECT * FROM resources WHERE mod_id = ?", (mod_id,))
        row = cursor.fetchone()
        assert row["type_id"] == 0x0333406C
        assert row["name"] == "my_tuning"
        conn.close()


def test_get_all_mods():
    """get_all_mods should return all mods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        upsert_mod(conn, "a.package", "a.package", 100, 1.0, "hash1", 1)
        upsert_mod(conn, "b.package", "b.package", 200, 2.0, "hash2", 2)

        mods = get_all_mods(conn)
        assert len(mods) == 2
        conn.close()


def test_mark_broken():
    """mark_broken should set broken flag and error message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "bad.package", "bad.package", 100, 1.0, "hash", 0)
        mark_broken(conn, "bad.package", "Invalid magic bytes")

        mod = get_mod_by_path(conn, "bad.package")
        assert mod["broken"] == 1
        assert mod["error_message"] == "Invalid magic bytes"
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_operations.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/db/operations.py
"""Database CRUD operations."""

import sqlite3
import time
from typing import Any


def upsert_mod(
    conn: sqlite3.Connection,
    path: str,
    filename: str,
    size: int,
    mtime: float,
    hash: str,
    resource_count: int,
) -> int:
    """Insert or update a mod record. Returns mod_id."""
    cursor = conn.execute(
        """
        INSERT INTO mods (path, filename, size, mtime, hash, resource_count, scan_time, broken)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(path) DO UPDATE SET
            filename = excluded.filename,
            size = excluded.size,
            mtime = excluded.mtime,
            hash = excluded.hash,
            resource_count = excluded.resource_count,
            scan_time = excluded.scan_time,
            broken = 0,
            error_message = NULL
        RETURNING id
        """,
        (path, filename, size, mtime, hash, resource_count, time.time()),
    )
    row = cursor.fetchone()
    conn.commit()
    return row[0]


def get_mod_by_path(conn: sqlite3.Connection, path: str) -> dict[str, Any] | None:
    """Get mod by path, or None if not found."""
    cursor = conn.execute("SELECT * FROM mods WHERE path = ?", (path,))
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_mod(conn: sqlite3.Connection, path: str) -> None:
    """Delete a mod by path (cascades to resources)."""
    conn.execute("DELETE FROM mods WHERE path = ?", (path,))
    conn.commit()


def insert_resource(
    conn: sqlite3.Connection,
    mod_id: int,
    type_id: int,
    group_id: int,
    instance_id: int,
    type_name: str | None,
    name: str | None,
    compressed_size: int,
    uncompressed_size: int,
) -> int:
    """Insert a resource record. Returns resource_id."""
    cursor = conn.execute(
        """
        INSERT INTO resources (mod_id, type_id, group_id, instance_id, type_name, name, compressed_size, uncompressed_size)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (mod_id, type_id, group_id, instance_id, type_name, name, compressed_size, uncompressed_size),
    )
    row = cursor.fetchone()
    conn.commit()
    return row[0]


def delete_resources_for_mod(conn: sqlite3.Connection, mod_id: int) -> None:
    """Delete all resources for a mod."""
    conn.execute("DELETE FROM resources WHERE mod_id = ?", (mod_id,))
    conn.commit()


def get_all_mods(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Get all mods."""
    cursor = conn.execute("SELECT * FROM mods")
    return [dict(row) for row in cursor.fetchall()]


def mark_broken(conn: sqlite3.Connection, path: str, error: str) -> None:
    """Mark a mod as broken with error message."""
    conn.execute(
        "UPDATE mods SET broken = 1, error_message = ? WHERE path = ?",
        (error, path),
    )
    conn.commit()
```

**Step 4: Update db __init__.py**

```python
# s4lt/db/__init__.py
"""S4LT Database - SQLite storage for mod index."""

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import (
    upsert_mod,
    get_mod_by_path,
    delete_mod,
    insert_resource,
    delete_resources_for_mod,
    get_all_mods,
    mark_broken,
)

__all__ = [
    "init_db",
    "get_connection",
    "upsert_mod",
    "get_mod_by_path",
    "delete_mod",
    "insert_resource",
    "delete_resources_for_mod",
    "get_all_mods",
    "mark_broken",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/db/test_operations.py -v`
Expected: 7 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: database CRUD operations"
```

---

## Task 4: Config Module

**Files:**
- Create: `s4lt/config/__init__.py`
- Create: `s4lt/config/settings.py`
- Create: `s4lt/config/paths.py`
- Create: `tests/config/__init__.py`
- Create: `tests/config/test_paths.py`

**Step 1: Write the failing test**

```python
# tests/config/__init__.py
```

```python
# tests/config/test_paths.py
"""Tests for path detection."""

import tempfile
from pathlib import Path

from s4lt.config.paths import find_mods_folder, SEARCH_PATHS


def test_search_paths_not_empty():
    """SEARCH_PATHS should have entries."""
    assert len(SEARCH_PATHS) > 0


def test_find_mods_folder_with_valid_path():
    """find_mods_folder should return path if Mods folder exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create fake Sims 4 structure
        mods_path = Path(tmpdir) / "Documents/Electronic Arts/The Sims 4/Mods"
        mods_path.mkdir(parents=True)

        # Create a test package
        (mods_path / "test.package").touch()

        result = find_mods_folder([tmpdir + "/Documents/Electronic Arts/The Sims 4"])
        assert result is not None
        assert result.name == "Mods"


def test_find_mods_folder_returns_none_if_not_found():
    """find_mods_folder should return None if no Mods folder found."""
    result = find_mods_folder(["/nonexistent/path/that/does/not/exist"])
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_paths.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# tests/config/__init__.py
```

```python
# s4lt/config/__init__.py
"""S4LT Configuration."""

from s4lt.config.paths import find_mods_folder, SEARCH_PATHS
from s4lt.config.settings import Settings, get_settings, save_settings

__all__ = [
    "find_mods_folder",
    "SEARCH_PATHS",
    "Settings",
    "get_settings",
    "save_settings",
]
```

```python
# s4lt/config/paths.py
"""Platform-specific path detection."""

import os
from pathlib import Path

# Common Sims 4 installation paths
SEARCH_PATHS = [
    # Steam Deck (NonSteamLauncher / Proton)
    "~/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    # Standard Steam Proton
    "~/.steam/steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    # Flatpak Steam
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    # Lutris / Wine default
    "~/.wine/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
    # Custom Wine prefix
    "~/Games/the-sims-4/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
]


def expand_path(path: str) -> Path:
    """Expand ~ and {user} in path."""
    expanded = os.path.expanduser(path)
    expanded = expanded.replace("{user}", os.environ.get("USER", "user"))
    return Path(expanded)


def find_mods_folder(search_paths: list[str] | None = None) -> Path | None:
    """Find the Mods folder by checking common locations.

    Args:
        search_paths: Paths to check (defaults to SEARCH_PATHS)

    Returns:
        Path to Mods folder if found, None otherwise
    """
    if search_paths is None:
        search_paths = SEARCH_PATHS

    for path_template in search_paths:
        base_path = expand_path(path_template)
        mods_path = base_path / "Mods"

        if mods_path.is_dir():
            return mods_path

    return None
```

```python
# s4lt/config/settings.py
"""User settings management."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "s4lt"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DATA_DIR = Path.home() / ".local" / "share" / "s4lt"
DB_PATH = DATA_DIR / "s4lt.db"


@dataclass
class Settings:
    """User settings."""

    mods_path: Path | None = None
    include_subfolders: bool = True
    ignore_patterns: list[str] = field(
        default_factory=lambda: ["__MACOSX", ".DS_Store", "*.disabled"]
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for saving."""
        return {
            "paths": {
                "mods": str(self.mods_path) if self.mods_path else None,
            },
            "scan": {
                "include_subfolders": self.include_subfolders,
                "ignore_patterns": self.ignore_patterns,
            },
        }


def get_settings() -> Settings:
    """Load settings from config file."""
    if not CONFIG_FILE.exists():
        return Settings()

    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

        mods_path = None
        if paths := data.get("paths", {}).get("mods"):
            mods_path = Path(paths)

        scan = data.get("scan", {})

        return Settings(
            mods_path=mods_path,
            include_subfolders=scan.get("include_subfolders", True),
            ignore_patterns=scan.get("ignore_patterns", Settings().ignore_patterns),
        )
    except Exception:
        return Settings()


def save_settings(settings: Settings) -> None:
    """Save settings to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Build TOML manually (no tomllib write support)
    lines = []
    lines.append("[paths]")
    if settings.mods_path:
        lines.append(f'mods = "{settings.mods_path}"')
    lines.append("")
    lines.append("[scan]")
    lines.append(f"include_subfolders = {'true' if settings.include_subfolders else 'false'}")
    patterns = ", ".join(f'"{p}"' for p in settings.ignore_patterns)
    lines.append(f"ignore_patterns = [{patterns}]")

    CONFIG_FILE.write_text("\n".join(lines) + "\n")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_paths.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: config module with path detection"
```

---

## Task 5: Scanner Module

**Files:**
- Create: `s4lt/mods/__init__.py`
- Create: `s4lt/mods/scanner.py`
- Create: `tests/mods/__init__.py`
- Create: `tests/mods/test_scanner.py`

**Step 1: Write the failing test**

```python
# tests/mods/__init__.py
```

```python
# tests/mods/test_scanner.py
"""Tests for mod scanner."""

import tempfile
from pathlib import Path

from s4lt.mods.scanner import discover_packages, categorize_changes
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod


def test_discover_packages_finds_packages():
    """discover_packages should find all .package files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir)

        # Create test packages
        (mods_path / "test1.package").touch()
        (mods_path / "test2.package").touch()
        (mods_path / "subdir").mkdir()
        (mods_path / "subdir" / "test3.package").touch()

        packages = discover_packages(mods_path)

        assert len(packages) == 3


def test_discover_packages_ignores_patterns():
    """discover_packages should ignore specified patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir)

        (mods_path / "good.package").touch()
        (mods_path / "__MACOSX").mkdir()
        (mods_path / "__MACOSX" / "bad.package").touch()

        packages = discover_packages(mods_path, ignore_patterns=["__MACOSX"])

        assert len(packages) == 1
        assert packages[0].name == "good.package"


def test_categorize_changes_new_files():
    """categorize_changes should identify new files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        pkg = mods_path / "new.package"
        pkg.write_bytes(b"DBPF" + b"\x00" * 92)

        disk_files = {pkg}
        new, modified, deleted = categorize_changes(conn, mods_path, disk_files)

        assert len(new) == 1
        assert len(modified) == 0
        assert len(deleted) == 0
        conn.close()


def test_categorize_changes_deleted_files():
    """categorize_changes should identify deleted files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        # Add mod to DB but not on disk
        upsert_mod(conn, "deleted.package", "deleted.package", 100, 1.0, "hash", 1)

        disk_files = set()
        new, modified, deleted = categorize_changes(conn, mods_path, disk_files)

        assert len(new) == 0
        assert len(modified) == 0
        assert len(deleted) == 1
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/mods/test_scanner.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/mods/__init__.py
"""S4LT Mod Scanner."""

from s4lt.mods.scanner import discover_packages, categorize_changes

__all__ = ["discover_packages", "categorize_changes"]
```

```python
# s4lt/mods/scanner.py
"""Mod folder scanner."""

import fnmatch
import sqlite3
from pathlib import Path

from s4lt.db.operations import get_all_mods


def discover_packages(
    mods_path: Path,
    include_subfolders: bool = True,
    ignore_patterns: list[str] | None = None,
) -> list[Path]:
    """Discover all .package files in the Mods folder.

    Args:
        mods_path: Path to the Mods folder
        include_subfolders: Whether to search subdirectories
        ignore_patterns: Folder/file patterns to ignore

    Returns:
        List of paths to .package files
    """
    if ignore_patterns is None:
        ignore_patterns = ["__MACOSX", ".DS_Store"]

    if include_subfolders:
        all_packages = list(mods_path.rglob("*.package"))
    else:
        all_packages = list(mods_path.glob("*.package"))

    # Filter out ignored patterns
    def should_include(path: Path) -> bool:
        for pattern in ignore_patterns:
            # Check if any parent folder matches
            for parent in path.parents:
                if fnmatch.fnmatch(parent.name, pattern):
                    return False
            # Check filename
            if fnmatch.fnmatch(path.name, pattern):
                return False
        return True

    return [p for p in all_packages if should_include(p)]


def categorize_changes(
    conn: sqlite3.Connection,
    mods_path: Path,
    disk_files: set[Path],
) -> tuple[set[Path], set[Path], set[str]]:
    """Categorize files into new, modified, and deleted.

    Args:
        conn: Database connection
        mods_path: Base Mods folder path
        disk_files: Set of .package files found on disk

    Returns:
        Tuple of (new_files, modified_files, deleted_paths)
    """
    # Get all mods from DB
    db_mods = {m["path"]: m for m in get_all_mods(conn)}
    db_paths = set(db_mods.keys())

    # Convert disk files to relative paths
    disk_relative = {}
    for path in disk_files:
        try:
            rel = str(path.relative_to(mods_path))
            disk_relative[rel] = path
        except ValueError:
            # Not relative to mods_path, use absolute
            disk_relative[str(path)] = path

    disk_path_set = set(disk_relative.keys())

    # Categorize
    new_paths = disk_path_set - db_paths
    deleted_paths = db_paths - disk_path_set
    existing_paths = disk_path_set & db_paths

    new_files = {disk_relative[p] for p in new_paths}
    deleted = deleted_paths

    # Check existing for modifications
    modified_files = set()
    for rel_path in existing_paths:
        disk_path = disk_relative[rel_path]
        db_record = db_mods[rel_path]

        stat = disk_path.stat()
        if stat.st_mtime != db_record["mtime"] or stat.st_size != db_record["size"]:
            modified_files.add(disk_path)

    return new_files, modified_files, deleted
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/mods/test_scanner.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: mod folder scanner with change detection"
```

---

## Task 6: Indexer Module

**Files:**
- Create: `s4lt/mods/indexer.py`
- Create: `tests/mods/test_indexer.py`

**Step 1: Write the failing test**

```python
# tests/mods/test_indexer.py
"""Tests for mod indexer."""

import struct
import tempfile
import hashlib
from pathlib import Path

from s4lt.mods.indexer import index_package, compute_hash, extract_tuning_name
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import get_mod_by_path


def create_test_package(resources: list[tuple[int, bytes]] = None) -> bytes:
    """Create a minimal valid DBPF package."""
    if resources is None:
        resources = []

    resource_data = b""
    entries = []

    for type_id, data in resources:
        entries.append({
            "type_id": type_id,
            "group_id": 0,
            "instance_hi": 0,
            "instance_lo": len(entries),
            "offset": 0,
            "file_size": len(data),
            "mem_size": len(data),
            "compressed": 0x0000,
        })
        resource_data += data

    index_size = 4 + (32 * len(entries))
    resource_start = 96
    index_start = resource_start + len(resource_data)

    offset = resource_start
    for entry in entries:
        entry["offset"] = offset
        offset += entry["file_size"]

    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<I", header, 8, 1)
    struct.pack_into("<I", header, 36, len(entries))
    struct.pack_into("<I", header, 44, index_size)
    struct.pack_into("<I", header, 64, index_start)

    index = bytearray()
    index.extend(struct.pack("<I", 0))

    for entry in entries:
        index.extend(struct.pack("<I", entry["type_id"]))
        index.extend(struct.pack("<I", entry["group_id"]))
        index.extend(struct.pack("<I", entry["instance_hi"]))
        index.extend(struct.pack("<I", entry["instance_lo"]))
        index.extend(struct.pack("<I", entry["offset"]))
        index.extend(struct.pack("<I", entry["file_size"]))
        index.extend(struct.pack("<I", entry["mem_size"]))
        index.extend(struct.pack("<HH", entry["compressed"], 0))

    return bytes(header) + resource_data + bytes(index)


def test_compute_hash():
    """compute_hash should return SHA256."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        path = Path(f.name)

    try:
        result = compute_hash(path)
        expected = hashlib.sha256(b"test content").hexdigest()
        assert result == expected
    finally:
        path.unlink()


def test_extract_tuning_name_from_n_attribute():
    """extract_tuning_name should get n attribute."""
    xml = b'<?xml version="1.0"?>\n<I n="coolhair_CASPart" c="CASPart"></I>'
    result = extract_tuning_name(xml)
    assert result == "coolhair_CASPart"


def test_extract_tuning_name_returns_none_for_non_xml():
    """extract_tuning_name should return None for non-XML."""
    result = extract_tuning_name(b"not xml data")
    assert result is None


def test_index_package_adds_to_db():
    """index_package should add mod and resources to DB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        pkg_data = create_test_package([
            (0x0333406C, b'<?xml version="1.0"?>\n<I n="test_tuning"></I>'),
            (0x034AEECB, b"caspart data"),
        ])
        pkg_path = mods_path / "test.package"
        pkg_path.write_bytes(pkg_data)

        index_package(conn, mods_path, pkg_path)

        mod = get_mod_by_path(conn, "test.package")
        assert mod is not None
        assert mod["resource_count"] == 2

        cursor = conn.execute("SELECT * FROM resources WHERE mod_id = ?", (mod["id"],))
        resources = cursor.fetchall()
        assert len(resources) == 2
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/mods/test_indexer.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/mods/indexer.py
"""Package indexer - extracts resources and metadata."""

import hashlib
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from s4lt.core import Package, DBPFError
from s4lt.db.operations import (
    upsert_mod,
    insert_resource,
    delete_resources_for_mod,
    mark_broken,
)


def compute_hash(path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_tuning_name(data: bytes) -> str | None:
    """Extract human-readable name from tuning XML.

    Args:
        data: Raw resource data

    Returns:
        Name if found, None otherwise
    """
    if not data.startswith(b"<?xml"):
        return None

    try:
        root = ET.fromstring(data)

        # Try n attribute on root (most common)
        if name := root.get("n"):
            return name

        # Try display_name or name element
        for elem in root.iter("T"):
            attr_name = elem.get("n")
            if attr_name in ("display_name", "name") and elem.text:
                return elem.text

        # Fallback to s attribute
        return root.get("s")

    except ET.ParseError:
        return None


def index_package(
    conn: sqlite3.Connection,
    mods_path: Path,
    package_path: Path,
) -> int | None:
    """Index a package file into the database.

    Args:
        conn: Database connection
        mods_path: Base Mods folder path
        package_path: Path to the .package file

    Returns:
        mod_id if successful, None if failed
    """
    try:
        rel_path = str(package_path.relative_to(mods_path))
    except ValueError:
        rel_path = str(package_path)

    stat = package_path.stat()
    file_hash = compute_hash(package_path)

    try:
        with Package.open(package_path) as pkg:
            # Upsert mod record
            mod_id = upsert_mod(
                conn,
                path=rel_path,
                filename=package_path.name,
                size=stat.st_size,
                mtime=stat.st_mtime,
                hash=file_hash,
                resource_count=len(pkg.resources),
            )

            # Clear old resources and add new ones
            delete_resources_for_mod(conn, mod_id)

            for resource in pkg.resources:
                # Try to extract name for tuning resources
                name = None
                if resource.type_name == "Tuning":
                    try:
                        data = resource.extract()
                        name = extract_tuning_name(data)
                    except Exception:
                        pass

                insert_resource(
                    conn,
                    mod_id=mod_id,
                    type_id=resource.type_id,
                    group_id=resource.group_id,
                    instance_id=resource.instance_id,
                    type_name=resource.type_name,
                    name=name,
                    compressed_size=resource.compressed_size,
                    uncompressed_size=resource.uncompressed_size,
                )

            return mod_id

    except DBPFError as e:
        # Mark as broken but still record the file
        mod_id = upsert_mod(
            conn,
            path=rel_path,
            filename=package_path.name,
            size=stat.st_size,
            mtime=stat.st_mtime,
            hash=file_hash,
            resource_count=0,
        )
        mark_broken(conn, rel_path, str(e))
        return None

    except Exception as e:
        # Unexpected error
        mod_id = upsert_mod(
            conn,
            path=rel_path,
            filename=package_path.name,
            size=stat.st_size,
            mtime=stat.st_mtime,
            hash=file_hash,
            resource_count=0,
        )
        mark_broken(conn, rel_path, f"Unexpected error: {e}")
        return None
```

**Step 4: Update mods __init__.py**

```python
# s4lt/mods/__init__.py
"""S4LT Mod Scanner."""

from s4lt.mods.scanner import discover_packages, categorize_changes
from s4lt.mods.indexer import index_package, compute_hash, extract_tuning_name

__all__ = [
    "discover_packages",
    "categorize_changes",
    "index_package",
    "compute_hash",
    "extract_tuning_name",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/mods/test_indexer.py -v`
Expected: 4 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: package indexer with name extraction"
```

---

## Task 7: Conflict Detection

**Files:**
- Create: `s4lt/mods/conflicts.py`
- Create: `tests/mods/test_conflicts.py`

**Step 1: Write the failing test**

```python
# tests/mods/test_conflicts.py
"""Tests for conflict detection."""

import tempfile
from pathlib import Path

from s4lt.mods.conflicts import find_conflicts, ConflictCluster
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource


def test_find_conflicts_no_conflicts():
    """find_conflicts should return empty list if no conflicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Two mods with different resources
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)

        insert_resource(conn, mod1, 0x0333406C, 0, 1111, "Tuning", "tuning1", 50, 100)
        insert_resource(conn, mod2, 0x0333406C, 0, 2222, "Tuning", "tuning2", 50, 100)

        conflicts = find_conflicts(conn)
        assert len(conflicts) == 0
        conn.close()


def test_find_conflicts_detects_conflict():
    """find_conflicts should detect TGI collision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Two mods with same TGI
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)

        # Same TGI in both mods
        insert_resource(conn, mod1, 0x0333406C, 0, 9999, "Tuning", "shared", 50, 100)
        insert_resource(conn, mod2, 0x0333406C, 0, 9999, "Tuning", "shared", 50, 100)

        conflicts = find_conflicts(conn)
        assert len(conflicts) == 1
        assert len(conflicts[0].mods) == 2
        conn.close()


def test_find_conflicts_groups_into_clusters():
    """find_conflicts should group related mods into clusters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Three mods sharing resources
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)
        mod3 = upsert_mod(conn, "mod3.package", "mod3.package", 100, 1.0, "hash3", 1)

        # mod1 and mod2 share resource A
        insert_resource(conn, mod1, 0x0333406C, 0, 1000, "Tuning", "A", 50, 100)
        insert_resource(conn, mod2, 0x0333406C, 0, 1000, "Tuning", "A", 50, 100)

        # mod2 and mod3 share resource B
        insert_resource(conn, mod2, 0x0333406C, 0, 2000, "Tuning", "B", 50, 100)
        insert_resource(conn, mod3, 0x0333406C, 0, 2000, "Tuning", "B", 50, 100)

        conflicts = find_conflicts(conn)
        # Should be one cluster with all 3 mods
        assert len(conflicts) == 1
        assert len(conflicts[0].mods) == 3
        conn.close()


def test_conflict_severity():
    """Conflicts should have correct severity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)

        # CASPart conflict = HIGH severity
        insert_resource(conn, mod1, 0x034AEECB, 0, 9999, "CASPart", "cas", 50, 100)
        insert_resource(conn, mod2, 0x034AEECB, 0, 9999, "CASPart", "cas", 50, 100)

        conflicts = find_conflicts(conn)
        assert len(conflicts) == 1
        assert conflicts[0].severity == "high"
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/mods/test_conflicts.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/mods/conflicts.py
"""Conflict detection between mods."""

import sqlite3
from dataclasses import dataclass, field

# Resource types by severity
HIGH_SEVERITY_TYPES = {"CASPart", "Geometry", "DDS", "PNG", "DST"}
MEDIUM_SEVERITY_TYPES = {"Tuning", "SimData", "CombinedTuning"}
LOW_SEVERITY_TYPES = {"StringTable", "Thumbnail", "ThumbnailAlt"}


@dataclass
class ConflictCluster:
    """A cluster of mods that share conflicting resources."""

    mods: list[str] = field(default_factory=list)
    resources: list[tuple[int, int, int]] = field(default_factory=list)  # (type, group, instance)
    resource_types: set[str] = field(default_factory=set)
    severity: str = "low"


def determine_severity(resource_types: set[str]) -> str:
    """Determine conflict severity based on resource types."""
    if resource_types & HIGH_SEVERITY_TYPES:
        return "high"
    if resource_types & MEDIUM_SEVERITY_TYPES:
        return "medium"
    return "low"


def find_conflicts(conn: sqlite3.Connection) -> list[ConflictCluster]:
    """Find all conflict clusters.

    A conflict is when multiple mods contain resources with the same TGI.
    Conflicts are grouped into clusters using connected components.

    Args:
        conn: Database connection

    Returns:
        List of ConflictCluster objects
    """
    # Find all TGI collisions
    cursor = conn.execute("""
        SELECT
            r.type_id, r.group_id, r.instance_id, r.type_name,
            GROUP_CONCAT(m.path) as mod_paths
        FROM resources r
        JOIN mods m ON r.mod_id = m.id
        WHERE m.broken = 0
        GROUP BY r.type_id, r.group_id, r.instance_id
        HAVING COUNT(DISTINCT m.id) > 1
    """)

    # Build adjacency: mod -> set of mods it conflicts with
    adjacency: dict[str, set[str]] = {}
    # Track TGI info per mod pair
    mod_tgis: dict[str, list[tuple[int, int, int, str]]] = {}

    for row in cursor.fetchall():
        type_id, group_id, instance_id, type_name, mod_paths_str = row
        mod_paths = mod_paths_str.split(",")

        # Add edges between all conflicting mods
        for mod in mod_paths:
            if mod not in adjacency:
                adjacency[mod] = set()
            if mod not in mod_tgis:
                mod_tgis[mod] = []
            adjacency[mod].update(mod_paths)
            adjacency[mod].discard(mod)  # Remove self
            mod_tgis[mod].append((type_id, group_id, instance_id, type_name or "Unknown"))

    # Find connected components (clusters)
    visited = set()
    clusters = []

    def dfs(mod: str, cluster_mods: list[str]):
        if mod in visited:
            return
        visited.add(mod)
        cluster_mods.append(mod)
        for neighbor in adjacency.get(mod, []):
            dfs(neighbor, cluster_mods)

    for mod in adjacency:
        if mod not in visited:
            cluster_mods: list[str] = []
            dfs(mod, cluster_mods)

            if len(cluster_mods) > 1:
                # Collect all TGIs and types for this cluster
                all_tgis = set()
                all_types = set()
                for m in cluster_mods:
                    for tgi in mod_tgis.get(m, []):
                        all_tgis.add((tgi[0], tgi[1], tgi[2]))
                        all_types.add(tgi[3])

                cluster = ConflictCluster(
                    mods=sorted(cluster_mods),
                    resources=list(all_tgis),
                    resource_types=all_types,
                    severity=determine_severity(all_types),
                )
                clusters.append(cluster)

    # Sort by severity (high first)
    severity_order = {"high": 0, "medium": 1, "low": 2}
    clusters.sort(key=lambda c: (severity_order[c.severity], -len(c.mods)))

    return clusters
```

**Step 4: Update mods __init__.py**

```python
# s4lt/mods/__init__.py
"""S4LT Mod Scanner."""

from s4lt.mods.scanner import discover_packages, categorize_changes
from s4lt.mods.indexer import index_package, compute_hash, extract_tuning_name
from s4lt.mods.conflicts import find_conflicts, ConflictCluster

__all__ = [
    "discover_packages",
    "categorize_changes",
    "index_package",
    "compute_hash",
    "extract_tuning_name",
    "find_conflicts",
    "ConflictCluster",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/mods/test_conflicts.py -v`
Expected: 4 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: conflict detection with severity clustering"
```

---

## Task 8: Duplicate Detection

**Files:**
- Create: `s4lt/mods/duplicates.py`
- Create: `tests/mods/test_duplicates.py`

**Step 1: Write the failing test**

```python
# tests/mods/test_duplicates.py
"""Tests for duplicate detection."""

import tempfile
from pathlib import Path

from s4lt.mods.duplicates import find_duplicates, DuplicateGroup
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource


def test_find_duplicates_exact_hash():
    """find_duplicates should find exact hash matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Same hash
        upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "samehash", 1)
        upsert_mod(conn, "mod2.package", "mod2.package", 100, 2.0, "samehash", 1)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 1
        assert duplicates[0].match_type == "exact"
        assert len(duplicates[0].mods) == 2
        conn.close()


def test_find_duplicates_no_duplicates():
    """find_duplicates should return empty if no duplicates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        upsert_mod(conn, "mod2.package", "mod2.package", 100, 2.0, "hash2", 1)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 0
        conn.close()


def test_find_duplicates_content_match():
    """find_duplicates should find content matches (same TGIs)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Different hashes but same resources
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 2)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 200, 2.0, "hash2", 2)

        # Same resources in both
        insert_resource(conn, mod1, 0x0333406C, 0, 1111, "Tuning", "t1", 50, 100)
        insert_resource(conn, mod1, 0x034AEECB, 0, 2222, "CASPart", "c1", 50, 100)

        insert_resource(conn, mod2, 0x0333406C, 0, 1111, "Tuning", "t1", 50, 100)
        insert_resource(conn, mod2, 0x034AEECB, 0, 2222, "CASPart", "c1", 50, 100)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 1
        assert duplicates[0].match_type == "content"
        conn.close()


def test_duplicate_wasted_bytes():
    """DuplicateGroup should calculate wasted bytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # 3 copies of same file, 1000 bytes each
        upsert_mod(conn, "mod1.package", "mod1.package", 1000, 1.0, "samehash", 1)
        upsert_mod(conn, "mod2.package", "mod2.package", 1000, 2.0, "samehash", 1)
        upsert_mod(conn, "mod3.package", "mod3.package", 1000, 3.0, "samehash", 1)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 1
        # Wasted = total - one copy = 3000 - 1000 = 2000
        assert duplicates[0].wasted_bytes == 2000
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/mods/test_duplicates.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/mods/duplicates.py
"""Duplicate detection between mods."""

import sqlite3
from dataclasses import dataclass, field


@dataclass
class DuplicateGroup:
    """A group of duplicate mods."""

    mods: list[dict] = field(default_factory=list)  # List of mod records
    match_type: str = "exact"  # "exact" or "content"
    wasted_bytes: int = 0


def find_duplicates(conn: sqlite3.Connection) -> list[DuplicateGroup]:
    """Find all duplicate mods.

    Tier 1: Exact hash matches (byte-for-byte identical)
    Tier 2: Content matches (same resources inside)

    Args:
        conn: Database connection

    Returns:
        List of DuplicateGroup objects
    """
    groups = []

    # Tier 1: Exact hash duplicates
    cursor = conn.execute("""
        SELECT hash, GROUP_CONCAT(id) as mod_ids, SUM(size) as total_size, MIN(size) as min_size
        FROM mods
        WHERE broken = 0
        GROUP BY hash
        HAVING COUNT(*) > 1
    """)

    exact_duplicate_mod_ids = set()

    for row in cursor.fetchall():
        hash_val, mod_ids_str, total_size, min_size = row
        mod_ids = [int(x) for x in mod_ids_str.split(",")]
        exact_duplicate_mod_ids.update(mod_ids)

        # Get mod details
        placeholders = ",".join("?" * len(mod_ids))
        mods_cursor = conn.execute(
            f"SELECT * FROM mods WHERE id IN ({placeholders}) ORDER BY mtime",
            mod_ids,
        )
        mods = [dict(r) for r in mods_cursor.fetchall()]

        wasted = total_size - min_size

        groups.append(DuplicateGroup(
            mods=mods,
            match_type="exact",
            wasted_bytes=wasted,
        ))

    # Tier 2: Content duplicates (same TGI fingerprint)
    # Skip mods already in exact duplicate groups
    cursor = conn.execute("""
        SELECT m.id, m.path, m.size,
            GROUP_CONCAT(r.type_id || '-' || r.group_id || '-' || r.instance_id ORDER BY r.type_id, r.group_id, r.instance_id) as fingerprint
        FROM mods m
        JOIN resources r ON m.id = r.mod_id
        WHERE m.broken = 0
        GROUP BY m.id
    """)

    # Group by fingerprint
    fingerprint_groups: dict[str, list[dict]] = {}
    for row in cursor.fetchall():
        mod_id, path, size, fingerprint = row
        if mod_id in exact_duplicate_mod_ids:
            continue
        if fingerprint not in fingerprint_groups:
            fingerprint_groups[fingerprint] = []
        fingerprint_groups[fingerprint].append({"id": mod_id, "path": path, "size": size})

    for fingerprint, mod_list in fingerprint_groups.items():
        if len(mod_list) > 1:
            # Get full mod details
            mod_ids = [m["id"] for m in mod_list]
            placeholders = ",".join("?" * len(mod_ids))
            mods_cursor = conn.execute(
                f"SELECT * FROM mods WHERE id IN ({placeholders}) ORDER BY mtime",
                mod_ids,
            )
            mods = [dict(r) for r in mods_cursor.fetchall()]

            total_size = sum(m["size"] for m in mods)
            min_size = min(m["size"] for m in mods)

            groups.append(DuplicateGroup(
                mods=mods,
                match_type="content",
                wasted_bytes=total_size - min_size,
            ))

    # Sort by wasted bytes (most waste first)
    groups.sort(key=lambda g: -g.wasted_bytes)

    return groups
```

**Step 4: Update mods __init__.py**

```python
# s4lt/mods/__init__.py
"""S4LT Mod Scanner."""

from s4lt.mods.scanner import discover_packages, categorize_changes
from s4lt.mods.indexer import index_package, compute_hash, extract_tuning_name
from s4lt.mods.conflicts import find_conflicts, ConflictCluster
from s4lt.mods.duplicates import find_duplicates, DuplicateGroup

__all__ = [
    "discover_packages",
    "categorize_changes",
    "index_package",
    "compute_hash",
    "extract_tuning_name",
    "find_conflicts",
    "ConflictCluster",
    "find_duplicates",
    "DuplicateGroup",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/mods/test_duplicates.py -v`
Expected: 4 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: duplicate detection (exact + content match)"
```

---

## Task 9: CLI Output Helpers

**Files:**
- Modify: `s4lt/cli/__init__.py`
- Create: `s4lt/cli/output.py`
- Create: `tests/cli/__init__.py`
- Create: `tests/cli/test_output.py`

**Step 1: Write the failing test**

```python
# tests/cli/__init__.py
```

```python
# tests/cli/test_output.py
"""Tests for CLI output helpers."""

from s4lt.cli.output import format_size, format_path


def test_format_size_bytes():
    """format_size should format bytes."""
    assert format_size(500) == "500 B"


def test_format_size_kb():
    """format_size should format kilobytes."""
    assert format_size(1536) == "1.5 KB"


def test_format_size_mb():
    """format_size should format megabytes."""
    assert format_size(1572864) == "1.5 MB"


def test_format_path_short():
    """format_path should return short paths unchanged."""
    assert format_path("Mods/test.package", 50) == "Mods/test.package"


def test_format_path_truncate():
    """format_path should truncate long paths."""
    long_path = "Mods/Very/Long/Path/To/Some/Deeply/Nested/Package.package"
    result = format_path(long_path, 30)
    assert len(result) <= 30
    assert "..." in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_output.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/cli/output.py
"""CLI output formatting helpers."""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

console = Console()


def format_size(bytes: int) -> str:
    """Format bytes as human-readable size."""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes / 1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes / (1024 * 1024 * 1024):.1f} GB"


def format_path(path: str, max_len: int = 60) -> str:
    """Format path, truncating if too long."""
    if len(path) <= max_len:
        return path

    # Keep filename, truncate middle
    parts = path.split("/")
    filename = parts[-1]

    if len(filename) >= max_len - 4:
        return "..." + filename[-(max_len - 3):]

    available = max_len - len(filename) - 4  # 4 for ".../""
    prefix = path[:available]
    return f"{prefix}.../{filename}"


def create_progress() -> Progress:
    """Create a Rich progress bar for scanning."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")
```

**Step 4: Update cli __init__.py**

```python
# s4lt/cli/__init__.py
"""S4LT Command Line Interface."""

from s4lt.cli.output import (
    console,
    format_size,
    format_path,
    create_progress,
    print_success,
    print_warning,
    print_error,
    print_info,
)

__all__ = [
    "console",
    "format_size",
    "format_path",
    "create_progress",
    "print_success",
    "print_warning",
    "print_error",
    "print_info",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/cli/test_output.py -v`
Expected: 5 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: CLI output helpers with Rich formatting"
```

---

## Task 10: CLI Main Entry Point

**Files:**
- Modify: `s4lt/cli/main.py`

**Step 1: Create main CLI app**

```python
# s4lt/cli/main.py
"""S4LT CLI main entry point."""

import click

from s4lt.cli.output import console


@click.group()
@click.version_option(package_name="s4lt")
def cli():
    """S4LT: Sims 4 Linux Toolkit.

    Native Linux tools for Sims 4 mod management.
    """
    pass


@cli.command()
@click.option("--full", is_flag=True, help="Force full rescan")
@click.option("--stats", is_flag=True, help="Show stats only, don't update")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def scan(full: bool, stats: bool, json_output: bool):
    """Scan and index the Mods folder."""
    from s4lt.cli.commands.scan import run_scan
    run_scan(full=full, stats_only=stats, json_output=json_output)


@cli.command()
@click.option("--high", is_flag=True, help="Show only high severity conflicts")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def conflicts(high: bool, json_output: bool):
    """Show mod conflicts."""
    from s4lt.cli.commands.conflicts import run_conflicts
    run_conflicts(high_only=high, json_output=json_output)


@cli.command()
@click.option("--exact", is_flag=True, help="Show only exact duplicates")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def duplicates(exact: bool, json_output: bool):
    """Find duplicate mods."""
    from s4lt.cli.commands.duplicates import run_duplicates
    run_duplicates(exact_only=exact, json_output=json_output)


@cli.command()
@click.argument("package")
def info(package: str):
    """Show package details."""
    from s4lt.cli.commands.info import run_info
    run_info(package)


if __name__ == "__main__":
    cli()
```

**Step 2: Verify CLI runs**

Run: `python -m s4lt.cli.main --help`
Expected: Shows help with commands

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: CLI main entry point with Click"
```

---

## Task 11: CLI Scan Command

**Files:**
- Create: `s4lt/cli/commands/__init__.py`
- Create: `s4lt/cli/commands/scan.py`

**Step 1: Write the scan command**

```python
# s4lt/cli/commands/__init__.py
"""CLI command implementations."""
```

```python
# s4lt/cli/commands/scan.py
"""Scan command implementation."""

import json
import sys
import time
from pathlib import Path

from s4lt.cli.output import (
    console,
    format_size,
    create_progress,
    print_success,
    print_error,
    print_info,
)
from s4lt.config import find_mods_folder, get_settings, save_settings, Settings
from s4lt.config.settings import DATA_DIR, DB_PATH
from s4lt.db import init_db, get_connection, delete_mod
from s4lt.mods import discover_packages, categorize_changes, index_package


def run_scan(full: bool = False, stats_only: bool = False, json_output: bool = False):
    """Run the scan command."""
    settings = get_settings()

    # First run: find or configure mods path
    if settings.mods_path is None:
        if json_output:
            print(json.dumps({"error": "Mods folder not configured. Run without --json first."}))
            sys.exit(1)

        console.print("\n[bold]First Run Setup[/bold]\n")

        mods_path = find_mods_folder()
        if mods_path:
            console.print(f"Found Mods folder: [cyan]{mods_path}[/cyan]")
            if click.confirm("Use this path?", default=True):
                settings.mods_path = mods_path
            else:
                path_str = click.prompt("Enter Mods folder path")
                settings.mods_path = Path(path_str)
        else:
            console.print("[yellow]Could not auto-detect Mods folder.[/yellow]")
            path_str = click.prompt("Enter Mods folder path")
            settings.mods_path = Path(path_str)

        if not settings.mods_path.is_dir():
            print_error(f"Path does not exist: {settings.mods_path}")
            sys.exit(1)

        save_settings(settings)
        console.print(f"[green]Saved configuration to ~/.config/s4lt/config.toml[/green]\n")

    mods_path = settings.mods_path

    # Initialize database
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)

    try:
        # Discover packages
        console.print(f"[bold]Scanning[/bold] {mods_path}\n") if not json_output else None

        disk_files = set(discover_packages(
            mods_path,
            include_subfolders=settings.include_subfolders,
            ignore_patterns=settings.ignore_patterns,
        ))

        if full:
            # Force full rescan - treat all as new
            new_files = disk_files
            modified_files = set()
            deleted_paths = set()
        else:
            new_files, modified_files, deleted_paths = categorize_changes(conn, mods_path, disk_files)

        total_on_disk = len(disk_files)
        to_process = new_files | modified_files

        if stats_only:
            if json_output:
                stats = {
                    "total": total_on_disk,
                    "new": len(new_files),
                    "modified": len(modified_files),
                    "deleted": len(deleted_paths),
                }
                print(json.dumps(stats))
            else:
                console.print(f"  Total packages: [bold]{total_on_disk}[/bold]")
                console.print(f"  New: {len(new_files)}")
                console.print(f"  Modified: {len(modified_files)}")
                console.print(f"  Deleted: {len(deleted_paths)}")
            return

        # Process changes
        start_time = time.time()

        # Delete removed mods
        for path in deleted_paths:
            delete_mod(conn, path)

        # Index new/modified mods
        broken_count = 0
        if to_process:
            with create_progress() as progress:
                task = progress.add_task("Indexing...", total=len(to_process))

                for pkg_path in to_process:
                    result = index_package(conn, mods_path, pkg_path)
                    if result is None:
                        broken_count += 1
                    progress.advance(task)

        elapsed = time.time() - start_time

        # Get final stats
        cursor = conn.execute("SELECT COUNT(*) FROM mods WHERE broken = 0")
        total_mods = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM resources")
        total_resources = cursor.fetchone()[0]

        if json_output:
            result = {
                "total_mods": total_mods,
                "total_resources": total_resources,
                "new": len(new_files),
                "modified": len(modified_files),
                "deleted": len(deleted_paths),
                "broken": broken_count,
                "time_seconds": round(elapsed, 2),
            }
            print(json.dumps(result))
        else:
            console.print()
            print_success("Scan complete")
            console.print(f"  Total: [bold]{total_mods}[/bold] mods ({total_resources:,} resources)")
            console.print(f"  New: {len(new_files)} | Updated: {len(modified_files)} | Removed: {len(deleted_paths)} | Broken: {broken_count}")
            console.print(f"  Time: {elapsed:.1f}s")

    finally:
        conn.close()


# Need click for prompt in first-run
import click
```

**Step 2: Test scan command**

Run: `python -m s4lt.cli.main scan --help`
Expected: Shows scan options

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: CLI scan command with progress bar"
```

---

## Task 12: CLI Conflicts Command

**Files:**
- Create: `s4lt/cli/commands/conflicts.py`

**Step 1: Write the conflicts command**

```python
# s4lt/cli/commands/conflicts.py
"""Conflicts command implementation."""

import json
import sys

from rich.tree import Tree

from s4lt.cli.output import console, print_info, print_warning
from s4lt.config.settings import DB_PATH
from s4lt.db import get_connection, init_db
from s4lt.mods.conflicts import find_conflicts


def run_conflicts(high_only: bool = False, json_output: bool = False):
    """Run the conflicts command."""
    if not DB_PATH.exists():
        if json_output:
            print(json.dumps({"error": "No scan data. Run 's4lt scan' first."}))
        else:
            print_warning("No scan data. Run 's4lt scan' first.")
        sys.exit(1)

    conn = get_connection(DB_PATH)

    try:
        clusters = find_conflicts(conn)

        if high_only:
            clusters = [c for c in clusters if c.severity == "high"]

        if json_output:
            result = []
            for cluster in clusters:
                result.append({
                    "severity": cluster.severity,
                    "mods": cluster.mods,
                    "resource_types": list(cluster.resource_types),
                    "resource_count": len(cluster.resources),
                })
            print(json.dumps(result))
            return

        if not clusters:
            print_info("No conflicts found!")
            return

        console.print(f"\n[bold]Found {len(clusters)} conflict cluster(s)[/bold]\n")

        for i, cluster in enumerate(clusters, 1):
            severity_color = {
                "high": "red",
                "medium": "yellow",
                "low": "blue",
            }[cluster.severity]

            header = f"[{severity_color}]{'⚠' if cluster.severity != 'low' else 'ℹ'}[/{severity_color}]  Conflict Cluster #{i} ([{severity_color}]{cluster.severity.upper()}[/{severity_color}]) - {len(cluster.mods)} mods, {len(cluster.resources)} resources"
            console.print(header)

            tree = Tree("   ")
            for mod in cluster.mods:
                tree.add(f"[cyan]{mod}[/cyan]")

            console.print(tree)
            console.print(f"   Shared: {', '.join(sorted(cluster.resource_types))}")
            console.print()

    finally:
        conn.close()
```

**Step 2: Test conflicts command**

Run: `python -m s4lt.cli.main conflicts --help`
Expected: Shows conflicts options

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: CLI conflicts command with clustering"
```

---

## Task 13: CLI Duplicates Command

**Files:**
- Create: `s4lt/cli/commands/duplicates.py`

**Step 1: Write the duplicates command**

```python
# s4lt/cli/commands/duplicates.py
"""Duplicates command implementation."""

import json
import sys

from rich.tree import Tree

from s4lt.cli.output import console, format_size, print_info, print_warning
from s4lt.config.settings import DB_PATH
from s4lt.db import get_connection
from s4lt.mods.duplicates import find_duplicates


def run_duplicates(exact_only: bool = False, json_output: bool = False):
    """Run the duplicates command."""
    if not DB_PATH.exists():
        if json_output:
            print(json.dumps({"error": "No scan data. Run 's4lt scan' first."}))
        else:
            print_warning("No scan data. Run 's4lt scan' first.")
        sys.exit(1)

    conn = get_connection(DB_PATH)

    try:
        groups = find_duplicates(conn)

        if exact_only:
            groups = [g for g in groups if g.match_type == "exact"]

        if json_output:
            result = []
            for group in groups:
                result.append({
                    "match_type": group.match_type,
                    "mods": [{"path": m["path"], "size": m["size"]} for m in group.mods],
                    "wasted_bytes": group.wasted_bytes,
                })
            print(json.dumps(result))
            return

        if not groups:
            print_info("No duplicates found!")
            return

        total_wasted = sum(g.wasted_bytes for g in groups)
        console.print(f"\n[bold]Found {len(groups)} duplicate group(s)[/bold] (wasting {format_size(total_wasted)})\n")

        for i, group in enumerate(groups, 1):
            match_label = "Exact match" if group.match_type == "exact" else "Same content"
            header = f"[yellow]📦[/yellow] Duplicate Group #{i} - {match_label} ({len(group.mods)} files, wasting {format_size(group.wasted_bytes)})"
            console.print(header)

            tree = Tree("   ")
            for j, mod in enumerate(group.mods):
                label = "[dim](oldest)[/dim]" if j == 0 else "[dim](delete?)[/dim]"
                tree.add(f"[cyan]{mod['path']}[/cyan] ({format_size(mod['size'])}) {label}")

            console.print(tree)
            console.print()

    finally:
        conn.close()
```

**Step 2: Test duplicates command**

Run: `python -m s4lt.cli.main duplicates --help`
Expected: Shows duplicates options

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: CLI duplicates command"
```

---

## Task 14: CLI Info Command

**Files:**
- Create: `s4lt/cli/commands/info.py`

**Step 1: Write the info command**

```python
# s4lt/cli/commands/info.py
"""Info command implementation."""

import sys
from collections import Counter
from pathlib import Path

from rich.panel import Panel
from rich.tree import Tree

from s4lt.cli.output import console, format_size, print_warning, print_error
from s4lt.config import get_settings
from s4lt.config.settings import DB_PATH
from s4lt.db import get_connection


def run_info(package: str):
    """Run the info command."""
    if not DB_PATH.exists():
        print_warning("No scan data. Run 's4lt scan' first.")
        sys.exit(1)

    settings = get_settings()
    if not settings.mods_path:
        print_warning("Mods folder not configured. Run 's4lt scan' first.")
        sys.exit(1)

    conn = get_connection(DB_PATH)

    try:
        # Find the mod - try exact path first, then search by filename
        cursor = conn.execute(
            "SELECT * FROM mods WHERE path = ? OR filename = ?",
            (package, package),
        )
        mod = cursor.fetchone()

        if not mod:
            # Try partial match
            cursor = conn.execute(
                "SELECT * FROM mods WHERE path LIKE ? OR filename LIKE ?",
                (f"%{package}%", f"%{package}%"),
            )
            mod = cursor.fetchone()

        if not mod:
            print_error(f"Package not found: {package}")
            sys.exit(1)

        mod = dict(mod)

        # Get resources
        cursor = conn.execute(
            "SELECT * FROM resources WHERE mod_id = ?",
            (mod["id"],),
        )
        resources = [dict(r) for r in cursor.fetchall()]

        # Count by type
        type_counts = Counter(r["type_name"] or "Unknown" for r in resources)

        # Find conflicts
        cursor = conn.execute("""
            SELECT DISTINCT m2.path
            FROM resources r1
            JOIN resources r2 ON r1.type_id = r2.type_id
                AND r1.group_id = r2.group_id
                AND r1.instance_id = r2.instance_id
            JOIN mods m2 ON r2.mod_id = m2.id
            WHERE r1.mod_id = ? AND r2.mod_id != ? AND m2.broken = 0
        """, (mod["id"], mod["id"]))
        conflicting_mods = [r[0] for r in cursor.fetchall()]

        # Display
        console.print()
        console.print(f"[bold]📦 {mod['filename']}[/bold]")
        console.print(f"   Path: [cyan]{mod['path']}[/cyan]")
        console.print(f"   Size: {format_size(mod['size'])}")
        console.print(f"   Resources: {mod['resource_count']}")

        if mod["broken"]:
            console.print(f"   [red]BROKEN: {mod['error_message']}[/red]")

        console.print()
        console.print("   [bold]Contents:[/bold]")
        tree = Tree("   ")
        for type_name, count in type_counts.most_common():
            # Get example names for this type
            names = [r["name"] for r in resources if r["type_name"] == type_name and r["name"]][:3]
            name_str = f' - "{", ".join(names)}"...' if names else ""
            tree.add(f"{type_name} ({count}){name_str}")
        console.print(tree)

        if conflicting_mods:
            console.print()
            console.print(f"   [yellow]⚠ Conflicts with:[/yellow]")
            for cmod in conflicting_mods[:5]:
                console.print(f"      [cyan]{cmod}[/cyan]")
            if len(conflicting_mods) > 5:
                console.print(f"      ... and {len(conflicting_mods) - 5} more")

        console.print()

    finally:
        conn.close()
```

**Step 2: Test info command**

Run: `python -m s4lt.cli.main info --help`
Expected: Shows info usage

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: CLI info command for package details"
```

---

## Task 15: Final Integration and Testing

**Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Test CLI end-to-end**

Run: `python -m s4lt.cli.main --version`
Expected: Shows version

Run: `python -m s4lt.cli.main --help`
Expected: Shows all commands

**Step 3: Update README**

Add to README.md after Phase 1 section:

```markdown
## Phase 2: Mod Scanner

Scan, index, and analyze your Mods folder:

```bash
# First run - detects Mods folder automatically
s4lt scan

# Show conflicts
s4lt conflicts
s4lt conflicts --high  # High severity only

# Find duplicates
s4lt duplicates

# Package info
s4lt info CoolHair.package
```

### Features

- **Full indexing** with human-readable names from tuning XML
- **Conflict detection** grouped by severity (high/medium/low)
- **Duplicate detection** - exact matches and content-identical packages
- **Incremental updates** - only re-indexes changed files
- **SQLite caching** for fast subsequent operations
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "docs: complete Phase 2 - Mod Scanner ready"
```

---

## Summary

**Tasks:**
1. Add dependencies (click, rich)
2. Database schema
3. Database operations
4. Config module with path detection
5. Scanner module
6. Indexer module
7. Conflict detection
8. Duplicate detection
9. CLI output helpers
10. CLI main entry point
11. CLI scan command
12. CLI conflicts command
13. CLI duplicates command
14. CLI info command
15. Final integration

**New Files:**
- `s4lt/db/` - Database module
- `s4lt/config/` - Configuration module
- `s4lt/mods/` - Scanner, indexer, conflicts, duplicates
- `s4lt/cli/commands/` - CLI command implementations
- `tests/db/`, `tests/config/`, `tests/mods/`, `tests/cli/` - Tests

**Capabilities:**
- Scan any Sims 4 Mods folder
- Index all resources with names
- Detect conflicts grouped by severity
- Find exact and content duplicates
- Rich CLI with JSON output option
