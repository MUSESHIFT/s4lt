"""Tests for tray folder path detection."""

import tempfile
from pathlib import Path

from s4lt.config.paths import find_tray_folder


def test_find_tray_folder_from_search():
    """Should find Tray folder from search paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake Sims 4 directory structure
        sims4_dir = Path(tmpdir) / "Documents" / "Electronic Arts" / "The Sims 4"
        tray_dir = sims4_dir / "Tray"
        tray_dir.mkdir(parents=True)

        search_paths = [str(sims4_dir)]
        result = find_tray_folder(search_paths)

        assert result == tray_dir


def test_find_tray_folder_returns_none_if_not_found():
    """Should return None if Tray folder not found."""
    result = find_tray_folder(["/nonexistent/path/that/does/not/exist"])
    assert result is None
