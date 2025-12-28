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


from s4lt.deck.storage import MoveResult, move_to_sd


def test_move_result_dataclass():
    """MoveResult should hold operation results."""
    result = MoveResult(
        success_count=2,
        failed_paths=[],
        bytes_moved=5000,
    )
    assert result.success_count == 2
    assert result.all_succeeded is True


def test_move_to_sd_moves_file():
    """Should move file to SD and create symlink."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        sd_path = Path(tmpdir) / "SD/S4LT"
        mods_path.mkdir()
        sd_path.mkdir(parents=True)

        # Create test file
        test_file = mods_path / "test.package"
        test_file.write_bytes(b"test data")

        result = move_to_sd([test_file], sd_path)

        assert result.success_count == 1
        assert result.bytes_moved == 9
        assert (mods_path / "test.package").is_symlink()
        assert (sd_path / "test.package").exists()
        assert (mods_path / "test.package").resolve() == sd_path / "test.package"


def test_move_to_sd_moves_folder():
    """Should move folder to SD and create symlink."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        sd_path = Path(tmpdir) / "SD/S4LT"
        mods_path.mkdir()
        sd_path.mkdir(parents=True)

        # Create test folder with files
        test_folder = mods_path / "MyMod"
        test_folder.mkdir()
        (test_folder / "file1.package").write_bytes(b"data1")
        (test_folder / "file2.package").write_bytes(b"data2")

        result = move_to_sd([test_folder], sd_path)

        assert result.success_count == 1
        assert (mods_path / "MyMod").is_symlink()
        assert (sd_path / "MyMod").is_dir()
        assert (sd_path / "MyMod" / "file1.package").exists()


def test_move_to_sd_checks_space():
    """Should fail if not enough space on SD."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        sd_path = Path(tmpdir) / "SD"
        mods_path.mkdir()
        sd_path.mkdir()

        test_file = mods_path / "huge.package"
        test_file.write_bytes(b"x" * 1000)

        # Mock disk_usage to return no free space
        with patch("shutil.disk_usage") as mock_usage:
            mock_usage.return_value = type("Usage", (), {"free": 100})()
            result = move_to_sd([test_file], sd_path)

        assert result.success_count == 0
        assert len(result.failed_paths) == 1


from s4lt.deck.storage import move_to_internal, check_symlink_health, SymlinkIssue


def test_check_symlink_health_finds_broken():
    """Should detect broken symlinks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        # Create broken symlink
        broken = mods_path / "broken.package"
        broken.symlink_to("/nonexistent/path")

        issues = check_symlink_health(mods_path)

        assert len(issues) == 1
        assert issues[0].path == broken
        assert issues[0].reason == "target_missing"


def test_check_symlink_health_ok_when_valid():
    """Should return empty list for valid symlinks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        sd_path = Path(tmpdir) / "SD"
        mods_path.mkdir()
        sd_path.mkdir()

        # Create valid symlink
        target = sd_path / "valid.package"
        target.write_bytes(b"data")
        link = mods_path / "valid.package"
        link.symlink_to(target)

        issues = check_symlink_health(mods_path)

        assert issues == []


def test_symlink_issue_dataclass():
    """SymlinkIssue should hold issue info."""
    issue = SymlinkIssue(
        path=Path("/mods/broken.package"),
        target=Path("/sd/broken.package"),
        reason="target_missing",
    )
    assert issue.path == Path("/mods/broken.package")
    assert issue.reason == "target_missing"


def test_move_to_internal_moves_symlinked_file():
    """Should move file back from SD and remove symlink."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        sd_path = Path(tmpdir) / "SD"
        mods_path.mkdir()
        sd_path.mkdir()

        # Create file on SD with symlink
        sd_file = sd_path / "test.package"
        sd_file.write_bytes(b"test data")
        symlink = mods_path / "test.package"
        symlink.symlink_to(sd_file)

        result = move_to_internal([symlink], mods_path)

        assert result.success_count == 1
        assert not symlink.is_symlink()
        assert symlink.is_file()
        assert symlink.read_bytes() == b"test data"
        assert not sd_file.exists()


def test_move_to_internal_ignores_non_symlinks():
    """Should skip files that aren't symlinks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        regular_file = mods_path / "regular.package"
        regular_file.write_bytes(b"data")

        result = move_to_internal([regular_file], mods_path)

        assert result.success_count == 0
        assert len(result.failed_paths) == 1
