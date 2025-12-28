"""Tests for Steam integration."""

import tempfile
from pathlib import Path

from s4lt.deck.steam import parse_shortcuts_vdf, find_shortcuts_file, add_to_steam, remove_from_steam


def test_parse_shortcuts_vdf_empty():
    """Should parse empty shortcuts file."""
    # Minimal VDF structure
    vdf_data = b'\x00shortcuts\x00\x08'

    with tempfile.NamedTemporaryFile(suffix=".vdf", delete=False) as f:
        f.write(vdf_data)
        path = Path(f.name)

    try:
        shortcuts = parse_shortcuts_vdf(path)
        assert shortcuts == []
    finally:
        path.unlink()


def test_find_shortcuts_file():
    """Should find shortcuts.vdf in Steam userdata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        steam_path = Path(tmpdir) / ".steam/steam/userdata/12345/config"
        steam_path.mkdir(parents=True)
        shortcuts_file = steam_path / "shortcuts.vdf"
        shortcuts_file.write_bytes(b"test")

        result = find_shortcuts_file(Path(tmpdir))

        assert result == shortcuts_file


def test_add_to_steam_creates_shortcut():
    """Should create shortcuts.vdf with S4LT entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        steam_path = Path(tmpdir) / ".steam/steam/userdata/12345/config"
        steam_path.mkdir(parents=True)

        result = add_to_steam(
            exe_path="/usr/bin/s4lt",
            home=Path(tmpdir),
        )

        assert result is True
        assert (steam_path / "shortcuts.vdf").exists()


def test_remove_from_steam():
    """Should remove S4LT from shortcuts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        steam_path = Path(tmpdir) / ".steam/steam/userdata/12345/config"
        steam_path.mkdir(parents=True)
        (steam_path / "shortcuts.vdf").write_bytes(b"test")

        # First add
        add_to_steam("/usr/bin/s4lt", home=Path(tmpdir))

        # Then remove
        result = remove_from_steam(home=Path(tmpdir))

        assert result is True
