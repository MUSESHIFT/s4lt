"""Tests for EA CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from s4lt.cli.main import cli
from s4lt.config.settings import Settings


def test_ea_status_no_index():
    """ea status should warn if no index exists."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("s4lt.cli.commands.ea.get_ea_db_path", return_value=Path(tmpdir) / "nonexistent.db"):
            result = runner.invoke(cli, ["ea", "status"])

        assert "not indexed" in result.output.lower()
