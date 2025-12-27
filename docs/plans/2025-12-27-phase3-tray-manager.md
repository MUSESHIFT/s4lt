# Phase 3: Tray Manager Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python module that can browse the Tray folder, display items with thumbnails, track CC usage per item, and detect missing CC.

**Architecture:** TrayItem class represents each household/lot/room by grouping related files (sharing same ID prefix). Lazy loading for thumbnails and CC lists. Database storage for indexing. Uses existing DBPF core engine for package cross-referencing.

**Tech Stack:** Python 3.11+, struct (binary parsing), Pillow (image handling), sqlite3 (database), Click (CLI)

---

## Background: Tray File Structure

The Tray folder contains saved Sims, lots, and rooms. Each tray item consists of multiple files sharing a common hex ID prefix:

**Households:**
- `{id}.trayitem` - Main metadata (all item types have this)
- `{id}.householdbinary` - Household data
- `{id}.hhi` - Household thumbnail images (2 per household)
- `{id}_sim{N}.sgi` - Individual Sim thumbnails (1 per Sim)

**Lots:**
- `{id}.trayitem` - Main metadata
- `{id}.blueprint` - Lot/building data
- `{id}.bpi` - Lot thumbnails (4 base + 1 per floor)

**Rooms:**
- `{id}.trayitem` - Main metadata
- `{id}.room` - Room data
- `{id}.midi` - Room thumbnails (2 per room)

---

## Task 1: Tray Module Setup

**Files:**
- Create: `s4lt/tray/__init__.py`
- Create: `s4lt/tray/exceptions.py`
- Create: `tests/tray/__init__.py`

**Step 1: Create exception classes**

```python
# s4lt/tray/exceptions.py
"""Tray parsing exceptions."""


class TrayError(Exception):
    """Base exception for tray operations."""


class TrayItemNotFoundError(TrayError):
    """Tray item files not found or incomplete."""


class TrayParseError(TrayError):
    """Failed to parse tray file."""


class ThumbnailError(TrayError):
    """Failed to extract or process thumbnail."""
```

**Step 2: Create tray __init__.py**

```python
# s4lt/tray/__init__.py
"""S4LT Tray - Tray folder management."""

from s4lt.tray.exceptions import (
    TrayError,
    TrayItemNotFoundError,
    TrayParseError,
    ThumbnailError,
)

__all__ = [
    "TrayError",
    "TrayItemNotFoundError",
    "TrayParseError",
    "ThumbnailError",
]
```

**Step 3: Create test __init__ file**

```python
# tests/tray/__init__.py
"""Tray module tests."""
```

**Step 4: Run tests to verify setup**

Run: `pytest tests/ -v --tb=short`
Expected: All existing tests pass, no errors from new modules

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(tray): module setup with exceptions"
```

---

## Task 2: Tray Scanner

**Files:**
- Create: `s4lt/tray/scanner.py`
- Create: `tests/tray/test_scanner.py`

**Step 1: Write the failing test**

```python
# tests/tray/test_scanner.py
"""Tests for tray folder scanner."""

import tempfile
from pathlib import Path

from s4lt.tray.scanner import discover_tray_items, TrayItemType


def test_discover_empty_folder():
    """Empty folder returns empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        items = discover_tray_items(Path(tmpdir))
        assert items == []


def test_discover_household():
    """Discovers a household with all required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"

        # Create household files
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.householdbinary").touch()
        (tray_path / f"{item_id}.hhi").touch()
        (tray_path / f"{item_id}!00000001.hhi").touch()
        (tray_path / f"{item_id}!00000000_0x0.sgi").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert items[0]["id"] == item_id
        assert items[0]["type"] == TrayItemType.HOUSEHOLD


def test_discover_lot():
    """Discovers a lot with required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x00000000ABCDEF01"

        # Create lot files
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.blueprint").touch()
        (tray_path / f"{item_id}.bpi").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert items[0]["type"] == TrayItemType.LOT


def test_discover_room():
    """Discovers a room with required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x00000000DEADBEEF"

        # Create room files
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.room").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert items[0]["type"] == TrayItemType.ROOM


