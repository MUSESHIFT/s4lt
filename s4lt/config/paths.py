"""Platform-specific path detection for Sims 4 on Linux/Steam Deck."""

import logging
import os
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


# Common Sims 4 installation paths - ordered by priority
# NonSteamLaunchers paths are checked FIRST (most common on Steam Deck)
SEARCH_PATHS = [
    # ===========================================
    # STEAM DECK - NonSteamLaunchers (HIGHEST PRIORITY)
    # This is the most common setup for Steam Deck users
    # ===========================================
    "~/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # ===========================================
    # STEAM DECK - Direct Steam/Proton installs
    # ===========================================
    # Steam Deck default (app ID 1222670)
    "~/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # ===========================================
    # DESKTOP LINUX - Standard Steam/Proton
    # ===========================================
    # Standard Steam location (symlinked .steam)
    "~/.steam/steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # Direct .local Steam location
    "~/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # ===========================================
    # FLATPAK STEAM
    # ===========================================
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # ===========================================
    # HEROIC LAUNCHER (Epic/GOG)
    # ===========================================
    "~/.config/heroic/prefixes/The Sims 4/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    "~/Games/Heroic/Prefixes/The Sims 4/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # ===========================================
    # LUTRIS
    # ===========================================
    "~/Games/the-sims-4/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
    "~/.wine/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",

    # ===========================================
    # BOTTLES
    # ===========================================
    "~/.var/app/com.usebottles.bottles/data/bottles/bottles/Sims4/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
    "~/.local/share/bottles/bottles/Sims4/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
]


def expand_path(path: str) -> Path:
    """Expand ~ and {user} in path."""
    expanded = os.path.expanduser(path)
    expanded = expanded.replace("{user}", os.environ.get("USER", "user"))
    return Path(expanded)


def find_sims4_base(search_paths: list[str] | None = None) -> Optional[Path]:
    """Find the base Sims 4 user data folder.

    Args:
        search_paths: Paths to check (defaults to SEARCH_PATHS)

    Returns:
        Path to base Sims 4 folder if found, None otherwise
    """
    if search_paths is None:
        search_paths = SEARCH_PATHS

    for path_template in search_paths:
        base_path = expand_path(path_template)
        # Check if this base folder exists and looks like a Sims 4 folder
        if base_path.is_dir():
            # Should have at least Options.ini or Mods folder to be valid
            if (base_path / "Options.ini").exists() or (base_path / "Mods").is_dir():
                logger.info(f"Found Sims 4 base folder: {base_path}")
                return base_path

    logger.warning("Could not auto-detect Sims 4 folder")
    return None


def find_mods_folder(search_paths: list[str] | None = None) -> Optional[Path]:
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
            logger.info(f"Found Mods folder: {mods_path}")
            return mods_path

    logger.warning("Could not auto-detect Mods folder")
    return None


def find_tray_folder(search_paths: list[str] | None = None) -> Optional[Path]:
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
            logger.info(f"Found Tray folder: {tray_path}")
            return tray_path

    logger.warning("Could not auto-detect Tray folder")
    return None


def find_saves_folder(search_paths: list[str] | None = None) -> Optional[Path]:
    """Find the saves folder by checking common locations.

    Args:
        search_paths: Paths to check (defaults to SEARCH_PATHS)

    Returns:
        Path to saves folder if found, None otherwise
    """
    if search_paths is None:
        search_paths = SEARCH_PATHS

    for path_template in search_paths:
        base_path = expand_path(path_template)
        saves_path = base_path / "saves"

        if saves_path.is_dir():
            logger.info(f"Found saves folder: {saves_path}")
            return saves_path

    logger.warning("Could not auto-detect saves folder")
    return None


def detect_all_paths() -> dict[str, Optional[Path]]:
    """Detect all Sims 4 paths at once.

    Returns:
        Dictionary with 'base', 'mods', 'tray', 'saves' paths
    """
    base = find_sims4_base()

    if base:
        return {
            'base': base,
            'mods': base / "Mods" if (base / "Mods").is_dir() else None,
            'tray': base / "Tray" if (base / "Tray").is_dir() else None,
            'saves': base / "saves" if (base / "saves").is_dir() else None,
        }

    # Fallback: try to find each individually
    return {
        'base': None,
        'mods': find_mods_folder(),
        'tray': find_tray_folder(),
        'saves': find_saves_folder(),
    }


def is_steam_deck() -> bool:
    """Check if running on Steam Deck."""
    # Steam Deck specific indicators
    indicators = [
        Path("/home/deck").is_dir(),
        os.environ.get("SteamDeck") == "1",
        os.environ.get("DESKTOP_SESSION") == "plasma" and Path("/home/deck").is_dir(),
    ]
    return any(indicators)
