"""Integration tests for FastAPI REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Kochi" in data["demo_sector"]


def test_spatial_layers_endpoint():
    response = client.get("/api/spatial/layers")
    assert response.status_code == 200
    data = response.json()
    assert "pfz" in data
    assert "restricted_zones" in data
    assert len(data["pfz"]["features"]) >= 3
    assert len(data["restricted_zones"]["features"]) >= 2


def test_chat_endpoint_marine_safety():
    payload = {
        "message": "Is it safe to go fishing near Kochi tomorrow morning?",
        "conversation_id": "demo-001"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "marine_safety"
    assert data["location"]["name"] == "Kochi"
    assert data["risk"]["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert len(data["agent_trace"]) >= 5
    assert "PlannerAgent" in data["agent_trace"]
    assert "WeatherAgent" in data["agent_trace"]
    assert "OceanAgent" in data["agent_trace"]
    assert "GeospatialAgent" in data["agent_trace"]
    assert "RiskAssessmentAgent" in data["agent_trace"]
    assert "EvidenceAgent" in data["agent_trace"]
    assert len(data["evidence"]) >= 3


def test_chat_endpoint_pfz():
    payload = {
        "message": "Where is the nearest potential fishing zone?",
        "conversation_id": "demo-002"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "pfz_search"
    assert "GeospatialAgent" in data["agent_trace"]
    assert "WeatherAgent" not in data["agent_trace"]
    assert data["spatial_features"]["nearest_pfz"] is not None
