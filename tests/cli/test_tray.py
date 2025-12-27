"""Tests for tray CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from s4lt.cli.main import cli
from s4lt.config.settings import Settings
from tests.tray.fixtures import create_trayitem_v14


# Minimal PNG
MINIMAL_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82,
])


def create_test_tray_folder(path: Path):
    """Create a test tray folder with sample items."""
    # Household
    item_id = "0x0000000012345678"
    (path / f"{item_id}.trayitem").write_bytes(
        create_trayitem_v14(name="Test Family", item_type=1)
    )
    (path / f"{item_id}.householdbinary").write_bytes(b"\x00" * 100)
    (path / f"{item_id}.hhi").write_bytes(MINIMAL_PNG)

    # Lot
    lot_id = "0x00000000ABCDEF01"
    (path / f"{lot_id}.trayitem").write_bytes(
        create_trayitem_v14(name="Test House", item_type=2)
    )
    (path / f"{lot_id}.blueprint").write_bytes(b"\x00" * 100)
    (path / f"{lot_id}.bpi").write_bytes(MINIMAL_PNG)


def test_tray_list_finds_items():
    """tray list should find tray items."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        create_test_tray_folder(tray_path)

        settings = Settings(tray_path=tray_path)

        with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
            result = runner.invoke(cli, ["tray", "list", "--json"])

        assert result.exit_code == 0
        assert "Test Family" in result.output or "items" in result.output


def test_tray_list_empty_folder():
    """tray list should handle empty folder."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        settings = Settings(tray_path=tray_path)

        with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
            result = runner.invoke(cli, ["tray", "list"])

        assert result.exit_code == 0


def test_tray_list_filter_by_type():
    """tray list --type should filter results."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        create_test_tray_folder(tray_path)

        settings = Settings(tray_path=tray_path)

        with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
            result = runner.invoke(cli, ["tray", "list", "--type", "household", "--json"])

        assert result.exit_code == 0
        # Should only have household items
        assert "household" in result.output


def test_tray_info_shows_details():
    """tray info should show item details."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        create_test_tray_folder(tray_path)

        settings = Settings(tray_path=tray_path)

        with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
            result = runner.invoke(cli, ["tray", "info", "0x0000000012345678", "--json"])

        assert result.exit_code == 0
        assert "Test Family" in result.output


def test_tray_info_not_found():
    """tray info should error on invalid ID."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tray_path = Path(tmpdir)
        settings = Settings(tray_path=tray_path)

        with patch("s4lt.cli.commands.tray.get_settings", return_value=settings):
            result = runner.invoke(cli, ["tray", "info", "nonexistent", "--json"])

        assert result.exit_code == 1
        assert "error" in result.output.lower()
