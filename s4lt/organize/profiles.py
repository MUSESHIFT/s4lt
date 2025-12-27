"""Profile management for mod configurations."""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from s4lt.organize.exceptions import ProfileNotFoundError, ProfileExistsError


@dataclass
class Profile:
    """A saved mod configuration profile."""
    id: int
    name: str
    created_at: float
    is_auto: bool


@dataclass
class ProfileMod:
    """A mod's state in a profile."""
    mod_path: str
    enabled: bool


def create_profile(
    conn: sqlite3.Connection,
    name: str,
    is_auto: bool = False,
) -> Profile:
    """Create a new profile.

    Args:
        conn: Database connection
        name: Profile name
        is_auto: Whether this is an auto-created profile (e.g., _pre_vanilla)

    Returns:
        The created Profile

    Raises:
        ProfileExistsError: If profile with name already exists
    """
    created_at = time.time()
    try:
        cursor = conn.execute(
            "INSERT INTO profiles (name, created_at, is_auto) VALUES (?, ?, ?) RETURNING id",
            (name, created_at, int(is_auto)),
        )
        row = cursor.fetchone()
        conn.commit()
        return Profile(id=row[0], name=name, created_at=created_at, is_auto=is_auto)
    except sqlite3.IntegrityError:
        raise ProfileExistsError(f"Profile '{name}' already exists")


def get_profile(conn: sqlite3.Connection, name: str) -> Profile | None:
    """Get a profile by name.

    Args:
        conn: Database connection
        name: Profile name

    Returns:
        Profile if found, None otherwise
    """
    cursor = conn.execute(
        "SELECT id, name, created_at, is_auto FROM profiles WHERE name = ?",
        (name,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return Profile(id=row[0], name=row[1], created_at=row[2], is_auto=bool(row[3]))


def list_profiles(conn: sqlite3.Connection) -> list[Profile]:
    """List all profiles.

    Args:
        conn: Database connection

    Returns:
        List of all profiles
    """
    cursor = conn.execute(
        "SELECT id, name, created_at, is_auto FROM profiles ORDER BY name"
    )
    return [
        Profile(id=row[0], name=row[1], created_at=row[2], is_auto=bool(row[3]))
        for row in cursor.fetchall()
    ]


def delete_profile(conn: sqlite3.Connection, name: str) -> None:
    """Delete a profile by name.

    Args:
        conn: Database connection
        name: Profile name

    Raises:
        ProfileNotFoundError: If profile doesn't exist
    """
    cursor = conn.execute("DELETE FROM profiles WHERE name = ? RETURNING id", (name,))
    if cursor.fetchone() is None:
        raise ProfileNotFoundError(f"Profile '{name}' not found")
    conn.commit()


def save_profile_snapshot(
    conn: sqlite3.Connection,
    profile_id: int,
    mods_path: Path,
) -> int:
    """Save current mod states to a profile.

    Scans the mods folder for all .package and .package.disabled files
    and records their enabled/disabled state.

    Args:
        conn: Database connection
        profile_id: ID of the profile to save to
        mods_path: Path to the Mods folder

    Returns:
        Number of mods saved
    """
    # Clear existing mods for this profile
    conn.execute("DELETE FROM profile_mods WHERE profile_id = ?", (profile_id,))

    # Find all mods (enabled and disabled)
    enabled_mods = list(mods_path.rglob("*.package"))
    disabled_mods = list(mods_path.rglob("*.package.disabled"))

    count = 0
    for mod in enabled_mods:
        rel_path = str(mod.relative_to(mods_path))
        conn.execute(
            "INSERT INTO profile_mods (profile_id, mod_path, enabled) VALUES (?, ?, 1)",
            (profile_id, rel_path),
        )
        count += 1

    for mod in disabled_mods:
        rel_path = str(mod.relative_to(mods_path))
        conn.execute(
            "INSERT INTO profile_mods (profile_id, mod_path, enabled) VALUES (?, ?, 0)",
            (profile_id, rel_path),
        )
        count += 1

    conn.commit()
    return count


def get_profile_mods(conn: sqlite3.Connection, profile_id: int) -> list[ProfileMod]:
    """Get all mods for a profile.

    Args:
        conn: Database connection
        profile_id: ID of the profile

    Returns:
        List of ProfileMod entries
    """
    cursor = conn.execute(
        "SELECT mod_path, enabled FROM profile_mods WHERE profile_id = ?",
        (profile_id,),
    )
    return [
        ProfileMod(mod_path=row[0], enabled=bool(row[1]))
        for row in cursor.fetchall()
    ]


@dataclass
class SwitchResult:
    """Result of switching profiles."""
    enabled: int
    disabled: int


def switch_profile(
    conn: sqlite3.Connection,
    name: str,
    mods_path: Path,
) -> SwitchResult:
    """Switch to a profile by applying its mod states.

    Args:
        conn: Database connection
        name: Profile name to switch to
        mods_path: Path to the Mods folder

    Returns:
        SwitchResult with counts of enabled/disabled mods

    Raises:
        ProfileNotFoundError: If profile doesn't exist
    """
    from s4lt.organize.toggle import enable_mod, disable_mod

    profile = get_profile(conn, name)
    if profile is None:
        raise ProfileNotFoundError(f"Profile '{name}' not found")

    profile_mods = get_profile_mods(conn, profile.id)
    enabled_count = 0
    disabled_count = 0

    for pm in profile_mods:
        # Determine current file path (could be .package or .package.disabled)
        if pm.mod_path.endswith(".disabled"):
            # Profile has it as disabled, find current path
            base_path = pm.mod_path[:-9]  # Remove .disabled
            current_enabled = mods_path / base_path
            current_disabled = mods_path / pm.mod_path
        else:
            current_enabled = mods_path / pm.mod_path
            current_disabled = mods_path / (pm.mod_path + ".disabled")

        if pm.enabled:
            # Should be enabled
            if current_disabled.exists():
                enable_mod(current_disabled)
                enabled_count += 1
        else:
            # Should be disabled
            if current_enabled.exists():
                disable_mod(current_enabled)
                disabled_count += 1

    return SwitchResult(enabled=enabled_count, disabled=disabled_count)
