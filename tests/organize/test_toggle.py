"""Tests for mod enable/disable toggle."""

import tempfile
from pathlib import Path

from s4lt.organize.toggle import enable_mod, disable_mod, is_enabled


def test_disable_mod_renames_file():
    """disable_mod should rename .package to .package.disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mod_path = Path(tmpdir) / "test.package"
        mod_path.write_bytes(b"DBPF")

        result = disable_mod(mod_path)

        assert result is True
        assert not mod_path.exists()
        assert (Path(tmpdir) / "test.package.disabled").exists()


def test_enable_mod_restores_file():
    """enable_mod should rename .package.disabled to .package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        disabled_path = Path(tmpdir) / "test.package.disabled"
        disabled_path.write_bytes(b"DBPF")

        result = enable_mod(disabled_path)

        assert result is True
        assert not disabled_path.exists()
        assert (Path(tmpdir) / "test.package").exists()


def test_disable_already_disabled_noop():
    """disable_mod on already disabled mod should return False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        disabled_path = Path(tmpdir) / "test.package.disabled"
        disabled_path.write_bytes(b"DBPF")

        result = disable_mod(disabled_path)

        assert result is False
        assert disabled_path.exists()


def test_enable_already_enabled_noop():
    """enable_mod on already enabled mod should return False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mod_path = Path(tmpdir) / "test.package"
        mod_path.write_bytes(b"DBPF")

        result = enable_mod(mod_path)

        assert result is False
        assert mod_path.exists()


def test_is_enabled_true():
    """is_enabled should return True for .package files."""
    assert is_enabled(Path("test.package")) is True


def test_is_enabled_false():
    """is_enabled should return False for .disabled files."""
    assert is_enabled(Path("test.package.disabled")) is False
