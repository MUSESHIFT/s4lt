# Phase 4: Organization - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add mod organization capabilities: auto-categorization, enable/disable, profiles, and batch operations.

**Architecture:** New `s4lt/organize/` module with categorizer, profiles, sorter, and batch submodules. SQLite tables for profile storage. CLI commands integrated into existing Click structure.

**Tech Stack:** Python 3.11+, Click (CLI), SQLite3, pytest

---

## Task 1: Database Schema Updates

**Files:**
- Modify: `s4lt/db/schema.py`
- Test: `tests/db/test_schema.py`

**Step 1: Write the failing test**

Add to `tests/db/test_schema.py`:

```python
def test_profiles_table_exists():
    """Schema should create profiles table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
        )
        assert cursor.fetchone() is not None
        conn.close()


def test_profile_mods_table_exists():
    """Schema should create profile_mods table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='profile_mods'"
        )
        assert cursor.fetchone() is not None
        conn.close()


def test_mods_has_category_column():
    """mods table should have category column."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        cursor = conn.execute("PRAGMA table_info(mods)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "category" in columns
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/db/test_schema.py -v -k "profiles or category"`

Expected: FAIL - tables/column don't exist

**Step 3: Write minimal implementation**

Modify `s4lt/db/schema.py` - update SCHEMA:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/db/test_schema.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/db/schema.py tests/db/test_schema.py
git commit -m "feat(db): add profiles tables and mods.category column"
```

---

## Task 2: Create organize module structure

**Files:**
- Create: `s4lt/organize/__init__.py`
- Create: `s4lt/organize/exceptions.py`
- Create: `tests/organize/__init__.py`

**Step 1: Create module files**

Create `s4lt/organize/__init__.py`:

```python
"""Mod organization: categorization, profiles, and sorting."""
```

Create `s4lt/organize/exceptions.py`:

```python
"""Organization-specific exceptions."""


class OrganizeError(Exception):
    """Base exception for organization operations."""
    pass


class ProfileNotFoundError(OrganizeError):
    """Profile does not exist."""
    pass


class ProfileExistsError(OrganizeError):
    """Profile already exists."""
    pass


class ModNotFoundError(OrganizeError):
    """Mod file not found."""
    pass
```

Create `tests/organize/__init__.py`:

```python
"""Tests for organize module."""
```

**Step 2: Verify module imports**

Run: `.venv/bin/python -c "from s4lt.organize.exceptions import OrganizeError; print('OK')"`

Expected: OK

**Step 3: Commit**

```bash
git add s4lt/organize/ tests/organize/
git commit -m "feat(organize): create module structure with exceptions"
```

---

## Task 3: ModCategory enum and type mappings

**Files:**
- Create: `s4lt/organize/categorizer.py`
- Create: `tests/organize/test_categorizer.py`

**Step 1: Write the failing test**

Create `tests/organize/test_categorizer.py`:

```python
"""Tests for mod categorizer."""

from s4lt.organize.categorizer import ModCategory, TYPE_TO_CATEGORY, CATEGORY_PRIORITY


def test_mod_category_enum_values():
    """ModCategory should have all expected values."""
    assert ModCategory.CAS.value == "CAS"
    assert ModCategory.BUILD_BUY.value == "BuildBuy"
    assert ModCategory.SCRIPT.value == "Script"
    assert ModCategory.TUNING.value == "Tuning"
    assert ModCategory.OVERRIDE.value == "Override"
    assert ModCategory.GAMEPLAY.value == "Gameplay"
    assert ModCategory.UNKNOWN.value == "Unknown"


def test_type_to_category_cas():
    """CASPart type should map to CAS category."""
    assert TYPE_TO_CATEGORY.get(0x034AEECB) == ModCategory.CAS


def test_type_to_category_buildbuy():
    """ObjectCatalog type should map to BUILD_BUY category."""
    assert TYPE_TO_CATEGORY.get(0x319E4F1D) == ModCategory.BUILD_BUY


def test_type_to_category_script():
    """Python bytecode type should map to SCRIPT category."""
    assert TYPE_TO_CATEGORY.get(0x9C07855E) == ModCategory.SCRIPT


def test_category_priority_script_highest():
    """SCRIPT should have highest priority."""
    assert CATEGORY_PRIORITY[ModCategory.SCRIPT] > CATEGORY_PRIORITY[ModCategory.CAS]
    assert CATEGORY_PRIORITY[ModCategory.SCRIPT] > CATEGORY_PRIORITY[ModCategory.BUILD_BUY]
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_categorizer.py -v`

Expected: FAIL - module not found

**Step 3: Write minimal implementation**

Create `s4lt/organize/categorizer.py`:

```python
"""Mod categorization by resource type analysis."""

from enum import Enum


class ModCategory(Enum):
    """Categories for mod classification."""
    CAS = "CAS"
    BUILD_BUY = "BuildBuy"
    SCRIPT = "Script"
    TUNING = "Tuning"
    OVERRIDE = "Override"
    GAMEPLAY = "Gameplay"
    UNKNOWN = "Unknown"


# Priority for tiebreaker (higher = wins ties)
CATEGORY_PRIORITY: dict[ModCategory, int] = {
    ModCategory.SCRIPT: 100,
    ModCategory.CAS: 80,
    ModCategory.BUILD_BUY: 70,
    ModCategory.OVERRIDE: 60,
    ModCategory.GAMEPLAY: 50,
    ModCategory.TUNING: 40,
    ModCategory.UNKNOWN: 0,
}


# Resource type ID → category mapping
TYPE_TO_CATEGORY: dict[int, ModCategory] = {
    # CAS (Create-a-Sim)
    0x034AEECB: ModCategory.CAS,      # CASPart
    0x0355E0A6: ModCategory.CAS,      # BoneDelta
    0x0354796A: ModCategory.CAS,      # Skintone
    0xB6C8B6A0: ModCategory.CAS,      # CASTexture
    0x105205BA: ModCategory.CAS,      # SimPreset
    0x71BDB8A2: ModCategory.CAS,      # StyledLook
    0xEAA32ADD: ModCategory.CAS,      # CASPreset

    # Build/Buy
    0x319E4F1D: ModCategory.BUILD_BUY,  # ObjectCatalog
    0xC0DB5AE7: ModCategory.BUILD_BUY,  # ObjectDefinition
    0xB91E18DB: ModCategory.BUILD_BUY,  # ObjectCatalogSet
    0x07936CE0: ModCategory.BUILD_BUY,  # Block
    0xB4F762C9: ModCategory.BUILD_BUY,  # Floor
    0xFE33068E: ModCategory.BUILD_BUY,  # Wall
    0x1C1CF1F7: ModCategory.BUILD_BUY,  # Railing
    0xEBCBB16C: ModCategory.BUILD_BUY,  # Stairs

    # Script mods
    0x9C07855E: ModCategory.SCRIPT,     # Python bytecode

    # Tuning
    0x0333406C: ModCategory.TUNING,     # Tuning XML
    0x025ED6F4: ModCategory.TUNING,     # SimData
    0x545AC67A: ModCategory.TUNING,     # CombinedTuning
}
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_categorizer.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/categorizer.py tests/organize/test_categorizer.py
git commit -m "feat(organize): add ModCategory enum and type mappings"
```

---

## Task 4: categorize_mod function

**Files:**
- Modify: `s4lt/organize/categorizer.py`
- Modify: `tests/organize/test_categorizer.py`

**Step 1: Write the failing test**

Add to `tests/organize/test_categorizer.py`:

```python
import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource
from s4lt.organize.categorizer import categorize_mod, ModCategory


