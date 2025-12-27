# Phase 4: CC Tracker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Detect which CC (custom content) each tray item uses and identify missing CC by cross-referencing against the mod index and a new EA content index.

**Architecture:** Two-index lookup system. EA index (base game content) stored in separate `ea.db`. TGI extraction from tray binary files. Classification: EA = ignore, Mods = show source, Neither = missing CC warning.

**Tech Stack:** Python 3.11+, sqlite3, struct (binary parsing), existing DBPF core engine

---

## Task 1: EA Module Setup

**Files:**
- Create: `s4lt/ea/__init__.py`
- Create: `s4lt/ea/exceptions.py`
- Create: `tests/ea/__init__.py`

**Step 1: Create exception classes**

```python
# s4lt/ea/exceptions.py
"""EA content indexing exceptions."""


class EAError(Exception):
    """Base exception for EA operations."""


class GameNotFoundError(EAError):
    """Game install folder not found."""


class EAIndexError(EAError):
    """Error indexing EA content."""
```

**Step 2: Create ea __init__.py**

```python
# s4lt/ea/__init__.py
"""S4LT EA - Base game content indexing."""

from s4lt.ea.exceptions import (
    EAError,
    GameNotFoundError,
    EAIndexError,
)

__all__ = [
    "EAError",
    "GameNotFoundError",
    "EAIndexError",
]
```

**Step 3: Create test __init__ file**

```python
# tests/ea/__init__.py
"""EA module tests."""
```

**Step 4: Run tests to verify setup**

Run: `pytest tests/ -v --tb=short`
Expected: All existing tests pass, no errors from new modules

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(ea): module setup with exceptions"
```

---

## Task 2: EA Path Detection

**Files:**
- Create: `s4lt/ea/paths.py`
- Create: `tests/ea/test_paths.py`

**Step 1: Write the failing test**

```python
# tests/ea/test_paths.py
"""Tests for EA game path detection."""

import tempfile
from pathlib import Path

from s4lt.ea.paths import find_game_folder, validate_game_folder


def test_validate_game_folder_valid():
    """Should return True for valid game folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir)
        # Create expected structure
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()

        assert validate_game_folder(game_path) is True


def test_validate_game_folder_invalid():
    """Should return False for invalid folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert validate_game_folder(Path(tmpdir)) is False


