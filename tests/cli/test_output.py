"""Tests for CLI output helpers."""

from s4lt.cli.output import format_size, format_path


def test_format_size_bytes():
    """format_size should format bytes."""
    assert format_size(500) == "500 B"


def test_format_size_kb():
    """format_size should format kilobytes."""
    assert format_size(1536) == "1.5 KB"


def test_format_size_mb():
    """format_size should format megabytes."""
    assert format_size(1572864) == "1.5 MB"


def test_format_path_short():
    """format_path should return short paths unchanged."""
    assert format_path("Mods/test.package", 50) == "Mods/test.package"


def test_format_path_truncate():
    """format_path should truncate long paths."""
    long_path = "Mods/Very/Long/Path/To/Some/Deeply/Nested/Package.package"
    result = format_path(long_path, 30)
    assert len(result) <= 30
    assert "..." in result
