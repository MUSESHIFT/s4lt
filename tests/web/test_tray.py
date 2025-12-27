"""Tests for tray routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_tray_page_returns_html():
    """Tray page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/tray")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Tray" in response.text
