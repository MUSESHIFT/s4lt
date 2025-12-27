"""Tests for mod categorizer."""

import tempfile
from pathlib import Path

from s4lt.organize.categorizer import ModCategory, TYPE_TO_CATEGORY, CATEGORY_PRIORITY


def test_mod_category_enum_values():
    """ModCategory should have all expected values."""
    assert ModCategory.CAS.value == "CAS"
    assert ModCategory.BUILD_BUY.value == "BuildBuy"
    assert ModCategory.SCRIPT.value == "Script"
    assert ModCategory.TUNING.value == "Tuning"
    assert ModCategory.OVERRIDE.value == "Override"
    assert ModCategory.GAMEPLAY.value == "Gameplay"
    assert ModCategory.UNKNOWN.value == "Unknown"


def test_type_to_category_cas():
    """CASPart type should map to CAS category."""
    assert TYPE_TO_CATEGORY.get(0x034AEECB) == ModCategory.CAS


def test_type_to_category_buildbuy():
    """ObjectCatalog type should map to BUILD_BUY category."""
    assert TYPE_TO_CATEGORY.get(0x319E4F1D) == ModCategory.BUILD_BUY


def test_type_to_category_script():
    """Python bytecode type should map to SCRIPT category."""
    assert TYPE_TO_CATEGORY.get(0x9C07855E) == ModCategory.SCRIPT


def test_category_priority_script_highest():
    """SCRIPT should have highest priority."""
    assert CATEGORY_PRIORITY[ModCategory.SCRIPT] > CATEGORY_PRIORITY[ModCategory.CAS]
    assert CATEGORY_PRIORITY[ModCategory.SCRIPT] > CATEGORY_PRIORITY[ModCategory.BUILD_BUY]


# Tests for categorize_mod function
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource
from s4lt.organize.categorizer import categorize_mod


def test_categorize_mod_cas_majority():
    """Mod with mostly CAS resources should be CAS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "cas.package", "cas.package", 100, 1.0, "hash", 5)
        # 3 CAS resources
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 2, "CASPart", None, 10, 20)
        insert_resource(conn, mod_id, 0x034AEECB, 0, 3, "CASPart", None, 10, 20)
        # 1 Tuning resource
        insert_resource(conn, mod_id, 0x0333406C, 0, 4, "Tuning", None, 10, 20)

        category = categorize_mod(conn, mod_id)

        assert category == ModCategory.CAS
        conn.close()


def test_categorize_mod_script_wins_tie():
    """Script should win over CAS in a tie."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "script.package", "script.package", 100, 1.0, "hash", 2)
        # 1 CAS, 1 Script
        insert_resource(conn, mod_id, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)
        insert_resource(conn, mod_id, 0x9C07855E, 0, 2, "Script", None, 10, 20)

        category = categorize_mod(conn, mod_id)

        assert category == ModCategory.SCRIPT
        conn.close()


def test_categorize_mod_unknown_resources():
    """Mod with unknown resource types should be UNKNOWN."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mod_id = upsert_mod(conn, "unknown.package", "unknown.package", 100, 1.0, "hash", 1)
        # Unknown type
        insert_resource(conn, mod_id, 0xDEADBEEF, 0, 1, "Unknown", None, 10, 20)

        category = categorize_mod(conn, mod_id)

        assert category == ModCategory.UNKNOWN
        conn.close()