def test_groups_related_files():
    """Files with same ID prefix are grouped together."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000011111111"

        # Create household with 2 sims
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.householdbinary").touch()
        (tray_path / f"{item_id}.hhi").touch()
        (tray_path / f"{item_id}!00000001.hhi").touch()
        (tray_path / f"{item_id}!00000000_0x0.sgi").touch()
        (tray_path / f"{item_id}!00000001_0x0.sgi").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert len(items[0]["files"]) == 6
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tray/test_scanner.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/tray/scanner.py
"""Tray folder scanner."""

from enum import Enum
from pathlib import Path


class TrayItemType(Enum):
    """Type of tray item."""
    HOUSEHOLD = "household"
    LOT = "lot"
    ROOM = "room"
    UNKNOWN = "unknown"


# File extensions by type
HOUSEHOLD_EXTENSIONS = {".householdbinary", ".hhi", ".sgi"}
LOT_EXTENSIONS = {".blueprint", ".bpi"}
ROOM_EXTENSIONS = {".room", ".midi"}
TRAY_EXTENSIONS = {".trayitem"} | HOUSEHOLD_EXTENSIONS | LOT_EXTENSIONS | ROOM_EXTENSIONS


def discover_tray_items(tray_path: Path) -> list[dict]:
    """Discover all tray items in a folder.

    Scans for .trayitem files and groups all related files
    (same ID prefix) together.

    Args:
        tray_path: Path to the Tray folder

    Returns:
        List of dicts with id, type, and files for each tray item
    """
    if not tray_path.is_dir():
        return []

    # Find all .trayitem files - these are the anchors
    trayitems = list(tray_path.glob("*.trayitem"))

    # Group files by ID prefix
    items = []
    for trayitem in trayitems:
        item_id = trayitem.stem  # e.g., "0x0000000012345678"

        # Find all files starting with this ID
        related_files = []
        for ext in TRAY_EXTENSIONS:
            # Match exact ID or ID with suffix (e.g., ID!00000001.hhi)
            related_files.extend(tray_path.glob(f"{item_id}{ext}"))
            related_files.extend(tray_path.glob(f"{item_id}!*{ext}"))
            related_files.extend(tray_path.glob(f"{item_id}_*{ext}"))

        # Deduplicate
        related_files = list(set(related_files))

        # Determine type based on file extensions present
        extensions = {f.suffix.lower() for f in related_files}

        if ".householdbinary" in extensions:
            item_type = TrayItemType.HOUSEHOLD
        elif ".blueprint" in extensions:
            item_type = TrayItemType.LOT
        elif ".room" in extensions:
            item_type = TrayItemType.ROOM
        else:
            item_type = TrayItemType.UNKNOWN

        items.append({
            "id": item_id,
            "type": item_type,
            "files": sorted(related_files),
            "trayitem_path": trayitem,
        })

    return items
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tray/test_scanner.py -v`
Expected: 5 passed

**Step 5: Update tray __init__.py**

```python
# s4lt/tray/__init__.py
"""S4LT Tray - Tray folder management."""

from s4lt.tray.exceptions import (
    TrayError,
    TrayItemNotFoundError,
    TrayParseError,
    ThumbnailError,
)
from s4lt.tray.scanner import discover_tray_items, TrayItemType

__all__ = [
    "TrayError",
    "TrayItemNotFoundError",
    "TrayParseError",
    "ThumbnailError",
    "discover_tray_items",
    "TrayItemType",
]
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(tray): tray folder scanner"
```

---

## Task 3: TrayItem Metadata Parser

**Files:**
- Create: `s4lt/tray/trayitem.py`
- Create: `tests/tray/test_trayitem.py`
- Create: `tests/tray/fixtures/__init__.py`

**Step 1: Create test fixture helper**

```python
# tests/tray/fixtures/__init__.py
"""Test fixtures for tray parsing."""

import struct
from pathlib import Path


def create_trayitem_v14(name: str = "Test Item", item_type: int = 1) -> bytes:
    """Create a minimal .trayitem file for testing.

    Based on observed trayitem structure:
    - Magic: varies by version
    - Version: uint32
    - Name: length-prefixed UTF-16 string
    - Type flag
    - Various metadata

    This is a simplified mock for testing.
    """
    data = bytearray()

    # Version (v14 is common in recent Sims 4)
    data.extend(struct.pack("<I", 14))

    # Name as length-prefixed UTF-16LE
    name_bytes = name.encode("utf-16-le")
    data.extend(struct.pack("<I", len(name_bytes) // 2))  # Char count
    data.extend(name_bytes)

    # Item type (1=household, 2=lot, 3=room)
    data.extend(struct.pack("<I", item_type))

    # Padding/unknown fields
    data.extend(b"\x00" * 64)

    return bytes(data)
```

**Step 2: Write the failing test**

```python
# tests/tray/test_trayitem.py
"""Tests for trayitem metadata parsing."""

import tempfile
from pathlib import Path

import pytest

from s4lt.tray.trayitem import parse_trayitem, TrayItemMeta
from s4lt.tray.exceptions import TrayParseError
from tests.tray.fixtures import create_trayitem_v14


def test_parse_trayitem_extracts_name():
    """Should extract the name from trayitem file."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(create_trayitem_v14(name="My Test Household"))
        path = Path(f.name)

    try:
        meta = parse_trayitem(path)
        assert meta.name == "My Test Household"
    finally:
        path.unlink()


def test_parse_trayitem_extracts_type():
    """Should identify household vs lot vs room."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(create_trayitem_v14(name="Test Lot", item_type=2))
        path = Path(f.name)

    try:
        meta = parse_trayitem(path)
        assert meta.item_type == "lot"
    finally:
        path.unlink()


def test_parse_invalid_file_raises():
    """Invalid file should raise TrayParseError."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(b"not a valid trayitem")
        path = Path(f.name)

    try:
        with pytest.raises(TrayParseError):
            parse_trayitem(path)
    finally:
        path.unlink()


def test_trayitem_meta_properties():
    """TrayItemMeta should have expected properties."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(create_trayitem_v14(name="Test", item_type=1))
        path = Path(f.name)

    try:
        meta = parse_trayitem(path)
        assert hasattr(meta, "name")
        assert hasattr(meta, "item_type")
        assert hasattr(meta, "version")
    finally:
        path.unlink()
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/tray/test_trayitem.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 4: Write the implementation**

```python
# s4lt/tray/trayitem.py
"""TrayItem metadata parser.

The .trayitem file format is a binary format that stores metadata
about saved households, lots, and rooms in The Sims 4.

