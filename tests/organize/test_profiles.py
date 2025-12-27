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
