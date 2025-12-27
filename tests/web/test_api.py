"""Tests for API routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_api_status():
    """API status endpoint should return JSON."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data
