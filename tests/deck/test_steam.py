"""Tests for Steam integration."""

import tempfile
from pathlib import Path

from s4lt.deck.steam import parse_shortcuts_vdf, find_shortcuts_file


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
