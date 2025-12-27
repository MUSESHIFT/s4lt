"""Vanilla mode toggle - disable/restore all mods."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from s4lt.organize.profiles import (
    create_profile,
    get_profile,
    delete_profile,
    save_profile_snapshot,
    switch_profile,
)
from s4lt.organize.toggle import disable_mod


PRE_VANILLA_PROFILE = "_pre_vanilla"


@dataclass
class VanillaResult:
    """Result of vanilla mode toggle."""
    is_vanilla: bool
    mods_changed: int


def is_vanilla_mode(conn: sqlite3.Connection) -> bool:
    """Check if currently in vanilla mode.

    Vanilla mode is detected by the existence of the _pre_vanilla profile.

    Args:
        conn: Database connection

    Returns:
        True if in vanilla mode
    """
    return get_profile(conn, PRE_VANILLA_PROFILE) is not None


def toggle_vanilla(conn: sqlite3.Connection, mods_path: Path) -> VanillaResult:
    """Toggle vanilla mode.

    First call: Save current state and disable all mods.
    Second call: Restore previous state and delete backup.

    Args:
        conn: Database connection
        mods_path: Path to the Mods folder

    Returns:
        VanillaResult indicating new state and mods changed
    """
    if is_vanilla_mode(conn):
        # Exit vanilla mode - restore previous state
        result = switch_profile(conn, PRE_VANILLA_PROFILE, mods_path)
        delete_profile(conn, PRE_VANILLA_PROFILE)
        return VanillaResult(
            is_vanilla=False,
            mods_changed=result.enabled + result.disabled,
        )
    else:
        # Enter vanilla mode - save state and disable all
        profile = create_profile(conn, PRE_VANILLA_PROFILE, is_auto=True)
        save_profile_snapshot(conn, profile.id, mods_path)

        # Disable all enabled mods
        enabled_mods = list(mods_path.rglob("*.package"))
        count = 0
        for mod in enabled_mods:
            if disable_mod(mod):
                count += 1

        return VanillaResult(is_vanilla=True, mods_changed=count)
