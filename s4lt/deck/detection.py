"""Steam Deck detection utilities."""

import os
from pathlib import Path


def is_steam_deck() -> bool:
    """Check if running on Steam Deck.

    Detects by checking for /home/deck directory.
    """
    return Path("/home/deck").exists()


def get_deck_user() -> str:
    """Get the appropriate user for media paths.

    Returns 'deck' on Steam Deck, current user otherwise.
    """
    if is_steam_deck():
        return "deck"
    return os.environ.get("USER", "user")
