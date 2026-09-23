"""ORCA Marine Intelligence - Milestone 5 Integration Tests
Deterministic Marine Reasoning Integration Verification

Verifies:
1. End-to-end API chat temporal comparison ("Is morning or afternoon better for fishing near Kochi?")
2. Multi-window telemetry fetching and trend evaluation
3. Prototype Route Risk Index (0–10) calculation on safe passage routes
4. Multi-turn context preservation of temporal_comparison and route_risk
5. Attribution of conditions to evaluation point (origin) and disclaimer enforcement
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.conversation_store import conversation_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_conversation_store():
    """Ensure clean conversation sessions for each test."""
    test_sessions = [
        "test-m5-temporal",
        "test-m5-route-risk",
        "test-m5-multi-turn",
        "test-m5-ml-temporal"
    ]
    for sid in test_sessions:
        conversation_store.clear_context(sid)
    yield
    for sid in test_sessions:
        conversation_store.clear_context(sid)


def test_temporal_comparison_api_integration():
    """Verify end-to-end temporal comparison query produces structured metrics,
    deterministic trend, and audit evidence without hallucinating values.
    """
    res = client.post("/api/chat", json={
        "message": "Is morning or afternoon better for fishing near Kochi?",
        "conversation_id": "test-m5-temporal"
    })
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "temporal_comparison"
    assert data["temporal_comparison"] is not None

    tc = data["temporal_comparison"]
    assert tc["window_1"]["time_window"] == "tomorrow_morning"
    assert tc["window_2"]["time_window"] == "tomorrow_afternoon"
    assert isinstance(tc["delta_wave_m"], float)
    assert isinstance(tc["delta_wind_kmh"], float)
    assert isinstance(tc["delta_rain_pct"], float)
    assert isinstance(tc["delta_risk_score"], float)
    assert tc["trend"] in ["IMPROVING", "DETERIORATING", "STABLE", "INDETERMINATE"]
    assert "recommendation" in tc
    assert tc["evaluation_point"]["name"] == "Kochi"

    # Verify agent trace includes risk assessment and evidence synthesis
    trace = data["agent_trace"]
    assert "PlannerAgent" in trace
    assert "WeatherAgent" in trace
    assert "OceanAgent" in trace
    assert "RiskAssessmentAgent" in trace
    assert "EvidenceAgent" in trace

    # Evidentiary audit verification
    sources = [e["source"] for e in data["evidence"]]
    assert "TEMPORAL_REASONING_ENGINE" in sources

    # Context persistence verification
    ctx = data["context"]
    assert ctx is not None
    assert ctx["temporal_comparison"] is not None
    assert ctx["temporal_comparison"]["trend"] == tc["trend"]


def test_prototype_route_risk_api_integration():
    """Verify end-to-end safe passage routing calculates Prototype Route Risk Index (0–10)
    with 4-factor breakdown and explicit non-authoritative disclaimer.
    """
    res = client.post("/api/chat", json={
        "message": "Plan a safe passage route to the nearest PFZ for a motorized FRP boat from Kochi",
        "conversation_id": "test-m5-route-risk"
    })
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "safe_passage_route"
    assert data["transit_route"] is not None
    assert data["route_risk"] is not None

    rr = data["route_risk"]
    assert 0.0 <= rr["prototype_route_risk_index"] <= 10.0
    assert rr["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert rr["evaluation_point"]["name"] == "Kochi"
    assert rr["vessel_type"] == "motorized_frp_obm"

    # Factor breakdown assertions
    fb = rr["factor_breakdown"]
    assert "environmental_factor" in fb
    assert "vessel_stress_factor" in fb
    assert "distance_exposure_factor" in fb
    assert "geofence_interaction_factor" in fb

    # Disclaimer check: must state it is a prototype decision-support metric
    assert "prototype" in rr["disclaimer"].lower()
    assert "not an official maritime safety rating" in rr["disclaimer"].lower()

    # Evidentiary audit verification
    sources = [e["source"] for e in data["evidence"]]
    assert "PROTOTYPE_ROUTE_RISK_ENGINE" in sources

    # Context persistence
    ctx = data["context"]
    assert ctx is not None
    assert ctx["route_risk"] is not None
    assert ctx["route_risk"]["prototype_route_risk_index"] == rr["prototype_route_risk_index"]


def test_multi_turn_temporal_and_route_risk_context_retention():
    """Verify multi-turn flow where Turn 1 asks temporal comparison and Turn 2 requests route,
    preserving context and accumulating reasoning artifacts.
    """
    session_id = "test-m5-multi-turn"

    # Turn 1: Temporal condition comparison
    r1 = client.post("/api/chat", json={
        "message": "Compare morning and afternoon fishing conditions near Kochi",
        "conversation_id": session_id
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["temporal_comparison"] is not None
    assert d1["context"]["temporal_comparison"] is not None

    # Turn 2: Route request inheriting location and prior state
    r2 = client.post("/api/chat", json={
        "message": "Give me the safe route to the fishing zone for a traditional canoe",
        "conversation_id": session_id
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "safe_passage_route"
    assert d2["transit_route"] is not None
    assert d2["route_risk"] is not None
    assert d2["route_risk"]["vessel_type"] == "traditional_craft"

    # Verify context retains both
    ctx2 = d2["context"]
    assert ctx2["location"]["name"] == "Kochi"
    assert ctx2["vessel_type"] == "traditional_craft"
    assert ctx2["route_risk"] is not None
    assert ctx2["temporal_comparison"] is not None
