"""S4LT Database - SQLite storage for mod index."""

from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import (
    upsert_mod,
    get_mod_by_path,
    delete_mod,
    insert_resource,
    delete_resources_for_mod,
    get_all_mods,
    mark_broken,
)

__all__ = [
    "init_db",
    "get_connection",
    "upsert_mod",
    "get_mod_by_path",
    "delete_mod",
    "insert_resource",
    "delete_resources_for_mod",
    "get_all_mods",
    "mark_broken",
]
