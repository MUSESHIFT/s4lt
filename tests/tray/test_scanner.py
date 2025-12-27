"""Tests for tray folder scanner."""

import tempfile
from pathlib import Path

from s4lt.tray.scanner import discover_tray_items, TrayItemType


def test_discover_empty_folder():
    """Empty folder returns empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        items = discover_tray_items(Path(tmpdir))
        assert items == []


def test_discover_household():
    """Discovers a household with all required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000012345678"

        # Create household files
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.householdbinary").touch()
        (tray_path / f"{item_id}.hhi").touch()
        (tray_path / f"{item_id}!00000001.hhi").touch()
        (tray_path / f"{item_id}!00000000_0x0.sgi").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert items[0]["id"] == item_id
        assert items[0]["type"] == TrayItemType.HOUSEHOLD


def test_discover_lot():
    """Discovers a lot with required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x00000000ABCDEF01"

        # Create lot files
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.blueprint").touch()
        (tray_path / f"{item_id}.bpi").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert items[0]["type"] == TrayItemType.LOT


def test_discover_room():
    """Discovers a room with required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x00000000DEADBEEF"

        # Create room files
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.room").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert items[0]["type"] == TrayItemType.ROOM


def test_groups_related_files():
    """Files with same ID prefix are grouped together."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        item_id = "0x0000000011111111"

        # Create household with 2 sims
        (tray_path / f"{item_id}.trayitem").touch()
        (tray_path / f"{item_id}.householdbinary").touch()
        (tray_path / f"{item_id}.hhi").touch()
        (tray_path / f"{item_id}!00000001.hhi").touch()
        (tray_path / f"{item_id}!00000000_0x0.sgi").touch()
        (tray_path / f"{item_id}!00000001_0x0.sgi").touch()

        items = discover_tray_items(tray_path)

        assert len(items) == 1
        assert len(items[0]["files"]) == 6
