"""Tests for database schema."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection


def test_init_creates_tables():
    """init_db should create all required tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "mods" in tables
        assert "resources" in tables
        assert "config" in tables
        conn.close()


def test_mods_table_columns():
    """mods table should have required columns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute("PRAGMA table_info(mods)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "id" in columns
        assert "path" in columns
        assert "hash" in columns
        assert "mtime" in columns
        assert "size" in columns
        assert "broken" in columns
        conn.close()


def test_resources_table_columns():
    """resources table should have required columns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute("PRAGMA table_info(resources)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "mod_id" in columns
        assert "type_id" in columns
        assert "group_id" in columns
        assert "instance_id" in columns
        assert "name" in columns
        conn.close()


def test_profiles_table_exists():
    """Schema should create profiles table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
        )
        assert cursor.fetchone() is not None
        conn.close()


def test_profile_mods_table_exists():
    """Schema should create profile_mods table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='profile_mods'"
        )
        assert cursor.fetchone() is not None
        conn.close()


def test_mods_has_category_column():
    """mods table should have category column."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        cursor = conn.execute("PRAGMA table_info(mods)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "category" in columns
        conn.close()
