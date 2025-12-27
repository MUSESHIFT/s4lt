"""Tests for database operations."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import (
    upsert_mod,
    get_mod_by_path,
    delete_mod,
    insert_resource,
    get_all_mods,
    mark_broken,
)


def test_upsert_mod_insert():
    """upsert_mod should insert new mod."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(
            conn,
            path="Mods/Test/cool.package",
            filename="cool.package",
            size=1024,
            mtime=1234567890.0,
            hash="abc123",
            resource_count=5,
        )

        assert mod_id == 1
        conn.close()


def test_upsert_mod_update():
    """upsert_mod should update existing mod."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert
        mod_id1 = upsert_mod(conn, "test.package", "test.package", 100, 1.0, "hash1", 1)
        # Update
        mod_id2 = upsert_mod(conn, "test.package", "test.package", 200, 2.0, "hash2", 2)

        assert mod_id1 == mod_id2

        mod = get_mod_by_path(conn, "test.package")
        assert mod["size"] == 200
        assert mod["hash"] == "hash2"
        conn.close()


def test_get_mod_by_path():
    """get_mod_by_path should return mod or None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        assert get_mod_by_path(conn, "nonexistent.package") is None

        upsert_mod(conn, "exists.package", "exists.package", 100, 1.0, "hash", 1)
        mod = get_mod_by_path(conn, "exists.package")
        assert mod is not None
        assert mod["filename"] == "exists.package"
        conn.close()


def test_delete_mod():
    """delete_mod should remove mod and its resources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "test.package", "test.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x0333406C, 0, 123456, "Tuning", "test_tuning", 50, 100)

        delete_mod(conn, "test.package")

        assert get_mod_by_path(conn, "test.package") is None
        # Resources should cascade delete
        cursor = conn.execute("SELECT COUNT(*) FROM resources WHERE mod_id = ?", (mod_id,))
        assert cursor.fetchone()[0] == 0
        conn.close()


def test_insert_resource():
    """insert_resource should add resource to mod."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "test.package", "test.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x0333406C, 0, 123456, "Tuning", "my_tuning", 50, 100)

        cursor = conn.execute("SELECT * FROM resources WHERE mod_id = ?", (mod_id,))
        row = cursor.fetchone()
        assert row["type_id"] == 0x0333406C
        assert row["name"] == "my_tuning"
        conn.close()


def test_get_all_mods():
    """get_all_mods should return all mods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        upsert_mod(conn, "a.package", "a.package", 100, 1.0, "hash1", 1)
        upsert_mod(conn, "b.package", "b.package", 200, 2.0, "hash2", 2)

        mods = get_all_mods(conn)
        assert len(mods) == 2
        conn.close()


def test_mark_broken():
    """mark_broken should set broken flag and error message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "bad.package", "bad.package", 100, 1.0, "hash", 0)
        mark_broken(conn, "bad.package", "Invalid magic bytes")

        mod = get_mod_by_path(conn, "bad.package")
        assert mod["broken"] == 1
        assert mod["error_message"] == "Invalid magic bytes"
        conn.close()
