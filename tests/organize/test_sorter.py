"""Tests for mod sorter."""

import tempfile
from pathlib import Path

from s4lt.organize.sorter import extract_creator, normalize_creator


def test_extract_creator_underscore():
    """extract_creator should parse underscore prefix."""
    assert extract_creator("SimsyCreator_CASHair.package") == "Simsycreator"


def test_extract_creator_ts4_prefix():
    """extract_creator should parse TS4 prefix."""
    assert extract_creator("TS4-Bobby-Dress.package") == "Bobby"
    assert extract_creator("TS4_Bobby_Dress.package") == "Bobby"


def test_extract_creator_dash():
    """extract_creator should parse dash prefix."""
    assert extract_creator("Creator-ModName.package") == "Creator"


def test_extract_creator_unknown():
    """extract_creator should return _Uncategorized for unknown patterns."""
    assert extract_creator("randomfile.package") == "_Uncategorized"


def test_normalize_creator():
    """normalize_creator should title case."""
    assert normalize_creator("SIMSY") == "Simsy"
    assert normalize_creator("simsy") == "Simsy"
    assert normalize_creator("SimsyCreator") == "Simsycreator"


# Tests for organize_by_type
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource
from s4lt.organize.sorter import organize_by_type, MoveOp


def test_organize_by_type_dry_run():
    """organize_by_type dry run should not move files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "cas.package"
        mod_file.write_bytes(b"DBPF")

        # Add to DB with CAS resources
        mod_id = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)

        result = organize_by_type(conn, mods_path, dry_run=True)

        # File should NOT move in dry run
        assert mod_file.exists()
        assert len(result.moves) == 1
        assert result.moves[0].target == mods_path / "CAS CC" / "cas.package"
        conn.close()


def test_organize_by_type_moves_files():
    """organize_by_type should move files to category folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "cas.package"
        mod_file.write_bytes(b"DBPF")

        mod_id = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "hash", 1)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)

        result = organize_by_type(conn, mods_path, dry_run=False)

        # File should move
        assert not mod_file.exists()
        assert (mods_path / "CAS CC" / "cas.package").exists()
        assert len(result.moves) == 1
        conn.close()


# Tests for organize_by_creator
from s4lt.organize.sorter import organize_by_creator


def test_organize_by_creator_moves_files():
    """organize_by_creator should move files to creator folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "SimsyCreator_Hair.package"
        mod_file.write_bytes(b"DBPF")

        upsert_mod(conn, "SimsyCreator_Hair.package", "SimsyCreator_Hair.package", 100, 1.0, "hash", 1)

        result = organize_by_creator(conn, mods_path, dry_run=False)

        assert not mod_file.exists()
        assert (mods_path / "Simsycreator" / "SimsyCreator_Hair.package").exists()
        assert len(result.moves) == 1
        conn.close()


def test_organize_by_creator_uncategorized():
    """organize_by_creator should put unknown to _Uncategorized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        mod_file = mods_path / "random.package"
        mod_file.write_bytes(b"DBPF")

        upsert_mod(conn, "random.package", "random.package", 100, 1.0, "hash", 1)

        result = organize_by_creator(conn, mods_path, dry_run=False)

        assert (mods_path / "_Uncategorized" / "random.package").exists()
        conn.close()
