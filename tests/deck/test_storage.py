"""Tests for SD card storage management."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from s4lt.deck.storage import (
    RemovableDrive,
    list_removable_drives,
    get_sd_card_path,
)


def test_removable_drive_dataclass():
    """RemovableDrive should hold drive info."""
    drive = RemovableDrive(
        name="deck-sd",
        path=Path("/run/media/deck/deck-sd"),
        total_bytes=128_000_000_000,
        free_bytes=64_000_000_000,
    )
    assert drive.name == "deck-sd"
    assert drive.free_gb == 64.0


def test_list_removable_drives_finds_mounted():
    """Should find drives mounted at /run/media/user/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create fake mount point
        media_path = Path(tmpdir) / "run/media/testuser"
        sd_path = media_path / "my-sd-card"
        sd_path.mkdir(parents=True)

        with patch("s4lt.deck.storage.get_deck_user", return_value="testuser"):
            with patch("s4lt.deck.storage.MEDIA_BASE", Path(tmpdir) / "run/media"):
                drives = list_removable_drives()

        assert len(drives) == 1
        assert drives[0].name == "my-sd-card"


def test_list_removable_drives_empty_when_none():
    """Should return empty list when no drives mounted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("s4lt.deck.storage.get_deck_user", return_value="testuser"):
            with patch("s4lt.deck.storage.MEDIA_BASE", Path(tmpdir) / "run/media"):
                drives = list_removable_drives()

        assert drives == []


def test_get_sd_card_path_returns_first_drive():
    """Should return path to first removable drive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = Path(tmpdir) / "run/media/testuser"
        sd_path = media_path / "deck-sd"
        sd_path.mkdir(parents=True)

        with patch("s4lt.deck.storage.get_deck_user", return_value="testuser"):
            with patch("s4lt.deck.storage.MEDIA_BASE", Path(tmpdir) / "run/media"):
                result = get_sd_card_path()

        assert result == sd_path
