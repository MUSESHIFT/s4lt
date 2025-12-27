"""Tests for package viewer routes."""

import tempfile
import struct
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_package_view_returns_html():
    """Package view should return HTML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        app = create_app()
        client = TestClient(app)

        # URL encode the path
        encoded_path = quote(str(pkg_path), safe="")
        response = client.get(f"/package/{encoded_path}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


def create_minimal_package() -> bytes:
    """Create a minimal valid DBPF package."""
    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<I", header, 8, 1)
    struct.pack_into("<I", header, 36, 0)
    struct.pack_into("<I", header, 44, 4)
    struct.pack_into("<I", header, 64, 96)
    return bytes(header) + struct.pack("<I", 0)