def test_categorize_mod_cas_majority():
    """Mod with mostly CAS resources should be CAS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "hash", 5)
        # 3 CAS resources
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 2, "CASPart", None, 10, 20)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 3, "CASPart", None, 10, 20)
        # 1 Tuning resource
        insert_resource(conn, mod_id, 0x0333406C, 0, 4, "Tuning", None, 10, 20)

        category = categorize_mod(conn, mod_id)

        assert category == ModCategory.CAS
        conn.close()


def test_categorize_mod_script_wins_tie():
    """Script should win over CAS in a tie."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "script.package", "script.package", 100, 1.0, "hash", 2)
        # 1 CAS, 1 Script
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)
        insert_resource(conn, mod_id, 0x9C07855E, 0, 2, "Script", None, 10, 20)

        category = categorize_mod(conn, mod_id)

        assert category == ModCategory.SCRIPT
        conn.close()


def test_categorize_mod_unknown_resources():
    """Mod with unknown resource types should be UNKNOWN."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "unknown.package", "unknown.package", 100, 1.0, "hash", 1)
        # Unknown type
        insert_resource(conn, mod_id, 0xDEADBEEF, 0, 1, "Unknown", None, 10, 20)

        category = categorize_mod(conn, mod_id)

        assert category == ModCategory.UNKNOWN
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_categorizer.py::test_categorize_mod_cas_majority -v`

Expected: FAIL - categorize_mod not defined

**Step 3: Write minimal implementation**

Add to `s4lt/organize/categorizer.py`:

```python
import sqlite3
from collections import Counter


def categorize_mod(conn: sqlite3.Connection, mod_id: int) -> ModCategory:
    """Determine category for a mod based on its resources.

    Algorithm:
    1. Count resources by category
    2. Pick category with highest count
    3. On tie, use priority to break

    Args:
        conn: Database connection
        mod_id: ID of the mod to categorize

    Returns:
        ModCategory for the mod
    """
    cursor = conn.execute(
        "SELECT type_id FROM resources WHERE mod_id = ?",
        (mod_id,)
    )
    type_ids = [row[0] for row in cursor.fetchall()]

    if not type_ids:
        return ModCategory.UNKNOWN

    # Count resources by category
    category_counts: Counter[ModCategory] = Counter()
    for type_id in type_ids:
        category = TYPE_TO_CATEGORY.get(type_id, ModCategory.UNKNOWN)
        category_counts[category] += 1

    if not category_counts:
        return ModCategory.UNKNOWN

    # Find max count
    max_count = max(category_counts.values())
    candidates = [cat for cat, count in category_counts.items() if count == max_count]

    if len(candidates) == 1:
        return candidates[0]

    # Tiebreaker: highest priority wins
    return max(candidates, key=lambda c: CATEGORY_PRIORITY[c])
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_categorizer.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/categorizer.py tests/organize/test_categorizer.py
git commit -m "feat(organize): add categorize_mod function"
```

---

## Task 5: Enable/disable mod functions

**Files:**
- Create: `s4lt/organize/toggle.py`
- Create: `tests/organize/test_toggle.py`

**Step 1: Write the failing test**

Create `tests/organize/test_toggle.py`:

```python
"""Tests for mod enable/disable toggle."""

import tempfile
from pathlib import Path

from s4lt.organize.toggle import enable_mod, disable_mod, is_enabled


def test_disable_mod_renames_file():
    """disable_mod should rename .package to .package.disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mod_path = Path(tmpdir) / "test.package"
        mod_path.write_bytes(b"DBPF")

        result = disable_mod(mod_path)

        assert result is True
        assert not mod_path.exists()
        assert (Path(tmpdir) / "test.package.disabled").exists()


def test_enable_mod_restores_file():
    """enable_mod should rename .package.disabled to .package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        disabled_path = Path(tmpdir) / "test.package.disabled"
        disabled_path.write_bytes(b"DBPF")

        result = enable_mod(disabled_path)

        assert result is True
        assert not disabled_path.exists()
        assert (Path(tmpdir) / "test.package").exists()


def test_disable_already_disabled_noop():
    """disable_mod on already disabled mod should return False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        disabled_path = Path(tmpdir) / "test.package.disabled"
        disabled_path.write_bytes(b"DBPF")

        result = disable_mod(disabled_path)

        assert result is False
        assert disabled_path.exists()


def test_enable_already_enabled_noop():
    """enable_mod on already enabled mod should return False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mod_path = Path(tmpdir) / "test.package"
        mod_path.write_bytes(b"DBPF")

        result = enable_mod(mod_path)

        assert result is False
        assert mod_path.exists()


def test_is_enabled_true():
    """is_enabled should return True for .package files."""
    assert is_enabled(Path("test.package")) is True


def test_is_enabled_false():
    """is_enabled should return False for .disabled files."""
    assert is_enabled(Path("test.package.disabled")) is False
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_toggle.py -v`

Expected: FAIL - module not found

**Step 3: Write minimal implementation**

Create `s4lt/organize/toggle.py`:

```python
"""Enable/disable mod toggle operations."""

from pathlib import Path

from s4lt.organize.exceptions import ModNotFoundError


def is_enabled(mod_path: Path) -> bool:
    """Check if a mod is enabled (not .disabled).

    Args:
        mod_path: Path to the mod file

    Returns:
        True if enabled (.package), False if disabled (.disabled)
    """
    return mod_path.suffix == ".package"


def disable_mod(mod_path: Path) -> bool:
    """Disable a mod by renaming .package to .package.disabled.

    Args:
        mod_path: Path to the mod file

    Returns:
        True if mod was disabled, False if already disabled

    Raises:
        ModNotFoundError: If mod file doesn't exist
    """
    if not mod_path.exists():
        raise ModNotFoundError(f"Mod not found: {mod_path}")

    if mod_path.suffix != ".package":
        return False  # Already disabled or not a package

    new_path = mod_path.with_suffix(".package.disabled")
    mod_path.rename(new_path)
    return True


def enable_mod(mod_path: Path) -> bool:
    """Enable a mod by renaming .package.disabled to .package.

    Args:
        mod_path: Path to the disabled mod file

    Returns:
        True if mod was enabled, False if already enabled

    Raises:
        ModNotFoundError: If mod file doesn't exist
    """
    if not mod_path.exists():
        raise ModNotFoundError(f"Mod not found: {mod_path}")

    if mod_path.suffix != ".disabled":
        return False  # Already enabled

    # Remove .disabled suffix (which includes .package)
    new_path = mod_path.with_suffix("")  # .package.disabled -> .package
    mod_path.rename(new_path)
    return True
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_toggle.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/toggle.py tests/organize/test_toggle.py
git commit -m "feat(organize): add enable/disable mod toggle functions"
```

---

## Task 6: Profile CRUD operations

**Files:**
- Create: `s4lt/organize/profiles.py`
- Create: `tests/organize/test_profiles.py`

**Step 1: Write the failing test**

Create `tests/organize/test_profiles.py`:

```python
"""Tests for profile management."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.organize.profiles import (
    create_profile,
    get_profile,
    list_profiles,
    delete_profile,
    Profile,
)
from s4lt.organize.exceptions import ProfileNotFoundError, ProfileExistsError
import pytest


