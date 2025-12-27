"""Tests for edit session management."""

import tempfile
from pathlib import Path

from s4lt.editor.session import EditSession, get_session, close_session


def test_get_session_creates_session():
    """get_session should create and cache a session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        session = get_session(str(pkg_path))
        assert session is not None
        assert session.path == pkg_path
        assert not session.has_unsaved_changes

        close_session(str(pkg_path))


def test_session_tracks_modifications():
    """Session should track when changes are made."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        session = get_session(str(pkg_path))
        assert not session.has_unsaved_changes

        session.add_resource(0x220557DA, 0, 0x123, b"test")
        assert session.has_unsaved_changes

        close_session(str(pkg_path))


def create_minimal_package() -> bytes:
    """Create a minimal valid DBPF package."""
    import struct
    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<I", header, 8, 1)
    struct.pack_into("<I", header, 36, 0)
    struct.pack_into("<I", header, 44, 4)
    struct.pack_into("<I", header, 64, 96)
    return bytes(header) + struct.pack("<I", 0)
