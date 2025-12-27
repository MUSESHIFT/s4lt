"""Tests for profiles routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_profiles_page_returns_html():
    """Profiles page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/profiles")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Profiles" in response.text