def test_create_profile():
    """create_profile should create a new profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        profile = create_profile(conn, "gameplay")

        assert profile.name == "gameplay"
        assert profile.id is not None
        assert profile.is_auto is False
        conn.close()


def test_create_profile_duplicate_raises():
    """create_profile should raise if profile exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "gameplay")

        with pytest.raises(ProfileExistsError):
            create_profile(conn, "gameplay")
        conn.close()


def test_get_profile():
    """get_profile should return profile by name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "test")
        profile = get_profile(conn, "test")

        assert profile is not None
        assert profile.name == "test"
        conn.close()


def test_get_profile_not_found():
    """get_profile should return None if not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        profile = get_profile(conn, "nonexistent")

        assert profile is None
        conn.close()


def test_list_profiles():
    """list_profiles should return all profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "a")
        create_profile(conn, "b")
        profiles = list_profiles(conn)

        assert len(profiles) == 2
        names = [p.name for p in profiles]
        assert "a" in names
        assert "b" in names
        conn.close()


def test_delete_profile():
    """delete_profile should remove profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "deleteme")
        delete_profile(conn, "deleteme")

        assert get_profile(conn, "deleteme") is None
        conn.close()


def test_delete_profile_not_found_raises():
    """delete_profile should raise if profile not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        with pytest.raises(ProfileNotFoundError):
            delete_profile(conn, "nonexistent")
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_profiles.py -v`

Expected: FAIL - module not found

**Step 3: Write minimal implementation**

Create `s4lt/organize/profiles.py`:

```python
"""Profile management for mod configurations."""

import sqlite3
import time
from dataclasses import dataclass

from s4lt.organize.exceptions import ProfileNotFoundError, ProfileExistsError


@dataclass
class Profile:
    """A saved mod configuration profile."""
    id: int
    name: str
    created_at: float
    is_auto: bool


def create_profile(
    conn: sqlite3.Connection,
    name: str,
    is_auto: bool = False,
) -> Profile:
    """Create a new profile.

    Args:
        conn: Database connection
        name: Profile name
        is_auto: Whether this is an auto-created profile (e.g., _pre_vanilla)

    Returns:
        The created Profile

    Raises:
        ProfileExistsError: If profile with name already exists
    """
    created_at = time.time()
    try:
        cursor = conn.execute(
            "INSERT INTO profiles (name, created_at, is_auto) VALUES (?, ?, ?) RETURNING id",
            (name, created_at, int(is_auto)),
        )
        row = cursor.fetchone()
        conn.commit()
        return Profile(id=row[0], name=name, created_at=created_at, is_auto=is_auto)
    except sqlite3.IntegrityError:
        raise ProfileExistsError(f"Profile '{name}' already exists")


def get_profile(conn: sqlite3.Connection, name: str) -> Profile | None:
    """Get a profile by name.

    Args:
        conn: Database connection
        name: Profile name

    Returns:
        Profile if found, None otherwise
    """
    cursor = conn.execute(
        "SELECT id, name, created_at, is_auto FROM profiles WHERE name = ?",
        (name,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return Profile(id=row[0], name=row[1], created_at=row[2], is_auto=bool(row[3]))


def list_profiles(conn: sqlite3.Connection) -> list[Profile]:
    """List all profiles.

    Args:
        conn: Database connection

    Returns:
        List of all profiles
    """
    cursor = conn.execute(
        "SELECT id, name, created_at, is_auto FROM profiles ORDER BY name"
    )
    return [
        Profile(id=row[0], name=row[1], created_at=row[2], is_auto=bool(row[3]))
        for row in cursor.fetchall()
    ]


def delete_profile(conn: sqlite3.Connection, name: str) -> None:
    """Delete a profile by name.

    Args:
        conn: Database connection
        name: Profile name

    Raises:
        ProfileNotFoundError: If profile doesn't exist
    """
    cursor = conn.execute("DELETE FROM profiles WHERE name = ? RETURNING id", (name,))
    if cursor.fetchone() is None:
        raise ProfileNotFoundError(f"Profile '{name}' not found")
    conn.commit()
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_profiles.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/profiles.py tests/organize/test_profiles.py
git commit -m "feat(organize): add profile CRUD operations"
```

---

## Task 7: Profile snapshot and restore

**Files:**
- Modify: `s4lt/organize/profiles.py`
- Modify: `tests/organize/test_profiles.py`

**Step 1: Write the failing test**

Add to `tests/organize/test_profiles.py`:

```python
from s4lt.organize.profiles import save_profile_snapshot, get_profile_mods, ProfileMod


def test_save_profile_snapshot():
    """save_profile_snapshot should save current mod states."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Create mods directory with some files
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "enabled.package").write_bytes(b"DBPF")
        (mods_path / "disabled.package.disabled").write_bytes(b"DBPF")

        profile = create_profile(conn, "snapshot")
        save_profile_snapshot(conn, profile.id, mods_path)

        mods = get_profile_mods(conn, profile.id)
        assert len(mods) == 2

        enabled = [m for m in mods if m.enabled]
        disabled = [m for m in mods if not m.enabled]
        assert len(enabled) == 1
        assert len(disabled) == 1
        conn.close()


def test_get_profile_mods():
    """get_profile_mods should return mods for a profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        profile = create_profile(conn, "test")
        # Manually insert some profile mods
        conn.execute(
            "INSERT INTO profile_mods (profile_id, mod_path, enabled) VALUES (?, ?, ?)",
            (profile.id, "test.package", 1),
        )
        conn.commit()

        mods = get_profile_mods(conn, profile.id)

        assert len(mods) == 1
        assert mods[0].mod_path == "test.package"
        assert mods[0].enabled is True
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_profiles.py::test_save_profile_snapshot -v`

Expected: FAIL - function not defined

**Step 3: Write minimal implementation**

Add to `s4lt/organize/profiles.py`:

```python
from pathlib import Path


@dataclass
class ProfileMod:
    """A mod's state in a profile."""
    mod_path: str
    enabled: bool


def save_profile_snapshot(
    conn: sqlite3.Connection,
    profile_id: int,
    mods_path: Path,
) -> int:
    """Save current mod states to a profile.

    Scans the mods folder for all .package and .package.disabled files
    and records their enabled/disabled state.

    Args:
        conn: Database connection
        profile_id: ID of the profile to save to
        mods_path: Path to the Mods folder

    Returns:
        Number of mods saved
    """
    # Clear existing mods for this profile
    conn.execute("DELETE FROM profile_mods WHERE profile_id = ?", (profile_id,))

    # Find all mods (enabled and disabled)
    enabled_mods = list(mods_path.rglob("*.package"))
    disabled_mods = list(mods_path.rglob("*.package.disabled"))

    count = 0
    for mod in enabled_mods:
        rel_path = str(mod.relative_to(mods_path))
        conn.execute(
            "INSERT INTO profile_mods (profile_id, mod_path, enabled) VALUES (?, ?, 1)",
            (profile_id, rel_path),
        )
        count += 1

    for mod in disabled_mods:
        rel_path = str(mod.relative_to(mods_path))
        conn.execute(
            "INSERT INTO profile_mods (profile_id, mod_path, enabled) VALUES (?, ?, 0)",
            (profile_id, rel_path),
        )
        count += 1

    conn.commit()
    return count