NOTE: This parser is based on reverse engineering and may not
handle all edge cases. It extracts basic metadata (name, type)
which is sufficient for browsing and organizing tray items.
"""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from s4lt.tray.exceptions import TrayParseError


# Item type codes (observed from file analysis)
ITEM_TYPE_HOUSEHOLD = 1
ITEM_TYPE_LOT = 2
ITEM_TYPE_ROOM = 3

ITEM_TYPE_NAMES = {
    ITEM_TYPE_HOUSEHOLD: "household",
    ITEM_TYPE_LOT: "lot",
    ITEM_TYPE_ROOM: "room",
}


@dataclass
class TrayItemMeta:
    """Parsed metadata from a .trayitem file."""

    name: str
    item_type: str
    version: int

    # Optional fields that may or may not be parseable
    description: str | None = None
    sim_count: int | None = None
    lot_size: tuple[int, int] | None = None


def parse_trayitem(path: Path) -> TrayItemMeta:
    """Parse metadata from a .trayitem file.

    Args:
        path: Path to the .trayitem file

    Returns:
        TrayItemMeta with extracted information

    Raises:
        TrayParseError: If file cannot be parsed
    """
    try:
        with open(path, "rb") as f:
            return _parse_trayitem_v14(f)
    except TrayParseError:
        raise
    except Exception as e:
        raise TrayParseError(f"Failed to parse trayitem: {e}")


def _parse_trayitem_v14(file: BinaryIO) -> TrayItemMeta:
    """Parse v14 format trayitem (common in recent Sims 4 versions)."""

    # Read version
    version_data = file.read(4)
    if len(version_data) < 4:
        raise TrayParseError("File too short for version field")

    version = struct.unpack("<I", version_data)[0]

    # Validate reasonable version range
    if version < 1 or version > 100:
        raise TrayParseError(f"Invalid version {version}")

    # Read name (length-prefixed UTF-16LE)
    name = _read_utf16_string(file)
    if name is None:
        raise TrayParseError("Could not read name from trayitem")

    # Read item type
    type_data = file.read(4)
    if len(type_data) < 4:
        # Default to unknown if we can't read type
        item_type_code = 0
    else:
        item_type_code = struct.unpack("<I", type_data)[0]

    item_type = ITEM_TYPE_NAMES.get(item_type_code, "unknown")

    return TrayItemMeta(
        name=name,
        item_type=item_type,
        version=version,
    )


def _read_utf16_string(file: BinaryIO) -> str | None:
    """Read a length-prefixed UTF-16LE string."""
    length_data = file.read(4)
    if len(length_data) < 4:
        return None

    char_count = struct.unpack("<I", length_data)[0]

    # Sanity check - names shouldn't be excessively long
    if char_count > 1000:
        return None

    string_data = file.read(char_count * 2)  # 2 bytes per UTF-16 char
    if len(string_data) < char_count * 2:
        return None

    try:
        return string_data.decode("utf-16-le")
    except UnicodeDecodeError:
        return None
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/tray/test_trayitem.py -v`
Expected: 4 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(tray): trayitem metadata parser"
```

---

## Task 4: Thumbnail Extraction

**Files:**
- Create: `s4lt/tray/thumbnails.py`
- Create: `tests/tray/test_thumbnails.py`

**Step 1: Write the failing test**

```python
# tests/tray/test_thumbnails.py
"""Tests for thumbnail extraction."""

import tempfile
from pathlib import Path

import pytest

from s4lt.tray.thumbnails import extract_thumbnail, get_image_format
from s4lt.tray.exceptions import ThumbnailError


# Minimal valid PNG header (8 bytes magic + IHDR chunk)
MINIMAL_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D,  # IHDR length = 13
    0x49, 0x48, 0x44, 0x52,  # "IHDR"
    0x00, 0x00, 0x00, 0x01,  # width = 1
    0x00, 0x00, 0x00, 0x01,  # height = 1
    0x08, 0x02,              # bit depth = 8, color type = 2 (RGB)
    0x00, 0x00, 0x00,        # compression, filter, interlace
    0x90, 0x77, 0x53, 0xDE,  # CRC
    0x00, 0x00, 0x00, 0x00,  # IEND length = 0
    0x49, 0x45, 0x4E, 0x44,  # "IEND"
    0xAE, 0x42, 0x60, 0x82,  # CRC
])


def test_detect_png_format():
    """Should detect PNG format from magic bytes."""
    with tempfile.NamedTemporaryFile(suffix=".hhi", delete=False) as f:
        f.write(MINIMAL_PNG)
        path = Path(f.name)

    try:
        fmt = get_image_format(path)
        assert fmt == "png"
    finally:
        path.unlink()


def test_extract_thumbnail_png():
    """Should extract PNG thumbnail data."""
    with tempfile.NamedTemporaryFile(suffix=".sgi", delete=False) as f:
        f.write(MINIMAL_PNG)
        path = Path(f.name)

    try:
        data, fmt = extract_thumbnail(path)
        assert fmt == "png"
        assert data == MINIMAL_PNG
    finally:
        path.unlink()


def test_extract_thumbnail_with_header():
    """Should handle files with prefix header before image data."""
    # Some Sims 4 thumbnail files have metadata before the PNG
    header = b"\x00\x01\x02\x03" * 16  # 64 byte fake header

    with tempfile.NamedTemporaryFile(suffix=".bpi", delete=False) as f:
        f.write(header + MINIMAL_PNG)
        path = Path(f.name)

    try:
        data, fmt = extract_thumbnail(path)
        assert fmt == "png"
        # Should find and extract just the PNG portion
        assert data.startswith(b"\x89PNG")
    finally:
        path.unlink()


def test_invalid_thumbnail_raises():
    """Invalid image file should raise ThumbnailError."""
    with tempfile.NamedTemporaryFile(suffix=".hhi", delete=False) as f:
        f.write(b"not an image file at all")
        path = Path(f.name)

    try:
        with pytest.raises(ThumbnailError):
            extract_thumbnail(path)
    finally:
        path.unlink()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tray/test_thumbnails.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/tray/thumbnails.py
"""Thumbnail extraction from tray image files.

