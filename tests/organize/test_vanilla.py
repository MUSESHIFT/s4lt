"""Tests for vanilla mode toggle."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode
from s4lt.organize.profiles import get_profile


def test_toggle_vanilla_disables_all():
    """First toggle_vanilla should disable all mods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package").write_bytes(b"DBPF")
        (mods_path / "b.package").write_bytes(b"DBPF")

        result = toggle_vanilla(conn, mods_path)

        assert result.is_vanilla is True
        assert result.mods_changed == 2
        assert (mods_path / "a.package.disabled").exists()
        assert (mods_path / "b.package.disabled").exists()
        # Pre-vanilla profile should exist
        assert get_profile(conn, "_pre_vanilla") is not None
        conn.close()


def test_toggle_vanilla_restores():
    """Second toggle_vanilla should restore previous state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package").write_bytes(b"DBPF")
        (mods_path / "b.package.disabled").write_bytes(b"DBPF")

        # First toggle (enter vanilla)
        toggle_vanilla(conn, mods_path)
        # Second toggle (exit vanilla)
        result = toggle_vanilla(conn, mods_path)

        assert result.is_vanilla is False
        assert (mods_path / "a.package").exists()
        assert (mods_path / "b.package.disabled").exists()
        # Pre-vanilla profile should be deleted
        assert get_profile(conn, "_pre_vanilla") is None
        conn.close()


def test_is_vanilla_mode():
    """is_vanilla_mode should detect vanilla state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package").write_bytes(b"DBPF")

        assert is_vanilla_mode(conn) is False

        toggle_vanilla(conn, mods_path)
        assert is_vanilla_mode(conn) is True

        toggle_vanilla(conn, mods_path)
        assert is_vanilla_mode(conn) is False
        conn.close()
