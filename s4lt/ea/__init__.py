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