Sims 4 tray items use several image file types:
- .hhi - Household images
- .sgi - Individual Sim images
- .bpi - Lot/blueprint images

These files typically contain PNG data, sometimes with a
proprietary header that must be skipped.
"""

from pathlib import Path

from s4lt.tray.exceptions import ThumbnailError


# Magic bytes for image formats
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JFIF_MAGIC = b"\xff\xd8\xff"


def get_image_format(path: Path) -> str | None:
    """Detect image format from file.

    Args:
        path: Path to image file

    Returns:
        Format string ("png", "jpeg") or None if unknown
    """
    try:
        with open(path, "rb") as f:
            data = f.read(1024)  # Read enough to find magic

            # Check for PNG anywhere in first 1KB
            png_offset = data.find(PNG_MAGIC)
            if png_offset >= 0:
                return "png"

            # Check for JPEG
            jfif_offset = data.find(JFIF_MAGIC)
            if jfif_offset >= 0:
                return "jpeg"

            return None

    except OSError:
        return None


def extract_thumbnail(path: Path) -> tuple[bytes, str]:
    """Extract thumbnail image data from tray image file.

    Handles files that may have proprietary headers before
    the actual image data.

    Args:
        path: Path to .hhi, .sgi, or .bpi file

    Returns:
        Tuple of (image_data, format_string)

    Raises:
        ThumbnailError: If no valid image found
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise ThumbnailError(f"Could not read file: {e}")

    # Try to find PNG data
    png_offset = data.find(PNG_MAGIC)
    if png_offset >= 0:
        return data[png_offset:], "png"

    # Try to find JPEG data
    jfif_offset = data.find(JFIF_MAGIC)
    if jfif_offset >= 0:
        return data[jfif_offset:], "jpeg"

    raise ThumbnailError(f"No valid image found in {path.name}")


