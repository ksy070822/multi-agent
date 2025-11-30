"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from ..main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_triage_endpoint_minimal(client):
    """Test triage endpoint with minimal required data."""
    request_data = {
        "symptom_description": "My pet is not feeling well",
    }
    response = client.post("/api/triage", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "success" in data


def test_triage_endpoint_full(client):
    """Test triage endpoint with full data."""
    request_data = {
        "symptom_description": "My dog has been vomiting for 2 days and seems lethargic",
        "species": "dog",
        "breed": "Golden Retriever",
        "age": 5.0,
        "sex": "male",
        "weight": 30.0,
        "image_urls": ["https://example.com/image.jpg"],
        "metadata": {"owner_concern": "high"},
    }
    response = client.post("/api/triage", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "success" in data


def test_triage_endpoint_missing_required(client):
    """Test triage endpoint with missing required field."""
    request_data = {}
    response = client.post("/api/triage", json=request_data)
    # Should return 422 (validation error) or handle gracefully
    assert response.status_code in [200, 422]

