"""Tests for profile management."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.organize.profiles import (
    create_profile,
    get_profile,
    list_profiles,
    delete_profile,
    Profile,
)
from s4lt.organize.exceptions import ProfileNotFoundError, ProfileExistsError
import pytest


def test_create_profile():
    """create_profile should create a new profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        profile = create_profile(conn, "gameplay")

        assert profile.name == "gameplay"
        assert profile.id is not None
        assert profile.is_auto is False
        conn.close()


def test_create_profile_duplicate_raises():
    """create_profile should raise if profile exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "gameplay")

        with pytest.raises(ProfileExistsError):
            create_profile(conn, "gameplay")
        conn.close()


def test_get_profile():
    """get_profile should return profile by name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "test")
        profile = get_profile(conn, "test")

        assert profile is not None
        assert profile.name == "test"
        conn.close()


def test_get_profile_not_found():
    """get_profile should return None if not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        profile = get_profile(conn, "nonexistent")

        assert profile is None
        conn.close()


def test_list_profiles():
    """list_profiles should return all profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "a")
        create_profile(conn, "b")
        profiles = list_profiles(conn)

        assert len(profiles) == 2
        names = [p.name for p in profiles]
        assert "a" in names
        assert "b" in names
        conn.close()


def test_delete_profile():
    """delete_profile should remove profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        create_profile(conn, "deleteme")
        delete_profile(conn, "deleteme")

        assert get_profile(conn, "deleteme") is None
        conn.close()


def test_delete_profile_not_found_raises():
    """delete_profile should raise if profile not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        with pytest.raises(ProfileNotFoundError):
            delete_profile(conn, "nonexistent")
        conn.close()


# Tests for snapshot and mod retrieval
from s4lt.organize.profiles import save_profile_snapshot, get_profile_mods, ProfileMod


def test_save_profile_snapshot():
    """save_profile_snapshot should save current mod states."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Create mods directory with some files
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "enabled.package").write_bytes(b"DBPF")
        (mods_path / "disabled.package.disabled").write_bytes(b"DBPF")

        profile = create_profile(conn, "snapshot")
        save_profile_snapshot(conn, profile.id, mods_path)

        mods = get_profile_mods(conn, profile.id)
        assert len(mods) == 2

        enabled = [m for m in mods if m.enabled]
        disabled = [m for m in mods if not m.enabled]
        assert len(enabled) == 1
        assert len(disabled) == 1
        conn.close()


def test_get_profile_mods():
    """get_profile_mods should return mods for a profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        profile = create_profile(conn, "test")
        # Manually insert some profile mods
        conn.execute(
            "INSERT INTO profile_mods (profile_id, mod_path, enabled) VALUES (?, ?, ?)",
            (profile.id, "test.package", 1),
        )
        conn.commit()

        mods = get_profile_mods(conn, profile.id)

        assert len(mods) == 1
        assert mods[0].mod_path == "test.package"
        assert mods[0].enabled is True
        conn.close()


# Tests for switch_profile
from s4lt.organize.profiles import switch_profile, SwitchResult


def test_switch_profile_enables_and_disables():
    """switch_profile should apply profile state to filesystem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        # Create initial state: one enabled, one disabled
        (mods_path / "a.package").write_bytes(b"DBPF")
        (mods_path / "b.package.disabled").write_bytes(b"DBPF")

        # Save as profile
        profile = create_profile(conn, "test")
        save_profile_snapshot(conn, profile.id, mods_path)

        # Now flip the states
        (mods_path / "a.package").rename(mods_path / "a.package.disabled")
        (mods_path / "b.package.disabled").rename(mods_path / "b.package")

        # Switch back to profile
        result = switch_profile(conn, "test", mods_path)

        # Should restore original state
        assert (mods_path / "a.package").exists()
        assert (mods_path / "b.package.disabled").exists()
        assert result.enabled == 1
        assert result.disabled == 1
        conn.close()