def get_profile_mods(conn: sqlite3.Connection, profile_id: int) -> list[ProfileMod]:
    """Get all mods for a profile.

    Args:
        conn: Database connection
        profile_id: ID of the profile

    Returns:
        List of ProfileMod entries
    """
    cursor = conn.execute(
        "SELECT mod_path, enabled FROM profile_mods WHERE profile_id = ?",
        (profile_id,),
    )
    return [
        ProfileMod(mod_path=row[0], enabled=bool(row[1]))
        for row in cursor.fetchall()
    ]
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_profiles.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/profiles.py tests/organize/test_profiles.py
git commit -m "feat(organize): add profile snapshot and mod retrieval"
```

---

## Task 8: Switch profile function

**Files:**
- Modify: `s4lt/organize/profiles.py`
- Modify: `tests/organize/test_profiles.py`

**Step 1: Write the failing test**

Add to `tests/organize/test_profiles.py`:

```python
from s4lt.organize.profiles import switch_profile, SwitchResult


def test_switch_profile_enables_and_disables():
    """switch_profile should apply profile state to filesystem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        # Create initial state: one enabled, one disabled
        (mods_path / "a.package").write_bytes(b"DBPF")
        (mods_path / "b.package.disabled").write_bytes(b"DBPF")

        # Save as profile
        profile = create_profile(conn, "test")
        save_profile_snapshot(conn, profile.id, mods_path)

        # Now flip the states
        (mods_path / "a.package").rename(mods_path / "a.package.disabled")
        (mods_path / "b.package.disabled").rename(mods_path / "b.package")

        # Switch back to profile
        result = switch_profile(conn, "test", mods_path)

        # Should restore original state
        assert (mods_path / "a.package").exists()
        assert (mods_path / "b.package.disabled").exists()
        assert result.enabled == 1
        assert result.disabled == 1
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_profiles.py::test_switch_profile_enables_and_disables -v`

Expected: FAIL - function not defined

**Step 3: Write minimal implementation**

Add to `s4lt/organize/profiles.py`:

```python
from s4lt.organize.toggle import enable_mod, disable_mod


@dataclass
class SwitchResult:
    """Result of switching profiles."""
    enabled: int
    disabled: int


def switch_profile(
    conn: sqlite3.Connection,
    name: str,
    mods_path: Path,
) -> SwitchResult:
    """Switch to a profile by applying its mod states.

    Args:
        conn: Database connection
        name: Profile name to switch to
        mods_path: Path to the Mods folder

    Returns:
        SwitchResult with counts of enabled/disabled mods

    Raises:
        ProfileNotFoundError: If profile doesn't exist
    """
    profile = get_profile(conn, name)
    if profile is None:
        raise ProfileNotFoundError(f"Profile '{name}' not found")

    profile_mods = get_profile_mods(conn, profile.id)
    enabled_count = 0
    disabled_count = 0

    for pm in profile_mods:
        # Determine current file path (could be .package or .package.disabled)
        enabled_path = mods_path / pm.mod_path
        if pm.mod_path.endswith(".disabled"):
            # Profile has it as disabled, find current path
            base_path = pm.mod_path[:-9]  # Remove .disabled
            current_enabled = mods_path / base_path
            current_disabled = mods_path / pm.mod_path
        else:
            current_enabled = mods_path / pm.mod_path
            current_disabled = mods_path / (pm.mod_path + ".disabled")

        if pm.enabled:
            # Should be enabled
            if current_disabled.exists():
                enable_mod(current_disabled)
                enabled_count += 1
        else:
            # Should be disabled
            if current_enabled.exists():
                disable_mod(current_enabled)
                disabled_count += 1

    return SwitchResult(enabled=enabled_count, disabled=disabled_count)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_profiles.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/profiles.py tests/organize/test_profiles.py
git commit -m "feat(organize): add switch_profile function"
```

---

## Task 9: Vanilla mode toggle

**Files:**
- Create: `s4lt/organize/vanilla.py`
- Create: `tests/organize/test_vanilla.py`

**Step 1: Write the failing test**

Create `tests/organize/test_vanilla.py`:

```python
"""Tests for vanilla mode toggle."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode
from s4lt.organize.profiles import get_profile


def test_toggle_vanilla_disables_all():
    """First toggle_vanilla should disable all mods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package").write_bytes(b"DBPF")
        (mods_path / "b.package").write_bytes(b"DBPF")

        result = toggle_vanilla(conn, mods_path)

        assert result.is_vanilla is True
        assert result.mods_changed == 2
        assert (mods_path / "a.package.disabled").exists()
        assert (mods_path / "b.package.disabled").exists()
        # Pre-vanilla profile should exist
        assert get_profile(conn, "_pre_vanilla") is not None
        conn.close()


def test_toggle_vanilla_restores():
    """Second toggle_vanilla should restore previous state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package").write_bytes(b"DBPF")
        (mods_path / "b.package.disabled").write_bytes(b"DBPF")

        # First toggle (enter vanilla)
        toggle_vanilla(conn, mods_path)
        # Second toggle (exit vanilla)
        result = toggle_vanilla(conn, mods_path)

        assert result.is_vanilla is False
        assert (mods_path / "a.package").exists()
        assert (mods_path / "b.package.disabled").exists()
        # Pre-vanilla profile should be deleted
        assert get_profile(conn, "_pre_vanilla") is None
        conn.close()


def test_is_vanilla_mode():
    """is_vanilla_mode should detect vanilla state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package").write_bytes(b"DBPF")

        assert is_vanilla_mode(conn) is False

        toggle_vanilla(conn, mods_path)
        assert is_vanilla_mode(conn) is True

        toggle_vanilla(conn, mods_path)
        assert is_vanilla_mode(conn) is False
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_vanilla.py -v`

Expected: FAIL - module not found

**Step 3: Write minimal implementation**

Create `s4lt/organize/vanilla.py`:

```python
"""Vanilla mode toggle - disable/restore all mods."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from s4lt.organize.profiles import (
    create_profile,
    get_profile,
    delete_profile,
    save_profile_snapshot,
    switch_profile,
)
from s4lt.organize.toggle import disable_mod


PRE_VANILLA_PROFILE = "_pre_vanilla"


@dataclass
class VanillaResult:
    """Result of vanilla mode toggle."""
    is_vanilla: bool
    mods_changed: int


def is_vanilla_mode(conn: sqlite3.Connection) -> bool:
    """Check if currently in vanilla mode.

    Vanilla mode is detected by the existence of the _pre_vanilla profile.

    Args:
        conn: Database connection

    Returns:
        True if in vanilla mode
    """
    return get_profile(conn, PRE_VANILLA_PROFILE) is not None