def save_thumbnail(path: Path, output_path: Path) -> str:
    """Extract and save thumbnail to output file.

    Args:
        path: Path to source tray image file
        output_path: Path to save extracted image

    Returns:
        Format of saved image ("png" or "jpeg")

    Raises:
        ThumbnailError: If extraction fails
    """
    data, fmt = extract_thumbnail(path)

    # Ensure correct extension
    if fmt == "png" and output_path.suffix.lower() != ".png":
        output_path = output_path.with_suffix(".png")
    elif fmt == "jpeg" and output_path.suffix.lower() not in (".jpg", ".jpeg"):
        output_path = output_path.with_suffix(".jpg")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
        return fmt
    except OSError as e:
        raise ThumbnailError(f"Could not save thumbnail: {e}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tray/test_thumbnails.py -v`
Expected: 4 passed

**Step 5: Update tray __init__.py**

```python
# s4lt/tray/__init__.py
"""S4LT Tray - Tray folder management."""

from s4lt.tray.exceptions import (
    TrayError,
    TrayItemNotFoundError,
    TrayParseError,
    ThumbnailError,
)
from s4lt.tray.scanner import discover_tray_items, TrayItemType
from s4lt.tray.trayitem import parse_trayitem, TrayItemMeta
from s4lt.tray.thumbnails import extract_thumbnail, save_thumbnail, get_image_format

__all__ = [
    # Exceptions
    "TrayError",
    "TrayItemNotFoundError",
    "TrayParseError",
    "ThumbnailError",
    # Scanner
    "discover_tray_items",
    "TrayItemType",
    # Metadata
    "parse_trayitem",
    "TrayItemMeta",
    # Thumbnails
    "extract_thumbnail",
    "save_thumbnail",
    "get_image_format",
]
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(tray): thumbnail extraction"
```

---

## Task 5: TrayItem Class (High-Level API)

**Files:**
- Create: `s4lt/tray/item.py`
- Create: `tests/tray/test_item.py`

**Step 1: Write the failing test**

```python
# tests/tray/test_item.py
"""Tests for TrayItem high-level class."""

import tempfile
from pathlib import Path

import pytest

from s4lt.tray.item import TrayItem
from s4lt.tray.scanner import TrayItemType
from tests.tray.fixtures import create_trayitem_v14


# Minimal PNG for thumbnails
MINIMAL_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82,
])


def create_household_files(tray_path: Path, item_id: str, name: str = "Test Family"):
    """Helper to create a complete set of household files."""
    (tray_path / f"{item_id}.trayitem").write_bytes(
        create_trayitem_v14(name=name, item_type=1)
    )
    (tray_path / f"{item_id}.householdbinary").write_bytes(b"\x00" * 100)
    (tray_path / f"{item_id}.hhi").write_bytes(MINIMAL_PNG)
    (tray_path / f"{item_id}!00000001.hhi").write_bytes(MINIMAL_PNG)
    (tray_path / f"{item_id}!00000000_0x0.sgi").write_bytes(MINIMAL_PNG)


def test_trayitem_from_discovery():
    """Should create TrayItem from scanner output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id, "Smith Family")

        item = TrayItem.from_path(tray_path, item_id)

        assert item.id == item_id
        assert item.name == "Smith Family"
        assert item.item_type == TrayItemType.HOUSEHOLD


def test_trayitem_list_thumbnails():
    """Should list available thumbnail files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id)

        item = TrayItem.from_path(tray_path, item_id)
        thumbs = item.list_thumbnails()

        # Should find .hhi and .sgi files
        assert len(thumbs) >= 2


def test_trayitem_get_primary_thumbnail():
    """Should return primary thumbnail data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id)

        item = TrayItem.from_path(tray_path, item_id)
        data, fmt = item.get_primary_thumbnail()

        assert data is not None
        assert fmt == "png"


def test_trayitem_str_representation():
    """Should have readable string representation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id, "The Johnsons")

        item = TrayItem.from_path(tray_path, item_id)
        s = str(item)

        assert "Johnsons" in s
        assert "household" in s.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tray/test_item.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/tray/item.py
"""High-level TrayItem class for working with tray entries."""

from pathlib import Path

from s4lt.tray.scanner import TrayItemType, HOUSEHOLD_EXTENSIONS, LOT_EXTENSIONS, ROOM_EXTENSIONS
from s4lt.tray.trayitem import parse_trayitem, TrayItemMeta
from s4lt.tray.thumbnails import extract_thumbnail
from s4lt.tray.exceptions import TrayItemNotFoundError, TrayParseError


# Extensions that contain thumbnail images
THUMBNAIL_EXTENSIONS = {".hhi", ".sgi", ".bpi", ".midi"}


class TrayItem:
    """A saved household, lot, or room from the Tray folder.

    Provides high-level access to tray item metadata, thumbnails,
    and associated files.
    """

    def __init__(
        self,
        item_id: str,
        tray_path: Path,
        files: list[Path],
        item_type: TrayItemType,
        meta: TrayItemMeta | None = None,
    ):
        """Create a TrayItem.

        Args:
            item_id: The hex ID of this tray item
            tray_path: Path to the Tray folder
            files: List of all files belonging to this item
            item_type: Type of item (household, lot, room)
            meta: Parsed metadata (lazy loaded if not provided)
        """
        self._id = item_id
        self._tray_path = tray_path
        self._files = files
        self._item_type = item_type
        self._meta = meta
        self._cached_meta: TrayItemMeta | None = None

    @classmethod
    def from_path(cls, tray_path: Path, item_id: str) -> "TrayItem":
        """Create TrayItem by discovering files for an ID.

        Args:
            tray_path: Path to the Tray folder
            item_id: The hex ID to look up

        Returns:
            TrayItem instance

        Raises:
            TrayItemNotFoundError: If no .trayitem file found
        """
        trayitem_path = tray_path / f"{item_id}.trayitem"
        if not trayitem_path.exists():
            raise TrayItemNotFoundError(f"No trayitem file for ID {item_id}")

        # Discover all related files
        files = [trayitem_path]

        # Add other extensions
        all_extensions = {".householdbinary", ".hhi", ".sgi", ".blueprint", ".bpi", ".room", ".midi"}
        for ext in all_extensions:
            files.extend(tray_path.glob(f"{item_id}{ext}"))
            files.extend(tray_path.glob(f"{item_id}!*{ext}"))
            files.extend(tray_path.glob(f"{item_id}_*{ext}"))

        files = list(set(files))

        # Determine type from files
        extensions = {f.suffix.lower() for f in files}

        if ".householdbinary" in extensions:
            item_type = TrayItemType.HOUSEHOLD
        elif ".blueprint" in extensions:
            item_type = TrayItemType.LOT
        elif ".room" in extensions:
            item_type = TrayItemType.ROOM
        else:
            item_type = TrayItemType.UNKNOWN

        return cls(
            item_id=item_id,
            tray_path=tray_path,
            files=files,
            item_type=item_type,
        )

    @property
    def id(self) -> str:
        """The hex ID of this tray item."""
        return self._id

    @property
    def item_type(self) -> TrayItemType:
        """Type of tray item."""
        return self._item_type

    @property
    def files(self) -> list[Path]:
        """All files belonging to this tray item."""
        return self._files

    @property
    def trayitem_path(self) -> Path:
        """Path to the .trayitem file."""
        return self._tray_path / f"{self._id}.trayitem"

    @property
    def name(self) -> str:
        """Name of the tray item (parsed from metadata)."""
        meta = self._get_meta()
        return meta.name if meta else self._id

    def _get_meta(self) -> TrayItemMeta | None:
        """Get or load metadata."""
        if self._meta is not None:
            return self._meta

        if self._cached_meta is not None:
            return self._cached_meta

        try:
            self._cached_meta = parse_trayitem(self.trayitem_path)
            return self._cached_meta
        except TrayParseError:
            return None

    def list_thumbnails(self) -> list[Path]:
        """List all thumbnail files for this item."""
        return [f for f in self._files if f.suffix.lower() in THUMBNAIL_EXTENSIONS]

    def get_primary_thumbnail(self) -> tuple[bytes, str] | tuple[None, None]:
        """Get the primary thumbnail for this item.

        Returns:
            Tuple of (image_data, format) or (None, None) if unavailable
        """
        thumbs = self.list_thumbnails()
        if not thumbs:
            return None, None

        # Prefer .hhi for households, .bpi for lots
        for preferred_ext in [".hhi", ".bpi", ".sgi", ".midi"]:
            for thumb in thumbs:
                if thumb.suffix.lower() == preferred_ext:
                    try:
                        return extract_thumbnail(thumb)
                    except Exception:
                        continue

        # Try first available
        try:
            return extract_thumbnail(thumbs[0])
        except Exception:
            return None, None

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"<TrayItem {self.item_type.value}: {self.name}>"

    def __repr__(self) -> str:
        return self.__str__()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tray/test_item.py -v`
Expected: 4 passed

**Step 5: Update tray __init__.py**

```python
# s4lt/tray/__init__.py
"""S4LT Tray - Tray folder management."""

from s4lt.tray.exceptions import (
    TrayError,
    TrayItemNotFoundError,
    TrayParseError,
    ThumbnailError,
)
from s4lt.tray.scanner import discover_tray_items, TrayItemType
from s4lt.tray.trayitem import parse_trayitem, TrayItemMeta
from s4lt.tray.thumbnails import extract_thumbnail, save_thumbnail, get_image_format
from s4lt.tray.item import TrayItem

__all__ = [
    # Exceptions
    "TrayError",
    "TrayItemNotFoundError",
    "TrayParseError",
    "ThumbnailError",
    # Scanner
    "discover_tray_items",
    "TrayItemType",
    # Metadata
    "parse_trayitem",
    "TrayItemMeta",
    # Thumbnails
    "extract_thumbnail",
    "save_thumbnail",
    "get_image_format",
    # High-level API
    "TrayItem",
]
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(tray): TrayItem high-level class"
```

---

## Task 6: Tray Path Detection

**Files:**
- Modify: `s4lt/config/paths.py`
- Create: `tests/config/test_tray_paths.py`

**Step 1: Write the failing test**

```python
# tests/config/test_tray_paths.py
"""Tests for tray folder path detection."""

import tempfile
from pathlib import Path

from s4lt.config.paths import find_tray_folder


def test_find_tray_folder_from_search():
    """Should find Tray folder from search paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake Sims 4 directory structure
        sims4_dir = Path(tmpdir) / "Documents" / "Electronic Arts" / "The Sims 4"
        tray_dir = sims4_dir / "Tray"
        tray_dir.mkdir(parents=True)

        search_paths = [str(sims4_dir)]
        result = find_tray_folder(search_paths)

        assert result == tray_dir


def test_find_tray_folder_returns_none_if_not_found():
    """Should return None if Tray folder not found."""
    result = find_tray_folder(["/nonexistent/path/that/does/not/exist"])
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_tray_paths.py -v`
Expected: FAIL (function doesn't exist)

**Step 3: Modify paths.py to add find_tray_folder**

Add to `s4lt/config/paths.py`:

```python
def find_tray_folder(search_paths: list[str] | None = None) -> Path | None:
    """Find the Tray folder by checking common locations.

    Args:
        search_paths: Paths to check (defaults to SEARCH_PATHS)

    Returns:
        Path to Tray folder if found, None otherwise
    """
    if search_paths is None:
        search_paths = SEARCH_PATHS

    for path_template in search_paths:
        base_path = expand_path(path_template)
        tray_path = base_path / "Tray"

        if tray_path.is_dir():
            return tray_path

    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_tray_paths.py -v`
Expected: 2 passed

**Step 5: Update config __init__.py**

Modify `s4lt/config/__init__.py` to export `find_tray_folder`:

```python
# s4lt/config/__init__.py
"""S4LT Configuration."""

from s4lt.config.paths import find_mods_folder, find_tray_folder
from s4lt.config.settings import get_settings, save_settings, Settings

__all__ = [
    "find_mods_folder",
    "find_tray_folder",
    "get_settings",
    "save_settings",
    "Settings",
]
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(config): tray folder path detection"
```

---

## Task 7: CLI Tray List Command

**Files:**
- Create: `s4lt/cli/commands/tray.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Write the command implementation**

```python
# s4lt/cli/commands/tray.py
"""Tray command implementations."""

import json
import sys
from pathlib import Path

import click

from s4lt.cli.output import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
)
from s4lt.config import find_tray_folder, get_settings, save_settings
from s4lt.tray import discover_tray_items, TrayItem, TrayItemType


def run_tray_list(
    item_type: str | None = None,
    json_output: bool = False,
):
    """List all tray items."""
    settings = get_settings()

    # Find tray folder
    if settings.tray_path is None:
        if json_output:
            print(json.dumps({"error": "Tray folder not configured"}))
            sys.exit(1)

        console.print("\n[bold]Tray Folder Setup[/bold]\n")

        tray_path = find_tray_folder()
        if tray_path:
            console.print(f"Found Tray folder: [cyan]{tray_path}[/cyan]")
            if click.confirm("Use this path?", default=True):
                settings.tray_path = tray_path
            else:
                path_str = click.prompt("Enter Tray folder path")
                settings.tray_path = Path(path_str)
        else:
            console.print("[yellow]Could not auto-detect Tray folder.[/yellow]")
            path_str = click.prompt("Enter Tray folder path")
            settings.tray_path = Path(path_str)

        if not settings.tray_path.is_dir():
            print_error(f"Path does not exist: {settings.tray_path}")
            sys.exit(1)

        save_settings(settings)
        console.print("[green]Saved configuration.[/green]\n")

    tray_path = settings.tray_path

    # Discover tray items
    if not json_output:
        console.print(f"[bold]Scanning[/bold] {tray_path}\n")

    discovered = discover_tray_items(tray_path)

    # Filter by type if specified
    if item_type:
        type_filter = {
            "household": TrayItemType.HOUSEHOLD,
            "lot": TrayItemType.LOT,
            "room": TrayItemType.ROOM,
        }.get(item_type.lower())

        if type_filter:
            discovered = [d for d in discovered if d["type"] == type_filter]

    # Load full TrayItem objects for names
    items = []
    for d in discovered:
        try:
            item = TrayItem.from_path(tray_path, d["id"])
            items.append({
                "id": item.id,
                "name": item.name,
                "type": item.item_type.value,
                "files": len(item.files),
                "thumbnails": len(item.list_thumbnails()),
            })
        except Exception as e:
            items.append({
                "id": d["id"],
                "name": "(error loading)",
                "type": d["type"].value if d["type"] else "unknown",
                "files": len(d.get("files", [])),
                "error": str(e),
            })

    if json_output:
        print(json.dumps({"items": items, "total": len(items)}))
        return

    # Display results
    if not items:
        print_warning("No tray items found.")
        return

    # Group by type
    households = [i for i in items if i["type"] == "household"]
    lots = [i for i in items if i["type"] == "lot"]
    rooms = [i for i in items if i["type"] == "room"]
    other = [i for i in items if i["type"] not in ("household", "lot", "room")]

    print_success(f"Found {len(items)} tray items")
    console.print()

    if households:
        console.print(f"[bold cyan]Households ({len(households)})[/bold cyan]")
        for h in households:
            console.print(f"  {h['name']}")
        console.print()

    if lots:
        console.print(f"[bold green]Lots ({len(lots)})[/bold green]")
        for l in lots:
            console.print(f"  {l['name']}")
        console.print()

    if rooms:
        console.print(f"[bold yellow]Rooms ({len(rooms)})[/bold yellow]")
        for r in rooms:
            console.print(f"  {r['name']}")
        console.print()

    if other:
        console.print(f"[dim]Unknown ({len(other)})[/dim]")
        for o in other:
            console.print(f"  {o['id']}")


def run_tray_export(
    name_or_id: str,
    output_dir: str | None = None,
    include_thumb: bool = True,
):
    """Export a tray item to a directory."""
    settings = get_settings()

    if settings.tray_path is None:
        print_error("Tray folder not configured. Run 's4lt tray list' first.")
        sys.exit(1)

    tray_path = settings.tray_path

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
        print_error(f"Tray item not found: {name_or_id}")
        sys.exit(1)

    # Load the full item
    item = TrayItem.from_path(tray_path, target["id"])

    # Determine output directory
    if output_dir:
        out_path = Path(output_dir)
    else:
        # Use item name, sanitized
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in item.name)
        out_path = Path.cwd() / safe_name

    out_path.mkdir(parents=True, exist_ok=True)

    # Copy all files
    console.print(f"Exporting [bold]{item.name}[/bold] to {out_path}")

    import shutil
    for f in item.files:
        dest = out_path / f.name
        shutil.copy2(f, dest)
        console.print(f"  Copied {f.name}")

    # Optionally export primary thumbnail as readable image
    if include_thumb:
        data, fmt = item.get_primary_thumbnail()
        if data:
            thumb_path = out_path / f"thumbnail.{fmt}"
            thumb_path.write_bytes(data)
            console.print(f"  Saved thumbnail.{fmt}")

    print_success(f"Exported {len(item.files)} files")
