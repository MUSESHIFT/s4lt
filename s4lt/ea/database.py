"""EA content database operations."""

import sqlite3
from pathlib import Path
from typing import Any

from s4lt.config.settings import DATA_DIR


def get_ea_db_path() -> Path:
    """Get path to EA database."""
    return DATA_DIR / "ea.db"


def init_ea_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Initialize EA database with schema.

    Args:
        db_path: Path to database (defaults to standard location)

    Returns:
        Database connection
    """
    if db_path is None:
        db_path = get_ea_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ea_resources (
            instance_id INTEGER PRIMARY KEY,
            type_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            package_name TEXT NOT NULL,
            pack TEXT
        );

        CREATE TABLE IF NOT EXISTS ea_scan_info (
            id INTEGER PRIMARY KEY,
            game_path TEXT NOT NULL,
            last_scan TEXT NOT NULL,
            package_count INTEGER,
            resource_count INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_ea_type ON ea_resources(type_id);
    """)

    conn.commit()
    return conn


class EADatabase:
    """EA content database wrapper."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_resource(
        self,
        instance_id: int,
        type_id: int,
        group_id: int,
        package_name: str,
        pack: str | None = None,
    ) -> None:
        """Insert a resource (ignore duplicates)."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO ea_resources
            (instance_id, type_id, group_id, package_name, pack)
            VALUES (?, ?, ?, ?, ?)
            """,
            (instance_id, type_id, group_id, package_name, pack),
        )

    def insert_batch(self, resources: list[tuple]) -> None:
        """Insert multiple resources efficiently."""
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO ea_resources
            (instance_id, type_id, group_id, package_name, pack)
            VALUES (?, ?, ?, ?, ?)
            """,
            resources,
        )
        self.conn.commit()

    def lookup_instance(self, instance_id: int) -> dict[str, Any] | None:
        """Look up resource by instance ID."""
        cursor = self.conn.execute(
            "SELECT * FROM ea_resources WHERE instance_id = ?",
            (instance_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def lookup_tgi(self, type_id: int, group_id: int, instance_id: int) -> dict[str, Any] | None:
        """Look up resource by full TGI."""
        cursor = self.conn.execute(
            """
            SELECT * FROM ea_resources
            WHERE type_id = ? AND group_id = ? AND instance_id = ?
            """,
            (type_id, group_id, instance_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def is_ea_content(self, instance_id: int) -> bool:
        """Check if instance ID is EA content."""
        return self.lookup_instance(instance_id) is not None

    def save_scan_info(self, game_path: str, package_count: int, resource_count: int) -> None:
        """Save scan metadata."""
        from datetime import datetime

        self.conn.execute("DELETE FROM ea_scan_info")
        self.conn.execute(
            """
            INSERT INTO ea_scan_info (game_path, last_scan, package_count, resource_count)
            VALUES (?, ?, ?, ?)
            """,
            (game_path, datetime.now().isoformat(), package_count, resource_count),
        )
        self.conn.commit()

    def get_scan_info(self) -> dict[str, Any] | None:
        """Get last scan info."""
        cursor = self.conn.execute("SELECT * FROM ea_scan_info LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def count_resources(self) -> int:
        """Count total resources in index."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM ea_resources")
        return cursor.fetchone()[0]
