"""Duplicate detection between mods."""

import sqlite3
from dataclasses import dataclass, field


@dataclass
class DuplicateGroup:
    """A group of duplicate mods."""

    mods: list[dict] = field(default_factory=list)  # List of mod records
    match_type: str = "exact"  # "exact" or "content"
    wasted_bytes: int = 0


def find_duplicates(conn: sqlite3.Connection) -> list[DuplicateGroup]:
    """Find all duplicate mods.

    Tier 1: Exact hash matches (byte-for-byte identical)
    Tier 2: Content matches (same resources inside)

    Args:
        conn: Database connection

    Returns:
        List of DuplicateGroup objects
    """
    groups = []

    # Tier 1: Exact hash duplicates
    cursor = conn.execute("""
        SELECT hash, GROUP_CONCAT(id) as mod_ids, SUM(size) as total_size, MIN(size) as min_size
        FROM mods
        WHERE broken = 0
        GROUP BY hash
        HAVING COUNT(*) > 1
    """)

    exact_duplicate_mod_ids = set()

    for row in cursor.fetchall():
        hash_val, mod_ids_str, total_size, min_size = row
        mod_ids = [int(x) for x in mod_ids_str.split(",")]
        exact_duplicate_mod_ids.update(mod_ids)

        # Get mod details
        placeholders = ",".join("?" * len(mod_ids))
        mods_cursor = conn.execute(
            f"SELECT * FROM mods WHERE id IN ({placeholders}) ORDER BY mtime",
            mod_ids,
        )
        mods = [dict(r) for r in mods_cursor.fetchall()]

        wasted = total_size - min_size

        groups.append(DuplicateGroup(
            mods=mods,
            match_type="exact",
            wasted_bytes=wasted,
        ))

    # Tier 2: Content duplicates (same TGI fingerprint)
    # Skip mods already in exact duplicate groups
    cursor = conn.execute("""
        SELECT m.id, m.path, m.size,
            GROUP_CONCAT(r.type_id || '-' || r.group_id || '-' || r.instance_id ORDER BY r.type_id, r.group_id, r.instance_id) as fingerprint
        FROM mods m
        JOIN resources r ON m.id = r.mod_id
        WHERE m.broken = 0
        GROUP BY m.id
    """)

    # Group by fingerprint
    fingerprint_groups: dict[str, list[dict]] = {}
    for row in cursor.fetchall():
        mod_id, path, size, fingerprint = row
        if mod_id in exact_duplicate_mod_ids:
            continue
        if fingerprint not in fingerprint_groups:
            fingerprint_groups[fingerprint] = []
        fingerprint_groups[fingerprint].append({"id": mod_id, "path": path, "size": size})

    for fingerprint, mod_list in fingerprint_groups.items():
        if len(mod_list) > 1:
            # Get full mod details
            mod_ids = [m["id"] for m in mod_list]
            placeholders = ",".join("?" * len(mod_ids))
            mods_cursor = conn.execute(
                f"SELECT * FROM mods WHERE id IN ({placeholders}) ORDER BY mtime",
                mod_ids,
            )
            mods = [dict(r) for r in mods_cursor.fetchall()]

            total_size = sum(m["size"] for m in mods)
            min_size = min(m["size"] for m in mods)

            groups.append(DuplicateGroup(
                mods=mods,
                match_type="content",
                wasted_bytes=total_size - min_size,
            ))

    # Sort by wasted bytes (most waste first)
    groups.sort(key=lambda g: -g.wasted_bytes)

    return groups
