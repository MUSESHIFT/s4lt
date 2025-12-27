"""Tests for EA game path detection."""

import tempfile
from pathlib import Path

from s4lt.ea.paths import (
    find_game_folder,
    validate_game_folder,
    expand_path,
    EA_SEARCH_PATHS,
)


def test_validate_game_folder_valid():
    """Should return True for valid game folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir)
        # Create expected structure
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()

        assert validate_game_folder(game_path) is True


def test_validate_game_folder_invalid():
    """Should return False for invalid folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert validate_game_folder(Path(tmpdir)) is False


def test_find_game_folder_from_search_paths():
    """Should find game folder from search paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir) / "The Sims 4"
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()

        result = find_game_folder(search_paths=[str(game_path)])
        assert result == game_path


def test_find_game_folder_returns_none_if_not_found():
    """Should return None if game not found."""
    result = find_game_folder(search_paths=["/nonexistent/path"])
    assert result is None


def test_expand_path_expands_tilde():
    """Should expand ~ to home directory."""
    result = expand_path("~/test")
    assert str(result).startswith(str(Path.home()))
    assert str(result).endswith("test")


def test_expand_path_handles_absolute_path():
    """Should handle absolute paths without tilde."""
    result = expand_path("/tmp/test")
    assert result == Path("/tmp/test")


def test_ea_search_paths_is_list():
    """EA_SEARCH_PATHS should be a non-empty list of strings."""
    assert isinstance(EA_SEARCH_PATHS, list)
    assert len(EA_SEARCH_PATHS) > 0
    for path in EA_SEARCH_PATHS:
        assert isinstance(path, str)
