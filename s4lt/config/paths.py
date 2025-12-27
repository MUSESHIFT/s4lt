"""Platform-specific path detection."""

import os
from pathlib import Path

# Common Sims 4 installation paths
SEARCH_PATHS = [
    # Steam Deck (NonSteamLauncher / Proton)
    "~/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    # Standard Steam Proton
    "~/.steam/steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    # Flatpak Steam
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",
    # Lutris / Wine default
    "~/.wine/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
    # Custom Wine prefix
    "~/Games/the-sims-4/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
]


def expand_path(path: str) -> Path:
    """Expand ~ and {user} in path."""
    expanded = os.path.expanduser(path)
    expanded = expanded.replace("{user}", os.environ.get("USER", "user"))
    return Path(expanded)


def find_mods_folder(search_paths: list[str] | None = None) -> Path | None:
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
            return mods_path

    return None


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
