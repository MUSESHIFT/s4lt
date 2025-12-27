"""Tests for duplicate detection."""

import tempfile
from pathlib import Path

from s4lt.mods.duplicates import find_duplicates, DuplicateGroup
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource


def test_find_duplicates_exact_hash():
    """find_duplicates should find exact hash matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Same hash
        upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "samehash", 1)
        upsert_mod(conn, "mod2.package", "mod2.package", 100, 2.0, "samehash", 1)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 1
        assert duplicates[0].match_type == "exact"
        assert len(duplicates[0].mods) == 2
        conn.close()


def test_find_duplicates_no_duplicates():
    """find_duplicates should return empty if no duplicates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        upsert_mod(conn, "mod2.package", "mod2.package", 100, 2.0, "hash2", 1)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 0
        conn.close()


def test_find_duplicates_content_match():
    """find_duplicates should find content matches (same TGIs)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Different hashes but same resources
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 2)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 200, 2.0, "hash2", 2)

        # Same resources in both
        insert_resource(conn, mod1, 0x0333406C, 0, 1111, "Tuning", "t1", 50, 100)
        insert_resource(conn, mod1, 0x034AEECB, 0, 2222, "CASPart", "c1", 50, 100)

        insert_resource(conn, mod2, 0x0333406C, 0, 1111, "Tuning", "t1", 50, 100)
        insert_resource(conn, mod2, 0x034AEECB, 0, 2222, "CASPart", "c1", 50, 100)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 1
        assert duplicates[0].match_type == "content"
        conn.close()


def test_duplicate_wasted_bytes():
    """DuplicateGroup should calculate wasted bytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # 3 copies of same file, 1000 bytes each
        upsert_mod(conn, "mod1.package", "mod1.package", 1000, 1.0, "samehash", 1)
        upsert_mod(conn, "mod2.package", "mod2.package", 1000, 2.0, "samehash", 1)
        upsert_mod(conn, "mod3.package", "mod3.package", 1000, 3.0, "samehash", 1)

        duplicates = find_duplicates(conn)
        assert len(duplicates) == 1
        # Wasted = total - one copy = 3000 - 1000 = 2000
        assert duplicates[0].wasted_bytes == 2000
        conn.close()
