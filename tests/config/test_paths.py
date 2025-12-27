"""Tests for path detection."""

import tempfile
from pathlib import Path

from s4lt.config.paths import find_mods_folder, SEARCH_PATHS


def test_search_paths_not_empty():
    """SEARCH_PATHS should have entries."""
    assert len(SEARCH_PATHS) > 0


def test_find_mods_folder_with_valid_path():
    """find_mods_folder should return path if Mods folder exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create fake Sims 4 structure
        mods_path = Path(tmpdir) / "Documents/Electronic Arts/The Sims 4/Mods"
        mods_path.mkdir(parents=True)

        # Create a test package
        (mods_path / "test.package").touch()

        result = find_mods_folder([tmpdir + "/Documents/Electronic Arts/The Sims 4"])
        assert result is not None
        assert result.name == "Mods"


def test_find_mods_folder_returns_none_if_not_found():
    """find_mods_folder should return None if no Mods folder found."""
    result = find_mods_folder(["/nonexistent/path/that/does/not/exist"])
    assert result is None
