"""Tests for batch operations."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource
from s4lt.organize.batch import batch_enable, batch_disable, BatchResult
from s4lt.organize.categorizer import ModCategory


def test_batch_disable_by_pattern():
    """batch_disable should disable mods matching glob pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "CAS").mkdir()
        (mods_path / "CAS" / "a.package").write_bytes(b"DBPF")
        (mods_path / "CAS" / "b.package").write_bytes(b"DBPF")
        (mods_path / "other.package").write_bytes(b"DBPF")

        result = batch_disable(mods_path, pattern="CAS/*")

        assert result.matched == 2
        assert result.changed == 2
        assert (mods_path / "CAS" / "a.package.disabled").exists()
        assert (mods_path / "CAS" / "b.package.disabled").exists()
        assert (mods_path / "other.package").exists()  # Not matched


def test_batch_enable_by_pattern():
    """batch_enable should enable mods matching glob pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package.disabled").write_bytes(b"DBPF")
        (mods_path / "b.package.disabled").write_bytes(b"DBPF")

        result = batch_enable(mods_path, pattern="*.disabled")

        assert result.matched == 2
        assert result.changed == 2
        assert (mods_path / "a.package").exists()
        assert (mods_path / "b.package").exists()


def test_batch_disable_by_category():
    """batch_disable should disable mods by category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "cas.package").write_bytes(b"DBPF")
        (mods_path / "script.package").write_bytes(b"DBPF")

        # Add mods with categories
        mod_id1 = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "h1", 1)
        insert_resource(conn, mod_id1, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)
        mod_id2 = upsert_mod(conn, "script.package", "script.package", 100, 1.0, "h2", 1)
        insert_resource(conn, mod_id2, 0x9C07855E, 0, 1, "Script", None, 10, 20)

        result = batch_disable(mods_path, category=ModCategory.CAS, conn=conn)

        assert result.matched == 1
        assert result.changed == 1
        assert (mods_path / "cas.package.disabled").exists()
        assert (mods_path / "script.package").exists()  # Not CAS
        conn.close()