def toggle_vanilla(conn: sqlite3.Connection, mods_path: Path) -> VanillaResult:
    """Toggle vanilla mode.

    First call: Save current state and disable all mods.
    Second call: Restore previous state and delete backup.

    Args:
        conn: Database connection
        mods_path: Path to the Mods folder

    Returns:
        VanillaResult indicating new state and mods changed
    """
    if is_vanilla_mode(conn):
        # Exit vanilla mode - restore previous state
        result = switch_profile(conn, PRE_VANILLA_PROFILE, mods_path)
        delete_profile(conn, PRE_VANILLA_PROFILE)
        return VanillaResult(
            is_vanilla=False,
            mods_changed=result.enabled + result.disabled,
        )
    else:
        # Enter vanilla mode - save state and disable all
        profile = create_profile(conn, PRE_VANILLA_PROFILE, is_auto=True)
        save_profile_snapshot(conn, profile.id, mods_path)

        # Disable all enabled mods
        enabled_mods = list(mods_path.rglob("*.package"))
        count = 0
        for mod in enabled_mods:
            if disable_mod(mod):
                count += 1

        return VanillaResult(is_vanilla=True, mods_changed=count)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_vanilla.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/vanilla.py tests/organize/test_vanilla.py
git commit -m "feat(organize): add vanilla mode toggle"
```

---

## Task 10: Creator extraction

**Files:**
- Create: `s4lt/organize/sorter.py`
- Create: `tests/organize/test_sorter.py`

**Step 1: Write the failing test**

Create `tests/organize/test_sorter.py`:

```python
"""Tests for mod sorter."""

from s4lt.organize.sorter import extract_creator, normalize_creator


def test_extract_creator_underscore():
    """extract_creator should parse underscore prefix."""
    assert extract_creator("SimsyCreator_CASHair.package") == "Simsycreator"


def test_extract_creator_ts4_prefix():
    """extract_creator should parse TS4 prefix."""
    assert extract_creator("TS4-Bobby-Dress.package") == "Bobby"
    assert extract_creator("TS4_Bobby_Dress.package") == "Bobby"


def test_extract_creator_dash():
    """extract_creator should parse dash prefix."""
    assert extract_creator("Creator-ModName.package") == "Creator"


def test_extract_creator_unknown():
    """extract_creator should return _Uncategorized for unknown patterns."""
    assert extract_creator("randomfile.package") == "_Uncategorized"


def test_normalize_creator():
    """normalize_creator should title case."""
    assert normalize_creator("SIMSY") == "Simsy"
    assert normalize_creator("simsy") == "Simsy"
    assert normalize_creator("SimsyCreator") == "Simsycreator"
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_sorter.py -v`

Expected: FAIL - module not found

**Step 3: Write minimal implementation**

Create `s4lt/organize/sorter.py`:

```python
"""Mod sorting and organization."""

import re
from pathlib import Path


def normalize_creator(name: str) -> str:
    """Normalize creator name for consistent grouping.

    Args:
        name: Raw creator name

    Returns:
        Normalized name (title case)
    """
    return name.title()


def extract_creator(filename: str) -> str:
    """Extract creator name from mod filename.

    Parses common naming conventions:
    - SimsyCreator_CASHair.package -> Simsycreator
    - TS4-Bobby-Dress.package -> Bobby
    - Creator-ModName.package -> Creator

    Args:
        filename: Mod filename

    Returns:
        Creator name or "_Uncategorized"
    """
    patterns = [
        r"^TS4[-_]([A-Za-z0-9]+)[-_]",  # TS4-Bobby-Dress, TS4_Bobby_Dress
        r"^([A-Za-z0-9]+)_",             # SimsyCreator_Hair
        r"^([A-Za-z0-9]+)-",             # Creator-ModName
    ]

    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return normalize_creator(match.group(1))

    return "_Uncategorized"
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_sorter.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/sorter.py tests/organize/test_sorter.py
git commit -m "feat(organize): add creator extraction from filenames"
```

---

## Task 11: Organize by type function

**Files:**
- Modify: `s4lt/organize/sorter.py`
- Modify: `tests/organize/test_sorter.py`

**Step 1: Write the failing test**

Add to `tests/organize/test_sorter.py`:

```python
import tempfile
from pathlib import Path
from dataclasses import dataclass

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource
from s4lt.organize.sorter import organize_by_type, MoveOp
from s4lt.organize.categorizer import ModCategory


def test_organize_by_type_dry_run():
    """organize_by_type dry run should not move files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "cas.package"
        mod_file.write_bytes(b"DBPF")

        # Add to DB with CAS resources
        mod_id = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)

        result = organize_by_type(conn, mods_path, dry_run=True)

        # File should NOT move in dry run
        assert mod_file.exists()
        assert len(result.moves) == 1
        assert result.moves[0].target == mods_path / "CAS" / "cas.package"
        conn.close()


def test_organize_by_type_moves_files():
    """organize_by_type should move files to category folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "cas.package"
        mod_file.write_bytes(b"DBPF")

        mod_id = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)

        result = organize_by_type(conn, mods_path, dry_run=False)

        # File should move
        assert not mod_file.exists()
        assert (mods_path / "CAS" / "cas.package").exists()
        assert len(result.moves) == 1
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_sorter.py::test_organize_by_type_dry_run -v`

Expected: FAIL - function not defined

**Step 3: Write minimal implementation**

Add to `s4lt/organize/sorter.py`:

```python
import sqlite3
from dataclasses import dataclass

from s4lt.organize.categorizer import categorize_mod, ModCategory
from s4lt.db.operations import get_all_mods


@dataclass
class MoveOp:
    """A file move operation."""
    source: Path
    target: Path


@dataclass
class OrganizeResult:
    """Result of organize operation."""
    moves: list[MoveOp]
    executed: bool


def organize_by_type(
    conn: sqlite3.Connection,
    mods_path: Path,
    dry_run: bool = True,
) -> OrganizeResult:
    """Organize mods into category subfolders.

    Args:
        conn: Database connection
        mods_path: Path to the Mods folder
        dry_run: If True, don't actually move files

    Returns:
        OrganizeResult with list of moves
    """
    moves = []
    mods = get_all_mods(conn)

    for mod in mods:
        mod_path = mods_path / mod["path"]
        if not mod_path.exists():
            continue

        # Get or compute category
        category = categorize_mod(conn, mod["id"])
        target_dir = mods_path / category.value

        # Skip if already in correct folder
        if mod_path.parent == target_dir:
            continue

        target_path = target_dir / mod_path.name
        moves.append(MoveOp(source=mod_path, target=target_path))

    if not dry_run:
        for move in moves:
            move.target.parent.mkdir(parents=True, exist_ok=True)
            move.source.rename(move.target)
            # Update path in database
            new_rel_path = str(move.target.relative_to(mods_path))
            conn.execute(
                "UPDATE mods SET path = ? WHERE path = ?",
                (new_rel_path, str(move.source.relative_to(mods_path))),
            )
        conn.commit()

    return OrganizeResult(moves=moves, executed=not dry_run)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_sorter.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/sorter.py tests/organize/test_sorter.py
git commit -m "feat(organize): add organize_by_type function"
```

---

## Task 12: Organize by creator function

**Files:**
- Modify: `s4lt/organize/sorter.py`
- Modify: `tests/organize/test_sorter.py`

**Step 1: Write the failing test**

Add to `tests/organize/test_sorter.py`:

```python
from s4lt.organize.sorter import organize_by_creator


