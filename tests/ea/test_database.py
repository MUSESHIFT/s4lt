"""Tests for EA database operations."""

import tempfile
from pathlib import Path

from s4lt.ea.database import init_ea_db, get_ea_db_path, EADatabase


def test_init_creates_tables():
    """Should create ea_resources and ea_scan_info tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ea.db"
        conn = init_ea_db(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "ea_resources" in tables
        assert "ea_scan_info" in tables

        conn.close()


def test_ea_database_insert_resource():
    """Should insert and lookup resources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ea.db"
        conn = init_ea_db(db_path)
        db = EADatabase(conn)

        db.insert_resource(
            instance_id=12345,
            type_id=100,
            group_id=0,
            package_name="Test.package",
            pack="BaseGame",
        )

        result = db.lookup_instance(12345)
        assert result is not None
        assert result["package_name"] == "Test.package"

        conn.close()


def test_ea_database_lookup_not_found():
    """Should return None for unknown instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ea.db"
        conn = init_ea_db(db_path)
        db = EADatabase(conn)

        result = db.lookup_instance(99999)
        assert result is None

        conn.close()
