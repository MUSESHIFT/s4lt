"""Tests for package viewer routes."""

import tempfile
import struct
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from s4lt.web import create_app
from s4lt.core.writer import write_package


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


def test_merge_page_returns_html():
    """Merge page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/package/merge")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Merge Packages" in response.text


def test_merge_check_returns_conflicts():
    """Check merge conflicts endpoint should return conflicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg1 = Path(tmpdir) / "a.package"
        pkg2 = Path(tmpdir) / "b.package"

        # Create packages with same resource (same TGI)
        create_package_with_resource(pkg1, 0x123, b"data1")
        create_package_with_resource(pkg2, 0x123, b"data2")

        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/package/merge/check",
            data={"paths": [str(pkg1), str(pkg2)]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "conflicts" in data
        assert len(data["conflicts"]) == 1


def test_merge_check_needs_two_packages():
    """Check merge should require at least 2 packages."""
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/package/merge/check",
        data={"paths": ["/some/path.package"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert "error" in data


def test_merge_execute_creates_output():
    """Execute merge should create output package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg1 = Path(tmpdir) / "a.package"
        pkg2 = Path(tmpdir) / "b.package"
        output = Path(tmpdir) / "merged.package"

        create_package_with_resource(pkg1, 0x111, b"data1")
        create_package_with_resource(pkg2, 0x222, b"data2")

        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/package/merge/execute",
            data={
                "paths": [str(pkg1), str(pkg2)],
                "output": str(output),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "merged"
        assert output.exists()


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


def create_package_with_resource(path: Path, instance_id: int, data: bytes) -> None:
    """Create a package with one resource."""
    resources = [{
        "type_id": 0x220557DA,
        "group_id": 0,
        "instance_id": instance_id,
        "data": data,
        "compress": False,
    }]
    write_package(path, resources, create_backup=False)
