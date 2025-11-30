"""Smoke tests for basic functionality."""

import pytest
from fastapi.testclient import TestClient
from ..main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "petcare-advisor"


def test_triage_endpoint_basic(client):
    """Test triage endpoint with basic request."""
    request_data = {
        "symptom_description": "My dog has been vomiting for 2 days",
        "species": "dog",
        "age": 5.0,
    }
    response = client.post("/api/triage", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    # Note: In a real test, we'd mock the agents and verify the report structure