def test_find_game_folder_from_search_paths():
    """Should find game folder from search paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir) / "The Sims 4"
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()

        result = find_game_folder(search_paths=[str(game_path)])
        assert result == game_path


def test_find_game_folder_returns_none_if_not_found():
    """Should return None if game not found."""
    result = find_game_folder(search_paths=["/nonexistent/path"])
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ea/test_paths.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/ea/paths.py
"""EA game path detection."""

import os
import subprocess
from pathlib import Path

# Common game install locations
EA_SEARCH_PATHS = [
    # NonSteamLaunchers (Steam Deck)
    "~/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/Program Files/EA Games/The Sims 4",
    # Standard Steam Proton
    "~/.steam/steam/steamapps/common/The Sims 4",
    "~/.local/share/Steam/steamapps/common/The Sims 4",
    # Flatpak Steam
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/The Sims 4",
    # Lutris/Wine
    "~/Games/the-sims-4/drive_c/Program Files/EA Games/The Sims 4",
]


def expand_path(path: str) -> Path:
    """Expand ~ in path."""
    return Path(os.path.expanduser(path))


def validate_game_folder(path: Path) -> bool:
    """Check if path is a valid Sims 4 game folder.

    Validates by checking for ClientFullBuild0.package.
    """
    marker = path / "Data" / "Client" / "ClientFullBuild0.package"
    return marker.is_file()


def find_game_folder(search_paths: list[str] | None = None) -> Path | None:
    """Find the game install folder.

    Args:
        search_paths: Paths to check (defaults to EA_SEARCH_PATHS)

    Returns:
        Path to game folder if found, None otherwise
    """
    if search_paths is None:
        search_paths = EA_SEARCH_PATHS

    # Check known paths first
    for path_template in search_paths:
        game_path = expand_path(path_template)
        if validate_game_folder(game_path):
            return game_path

    return None


def find_game_folder_search() -> Path | None:
    """Find game folder by searching filesystem.

    Fallback when known paths don't work.
    Uses: find ~ -name "ClientFullBuild0.package"
    """
    try:
        result = subprocess.run(
            ["find", str(Path.home()), "-name", "ClientFullBuild0.package", "-type", "f"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0 and result.stdout.strip():
            # Take first result, derive game folder
            package_path = Path(result.stdout.strip().split("\n")[0])
            # ClientFullBuild0.package is in Data/Client/
            game_path = package_path.parent.parent.parent
            if validate_game_folder(game_path):
                return game_path

    except (subprocess.TimeoutExpired, Exception):
        pass

    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ea/test_paths.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(ea): game path detection"
```

---

## Task 3: EA Database Schema

**Files:**
- Create: `s4lt/ea/database.py`
- Create: `tests/ea/test_database.py`

**Step 1: Write the failing test**

```python
# tests/ea/test_database.py
"""Tests for EA database operations."""

import tempfile
from pathlib import Path

from s4lt.ea.database import init_ea_db, get_ea_db_path, EADatabase


def test_init_creates_tables():
    """Should create ea_resources and ea_scan_info tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ea.db"
        conn = init_ea_db(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "ea_resources" in tables
        assert "ea_scan_info" in tables

        conn.close()


def test_ea_database_insert_resource():
    """Should insert and lookup resources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ea.db"
        conn = init_ea_db(db_path)
        db = EADatabase(conn)

        db.insert_resource(
            instance_id=12345,
            type_id=100,
            group_id=0,
            package_name="Test.package",
            pack="BaseGame",
        )

        result = db.lookup_instance(12345)
        assert result is not None
        assert result["package_name"] == "Test.package"

        conn.close()


def test_ea_database_lookup_not_found():
    """Should return None for unknown instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ea.db"
        conn = init_ea_db(db_path)
        db = EADatabase(conn)

        result = db.lookup_instance(99999)
        assert result is None

        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ea/test_database.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/ea/database.py
"""EA content database operations."""

import sqlite3
from pathlib import Path
from typing import Any

from s4lt.config.settings import DATA_DIR


def get_ea_db_path() -> Path:
    """Get path to EA database."""
    return DATA_DIR / "ea.db"


def init_ea_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Initialize EA database with schema.

    Args:
        db_path: Path to database (defaults to standard location)

    Returns:
        Database connection
    """
    if db_path is None:
        db_path = get_ea_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ea_resources (
            instance_id INTEGER PRIMARY KEY,
            type_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            package_name TEXT NOT NULL,
            pack TEXT
        );

        CREATE TABLE IF NOT EXISTS ea_scan_info (
            id INTEGER PRIMARY KEY,
            game_path TEXT NOT NULL,
            last_scan TEXT NOT NULL,
            package_count INTEGER,
            resource_count INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_ea_type ON ea_resources(type_id);
    """)

    conn.commit()
    return conn


