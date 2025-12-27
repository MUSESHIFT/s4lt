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
