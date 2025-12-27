"""Mod folder scanner."""

import fnmatch
import sqlite3
from pathlib import Path

from s4lt.db.operations import get_all_mods


def discover_packages(
    mods_path: Path,
    include_subfolders: bool = True,
    ignore_patterns: list[str] | None = None,
) -> list[Path]:
    """Discover all .package files in the Mods folder.

    Args:
        mods_path: Path to the Mods folder
        include_subfolders: Whether to search subdirectories
        ignore_patterns: Folder/file patterns to ignore

    Returns:
        List of paths to .package files
    """
    if ignore_patterns is None:
        ignore_patterns = ["__MACOSX", ".DS_Store"]

    if include_subfolders:
        all_packages = list(mods_path.rglob("*.package"))
    else:
        all_packages = list(mods_path.glob("*.package"))

    # Filter out ignored patterns
    def should_include(path: Path) -> bool:
        for pattern in ignore_patterns:
            # Check if any parent folder matches
            for parent in path.parents:
                if fnmatch.fnmatch(parent.name, pattern):
                    return False
            # Check filename
            if fnmatch.fnmatch(path.name, pattern):
                return False
        return True

    return [p for p in all_packages if should_include(p)]


def categorize_changes(
    conn: sqlite3.Connection,
    mods_path: Path,
    disk_files: set[Path],
) -> tuple[set[Path], set[Path], set[str]]:
    """Categorize files into new, modified, and deleted.

    Args:
        conn: Database connection
        mods_path: Base Mods folder path
        disk_files: Set of .package files found on disk

    Returns:
        Tuple of (new_files, modified_files, deleted_paths)
    """
    # Get all mods from DB
    db_mods = {m["path"]: m for m in get_all_mods(conn)}
    db_paths = set(db_mods.keys())

    # Convert disk files to relative paths
    disk_relative = {}
    for path in disk_files:
        try:
            rel = str(path.relative_to(mods_path))
            disk_relative[rel] = path
        except ValueError:
            # Not relative to mods_path, use absolute
            disk_relative[str(path)] = path

    disk_path_set = set(disk_relative.keys())

    # Categorize
    new_paths = disk_path_set - db_paths
    deleted_paths = db_paths - disk_path_set
    existing_paths = disk_path_set & db_paths

    new_files = {disk_relative[p] for p in new_paths}
    deleted = deleted_paths

    # Check existing for modifications
    modified_files = set()
    for rel_path in existing_paths:
        disk_path = disk_relative[rel_path]
        db_record = db_mods[rel_path]

        stat = disk_path.stat()
        if stat.st_mtime != db_record["mtime"] or stat.st_size != db_record["size"]:
            modified_files.add(disk_path)

    return new_files, modified_files, deleted
