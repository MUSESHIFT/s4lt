"""Tests for mod scanner."""

import tempfile
from pathlib import Path

from s4lt.mods.scanner import discover_packages, categorize_changes
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod


def test_discover_packages_finds_packages():
    """discover_packages should find all .package files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir)

        # Create test packages
        (mods_path / "test1.package").touch()
        (mods_path / "test2.package").touch()
        (mods_path / "subdir").mkdir()
        (mods_path / "subdir" / "test3.package").touch()

        packages = discover_packages(mods_path)

        assert len(packages) == 3


def test_discover_packages_ignores_patterns():
    """discover_packages should ignore specified patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mods_path = Path(tmpdir)

        (mods_path / "good.package").touch()
        (mods_path / "__MACOSX").mkdir()
        (mods_path / "__MACOSX" / "bad.package").touch()

        packages = discover_packages(mods_path, ignore_patterns=["__MACOSX"])

        assert len(packages) == 1
        assert packages[0].name == "good.package"


def test_categorize_changes_new_files():
    """categorize_changes should identify new files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        pkg = mods_path / "new.package"
        pkg.write_bytes(b"DBPF" + b"\x00" * 92)

        disk_files = {pkg}
        new, modified, deleted = categorize_changes(conn, mods_path, disk_files)

        assert len(new) == 1
        assert len(modified) == 0
        assert len(deleted) == 0
        conn.close()


def test_categorize_changes_deleted_files():
    """categorize_changes should identify deleted files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        # Add mod to DB but not on disk
        upsert_mod(conn, "deleted.package", "deleted.package", 100, 1.0, "hash", 1)

        disk_files = set()
        new, modified, deleted = categorize_changes(conn, mods_path, disk_files)

        assert len(new) == 0
        assert len(modified) == 0
        assert len(deleted) == 1
        conn.close()
