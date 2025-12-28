"""Tests for Steam Deck detection."""

from unittest.mock import patch
from pathlib import Path

from s4lt.deck.detection import is_steam_deck, get_deck_user


def test_is_steam_deck_true_when_deck_user_exists():
    """Should detect Steam Deck by /home/deck directory."""
    with patch.object(Path, "exists", return_value=True):
        assert is_steam_deck() is True


def test_is_steam_deck_false_on_desktop():
    """Should return False when not on Steam Deck."""
    with patch.object(Path, "exists", return_value=False):
        assert is_steam_deck() is False


def test_get_deck_user_returns_deck():
    """Should return 'deck' on Steam Deck."""
    with patch.object(Path, "exists", return_value=True):
        assert get_deck_user() == "deck"


def test_get_deck_user_returns_current_user():
    """Should return current user on desktop."""
    with patch.object(Path, "exists", return_value=False):
        with patch("os.environ.get", return_value="testuser"):
            assert get_deck_user() == "testuser"
