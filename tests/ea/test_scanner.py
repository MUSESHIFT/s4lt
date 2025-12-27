"""Tests for EA content scanner."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from s4lt.ea.scanner import discover_ea_packages, scan_ea_content
from s4lt.ea.database import init_ea_db, EADatabase


def test_discover_ea_packages():
    """Should find .package files in Data folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir)

        # Create fake package structure
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()
        (client_dir / "ClientFullBuild1.package").touch()

        sim_dir = game_path / "Data" / "Simulation" / "Gameplay"
        sim_dir.mkdir(parents=True)
        (sim_dir / "SimulationFullBuild0.package").touch()

        packages = discover_ea_packages(game_path)

        assert len(packages) == 3
        assert any("ClientFullBuild0" in str(p) for p in packages)


def test_discover_ea_packages_includes_dlc():
    """Should find packages in EP/GP/SP folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        game_path = Path(tmpdir)

        # Base game
        client_dir = game_path / "Data" / "Client"
        client_dir.mkdir(parents=True)
        (client_dir / "ClientFullBuild0.package").touch()

        # Expansion pack
        ep01_dir = game_path / "EP01" / "Data" / "Client"
        ep01_dir.mkdir(parents=True)
        (ep01_dir / "ClientFullBuild0.package").touch()

        packages = discover_ea_packages(game_path)

        assert len(packages) == 2
