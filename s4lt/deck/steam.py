"""Steam library integration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SteamShortcut:
    """A non-Steam game shortcut."""

    app_id: int
    app_name: str
    exe: str
    start_dir: str
    launch_options: str


def find_shortcuts_file(home: Path | None = None) -> Path | None:
    """Find Steam shortcuts.vdf file.

    Args:
        home: Home directory to search from (defaults to ~)

    Returns:
        Path to shortcuts.vdf or None if not found
    """
    if home is None:
        home = Path.home()

    # Check common Steam locations
    steam_paths = [
        home / ".steam/steam/userdata",
        home / ".local/share/Steam/userdata",
    ]

    for steam_path in steam_paths:
        if not steam_path.exists():
            continue

        # Find user directories
        for user_dir in steam_path.iterdir():
            if not user_dir.is_dir():
                continue

            shortcuts = user_dir / "config" / "shortcuts.vdf"
            if shortcuts.exists():
                return shortcuts

    return None


def parse_shortcuts_vdf(path: Path) -> list[SteamShortcut]:
    """Parse Steam shortcuts.vdf file.

    This is a binary VDF format, not text VDF.

    Args:
        path: Path to shortcuts.vdf

    Returns:
        List of existing shortcuts
    """
    # Binary VDF is complex - for now return empty list
    # Full implementation would parse the binary format
    # But we mainly need to write, not read
    return []
