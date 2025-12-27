"""Tests for conflict detection."""

import tempfile
from pathlib import Path

from s4lt.mods.conflicts import find_conflicts, ConflictCluster
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource


def test_find_conflicts_no_conflicts():
    """find_conflicts should return empty list if no conflicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Two mods with different resources
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)

        insert_resource(conn, mod1, 0x0333406C, 0, 1111, "Tuning", "tuning1", 50, 100)
        insert_resource(conn, mod2, 0x0333406C, 0, 2222, "Tuning", "tuning2", 50, 100)

        conflicts = find_conflicts(conn)
        assert len(conflicts) == 0
        conn.close()


def test_find_conflicts_detects_conflict():
    """find_conflicts should detect TGI collision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Two mods with same TGI
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)

        # Same TGI in both mods
        insert_resource(conn, mod1, 0x0333406C, 0, 9999, "Tuning", "shared", 50, 100)
        insert_resource(conn, mod2, 0x0333406C, 0, 9999, "Tuning", "shared", 50, 100)

        conflicts = find_conflicts(conn)
        assert len(conflicts) == 1
        assert len(conflicts[0].mods) == 2
        conn.close()


def test_find_conflicts_groups_into_clusters():
    """find_conflicts should group related mods into clusters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Three mods sharing resources
        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)
        mod3 = upsert_mod(conn, "mod3.package", "mod3.package", 100, 1.0, "hash3", 1)

        # mod1 and mod2 share resource A
        insert_resource(conn, mod1, 0x0333406C, 0, 1000, "Tuning", "A", 50, 100)
        insert_resource(conn, mod2, 0x0333406C, 0, 1000, "Tuning", "A", 50, 100)

        # mod2 and mod3 share resource B
        insert_resource(conn, mod2, 0x0333406C, 0, 2000, "Tuning", "B", 50, 100)
        insert_resource(conn, mod3, 0x0333406C, 0, 2000, "Tuning", "B", 50, 100)

        conflicts = find_conflicts(conn)
        # Should be one cluster with all 3 mods
        assert len(conflicts) == 1
        assert len(conflicts[0].mods) == 3
        conn.close()


def test_conflict_severity():
    """Conflicts should have correct severity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod1 = upsert_mod(conn, "mod1.package", "mod1.package", 100, 1.0, "hash1", 1)
        mod2 = upsert_mod(conn, "mod2.package", "mod2.package", 100, 1.0, "hash2", 1)

        # CASPart conflict = HIGH severity
        insert_resource(conn, mod1, 0x034AEECB, 0, 9999, "CASPart", "cas", 50, 100)
        insert_resource(conn, mod2, 0x034AEECB, 0, 9999, "CASPart", "cas", 50, 100)

        conflicts = find_conflicts(conn)
        assert len(conflicts) == 1
        assert conflicts[0].severity == "high"
        conn.close()
