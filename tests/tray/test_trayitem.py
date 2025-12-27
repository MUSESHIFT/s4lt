"""Tests for trayitem metadata parsing."""

import tempfile
from pathlib import Path

import pytest

from s4lt.tray.trayitem import parse_trayitem, TrayItemMeta
from s4lt.tray.exceptions import TrayParseError
from tests.tray.fixtures import create_trayitem_v14


def test_parse_trayitem_extracts_name():
    """Should extract the name from trayitem file."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(create_trayitem_v14(name="My Test Household"))
        path = Path(f.name)

    try:
        meta = parse_trayitem(path)
        assert meta.name == "My Test Household"
    finally:
        path.unlink()


def test_parse_trayitem_extracts_type():
    """Should identify household vs lot vs room."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(create_trayitem_v14(name="Test Lot", item_type=2))
        path = Path(f.name)

    try:
        meta = parse_trayitem(path)
        assert meta.item_type == "lot"
    finally:
        path.unlink()


def test_parse_invalid_file_raises():
    """Invalid file should raise TrayParseError."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(b"not a valid trayitem")
        path = Path(f.name)

    try:
        with pytest.raises(TrayParseError):
            parse_trayitem(path)
    finally:
        path.unlink()


def test_trayitem_meta_properties():
    """TrayItemMeta should have expected properties."""
    with tempfile.NamedTemporaryFile(suffix=".trayitem", delete=False) as f:
        f.write(create_trayitem_v14(name="Test", item_type=1))
        path = Path(f.name)

    try:
        meta = parse_trayitem(path)
        assert hasattr(meta, "name")
        assert hasattr(meta, "item_type")
        assert hasattr(meta, "version")
    finally:
        path.unlink()
