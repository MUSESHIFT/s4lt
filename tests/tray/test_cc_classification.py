"""Tests for CC classification."""

import tempfile
from pathlib import Path

from s4lt.tray.cc_tracker import TGI, CCReference, classify_tgis
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
