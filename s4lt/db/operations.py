"""Database CRUD operations."""

import sqlite3
import time
from typing import Any


def upsert_mod(
    conn: sqlite3.Connection,
    path: str,
    filename: str,
    size: int,
    mtime: float,
    hash: str,
    resource_count: int,
) -> int:
    """Insert or update a mod record. Returns mod_id."""
    cursor = conn.execute(
        """
        INSERT INTO mods (path, filename, size, mtime, hash, resource_count, scan_time, broken)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(path) DO UPDATE SET
            filename = excluded.filename,
            size = excluded.size,
            mtime = excluded.mtime,
            hash = excluded.hash,
            resource_count = excluded.resource_count,
            scan_time = excluded.scan_time,
            broken = 0,
            error_message = NULL
        RETURNING id
        """,
        (path, filename, size, mtime, hash, resource_count, time.time()),
    )
    row = cursor.fetchone()
    conn.commit()
    return row[0]


def get_mod_by_path(conn: sqlite3.Connection, path: str) -> dict[str, Any] | None:
    """Get mod by path, or None if not found."""
    cursor = conn.execute("SELECT * FROM mods WHERE path = ?", (path,))
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_mod(conn: sqlite3.Connection, path: str) -> None:
    """Delete a mod by path (cascades to resources)."""
    conn.execute("DELETE FROM mods WHERE path = ?", (path,))
    conn.commit()


def insert_resource(
    conn: sqlite3.Connection,
    mod_id: int,
    type_id: int,
    group_id: int,
    instance_id: int,
    type_name: str | None,
    name: str | None,
    compressed_size: int,
    uncompressed_size: int,
) -> int:
    """Insert a resource record. Returns resource_id."""
    cursor = conn.execute(
        """
        INSERT INTO resources (mod_id, type_id, group_id, instance_id, type_name, name, compressed_size, uncompressed_size)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (mod_id, type_id, group_id, instance_id, type_name, name, compressed_size, uncompressed_size),
    )
    row = cursor.fetchone()
    conn.commit()
    return row[0]


def delete_resources_for_mod(conn: sqlite3.Connection, mod_id: int) -> None:
    """Delete all resources for a mod."""
    conn.execute("DELETE FROM resources WHERE mod_id = ?", (mod_id,))
    conn.commit()


def get_all_mods(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Get all mods."""
    cursor = conn.execute("SELECT * FROM mods")
    return [dict(row) for row in cursor.fetchall()]


def mark_broken(conn: sqlite3.Connection, path: str, error: str) -> None:
    """Mark a mod as broken with error message."""
    conn.execute(
        "UPDATE mods SET broken = 1, error_message = ? WHERE path = ?",
        (error, path),
    )
    conn.commit()
