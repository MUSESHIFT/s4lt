"""Tests for mods routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_mods_page_returns_html():
    """Mods page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/mods")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Mods" in response.text
