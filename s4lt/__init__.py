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
