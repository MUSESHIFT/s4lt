"""EA game path detection."""

import os
import subprocess
from pathlib import Path

# Common game install locations
EA_SEARCH_PATHS = [
    # NonSteamLaunchers (Steam Deck)
    "~/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/Program Files/EA Games/The Sims 4",
    # Standard Steam Proton
    "~/.steam/steam/steamapps/common/The Sims 4",
    "~/.local/share/Steam/steamapps/common/The Sims 4",
    # Flatpak Steam
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/The Sims 4",
    # Lutris/Wine
    "~/Games/the-sims-4/drive_c/Program Files/EA Games/The Sims 4",
]


def expand_path(path: str) -> Path:
    """Expand ~ in path."""
    return Path(os.path.expanduser(path))


def validate_game_folder(path: Path) -> bool:
    """Check if path is a valid Sims 4 game folder.

    Validates by checking for ClientFullBuild0.package.
    """
    marker = path / "Data" / "Client" / "ClientFullBuild0.package"
    return marker.is_file()


def find_game_folder(search_paths: list[str] | None = None) -> Path | None:
    """Find the game install folder.

    Args:
        search_paths: Paths to check (defaults to EA_SEARCH_PATHS)

    Returns:
        Path to game folder if found, None otherwise
    """
    if search_paths is None:
        search_paths = EA_SEARCH_PATHS

    # Check known paths first
    for path_template in search_paths:
        game_path = expand_path(path_template)
        if validate_game_folder(game_path):
            return game_path

    return None


def find_game_folder_search() -> Path | None:
    """Find game folder by searching filesystem.

    Fallback when known paths don't work.
    Uses: find ~ -name "ClientFullBuild0.package"
    """
    try:
        result = subprocess.run(
            ["find", str(Path.home()), "-name", "ClientFullBuild0.package", "-type", "f"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0 and result.stdout.strip():
            # Take first result, derive game folder
            package_path = Path(result.stdout.strip().split("\n")[0])
            # ClientFullBuild0.package is in Data/Client/
            game_path = package_path.parent.parent.parent
            if validate_game_folder(game_path):
                return game_path

    except (subprocess.TimeoutExpired, Exception):
        pass

    return None