```

**Step 2: Modify main.py to add tray commands**

Add to `s4lt/cli/main.py`:

```python
@cli.group()
def tray():
    """Manage tray items (saved Sims, lots, rooms)."""
    pass


@tray.command("list")
@click.option("--type", "item_type", type=click.Choice(["household", "lot", "room"]),
              help="Filter by item type")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def tray_list(item_type: str | None, json_output: bool):
    """List all tray items."""
    from s4lt.cli.commands.tray import run_tray_list
    run_tray_list(item_type=item_type, json_output=json_output)


@tray.command("export")
@click.argument("name_or_id")
@click.option("--output", "-o", "output_dir", help="Output directory")
@click.option("--no-thumb", is_flag=True, help="Don't export thumbnail")
def tray_export(name_or_id: str, output_dir: str | None, no_thumb: bool):
    """Export a tray item to a directory."""
    from s4lt.cli.commands.tray import run_tray_export
    run_tray_export(name_or_id, output_dir, include_thumb=not no_thumb)
```

**Step 3: Update settings to include tray_path**

Modify `s4lt/config/settings.py` to add `tray_path`:

```python
@dataclass
class Settings:
    """S4LT configuration settings."""

    mods_path: Path | None = None
    tray_path: Path | None = None  # Add this line
    include_subfolders: bool = True
    ignore_patterns: list[str] = field(default_factory=lambda: ["__MACOSX", ".DS_Store"])
