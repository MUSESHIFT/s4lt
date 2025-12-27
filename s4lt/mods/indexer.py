"""Package indexer - extracts resources and metadata."""

import hashlib
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from s4lt.core import Package, DBPFError
from s4lt.db.operations import (
    upsert_mod,
    insert_resource,
    delete_resources_for_mod,
    mark_broken,
)


def compute_hash(path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_tuning_name(data: bytes) -> str | None:
    """Extract human-readable name from tuning XML.

    Args:
        data: Raw resource data

    Returns:
        Name if found, None otherwise
    """
    if not data.startswith(b"<?xml"):
        return None

    try:
        root = ET.fromstring(data)

        # Try n attribute on root (most common)
        if name := root.get("n"):
            return name

        # Try display_name or name element
        for elem in root.iter("T"):
            attr_name = elem.get("n")
            if attr_name in ("display_name", "name") and elem.text:
                return elem.text

        # Fallback to s attribute
        return root.get("s")

    except ET.ParseError:
        return None


def index_package(
    conn: sqlite3.Connection,
    mods_path: Path,
    package_path: Path,
) -> int | None:
    """Index a package file into the database.

    Args:
        conn: Database connection
        mods_path: Base Mods folder path
        package_path: Path to the .package file

    Returns:
        mod_id if successful, None if failed
    """
    try:
        rel_path = str(package_path.relative_to(mods_path))
    except ValueError:
        rel_path = str(package_path)

    stat = package_path.stat()
    file_hash = compute_hash(package_path)

    try:
        with Package.open(package_path) as pkg:
            # Upsert mod record
            mod_id = upsert_mod(
                conn,
                path=rel_path,
                filename=package_path.name,
                size=stat.st_size,
                mtime=stat.st_mtime,
                hash=file_hash,
                resource_count=len(pkg.resources),
            )

            # Clear old resources and add new ones
            delete_resources_for_mod(conn, mod_id)

            for resource in pkg.resources:
                # Try to extract name for tuning resources
                name = None
                if resource.type_name == "Tuning":
                    try:
                        data = resource.extract()
                        name = extract_tuning_name(data)
                    except Exception:
                        pass

                insert_resource(
                    conn,
                    mod_id=mod_id,
                    type_id=resource.type_id,
                    group_id=resource.group_id,
                    instance_id=resource.instance_id,
                    type_name=resource.type_name,
                    name=name,
                    compressed_size=resource.compressed_size,
                    uncompressed_size=resource.uncompressed_size,
                )

            return mod_id

    except DBPFError as e:
        # Mark as broken but still record the file
        mod_id = upsert_mod(
            conn,
            path=rel_path,
            filename=package_path.name,
            size=stat.st_size,
            mtime=stat.st_mtime,
            hash=file_hash,
            resource_count=0,
        )
        mark_broken(conn, rel_path, str(e))
        return None

    except Exception as e:
        # Unexpected error
        mod_id = upsert_mod(
            conn,
            path=rel_path,
            filename=package_path.name,
            size=stat.st_size,
            mtime=stat.st_mtime,
            hash=file_hash,
            resource_count=0,
        )
        mark_broken(conn, rel_path, f"Unexpected error: {e}")
        return None
