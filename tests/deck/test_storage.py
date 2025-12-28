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


from s4lt.deck.storage import StorageSummary, get_storage_summary


def test_storage_summary_dataclass():
    """StorageSummary should hold storage info."""
    summary = StorageSummary(
        internal_used_bytes=10_000_000_000,
        internal_free_bytes=50_000_000_000,
        sd_used_bytes=5_000_000_000,
        sd_free_bytes=100_000_000_000,
        symlink_count=3,
    )
    assert summary.internal_used_gb == 10.0
    assert summary.sd_free_gb == 100.0


def test_get_storage_summary_internal_only():
    """Should calculate storage when no SD card."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        # Create some test files
        (mods_path / "test.package").write_bytes(b"x" * 1000)

        summary = get_storage_summary(mods_path, None)

        assert summary.internal_used_bytes == 1000
        assert summary.sd_used_bytes == 0
        assert summary.symlink_count == 0


def test_get_storage_summary_with_symlinks():
    """Should count symlinked mods as SD storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        sd_path = Path(tmpdir) / "SD"
        mods_path.mkdir()
        sd_path.mkdir()

        # Regular file on internal
        (mods_path / "internal.package").write_bytes(b"x" * 1000)

        # File on SD with symlink
        sd_file = sd_path / "external.package"
        sd_file.write_bytes(b"y" * 2000)
        (mods_path / "external.package").symlink_to(sd_file)

        summary = get_storage_summary(mods_path, sd_path)

        assert summary.internal_used_bytes == 1000
        assert summary.sd_used_bytes == 2000
        assert summary.symlink_count == 1