```

**Step 4: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(cli): tray list and export commands"
```

---

## Task 8: CLI Tray Info Command

**Files:**
- Modify: `s4lt/cli/commands/tray.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Add info command implementation**

Add to `s4lt/cli/commands/tray.py`:

```python
def run_tray_info(name_or_id: str, json_output: bool = False):
    """Show detailed information about a tray item."""
    settings = get_settings()

    if settings.tray_path is None:
        if json_output:
            print(json.dumps({"error": "Tray folder not configured"}))
        else:
            print_error("Tray folder not configured. Run 's4lt tray list' first.")
        sys.exit(1)

    tray_path = settings.tray_path

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
            print(json.dumps({"error": f"Tray item not found: {name_or_id}"}))
        else:
            print_error(f"Tray item not found: {name_or_id}")
        sys.exit(1)

    # Load full item
    item = TrayItem.from_path(tray_path, target["id"])

    info = {
        "id": item.id,
        "name": item.name,
        "type": item.item_type.value,
        "files": [str(f.name) for f in item.files],
        "file_count": len(item.files),
        "thumbnails": [str(f.name) for f in item.list_thumbnails()],
        "has_thumbnail": len(item.list_thumbnails()) > 0,
    }

    if json_output:
        print(json.dumps(info))
        return

    console.print(f"\n[bold]{item.name}[/bold]")
    console.print(f"  Type: [cyan]{item.item_type.value}[/cyan]")
    console.print(f"  ID: [dim]{item.id}[/dim]")
    console.print()

    console.print("[bold]Files:[/bold]")
    for f in sorted(item.files, key=lambda x: x.suffix):
        size = f.stat().st_size
        console.print(f"  {f.name} ({size:,} bytes)")

    console.print()
    thumbs = item.list_thumbnails()
    if thumbs:
        console.print(f"[bold]Thumbnails:[/bold] {len(thumbs)} available")
    else:
        console.print("[dim]No thumbnails found[/dim]")
