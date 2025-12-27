"""Tests for CC classification."""

import struct
import tempfile
from pathlib import Path

from s4lt.tray.cc_tracker import TGI, CCReference, classify_tgis, get_cc_summary, CC_RESOURCE_TYPES
from s4lt.tray.item import TrayItem
from s4lt.tray.scanner import TrayItemType
from s4lt.ea.database import init_ea_db, EADatabase
from s4lt.db.schema import init_db, get_connection


def test_classify_tgi_as_ea():
    """Should classify TGI found in EA index as 'ea'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup EA database with a resource
        ea_db_path = Path(tmpdir) / "ea.db"
        ea_conn = init_ea_db(ea_db_path)
        ea_db = EADatabase(ea_conn)
        ea_db.insert_resource(
            instance_id=12345,
            type_id=100,
            group_id=0,
            package_name="BaseGame.package",
            pack="BaseGame",
        )
        ea_conn.commit()

        # Setup mods database (empty)
        mods_db_path = Path(tmpdir) / "mods.db"
        init_db(mods_db_path)
        mods_conn = get_connection(mods_db_path)

        tgis = [TGI(100, 0, 12345)]
        results = classify_tgis(tgis, ea_conn, mods_conn)

        assert len(results) == 1
        assert results[0].source == "ea"

        ea_conn.close()
        mods_conn.close()


def test_classify_tgi_as_missing():
    """Should classify TGI not found anywhere as 'missing'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ea_db_path = Path(tmpdir) / "ea.db"
        ea_conn = init_ea_db(ea_db_path)

        mods_db_path = Path(tmpdir) / "mods.db"
        init_db(mods_db_path)
        mods_conn = get_connection(mods_db_path)

        tgis = [TGI(100, 0, 99999)]  # Unknown TGI
        results = classify_tgis(tgis, ea_conn, mods_conn)

        assert len(results) == 1
        assert results[0].source == "missing"

        ea_conn.close()
        mods_conn.close()


def test_classify_tgi_as_mod():
    """Should classify TGI found in mods index as 'mod' with path info."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup EA database (empty - resource not in EA)
        ea_db_path = Path(tmpdir) / "ea.db"
        ea_conn = init_ea_db(ea_db_path)

        # Setup mods database with a mod containing the resource
        mods_db_path = Path(tmpdir) / "mods.db"
        init_db(mods_db_path)
        mods_conn = get_connection(mods_db_path)

        # Insert a mod into the mods table
        mods_conn.execute(
            """
            INSERT INTO mods (path, filename, size, mtime, hash, resource_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/path/to/Mods/TestMod.package", "TestMod.package", 1024, 1234567890.0, "abc123", 1),
        )
        mod_id = mods_conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert a resource for this mod
        mods_conn.execute(
            """
            INSERT INTO resources (mod_id, type_id, group_id, instance_id)
            VALUES (?, ?, ?, ?)
            """,
            (mod_id, 100, 0, 54321),
        )
        mods_conn.commit()

        tgis = [TGI(100, 0, 54321)]
        results = classify_tgis(tgis, ea_conn, mods_conn)

        assert len(results) == 1
        assert results[0].source == "mod"
        assert results[0].mod_path == Path("/path/to/Mods/TestMod.package")
        assert results[0].mod_name == "TestMod.package"

        ea_conn.close()
        mods_conn.close()


def test_get_cc_summary():
    """Should return proper summary dict with mods, missing_count, ea_count, total."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a binary file with TGI patterns
        # TGI = type(4 bytes) + group(4 bytes) + instance(8 bytes)
        binary_path = tmpdir_path / "test123.householdbinary"

        # Get a known CC resource type
        cc_type = list(CC_RESOURCE_TYPES)[0]  # e.g., 0x034AEECB (CAS Part)

        # Create binary data with 3 TGIs:
        # - instance 11111: will be in EA
        # - instance 22222: will be in mod
        # - instance 33333: will be missing
        binary_data = b""
        binary_data += struct.pack("<I", cc_type)      # type_id
        binary_data += struct.pack("<I", 0)            # group_id
        binary_data += struct.pack("<Q", 11111)        # instance_id (EA)

        binary_data += struct.pack("<I", cc_type)      # type_id
        binary_data += struct.pack("<I", 0)            # group_id
        binary_data += struct.pack("<Q", 22222)        # instance_id (mod)

        binary_data += struct.pack("<I", cc_type)      # type_id
        binary_data += struct.pack("<I", 0)            # group_id
        binary_data += struct.pack("<Q", 33333)        # instance_id (missing)

        binary_path.write_bytes(binary_data)

        # Create TrayItem with the binary file
        item = TrayItem(
            item_id="test123",
            tray_path=tmpdir_path,
            files=[binary_path],
            item_type=TrayItemType.HOUSEHOLD,
        )

        # Setup EA database with one resource
        ea_db_path = tmpdir_path / "ea.db"
        ea_conn = init_ea_db(ea_db_path)
        ea_db = EADatabase(ea_conn)
        ea_db.insert_resource(
            instance_id=11111,
            type_id=cc_type,
            group_id=0,
            package_name="BaseGame.package",
            pack="BaseGame",
        )
        ea_conn.commit()

        # Setup mods database with one mod
        mods_db_path = tmpdir_path / "mods.db"
        init_db(mods_db_path)
        mods_conn = get_connection(mods_db_path)

        mods_conn.execute(
            """
            INSERT INTO mods (path, filename, size, mtime, hash, resource_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/path/to/Mods/CustomMod.package", "CustomMod.package", 2048, 1234567890.0, "def456", 1),
        )
        mod_id = mods_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        mods_conn.execute(
            """
            INSERT INTO resources (mod_id, type_id, group_id, instance_id)
            VALUES (?, ?, ?, ?)
            """,
            (mod_id, cc_type, 0, 22222),
        )
        mods_conn.commit()

        # Get summary
        summary = get_cc_summary(item, ea_conn, mods_conn)

        # Verify structure and counts
        assert isinstance(summary, dict)
        assert "mods" in summary
        assert "missing_count" in summary
        assert "ea_count" in summary
        assert "total" in summary

        assert summary["ea_count"] == 1
        assert summary["missing_count"] == 1
        assert summary["total"] == 3
        assert isinstance(summary["mods"], dict)
        assert "CustomMod.package" in summary["mods"]
        assert summary["mods"]["CustomMod.package"] == 1

        ea_conn.close()
        mods_conn.close()
