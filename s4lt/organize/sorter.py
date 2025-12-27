"""Mod sorting and organization."""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from s4lt.organize.categorizer import categorize_mod, ModCategory
from s4lt.db.operations import get_all_mods


def normalize_creator(name: str) -> str:
    """Normalize creator name for consistent grouping.

    Args:
        name: Raw creator name

    Returns:
        Normalized name (title case)
    """
    return name.title()


def extract_creator(filename: str) -> str:
    """Extract creator name from mod filename.

    Parses common naming conventions:
    - SimsyCreator_CASHair.package -> Simsycreator
    - TS4-Bobby-Dress.package -> Bobby
    - Creator-ModName.package -> Creator

    Args:
        filename: Mod filename

    Returns:
        Creator name or "_Uncategorized"
    """
    patterns = [
        r"^TS4[-_]([A-Za-z0-9]+)[-_]",  # TS4-Bobby-Dress, TS4_Bobby_Dress
        r"^([A-Za-z0-9]+)_",             # SimsyCreator_Hair
        r"^([A-Za-z0-9]+)-",             # Creator-ModName
    ]

    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return normalize_creator(match.group(1))

    return "_Uncategorized"


@dataclass
class MoveOp:
    """A file move operation."""
    source: Path
    target: Path


@dataclass
class OrganizeResult:
    """Result of organize operation."""
    moves: list[MoveOp]
    executed: bool


def organize_by_type(
    conn: sqlite3.Connection,
    mods_path: Path,
    dry_run: bool = True,
) -> OrganizeResult:
    """Organize mods into category subfolders.

    Args:
        conn: Database connection
        mods_path: Path to the Mods folder
        dry_run: If True, don't actually move files

    Returns:
        OrganizeResult with list of moves
    """
    moves = []
    mods = get_all_mods(conn)

    for mod in mods:
        mod_path = mods_path / mod["path"]
        if not mod_path.exists():
            continue

        # Get or compute category
        category = categorize_mod(conn, mod["id"])
        target_dir = mods_path / category.value

        # Skip if already in correct folder
        if mod_path.parent == target_dir:
            continue

        target_path = target_dir / mod_path.name
        moves.append(MoveOp(source=mod_path, target=target_path))

    if not dry_run:
        for move in moves:
            move.target.parent.mkdir(parents=True, exist_ok=True)
            move.source.rename(move.target)
            # Update path in database
            new_rel_path = str(move.target.relative_to(mods_path))
            conn.execute(
                "UPDATE mods SET path = ? WHERE path = ?",
                (new_rel_path, str(move.source.relative_to(mods_path))),
            )
        conn.commit()

    return OrganizeResult(moves=moves, executed=not dry_run)
