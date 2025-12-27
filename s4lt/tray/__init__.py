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
from s4lt.tray.cc_tracker import (
    TGI,
    CCReference,
    extract_tgis_from_binary,
    extract_tgis_from_tray_item,
    classify_tgis,
    get_cc_summary,
)

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
    # CC Tracker
    "TGI",
    "CCReference",
    "extract_tgis_from_binary",
    "extract_tgis_from_tray_item",
    "classify_tgis",
    "get_cc_summary",
]
