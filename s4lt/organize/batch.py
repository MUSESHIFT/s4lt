"""Batch enable/disable operations."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from s4lt.organize.toggle import enable_mod, disable_mod
from s4lt.organize.categorizer import categorize_mod, ModCategory
from s4lt.db.operations import get_all_mods


@dataclass
class BatchResult:
    """Result of a batch operation."""
    matched: int
    changed: int


def batch_disable(
    mods_path: Path,
    pattern: str | None = None,
    category: ModCategory | None = None,
    creator: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> BatchResult:
    """Disable multiple mods by filter.

    Args:
        mods_path: Path to the Mods folder
        pattern: Glob pattern to match (e.g., "CAS/*")
        category: Category to filter by
        creator: Creator name to filter by
        conn: Database connection (required for category filter)

    Returns:
        BatchResult with counts
    """
    if pattern:
        # Use glob pattern matching
        matched_files = list(mods_path.glob(pattern))
        # Filter to only .package files
        matched_files = [f for f in matched_files if f.suffix == ".package"]
    else:
        matched_files = list(mods_path.rglob("*.package"))

    if category and conn:
        # Filter by category
        mods = {m["path"]: m for m in get_all_mods(conn)}
        filtered = []
        for f in matched_files:
            rel_path = str(f.relative_to(mods_path))
            if rel_path in mods:
                mod = mods[rel_path]
                mod_category = categorize_mod(conn, mod["id"])
                if mod_category == category:
                    filtered.append(f)
        matched_files = filtered

    matched = len(matched_files)
    changed = 0
    for f in matched_files:
        if disable_mod(f):
            changed += 1

    return BatchResult(matched=matched, changed=changed)


def batch_enable(
    mods_path: Path,
    pattern: str | None = None,
    category: ModCategory | None = None,
    creator: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> BatchResult:
    """Enable multiple mods by filter.

    Args:
        mods_path: Path to the Mods folder
        pattern: Glob pattern to match (e.g., "*.disabled")
        category: Category to filter by
        creator: Creator name to filter by
        conn: Database connection (required for category filter)

    Returns:
        BatchResult with counts
    """
    if pattern:
        matched_files = list(mods_path.glob(pattern))
        matched_files = [f for f in matched_files if f.suffix == ".disabled"]
    else:
        matched_files = list(mods_path.rglob("*.disabled"))

    matched = len(matched_files)
    changed = 0
    for f in matched_files:
        if enable_mod(f):
            changed += 1

    return BatchResult(matched=matched, changed=changed)