def test_organize_by_creator_moves_files():
    """organize_by_creator should move files to creator folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "SimsyCreator_Hair.package"
        mod_file.write_bytes(b"DBPF")

        upsert_mod(conn, "SimsyCreator_Hair.package", "SimsyCreator_Hair.package", 100, 1.0, "hash", 1)

        result = organize_by_creator(conn, mods_path, dry_run=False)

        assert not mod_file.exists()
        assert (mods_path / "Simsycreator" / "SimsyCreator_Hair.package").exists()
        assert len(result.moves) == 1
        conn.close()


def test_organize_by_creator_uncategorized():
    """organize_by_creator should put unknown to _Uncategorized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "random.package"
        mod_file.write_bytes(b"DBPF")

        upsert_mod(conn, "random.package", "random.package", 100, 1.0, "hash", 1)

        result = organize_by_creator(conn, mods_path, dry_run=False)

        assert (mods_path / "_Uncategorized" / "random.package").exists()
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_sorter.py::test_organize_by_creator_moves_files -v`

Expected: FAIL - function not defined

**Step 3: Write minimal implementation**

Add to `s4lt/organize/sorter.py`:

```python
def organize_by_creator(
    conn: sqlite3.Connection,
    mods_path: Path,
    dry_run: bool = True,
) -> OrganizeResult:
    """Organize mods into creator subfolders.

    Args:
        conn: Database connection
        mods_path: Path to the Mods folder
        dry_run: If True, don't actually move files

    Returns:
        OrganizeResult with list of moves
    """
    moves = []
    mods = get_all_mods(conn)

    for mod in mods:
        mod_path = mods_path / mod["path"]
        if not mod_path.exists():
            continue

        creator = extract_creator(mod["filename"])
        target_dir = mods_path / creator

        # Skip if already in correct folder
        if mod_path.parent == target_dir:
            continue

        target_path = target_dir / mod_path.name
        moves.append(MoveOp(source=mod_path, target=target_path))

    if not dry_run:
        for move in moves:
            move.target.parent.mkdir(parents=True, exist_ok=True)
            move.source.rename(move.target)
            # Update path in database
            new_rel_path = str(move.target.relative_to(mods_path))
            conn.execute(
                "UPDATE mods SET path = ? WHERE path = ?",
                (new_rel_path, str(move.source.relative_to(mods_path))),
            )
        conn.commit()

    return OrganizeResult(moves=moves, executed=not dry_run)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_sorter.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/sorter.py tests/organize/test_sorter.py
git commit -m "feat(organize): add organize_by_creator function"
```

---

## Task 13: Batch enable/disable

**Files:**
- Create: `s4lt/organize/batch.py`
- Create: `tests/organize/test_batch.py`

**Step 1: Write the failing test**

Create `tests/organize/test_batch.py`:

```python
"""Tests for batch operations."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource
from s4lt.organize.batch import batch_enable, batch_disable, BatchResult
from s4lt.organize.categorizer import ModCategory


def test_batch_disable_by_pattern():
    """batch_disable should disable mods matching glob pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "CAS").mkdir()
        (mods_path / "CAS" / "a.package").write_bytes(b"DBPF")
        (mods_path / "CAS" / "b.package").write_bytes(b"DBPF")
        (mods_path / "other.package").write_bytes(b"DBPF")

        result = batch_disable(mods_path, pattern="CAS/*")

        assert result.matched == 2
        assert result.changed == 2
        assert (mods_path / "CAS" / "a.package.disabled").exists()
        assert (mods_path / "CAS" / "b.package.disabled").exists()
        assert (mods_path / "other.package").exists()  # Not matched


def test_batch_enable_by_pattern():
    """batch_enable should enable mods matching glob pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package.disabled").write_bytes(b"DBPF")
        (mods_path / "b.package.disabled").write_bytes(b"DBPF")

        result = batch_enable(mods_path, pattern="*.disabled")

        assert result.matched == 2
        assert result.changed == 2
        assert (mods_path / "a.package").exists()
        assert (mods_path / "b.package").exists()


def test_batch_disable_by_category():
    """batch_disable should disable mods by category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "cas.package").write_bytes(b"DBPF")
        (mods_path / "script.package").write_bytes(b"DBPF")

        # Add mods with categories
        mod_id1 = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "h1", 1)
        insert_resource(conn, mod_id1, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)
        mod_id2 = upsert_mod(conn, "script.package", "script.package", 100, 1.0, "h2", 1)
        insert_resource(conn, mod_id2, 0x9C07855E, 0, 1, "Script", None, 10, 20)

        result = batch_disable(mods_path, category=ModCategory.CAS, conn=conn)

        assert result.matched == 1
        assert result.changed == 1
        assert (mods_path / "cas.package.disabled").exists()
        assert (mods_path / "script.package").exists()  # Not CAS
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/organize/test_batch.py -v`

Expected: FAIL - module not found

**Step 3: Write minimal implementation**

Create `s4lt/organize/batch.py`:

```python
"""Batch enable/disable operations."""

import fnmatch
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from s4lt.organize.toggle import enable_mod, disable_mod
from s4lt.organize.categorizer import categorize_mod, ModCategory
from s4lt.db.operations import get_all_mods


@dataclass
class BatchResult:
    """Result of a batch operation."""
    matched: int
    changed: int


