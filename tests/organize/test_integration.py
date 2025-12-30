"""Integration tests for organize module."""

import tempfile
from pathlib import Path

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import upsert_mod, insert_resource
from s4lt.organize import (
    ModCategory,
    categorize_mod,
    create_profile,
    save_profile_snapshot,
    switch_profile,
    toggle_vanilla,
    is_vanilla_mode,
    organize_by_type,
    enable_mod,
    disable_mod,
)


def test_full_organize_workflow():
    """Test complete workflow: scan, categorize, organize, profile, vanilla."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Setup: Create mods folder with test packages
        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        # CAS mod
        cas_mod = mods_path / "SimsyCreator_Hair.package"
        cas_mod.write_bytes(b"DBPF")
        mod_id1 = upsert_mod(conn, "SimsyCreator_Hair.package", "SimsyCreator_Hair.package", 100, 1.0, "h1", 1)
        insert_resource(conn, mod_id1, 0x034AEECB, 0, 1, "CASPart", None, 10, 20)

        # Script mod
        script_mod = mods_path / "MCCC_Main.package"
        script_mod.write_bytes(b"DBPF")
        mod_id2 = upsert_mod(conn, "MCCC_Main.package", "MCCC_Main.package", 100, 1.0, "h2", 1)
        insert_resource(conn, mod_id2, 0x9C07855E, 0, 1, "Script", None, 10, 20)

        # Step 1: Categorize mods
        cat1 = categorize_mod(conn, mod_id1)
        cat2 = categorize_mod(conn, mod_id2)
        assert cat1 == ModCategory.CAS
        assert cat2 == ModCategory.SCRIPT

        # Step 2: Organize by type
        result = organize_by_type(conn, mods_path, dry_run=False)
        assert len(result.moves) == 2
        assert (mods_path / "CAS CC" / "SimsyCreator_Hair.package").exists()
        assert (mods_path / "Script Mod" / "MCCC_Main.package").exists()

        # Step 3: Save profile
        profile = create_profile(conn, "gameplay")
        save_profile_snapshot(conn, profile.id, mods_path)

        # Step 4: Enter vanilla mode
        assert not is_vanilla_mode(conn)
        toggle_vanilla(conn, mods_path)
        assert is_vanilla_mode(conn)
        # All mods should be disabled
        assert (mods_path / "CAS CC" / "SimsyCreator_Hair.package.disabled").exists()
        assert (mods_path / "Script Mod" / "MCCC_Main.package.disabled").exists()

        # Step 5: Exit vanilla mode
        toggle_vanilla(conn, mods_path)
        assert not is_vanilla_mode(conn)
        # Mods should be restored
        assert (mods_path / "CAS CC" / "SimsyCreator_Hair.package").exists()
        assert (mods_path / "Script Mod" / "MCCC_Main.package").exists()

        # Step 6: Manually disable one mod
        disable_mod(mods_path / "CAS CC" / "SimsyCreator_Hair.package")
        assert (mods_path / "CAS CC" / "SimsyCreator_Hair.package.disabled").exists()

        # Step 7: Restore from profile
        switch_profile(conn, "gameplay", mods_path)
        # Should restore the disabled mod
        assert (mods_path / "CAS CC" / "SimsyCreator_Hair.package").exists()

        conn.close()


def test_profile_preserves_disabled_state():
    """Profile should preserve which mods were disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()
        (mods_path / "a.package").write_bytes(b"DBPF")
        (mods_path / "b.package.disabled").write_bytes(b"DBPF")

        # Save profile with mixed state
        profile = create_profile(conn, "mixed")
        save_profile_snapshot(conn, profile.id, mods_path)

        # Enable everything
        enable_mod(mods_path / "b.package.disabled")
        assert (mods_path / "b.package").exists()

        # Restore profile - should disable b again
        switch_profile(conn, "mixed", mods_path)
        assert (mods_path / "a.package").exists()
        assert (mods_path / "b.package.disabled").exists()

        conn.close()
