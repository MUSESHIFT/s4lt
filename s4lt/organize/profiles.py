"""Profile management for mod configurations."""

import sqlite3
import time
from dataclasses import dataclass

from s4lt.organize.exceptions import ProfileNotFoundError, ProfileExistsError


@dataclass
class Profile:
    """A saved mod configuration profile."""
    id: int
    name: str
    created_at: float
    is_auto: bool


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
