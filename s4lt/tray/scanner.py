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
