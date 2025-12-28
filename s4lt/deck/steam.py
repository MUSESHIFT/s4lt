"""Steam library integration."""

import shutil
import struct
import zlib
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


def _generate_app_id(exe: str, app_name: str) -> int:
    """Generate Steam app ID from exe and name."""
    # Steam uses CRC32 of exe+name
    data = (exe + app_name).encode("utf-8")
    return zlib.crc32(data) & 0xFFFFFFFF


def _build_shortcuts_vdf(shortcuts: list[dict]) -> bytes:
    """Build binary VDF for shortcuts.

    Binary VDF format:
    - 0x00 = start of map
    - 0x01 = string value
    - 0x02 = int value
    - 0x08 = end of map
    """
    def write_string(key: str, value: str) -> bytes:
        return b'\x01' + key.encode() + b'\x00' + value.encode() + b'\x00'

    def write_int(key: str, value: int) -> bytes:
        return b'\x02' + key.encode() + b'\x00' + struct.pack('<I', value)

    result = b'\x00shortcuts\x00'

    for i, shortcut in enumerate(shortcuts):
        result += b'\x00' + str(i).encode() + b'\x00'
        result += write_int('appid', shortcut.get('appid', 0))
        result += write_string('AppName', shortcut.get('AppName', ''))
        result += write_string('Exe', shortcut.get('Exe', ''))
        result += write_string('StartDir', shortcut.get('StartDir', ''))
        result += write_string('LaunchOptions', shortcut.get('LaunchOptions', ''))
        result += b'\x08'

    result += b'\x08'
    return result


def add_to_steam(exe_path: str, home: Path | None = None) -> bool:
    """Add S4LT to Steam as non-Steam game.

    Args:
        exe_path: Path to s4lt executable
        home: Home directory (for testing)

    Returns:
        True if successful
    """
    if home is None:
        home = Path.home()

    # Find or create shortcuts file location
    shortcuts_file = find_shortcuts_file(home)

    if shortcuts_file is None:
        # Try to find Steam userdata directory
        for steam_path in [
            home / ".steam/steam/userdata",
            home / ".local/share/Steam/userdata",
        ]:
            if steam_path.exists():
                # Use first user directory
                for user_dir in steam_path.iterdir():
                    if user_dir.is_dir():
                        config_dir = user_dir / "config"
                        config_dir.mkdir(exist_ok=True)
                        shortcuts_file = config_dir / "shortcuts.vdf"
                        break
                if shortcuts_file:
                    break

    if shortcuts_file is None:
        return False

    # Create S4LT shortcut
    app_name = "S4LT - Sims 4 Linux Toolkit"
    shortcut = {
        'appid': _generate_app_id(exe_path, app_name),
        'AppName': app_name,
        'Exe': f'"{exe_path}"',
        'StartDir': f'"{Path(exe_path).parent}"',
        'LaunchOptions': 'serve --open',
    }

    # WARNING: Full merging of existing shortcuts is not yet implemented.
    # This will overwrite the file with only the S4LT shortcut.
    # Backup existing shortcuts.vdf before writing
    if shortcuts_file.exists():
        backup = shortcuts_file.with_suffix('.vdf.bak')
        shutil.copy2(shortcuts_file, backup)

    # Write shortcuts file
    vdf_data = _build_shortcuts_vdf([shortcut])
    shortcuts_file.write_bytes(vdf_data)

    return True


def remove_from_steam(home: Path | None = None) -> bool:
    """Remove S4LT from Steam library.

    Args:
        home: Home directory (for testing)

    Returns:
        True if successful
    """
    if home is None:
        home = Path.home()

    shortcuts_file = find_shortcuts_file(home)
    if shortcuts_file is None:
        return False

    # WARNING: Full merging of existing shortcuts is not yet implemented.
    # This will overwrite the file with empty shortcuts.
    # Backup existing shortcuts.vdf before writing
    if shortcuts_file.exists():
        backup = shortcuts_file.with_suffix('.vdf.bak')
        shutil.copy2(shortcuts_file, backup)

    # Write empty shortcuts (simplified - real impl would preserve others)
    vdf_data = _build_shortcuts_vdf([])
    shortcuts_file.write_bytes(vdf_data)

    return True
