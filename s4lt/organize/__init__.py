"""Mod organization: categorization, profiles, and sorting."""

from s4lt.organize.categorizer import ModCategory, categorize_mod
from s4lt.organize.toggle import enable_mod, disable_mod, is_enabled
from s4lt.organize.profiles import (
    Profile,
    ProfileMod,
    SwitchResult,
    create_profile,
    get_profile,
    list_profiles,
    delete_profile,
    save_profile_snapshot,
    get_profile_mods,
    switch_profile,
)
from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode, VanillaResult
from s4lt.organize.sorter import (
    extract_creator,
    organize_by_type,
    organize_by_creator,
    MoveOp,
    OrganizeResult,
)
from s4lt.organize.batch import batch_enable, batch_disable, BatchResult
from s4lt.organize.exceptions import (
    OrganizeError,
    ProfileNotFoundError,
    ProfileExistsError,
    ModNotFoundError,
)

__all__ = [
    # Categories
    "ModCategory",
    "categorize_mod",
    # Toggle
    "enable_mod",
    "disable_mod",
    "is_enabled",
    # Profiles
    "Profile",
    "ProfileMod",
    "SwitchResult",
    "create_profile",
    "get_profile",
    "list_profiles",
    "delete_profile",
    "save_profile_snapshot",
    "get_profile_mods",
    "switch_profile",
    # Vanilla
    "toggle_vanilla",
    "is_vanilla_mode",
    "VanillaResult",
    # Sorting
    "extract_creator",
    "organize_by_type",
    "organize_by_creator",
    "MoveOp",
    "OrganizeResult",
    # Batch
    "batch_enable",
    "batch_disable",
    "BatchResult",
    # Exceptions
    "OrganizeError",
    "ProfileNotFoundError",
    "ProfileExistsError",
    "ModNotFoundError",
]
