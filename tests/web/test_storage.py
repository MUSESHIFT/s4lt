"""Tests for storage management page."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_storage_page_returns_html():
    """Storage page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/storage")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Storage Management" in response.text
