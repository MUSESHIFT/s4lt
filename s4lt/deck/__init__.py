"""Steam Deck-specific features."""

from s4lt.deck.detection import is_steam_deck, get_deck_user
from s4lt.deck.storage import (
    RemovableDrive,
    StorageSummary,
    MoveResult,
    SymlinkIssue,
    list_removable_drives,
    get_sd_card_path,
    get_storage_summary,
    move_to_sd,
    move_to_internal,
    check_symlink_health,
)
from s4lt.deck.steam import (
    find_shortcuts_file,
    add_to_steam,
    remove_from_steam,
)

__all__ = [
    # Detection
    "is_steam_deck",
    "get_deck_user",
    # Storage
    "RemovableDrive",
    "StorageSummary",
    "MoveResult",
    "SymlinkIssue",
    "list_removable_drives",
    "get_sd_card_path",
    "get_storage_summary",
    "move_to_sd",
    "move_to_internal",
    "check_symlink_health",
    # Steam
    "find_shortcuts_file",
    "add_to_steam",
    "remove_from_steam",
]
