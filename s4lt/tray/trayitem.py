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