def batch_disable(
    mods_path: Path,
    pattern: str | None = None,
    category: ModCategory | None = None,
    creator: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> BatchResult:
    """Disable multiple mods by filter.

    Args:
        mods_path: Path to the Mods folder
        pattern: Glob pattern to match (e.g., "CAS/*")
        category: Category to filter by
        creator: Creator name to filter by
        conn: Database connection (required for category filter)

    Returns:
        BatchResult with counts
    """
    if pattern:
        # Use glob pattern matching
        matched_files = list(mods_path.glob(pattern))
        # Filter to only .package files
        matched_files = [f for f in matched_files if f.suffix == ".package"]
    else:
        matched_files = list(mods_path.rglob("*.package"))

    if category and conn:
        # Filter by category
        mods = {m["path"]: m for m in get_all_mods(conn)}
        filtered = []
        for f in matched_files:
            rel_path = str(f.relative_to(mods_path))
            if rel_path in mods:
                mod = mods[rel_path]
                mod_category = categorize_mod(conn, mod["id"])
                if mod_category == category:
                    filtered.append(f)
        matched_files = filtered

    matched = len(matched_files)
    changed = 0
    for f in matched_files:
        if disable_mod(f):
            changed += 1

    return BatchResult(matched=matched, changed=changed)


def batch_enable(
    mods_path: Path,
    pattern: str | None = None,
    category: ModCategory | None = None,
    creator: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> BatchResult:
    """Enable multiple mods by filter.

    Args:
        mods_path: Path to the Mods folder
        pattern: Glob pattern to match (e.g., "*.disabled")
        category: Category to filter by
        creator: Creator name to filter by
        conn: Database connection (required for category filter)

    Returns:
        BatchResult with counts
    """
    if pattern:
        matched_files = list(mods_path.glob(pattern))
        matched_files = [f for f in matched_files if f.suffix == ".disabled"]
    else:
        matched_files = list(mods_path.rglob("*.disabled"))

    matched = len(matched_files)
    changed = 0
    for f in matched_files:
        if enable_mod(f):
            changed += 1

    return BatchResult(matched=matched, changed=changed)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/organize/test_batch.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add s4lt/organize/batch.py tests/organize/test_batch.py
git commit -m "feat(organize): add batch enable/disable operations"
```

---

## Task 14: CLI organize command

**Files:**
- Create: `s4lt/cli/commands/organize.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Create the command**

Create `s4lt/cli/commands/organize.py`:

```python
"""Organize command implementation."""

import click
from pathlib import Path

from s4lt.cli.output import console
from s4lt.config.settings import get_settings
from s4lt.db.schema import get_connection, init_db


def run_organize(by_type: bool, by_creator: bool, yes: bool) -> None:
    """Run the organize command."""
    from s4lt.organize.sorter import organize_by_type, organize_by_creator

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        if by_type:
            result = organize_by_type(conn, mods_path, dry_run=True)
            action = "type"
        elif by_creator:
            result = organize_by_creator(conn, mods_path, dry_run=True)
            action = "creator"
        else:
            console.print("[red]Error: Specify --by-type or --by-creator[/red]")
            return

        if not result.moves:
            console.print("[green]All mods are already organized.[/green]")
            return

        # Show preview
        console.print(f"\n[bold]Will organize {len(result.moves)} mods by {action}:[/bold]\n")

        # Group by target folder
        by_folder: dict[Path, list] = {}
        for move in result.moves:
            folder = move.target.parent
            if folder not in by_folder:
                by_folder[folder] = []
            by_folder[folder].append(move)

        for folder, moves in sorted(by_folder.items()):
            console.print(f"  → {folder.name}/: {len(moves)} mods")

        if not yes:
            console.print()
            if not click.confirm("Proceed?"):
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # Execute
        if by_type:
            result = organize_by_type(conn, mods_path, dry_run=False)
        else:
            result = organize_by_creator(conn, mods_path, dry_run=False)

        console.print(f"\n[green]Organized {len(result.moves)} mods.[/green]")
    finally:
        conn.close()
```

**Step 2: Add to main CLI**

Add to `s4lt/cli/main.py` after the `ea` group:

```python
@cli.command()
@click.option("--by-type", is_flag=True, help="Sort by mod category")
@click.option("--by-creator", is_flag=True, help="Sort by creator name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def organize(by_type: bool, by_creator: bool, yes: bool):
    """Auto-sort mods into subfolders."""
    from s4lt.cli.commands.organize import run_organize
    run_organize(by_type=by_type, by_creator=by_creator, yes=yes)
```

**Step 3: Verify import works**

Run: `.venv/bin/python -c "from s4lt.cli.main import cli; print('OK')"`

Expected: OK

**Step 4: Commit**

```bash
git add s4lt/cli/commands/organize.py s4lt/cli/main.py
git commit -m "feat(cli): add organize command"
```

---

## Task 15: CLI enable/disable/vanilla commands

**Files:**
- Create: `s4lt/cli/commands/toggle.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Create the commands**

Create `s4lt/cli/commands/toggle.py`:

```python
"""Enable/disable/vanilla command implementations."""

from pathlib import Path

from s4lt.cli.output import console
from s4lt.config.settings import get_settings
from s4lt.db.schema import get_connection, init_db


def run_enable(mod: str | None, category: str | None, creator: str | None) -> None:
    """Run the enable command."""
    from s4lt.organize.batch import batch_enable
    from s4lt.organize.toggle import enable_mod
    from s4lt.organize.categorizer import ModCategory

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"

    if mod and not category and not creator:
        # Single mod enable
        mod_path = mods_path / mod
        if not mod_path.exists():
            # Try with .disabled suffix
            mod_path = mods_path / (mod + ".disabled")
        if not mod_path.exists():
            console.print(f"[red]Mod not found: {mod}[/red]")
            return

        if enable_mod(mod_path):
            console.print(f"[green]Enabled: {mod_path.name}[/green]")
        else:
            console.print(f"[yellow]Already enabled: {mod_path.name}[/yellow]")
    else:
        # Batch enable
        conn = None
        cat = None
        if category:
            init_db(db_path)
            conn = get_connection(db_path)
            cat = ModCategory(category)

        result = batch_enable(
            mods_path,
            pattern=mod,
            category=cat,
            creator=creator,
            conn=conn,
        )

        if conn:
            conn.close()

        console.print(f"[green]Enabled {result.changed} of {result.matched} mods.[/green]")


def run_disable(mod: str | None, category: str | None, creator: str | None) -> None:
    """Run the disable command."""
    from s4lt.organize.batch import batch_disable
    from s4lt.organize.toggle import disable_mod
    from s4lt.organize.categorizer import ModCategory

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"

    if mod and not category and not creator:
        # Single mod disable
        mod_path = mods_path / mod
        if not mod_path.exists():
            console.print(f"[red]Mod not found: {mod}[/red]")
            return

        if disable_mod(mod_path):
            console.print(f"[green]Disabled: {mod_path.name}[/green]")
        else:
            console.print(f"[yellow]Already disabled: {mod_path.name}[/yellow]")
    else:
        # Batch disable
        conn = None
        cat = None
        if category:
            init_db(db_path)
            conn = get_connection(db_path)
            cat = ModCategory(category)

        result = batch_disable(
            mods_path,
            pattern=mod,
            category=cat,
            creator=creator,
            conn=conn,
        )

        if conn:
            conn.close()

        console.print(f"[green]Disabled {result.changed} of {result.matched} mods.[/green]")


def run_vanilla() -> None:
    """Run the vanilla command."""
    from s4lt.organize.vanilla import toggle_vanilla

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        result = toggle_vanilla(conn, mods_path)

        if result.is_vanilla:
            console.print(f"[green]Vanilla mode enabled. Disabled {result.mods_changed} mods.[/green]")
        else:
            console.print(f"[green]Restored from vanilla mode. Changed {result.mods_changed} mods.[/green]")
    finally:
        conn.close()
```

**Step 2: Add to main CLI**

Add to `s4lt/cli/main.py`:

```python
CATEGORIES = ["CAS", "BuildBuy", "Script", "Tuning", "Override", "Gameplay"]


@cli.command()
@click.argument("mod", required=False)
@click.option("--category", type=click.Choice(CATEGORIES), help="Filter by category")
@click.option("--creator", help="Filter by creator name")
def enable(mod: str | None, category: str | None, creator: str | None):
    """Enable mod(s)."""
    from s4lt.cli.commands.toggle import run_enable
    run_enable(mod=mod, category=category, creator=creator)


@cli.command()
@click.argument("mod", required=False)
@click.option("--category", type=click.Choice(CATEGORIES), help="Filter by category")
@click.option("--creator", help="Filter by creator name")
def disable(mod: str | None, category: str | None, creator: str | None):
    """Disable mod(s)."""
    from s4lt.cli.commands.toggle import run_disable
    run_disable(mod=mod, category=category, creator=creator)


@cli.command()
def vanilla():
    """Toggle vanilla mode (disable/restore all mods)."""
    from s4lt.cli.commands.toggle import run_vanilla
    run_vanilla()
```

**Step 3: Verify CLI**

Run: `.venv/bin/python -m s4lt.cli.main --help`

Expected: Should show enable, disable, vanilla commands

**Step 4: Commit**

```bash
git add s4lt/cli/commands/toggle.py s4lt/cli/main.py
git commit -m "feat(cli): add enable, disable, vanilla commands"
```

---

## Task 16: CLI profile commands

**Files:**
- Create: `s4lt/cli/commands/profile.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Create the commands**

Create `s4lt/cli/commands/profile.py`:

```python
"""Profile command implementations."""

from datetime import datetime
from pathlib import Path

from s4lt.cli.output import console
from s4lt.config.settings import get_settings
from s4lt.db.schema import get_connection, init_db


def run_profile_list() -> None:
    """List all profiles."""
    from s4lt.organize.profiles import list_profiles

    settings = get_settings()
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        profiles = list_profiles(conn)

        if not profiles:
            console.print("[yellow]No profiles found.[/yellow]")
            return

        console.print("\n[bold]Profiles:[/bold]\n")
        for p in profiles:
            created = datetime.fromtimestamp(p.created_at).strftime("%Y-%m-%d %H:%M")
            auto_tag = " [dim](auto)[/dim]" if p.is_auto else ""
            console.print(f"  • {p.name}{auto_tag} - created {created}")
    finally:
        conn.close()


def run_profile_create(name: str) -> None:
    """Create a new profile."""
    from s4lt.organize.profiles import create_profile, save_profile_snapshot
    from s4lt.organize.exceptions import ProfileExistsError

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        profile = create_profile(conn, name)
        count = save_profile_snapshot(conn, profile.id, mods_path)
        console.print(f"[green]Created profile '{name}' with {count} mods.[/green]")
    except ProfileExistsError:
        console.print(f"[red]Profile '{name}' already exists.[/red]")
    finally:
        conn.close()


def run_profile_switch(name: str) -> None:
    """Switch to a profile."""
    from s4lt.organize.profiles import switch_profile
    from s4lt.organize.exceptions import ProfileNotFoundError

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        result = switch_profile(conn, name, mods_path)
        console.print(
            f"[green]Switched to '{name}': "
            f"enabled {result.enabled}, disabled {result.disabled}[/green]"
        )
    except ProfileNotFoundError:
        console.print(f"[red]Profile '{name}' not found.[/red]")
    finally:
        conn.close()


def run_profile_delete(name: str) -> None:
    """Delete a profile."""
    from s4lt.organize.profiles import delete_profile
    from s4lt.organize.exceptions import ProfileNotFoundError

    settings = get_settings()
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        delete_profile(conn, name)
        console.print(f"[green]Deleted profile '{name}'.[/green]")
    except ProfileNotFoundError:
        console.print(f"[red]Profile '{name}' not found.[/red]")
    finally:
        conn.close()
```

**Step 2: Add to main CLI**

Add to `s4lt/cli/main.py`:

```python
@cli.group()
def profile():
    """Manage mod profiles."""
    pass


@profile.command("list")
def profile_list():
    """Show all profiles."""
    from s4lt.cli.commands.profile import run_profile_list
    run_profile_list()


@profile.command("create")
@click.argument("name")
def profile_create(name: str):
    """Save current config as profile."""
    from s4lt.cli.commands.profile import run_profile_create
    run_profile_create(name)


@profile.command("switch")
@click.argument("name")
def profile_switch(name: str):
    """Switch to profile."""
    from s4lt.cli.commands.profile import run_profile_switch
    run_profile_switch(name)


@profile.command("delete")
@click.argument("name")
def profile_delete(name: str):
    """Delete profile."""
    from s4lt.cli.commands.profile import run_profile_delete
    run_profile_delete(name)
```

**Step 3: Verify CLI**

Run: `.venv/bin/python -m s4lt.cli.main profile --help`

Expected: Should show list, create, switch, delete subcommands

**Step 4: Commit**

```bash
git add s4lt/cli/commands/profile.py s4lt/cli/main.py
git commit -m "feat(cli): add profile commands"
```

---

## Task 17: Update module exports

**Files:**
- Modify: `s4lt/organize/__init__.py`

**Step 1: Update exports**

Update `s4lt/organize/__init__.py`:

```python
"""Mod organization: categorization, profiles, and sorting."""

from s4lt.organize.categorizer import ModCategory, categorize_mod
from s4lt.organize.toggle import enable_mod, disable_mod, is_enabled
from s4lt.organize.profiles import (
    Profile,
    ProfileMod,
    SwitchResult,
    create_profile,
    get_profile,
    list_profiles,
    delete_profile,
    save_profile_snapshot,
    get_profile_mods,
    switch_profile,
)
from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode, VanillaResult
from s4lt.organize.sorter import (
    MoveOp,
    OrganizeResult,
    organize_by_type,
    organize_by_creator,
    extract_creator,
)
from s4lt.organize.batch import batch_enable, batch_disable, BatchResult
from s4lt.organize.exceptions import (
    OrganizeError,
    ProfileNotFoundError,
    ProfileExistsError,
    ModNotFoundError,
)

__all__ = [
    # Categorization
    "ModCategory",
    "categorize_mod",
    # Toggle
    "enable_mod",
    "disable_mod",
    "is_enabled",
    # Profiles
    "Profile",
    "ProfileMod",
    "SwitchResult",
    "create_profile",
    "get_profile",
    "list_profiles",
    "delete_profile",
    "save_profile_snapshot",
    "get_profile_mods",
    "switch_profile",
    # Vanilla
    "toggle_vanilla",
    "is_vanilla_mode",
    "VanillaResult",
    # Sorter
    "MoveOp",
    "OrganizeResult",
    "organize_by_type",
    "organize_by_creator",
    "extract_creator",
    # Batch
    "batch_enable",
    "batch_disable",
    "BatchResult",
    # Exceptions
    "OrganizeError",
    "ProfileNotFoundError",
    "ProfileExistsError",
    "ModNotFoundError",
]
```

**Step 2: Verify imports**

Run: `.venv/bin/python -c "from s4lt.organize import ModCategory, toggle_vanilla; print('OK')"`

Expected: OK

**Step 3: Commit**

```bash
git add s4lt/organize/__init__.py
git commit -m "feat(organize): export all public APIs from module"
```

---

## Task 18: Run all tests

**Step 1: Run full test suite**

Run: `.venv/bin/pytest tests/ -v --tb=short`

Expected: All tests pass

**Step 2: Check test count**

Run: `.venv/bin/pytest tests/ --collect-only | tail -5`

Expected: Should show ~130+ tests collected

**Step 3: Commit any fixes if needed**

If tests fail, fix and commit.

---

## Task 19: Update version to 0.4.0

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update version**

In `pyproject.toml`, change version to `0.4.0`:

```toml
version = "0.4.0"
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.4.0"
```

---

## Task 20: Final integration test

**Step 1: Manual CLI test**

Run these commands to verify:

```bash
# Check help
.venv/bin/python -m s4lt.cli.main --help

# Check organize help
.venv/bin/python -m s4lt.cli.main organize --help

# Check profile help
.venv/bin/python -m s4lt.cli.main profile --help

# Check enable/disable help
.venv/bin/python -m s4lt.cli.main enable --help
.venv/bin/python -m s4lt.cli.main disable --help
.venv/bin/python -m s4lt.cli.main vanilla --help
```

**Step 2: Tag release**

```bash
git tag -a v0.4.0 -m "Phase 4: Organization features"
```

---

## Summary

**Total Tasks:** 20
**Estimated New Tests:** ~30
**New Files:** 10
**Modified Files:** 5

**Features Delivered:**
- Auto-categorization by resource type
- Enable/disable with .disabled suffix
- Profile management (create, switch, list, delete)
- Vanilla mode toggle
- Organize by type/creator
- Batch enable/disable operations
- Full CLI integration