class EADatabase:
    """EA content database wrapper."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_resource(
        self,
        instance_id: int,
        type_id: int,
        group_id: int,
        package_name: str,
        pack: str | None = None,
    ) -> None:
        """Insert a resource (ignore duplicates)."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO ea_resources
            (instance_id, type_id, group_id, package_name, pack)
            VALUES (?, ?, ?, ?, ?)
            """,
            (instance_id, type_id, group_id, package_name, pack),
        )

    def insert_batch(self, resources: list[tuple]) -> None:
        """Insert multiple resources efficiently."""
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO ea_resources
            (instance_id, type_id, group_id, package_name, pack)
            VALUES (?, ?, ?, ?, ?)
            """,
            resources,
        )
        self.conn.commit()

    def lookup_instance(self, instance_id: int) -> dict[str, Any] | None:
        """Look up resource by instance ID."""
        cursor = self.conn.execute(
            "SELECT * FROM ea_resources WHERE instance_id = ?",
            (instance_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def lookup_tgi(self, type_id: int, group_id: int, instance_id: int) -> dict[str, Any] | None:
        """Look up resource by full TGI."""
        cursor = self.conn.execute(
            """
            SELECT * FROM ea_resources
            WHERE type_id = ? AND group_id = ? AND instance_id = ?
            """,
            (type_id, group_id, instance_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def is_ea_content(self, instance_id: int) -> bool:
        """Check if instance ID is EA content."""
        return self.lookup_instance(instance_id) is not None

    def save_scan_info(self, game_path: str, package_count: int, resource_count: int) -> None:
        """Save scan metadata."""
        from datetime import datetime

        self.conn.execute("DELETE FROM ea_scan_info")
        self.conn.execute(
            """
            INSERT INTO ea_scan_info (game_path, last_scan, package_count, resource_count)
            VALUES (?, ?, ?, ?)
            """,
            (game_path, datetime.now().isoformat(), package_count, resource_count),
        )
        self.conn.commit()

    def get_scan_info(self) -> dict[str, Any] | None:
        """Get last scan info."""
        cursor = self.conn.execute("SELECT * FROM ea_scan_info LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def count_resources(self) -> int:
        """Count total resources in index."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM ea_resources")
        return cursor.fetchone()[0]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ea/test_database.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(ea): database schema and operations"
```

---

## Task 4: EA Content Scanner

**Files:**
- Create: `s4lt/ea/scanner.py`
- Create: `tests/ea/test_scanner.py`

**Step 1: Write the failing test**

```python
# tests/ea/test_scanner.py
"""Tests for EA content scanner."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from s4lt.ea.scanner import discover_ea_packages, scan_ea_content
from s4lt.ea.database import init_ea_db, EADatabase


def test_discover_ea_packages():
    """Should find .package files in Data folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir)

        # Create fake package structure
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()
        (client_dir / "ClientFullBuild1.package").touch()

        sim_dir = game_path / "Data" / "Simulation" / "Gameplay"
        sim_dir.mkdir(parents=True)
        (sim_dir / "SimulationFullBuild0.package").touch()

        packages = discover_ea_packages(game_path)

        assert len(packages) == 3
        assert any("ClientFullBuild0" in str(p) for p in packages)


def test_discover_ea_packages_includes_dlc():
    """Should find packages in EP/GP/SP folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir)

        # Base game
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()

        # Expansion pack
        ep01_dir = game_path / "EP01" / "Data" / "Client"
        ep01_dir.mkdir(parents=True)
        (ep01_dir / "ClientFullBuild0.package").touch()

        packages = discover_ea_packages(game_path)

        assert len(packages) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ea/test_scanner.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/ea/scanner.py
"""EA content scanner."""

from pathlib import Path
from typing import Callable

from s4lt.core import Package
from s4lt.ea.database import EADatabase


# Pack folder prefixes
PACK_PREFIXES = ["EP", "GP", "SP", "FP"]


def discover_ea_packages(game_path: Path) -> list[Path]:
    """Discover all EA .package files in game folder.

    Scans:
    - Data/Client/*.package
    - Data/Simulation/**/*.package
    - EP*/Data/**/*.package (expansions)
    - GP*/Data/**/*.package (game packs)
    - SP*/Data/**/*.package (stuff packs)
    - FP*/Data/**/*.package (free packs)
    """
    packages = []

    # Base game Data folder
    data_dir = game_path / "Data"
    if data_dir.is_dir():
        packages.extend(data_dir.rglob("*.package"))

    # DLC folders (EP01, GP05, etc.)
    for item in game_path.iterdir():
        if item.is_dir() and any(item.name.startswith(p) for p in PACK_PREFIXES):
            dlc_data = item / "Data"
            if dlc_data.is_dir():
                packages.extend(dlc_data.rglob("*.package"))

    return sorted(packages)


def get_pack_name(package_path: Path, game_path: Path) -> str:
    """Determine pack name from package path."""
    try:
        relative = package_path.relative_to(game_path)
        parts = relative.parts

        # Check if in DLC folder
        if parts and any(parts[0].startswith(p) for p in PACK_PREFIXES):
            return parts[0]  # EP01, GP05, etc.

        return "BaseGame"
    except ValueError:
        return "Unknown"


def scan_ea_content(
    game_path: Path,
    db: EADatabase,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> tuple[int, int]:
    """Scan all EA packages and index their resources.

    Args:
        game_path: Path to game install folder
        db: EA database instance
        progress_callback: Optional callback(package_name, current, total)

    Returns:
        Tuple of (package_count, resource_count)
    """
    packages = discover_ea_packages(game_path)
    total_packages = len(packages)
    total_resources = 0

    for i, package_path in enumerate(packages):
        if progress_callback:
            progress_callback(package_path.name, i + 1, total_packages)

        try:
            pack_name = get_pack_name(package_path, game_path)

            with Package(package_path) as pkg:
                batch = []
                for entry in pkg.entries:
                    batch.append((
                        entry.instance_id,
                        entry.type_id,
                        entry.group_id,
                        package_path.name,
                        pack_name,
                    ))

                if batch:
                    db.insert_batch(batch)
                    total_resources += len(batch)

        except Exception:
            # Skip corrupt/unreadable packages
            continue

    db.save_scan_info(str(game_path), total_packages, total_resources)

    return total_packages, total_resources
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ea/test_scanner.py -v`
Expected: 2 passed

**Step 5: Update ea __init__.py**

```python
# s4lt/ea/__init__.py
"""S4LT EA - Base game content indexing."""

from s4lt.ea.exceptions import (
    EAError,
    GameNotFoundError,
    EAIndexError,
)
from s4lt.ea.paths import find_game_folder, validate_game_folder
from s4lt.ea.database import init_ea_db, get_ea_db_path, EADatabase
from s4lt.ea.scanner import discover_ea_packages, scan_ea_content

__all__ = [
    # Exceptions
    "EAError",
    "GameNotFoundError",
    "EAIndexError",
    # Paths
    "find_game_folder",
    "validate_game_folder",
    # Database
    "init_ea_db",
    "get_ea_db_path",
    "EADatabase",
    # Scanner
    "discover_ea_packages",
    "scan_ea_content",
]
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(ea): content scanner"
```

---

## Task 5: TGI Extraction from Tray Files

**Files:**
- Create: `s4lt/tray/cc_tracker.py`
- Create: `tests/tray/test_cc_tracker.py`

**Step 1: Write the failing test**

```python
# tests/tray/test_cc_tracker.py
"""Tests for CC tracking and TGI extraction."""

import struct
import tempfile
from pathlib import Path

from s4lt.tray.cc_tracker import extract_tgis_from_binary, TGI


def create_mock_binary_with_tgis(tgis: list[tuple[int, int, int]]) -> bytes:
    """Create mock binary data containing TGI references."""
    data = bytearray()
    # Header padding
    data.extend(b"\x00" * 32)

    for type_id, group_id, instance_id in tgis:
        # TGI format: type(4) + group(4) + instance(8) = 16 bytes
        data.extend(struct.pack("<I", type_id))
        data.extend(struct.pack("<I", group_id))
        data.extend(struct.pack("<Q", instance_id))

    # Footer padding
    data.extend(b"\x00" * 32)
    return bytes(data)


def test_extract_tgis_finds_patterns():
    """Should extract TGI patterns from binary data."""
    test_tgis = [
        (0x034AEECB, 0, 12345678901234),  # CAS part
        (0x319E4F1D, 0, 98765432109876),  # Object
    ]

    data = create_mock_binary_with_tgis(test_tgis)

    with tempfile.NamedTemporaryFile(suffix=".householdbinary", delete=False) as f:
        f.write(data)
        path = Path(f.name)

    try:
        extracted = extract_tgis_from_binary(path)

        # Should find our TGIs
        instance_ids = {tgi.instance_id for tgi in extracted}
        assert 12345678901234 in instance_ids
        assert 98765432109876 in instance_ids
    finally:
        path.unlink()


def test_tgi_dataclass():
    """TGI should have expected properties."""
    tgi = TGI(type_id=100, group_id=0, instance_id=12345)

    assert tgi.type_id == 100
    assert tgi.group_id == 0
    assert tgi.instance_id == 12345
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tray/test_cc_tracker.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/tray/cc_tracker.py
"""CC tracking - TGI extraction and classification."""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from s4lt.tray.item import TrayItem


@dataclass
class TGI:
    """Type/Group/Instance identifier."""
    type_id: int
    group_id: int
    instance_id: int

    def __hash__(self):
        return hash((self.type_id, self.group_id, self.instance_id))

    def __eq__(self, other):
        if not isinstance(other, TGI):
            return False
        return (self.type_id, self.group_id, self.instance_id) == \
               (other.type_id, other.group_id, other.instance_id)


@dataclass
class CCReference:
    """A CC reference with its source."""
    tgi: TGI
    source: str  # "ea", "mod", "missing"
    mod_path: Path | None = None
    mod_name: str | None = None


# Known resource types that indicate CC content
CC_RESOURCE_TYPES = {
    0x034AEECB,  # CAS Part
    0x319E4F1D,  # Object Definition
    0x00B2D882,  # DDS Texture
    0xC0DB5AE7,  # Thumbnail
    0x025ED6F4,  # STBL (strings)
    0x545AC67A,  # Geometry
}


def extract_tgis_from_binary(path: Path) -> list[TGI]:
    """Extract TGI patterns from a binary tray file.

    Scans the file for 16-byte TGI patterns.

    Args:
        path: Path to .householdbinary, .blueprint, etc.

    Returns:
        List of extracted TGIs
    """
    tgis = []

    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return []

    # Scan for TGI patterns
    # TGI = type(4 bytes) + group(4 bytes) + instance(8 bytes)
    offset = 0
    while offset + 16 <= len(data):
        type_id = struct.unpack_from("<I", data, offset)[0]
        group_id = struct.unpack_from("<I", data, offset + 4)[0]
        instance_id = struct.unpack_from("<Q", data, offset + 8)[0]

        # Filter: only include known CC resource types
        # and reasonable instance IDs (non-zero)
        if type_id in CC_RESOURCE_TYPES and instance_id > 0:
            tgis.append(TGI(type_id, group_id, instance_id))

        offset += 1  # Slide window by 1 byte

    # Deduplicate
    return list(set(tgis))


def extract_tgis_from_tray_item(item: TrayItem) -> list[TGI]:
    """Extract all TGIs from a tray item's binary files.

    Args:
        item: TrayItem to analyze

    Returns:
        List of unique TGIs found
    """
    all_tgis = []

    # Binary file extensions to scan
    binary_extensions = {".householdbinary", ".blueprint", ".room"}

    for file_path in item.files:
        if file_path.suffix.lower() in binary_extensions:
            tgis = extract_tgis_from_binary(file_path)
            all_tgis.extend(tgis)

    return list(set(all_tgis))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tray/test_cc_tracker.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(tray): TGI extraction from binary files"
```

---

## Task 6: CC Classification

**Files:**
- Modify: `s4lt/tray/cc_tracker.py`
- Create: `tests/tray/test_cc_classification.py`

**Step 1: Write the failing test**

```python
# tests/tray/test_cc_classification.py
"""Tests for CC classification."""

import tempfile
from pathlib import Path

from s4lt.tray.cc_tracker import TGI, CCReference, classify_tgis
from s4lt.ea.database import init_ea_db, EADatabase
from s4lt.db.schema import init_db


def test_classify_tgi_as_ea():
    """Should classify TGI found in EA index as 'ea'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup EA database with a resource
        ea_db_path = Path(tmpdir) / "ea.db"
        ea_conn = init_ea_db(ea_db_path)
        ea_db = EADatabase(ea_conn)
        ea_db.insert_resource(
            instance_id=12345,
            type_id=100,
            group_id=0,
            package_name="BaseGame.package",
            pack="BaseGame",
        )

        # Setup mods database (empty)
        mods_db_path = Path(tmpdir) / "mods.db"
        mods_conn = init_db(mods_db_path)

        tgis = [TGI(100, 0, 12345)]
        results = classify_tgis(tgis, ea_conn, mods_conn)

        assert len(results) == 1
        assert results[0].source == "ea"

        ea_conn.close()
        mods_conn.close()


def test_classify_tgi_as_missing():
    """Should classify TGI not found anywhere as 'missing'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ea_db_path = Path(tmpdir) / "ea.db"
        ea_conn = init_ea_db(ea_db_path)

        mods_db_path = Path(tmpdir) / "mods.db"
        mods_conn = init_db(mods_db_path)

        tgis = [TGI(100, 0, 99999)]  # Unknown TGI
        results = classify_tgis(tgis, ea_conn, mods_conn)

        assert len(results) == 1
        assert results[0].source == "missing"

        ea_conn.close()
        mods_conn.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tray/test_cc_classification.py -v`
Expected: FAIL with ImportError (classify_tgis not defined)

**Step 3: Add classify_tgis to cc_tracker.py**

Add to `s4lt/tray/cc_tracker.py`:

```python
import sqlite3


def classify_tgis(
    tgis: list[TGI],
    ea_conn: sqlite3.Connection,
    mods_conn: sqlite3.Connection,
) -> list[CCReference]:
    """Classify TGIs as EA content, mod CC, or missing.

    Args:
        tgis: List of TGIs to classify
        ea_conn: EA database connection
        mods_conn: Mods database connection

    Returns:
        List of CCReference with classification
    """
    from s4lt.ea.database import EADatabase

    ea_db = EADatabase(ea_conn)
    results = []

    for tgi in tgis:
        # Check EA index first
        ea_result = ea_db.lookup_instance(tgi.instance_id)
        if ea_result:
            results.append(CCReference(tgi=tgi, source="ea"))
            continue

        # Check mods index
        cursor = mods_conn.execute(
            """
            SELECT m.path, m.filename
            FROM resources r
            JOIN mods m ON r.mod_id = m.id
            WHERE r.instance_id = ?
            LIMIT 1
            """,
            (tgi.instance_id,),
        )
        row = cursor.fetchone()

        if row:
            results.append(CCReference(
                tgi=tgi,
                source="mod",
                mod_path=Path(row[0]),
                mod_name=row[1],
            ))
            continue

        # Not found anywhere
        results.append(CCReference(tgi=tgi, source="missing"))

    return results


def get_cc_summary(
    item: TrayItem,
    ea_conn: sqlite3.Connection,
    mods_conn: sqlite3.Connection,
) -> dict:
    """Get mod-centric CC summary for a tray item.

    Returns:
        {
            "mods": {mod_name: count, ...},
            "missing_count": int,
            "ea_count": int,
            "total": int,
        }
    """
    tgis = extract_tgis_from_tray_item(item)
    refs = classify_tgis(tgis, ea_conn, mods_conn)

    mods = {}
    missing_count = 0
    ea_count = 0

    for ref in refs:
        if ref.source == "ea":
            ea_count += 1
        elif ref.source == "mod":
            name = ref.mod_name or "Unknown"
            mods[name] = mods.get(name, 0) + 1
        else:
            missing_count += 1

    return {
        "mods": mods,
        "missing_count": missing_count,
        "ea_count": ea_count,
        "total": len(refs),
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tray/test_cc_classification.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(tray): CC classification logic"
```

---

## Task 7: CLI EA Scan Command

**Files:**
- Create: `s4lt/cli/commands/ea.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Write the command implementation**

```python
# s4lt/cli/commands/ea.py
"""EA content commands."""

import sys

import click

from s4lt.cli.output import console, print_success, print_error, print_warning
from s4lt.config import get_settings, save_settings
from s4lt.ea import (
    find_game_folder,
    validate_game_folder,
    init_ea_db,
    get_ea_db_path,
    EADatabase,
    scan_ea_content,
)


def run_ea_scan(game_path_arg: str | None = None):
    """Scan EA game content and build index."""
    from pathlib import Path
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

    settings = get_settings()

    # Determine game path
    if game_path_arg:
        game_path = Path(game_path_arg)
        if not validate_game_folder(game_path):
            print_error(f"Invalid game folder: {game_path}")
            print_error("Expected to find Data/Client/ClientFullBuild0.package")
            sys.exit(1)
    elif settings.game_path:
        game_path = settings.game_path
    else:
        console.print("\n[bold]Game Folder Setup[/bold]\n")

        game_path = find_game_folder()
        if game_path:
            console.print(f"Found game folder: [cyan]{game_path}[/cyan]")
            if not click.confirm("Use this path?", default=True):
                path_str = click.prompt("Enter game folder path")
                game_path = Path(path_str)
        else:
            console.print("[yellow]Could not auto-detect game folder.[/yellow]")
            console.print("Searching filesystem (this may take a minute)...")

            from s4lt.ea.paths import find_game_folder_search
            game_path = find_game_folder_search()

            if game_path:
                console.print(f"Found: [cyan]{game_path}[/cyan]")
                if not click.confirm("Use this path?", default=True):
                    path_str = click.prompt("Enter game folder path")
                    game_path = Path(path_str)
            else:
                path_str = click.prompt("Enter game folder path")
                game_path = Path(path_str)

        if not validate_game_folder(game_path):
            print_error(f"Invalid game folder: {game_path}")
            sys.exit(1)

        settings.game_path = game_path
        save_settings(settings)
        console.print("[green]Saved configuration.[/green]\n")

    # Initialize database
    db_path = get_ea_db_path()
    conn = init_ea_db(db_path)
    db = EADatabase(conn)

    # Check if already scanned
    existing = db.get_scan_info()
    if existing:
        console.print(f"[dim]Previous scan: {existing['resource_count']:,} resources[/dim]")
        if not click.confirm("Rescan?", default=False):
            conn.close()
            return
        # Clear existing data
        conn.execute("DELETE FROM ea_resources")
        conn.commit()

    console.print(f"\n[bold]Scanning[/bold] {game_path}\n")

    # Scan with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning packages...", total=None)

        def update_progress(name: str, current: int, total: int):
            progress.update(task, description=f"[cyan]{name}[/cyan]", completed=current, total=total)

        pkg_count, res_count = scan_ea_content(game_path, db, update_progress)

    console.print()
    print_success(f"Indexed {res_count:,} resources from {pkg_count} packages")
    console.print(f"[dim]Saved to {db_path}[/dim]")

    conn.close()


def run_ea_status():
    """Show EA index status."""
    db_path = get_ea_db_path()

    if not db_path.exists():
        print_warning("EA content not indexed. Run 's4lt ea scan' first.")
        return

    conn = init_ea_db(db_path)
    db = EADatabase(conn)

    info = db.get_scan_info()
    if not info:
        print_warning("EA content not indexed. Run 's4lt ea scan' first.")
        conn.close()
        return

    console.print("\n[bold]EA Content Index[/bold]\n")
    console.print(f"  Game path: [cyan]{info['game_path']}[/cyan]")
    console.print(f"  Last scan: {info['last_scan']}")
    console.print(f"  Packages: {info['package_count']:,}")
    console.print(f"  Resources: {info['resource_count']:,}")
    console.print()

    conn.close()
```

**Step 2: Add settings.game_path**

Modify `s4lt/config/settings.py` - add `game_path` field:

```python
@dataclass
class Settings:
    """User settings."""

    mods_path: Path | None = None
    tray_path: Path | None = None
    game_path: Path | None = None  # Add this
    include_subfolders: bool = True
    ignore_patterns: list[str] = field(
        default_factory=lambda: ["__MACOSX", ".DS_Store", "*.disabled"]
    )
```

Update `to_dict`, `get_settings`, and `save_settings` to handle `game_path`.

**Step 3: Add ea commands to main.py**

Add to `s4lt/cli/main.py`:

```python
@cli.group()
def ea():
    """Manage EA content index (base game)."""
    pass


@ea.command("scan")
@click.option("--path", "game_path", help="Path to game folder")
def ea_scan(game_path: str | None):
    """Scan and index base game content."""
    from s4lt.cli.commands.ea import run_ea_scan
    run_ea_scan(game_path_arg=game_path)


@ea.command("status")
def ea_status():
    """Show EA index status."""
    from s4lt.cli.commands.ea import run_ea_status
    run_ea_status()
```

**Step 4: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(cli): ea scan and status commands"
```

---

## Task 8: CLI Tray CC Command

**Files:**
- Modify: `s4lt/cli/commands/tray.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Add CC command implementation**

Add to `s4lt/cli/commands/tray.py`:

```python
def run_tray_cc(
    name_or_id: str,
    verbose: bool = False,
    json_output: bool = False,
):
    """Show CC usage for a tray item."""
    import json as json_lib

    from s4lt.tray import discover_tray_items, TrayItem
    from s4lt.tray.cc_tracker import get_cc_summary, extract_tgis_from_tray_item, classify_tgis
    from s4lt.ea import init_ea_db, get_ea_db_path
    from s4lt.db.schema import init_db
    from s4lt.config.settings import DB_PATH

    settings = get_settings()

    if settings.tray_path is None:
        print_error("Tray folder not configured. Run 's4lt tray list' first.")
        sys.exit(1)

    tray_path = settings.tray_path

    # Check EA index
    ea_db_path = get_ea_db_path()
    if not ea_db_path.exists():
        if not json_output:
            print_warning("EA content not indexed. Run 's4lt ea scan' first.")
            print_warning("Without EA index, all non-mod TGIs show as 'unknown'.")
            if not click.confirm("Continue anyway?", default=False):
                sys.exit(0)

    # Find the item
    discovered = discover_tray_items(tray_path)
    target = None

    for d in discovered:
        if d["id"] == name_or_id:
            target = d
            break
        try:
            item = TrayItem.from_path(tray_path, d["id"])
            if item.name.lower() == name_or_id.lower():
                target = d
                break
        except Exception:
            pass

    if not target:
        if json_output:
            print(json_lib.dumps({"error": f"Tray item not found: {name_or_id}"}))
        else:
            print_error(f"Tray item not found: {name_or_id}")
        sys.exit(1)

    # Load item and analyze
    item = TrayItem.from_path(tray_path, target["id"])

    # Connect to databases
    ea_conn = init_ea_db(ea_db_path) if ea_db_path.exists() else None
    mods_conn = init_db(DB_PATH) if DB_PATH.exists() else None

    if ea_conn is None and mods_conn is None:
        print_error("No indexes available. Run 's4lt scan' and 's4lt ea scan' first.")
        sys.exit(1)

    # Get summary
    if mods_conn:
        summary = get_cc_summary(item, ea_conn, mods_conn)
    else:
        summary = {"mods": {}, "missing_count": 0, "ea_count": 0, "total": 0}

    if json_output:
        print(json_lib.dumps({
            "name": item.name,
            "id": item.id,
            "type": item.item_type.value,
            "cc": summary,
        }))
    else:
        console.print(f"\n[bold]{item.name}[/bold]")
        console.print(f"  Type: [cyan]{item.item_type.value}[/cyan]")
        console.print()

        if summary["mods"]:
            console.print("[bold]CC Usage:[/bold]")
            for mod_name, count in sorted(summary["mods"].items()):
                console.print(f"  {count} items from [cyan]{mod_name}[/cyan]")
        else:
            console.print("[dim]No CC detected[/dim]")

        if summary["missing_count"] > 0:
            console.print(f"\n[red]⚠ {summary['missing_count']} missing CC items[/red]")

        if verbose:
            console.print(f"\n[dim]EA resources: {summary['ea_count']}[/dim]")
            console.print(f"[dim]Total TGIs: {summary['total']}[/dim]")

    if ea_conn:
        ea_conn.close()
    if mods_conn:
        mods_conn.close()
```

**Step 2: Add cc command to main.py**

Add to tray group in `s4lt/cli/main.py`:

```python
@tray.command("cc")
@click.argument("name_or_id")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def tray_cc(name_or_id: str, verbose: bool, json_output: bool):
    """Show CC usage for a tray item."""
    from s4lt.cli.commands.tray import run_tray_cc
    run_tray_cc(name_or_id, verbose=verbose, json_output=json_output)
```

**Step 3: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "feat(cli): tray cc command"
```

---

## Task 9: Enhanced Tray Info with CC Summary

**Files:**
- Modify: `s4lt/cli/commands/tray.py`

**Step 1: Update run_tray_info to include CC summary**

Modify the existing `run_tray_info` function to add CC summary at the end:

```python
# Add at end of run_tray_info, before closing:

    # Add CC summary if indexes exist
    from s4lt.ea import get_ea_db_path, init_ea_db
    from s4lt.db.schema import init_db
    from s4lt.config.settings import DB_PATH
    from s4lt.tray.cc_tracker import get_cc_summary

    ea_db_path = get_ea_db_path()

    if ea_db_path.exists() and DB_PATH.exists():
        ea_conn = init_ea_db(ea_db_path)
        mods_conn = init_db(DB_PATH)

        summary = get_cc_summary(item, ea_conn, mods_conn)

        if not json_output:
            console.print()
            if summary["mods"]:
                console.print("[bold]CC Usage:[/bold]")
                for mod_name, count in sorted(summary["mods"].items()):
                    console.print(f"  {count} items from [cyan]{mod_name}[/cyan]")

            if summary["missing_count"] > 0:
                console.print(f"[red]⚠ {summary['missing_count']} missing CC[/red]")
        else:
            info["cc"] = summary

        ea_conn.close()
        mods_conn.close()
```

**Step 2: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 3: Commit**

```bash
git add -A
git commit -m "feat(cli): CC summary in tray info"
```

---

## Task 10: CLI Tests for CC Commands

**Files:**
- Modify: `tests/cli/test_tray.py`
- Create: `tests/cli/test_ea.py`

**Step 1: Add EA CLI tests**

```python
# tests/cli/test_ea.py
"""Tests for EA CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from s4lt.cli.main import cli
from s4lt.config.settings import Settings


def test_ea_status_no_index():
    """ea status should warn if no index exists."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("s4lt.cli.commands.ea.get_ea_db_path", return_value=Path(tmpdir) / "nonexistent.db"):
            result = runner.invoke(cli, ["ea", "status"])

        assert "not indexed" in result.output.lower()
```

**Step 2: Add CC command tests to test_tray.py**

Add to `tests/cli/test_tray.py`:

```python
def test_tray_cc_no_tray_configured():
    """tray cc should error if tray not configured."""
    runner = CliRunner()

    settings = Settings()  # No tray_path

    with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
        result = runner.invoke(cli, ["tray", "cc", "test"])

    assert result.exit_code == 1
    assert "not configured" in result.output.lower()
```

**Step 3: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "test(cli): EA and CC command tests"
```

---

## Task 11: Final Integration

**Step 1: Update tray __init__.py**

```python
# Add to s4lt/tray/__init__.py exports:
from s4lt.tray.cc_tracker import (
    TGI,
    CCReference,
    extract_tgis_from_binary,
    extract_tgis_from_tray_item,
    classify_tgis,
    get_cc_summary,
)

# Add to __all__:
    "TGI",
    "CCReference",
    "extract_tgis_from_binary",
    "extract_tgis_from_tray_item",
    "classify_tgis",
    "get_cc_summary",
```

**Step 2: Update top-level __init__.py**

```python
# s4lt/__init__.py - bump version
__version__ = "0.3.0"
```

**Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Phase 4 - CC Tracker ready"
```

---

## Summary

**Files Created:**
- `s4lt/ea/__init__.py` - EA module exports
- `s4lt/ea/exceptions.py` - Error classes
- `s4lt/ea/paths.py` - Game path detection
- `s4lt/ea/database.py` - EA index database
- `s4lt/ea/scanner.py` - EA content scanner
- `s4lt/tray/cc_tracker.py` - TGI extraction and classification
- `s4lt/cli/commands/ea.py` - EA CLI commands
- `tests/ea/` - EA test suite

**Files Modified:**
- `s4lt/config/settings.py` - Added game_path
- `s4lt/cli/main.py` - Added ea and tray cc commands
- `s4lt/cli/commands/tray.py` - Added CC features
- `s4lt/tray/__init__.py` - Added CC exports

**CLI Commands Added:**
- `s4lt ea scan [--path]` - Scan and index base game content
- `s4lt ea status` - Show EA index status
- `s4lt tray cc <name_or_id> [-v] [--json]` - Show CC usage
- Enhanced `s4lt tray info` with CC summary

**Capabilities:**
- Index base game content (~2-3M TGIs)
- Extract TGIs from tray binary files
- Classify TGIs as EA/mod/missing
- Show mod-centric CC summaries
- Detect missing CC
