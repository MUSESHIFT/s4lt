"""Tests for TrayItem high-level class."""

import tempfile
from pathlib import Path

import pytest

from s4lt.tray.item import TrayItem
from s4lt.tray.scanner import TrayItemType
from tests.tray.fixtures import create_trayitem_v14


# Minimal PNG for thumbnails
MINIMAL_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82,
])


def create_household_files(tray_path: Path, item_id: str, name: str = "Test Family"):
    """Helper to create a complete set of household files."""
    (tray_path / f"{item_id}.trayitem").write_bytes(
        create_trayitem_v14(name=name, item_type=1)
    )
    (tray_path / f"{item_id}.householdbinary").write_bytes(b"\x00" * 100)
    (tray_path / f"{item_id}.hhi").write_bytes(MINIMAL_PNG)
    (tray_path / f"{item_id}!00000001.hhi").write_bytes(MINIMAL_PNG)
    (tray_path / f"{item_id}!00000000_0x0.sgi").write_bytes(MINIMAL_PNG)


def test_trayitem_from_discovery():
    """Should create TrayItem from scanner output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id, "Smith Family")

        item = TrayItem.from_path(tray_path, item_id)

        assert item.id == item_id
        assert item.name == "Smith Family"
        assert item.item_type == TrayItemType.HOUSEHOLD


def test_trayitem_list_thumbnails():
    """Should list available thumbnail files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id)

        item = TrayItem.from_path(tray_path, item_id)
        thumbs = item.list_thumbnails()

        # Should find .hhi and .sgi files
        assert len(thumbs) >= 2


def test_trayitem_get_primary_thumbnail():
    """Should return primary thumbnail data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id)

        item = TrayItem.from_path(tray_path, item_id)
        data, fmt = item.get_primary_thumbnail()

        assert data is not None
        assert fmt == "png"


def test_trayitem_str_representation():
    """Should have readable string representation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"
        create_household_files(tray_path, item_id, "The Johnsons")

        item = TrayItem.from_path(tray_path, item_id)
        s = str(item)

        assert "Johnsons" in s
        assert "household" in s.lower()