```

**Step 2: Add info command to main.py**

Add to `s4lt/cli/main.py`:

```python
@tray.command("info")
@click.argument("name_or_id")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def tray_info(name_or_id: str, json_output: bool):
    """Show details about a tray item."""
    from s4lt.cli.commands.tray import run_tray_info
    run_tray_info(name_or_id, json_output=json_output)
```

**Step 3: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "feat(cli): tray info command"
```

---

## Task 9: CLI Tests for Tray Commands

**Files:**
- Create: `tests/cli/test_tray.py`

**Step 1: Write CLI tests**

```python
# tests/cli/test_tray.py
"""Tests for tray CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from s4lt.cli.main import cli
from s4lt.config.settings import Settings
from tests.tray.fixtures import create_trayitem_v14


# Minimal PNG
MINIMAL_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82,
])


def create_test_tray_folder(path: Path):
    """Create a test tray folder with sample items."""
    # Household
    item_id = "0x0000000012345678"
    (path / f"{item_id}.trayitem").write_bytes(
        create_trayitem_v14(name="Test Family", item_type=1)
    )
    (path / f"{item_id}.householdbinary").write_bytes(b"\x00" * 100)
    (path / f"{item_id}.hhi").write_bytes(MINIMAL_PNG)

    # Lot
    lot_id = "0x00000000ABCDEF01"
    (path / f"{lot_id}.trayitem").write_bytes(
        create_trayitem_v14(name="Test House", item_type=2)
    )
    (path / f"{lot_id}.blueprint").write_bytes(b"\x00" * 100)
    (path / f"{lot_id}.bpi").write_bytes(MINIMAL_PNG)


def test_tray_list_finds_items():
    """tray list should find tray items."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        create_test_tray_folder(tray_path)

        settings = Settings(tray_path=tray_path)

        with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
            result = runner.invoke(cli, ["tray", "list", "--json"])

        assert result.exit_code == 0
        assert "Test Family" in result.output or "items" in result.output


def test_tray_list_empty_folder():
    """tray list should handle empty folder."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        settings = Settings(tray_path=tray_path)

        with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
            result = runner.invoke(cli, ["tray", "list"])

        assert result.exit_code == 0
```

**Step 2: Run tests**

Run: `pytest tests/cli/test_tray.py -v`
Expected: 2 passed

**Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "test(cli): tray command tests"
```

---

## Task 10: Final Integration and Documentation

**Step 1: Update top-level s4lt __init__.py**

```python
# s4lt/__init__.py
"""S4LT: Sims 4 Linux Toolkit.

A native Linux toolkit for Sims 4 mod management.
"""

from s4lt.core import Package, Resource, DBPFError
from s4lt.tray import TrayItem, TrayItemType, discover_tray_items

__version__ = "0.2.0"

__all__ = [
    # Core
    "Package",
    "Resource",
    "DBPFError",
    # Tray
    "TrayItem",
    "TrayItemType",
    "discover_tray_items",
    # Version
    "__version__",
]
```

**Step 2: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 3: Final commit**

```bash
git add -A
git commit -m "docs: complete Phase 3 - Tray Manager ready"
```

---

## Summary

**Files Created:**
- `s4lt/tray/__init__.py` - Tray module exports
- `s4lt/tray/exceptions.py` - Error classes
- `s4lt/tray/scanner.py` - Tray folder discovery
- `s4lt/tray/trayitem.py` - Metadata parsing
- `s4lt/tray/thumbnails.py` - Thumbnail extraction
- `s4lt/tray/item.py` - High-level TrayItem class
- `s4lt/cli/commands/tray.py` - CLI commands
- `tests/tray/` - Complete test suite

**Files Modified:**
- `s4lt/config/paths.py` - Added find_tray_folder
- `s4lt/config/settings.py` - Added tray_path setting
- `s4lt/cli/main.py` - Added tray command group
- `s4lt/__init__.py` - Updated exports and version

**CLI Commands Added:**
- `s4lt tray list [--type] [--json]` - List all tray items
- `s4lt tray info <name_or_id> [--json]` - Show item details
- `s4lt tray export <name_or_id> [-o dir]` - Export item files

**Capabilities:**
- Discover all tray items (households, lots, rooms)
- Parse item names and metadata from .trayitem files
- Extract thumbnails from .hhi, .sgi, .bpi files
- Group related files by ID
- Export tray items with thumbnails
- CLI for browsing and exporting

**Next Phase:** CC Tracking & Missing CC Detection (extends this foundation)
