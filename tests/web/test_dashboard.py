"""Tests for dashboard routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_dashboard_returns_html():
    """Dashboard should return HTML page."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "S4LT" in response.text
