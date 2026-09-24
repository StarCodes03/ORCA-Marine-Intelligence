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
        "test-m5-ml-temporal",
        "test-m5-candidates",
        "test-m5-radial",
        "test-m5-safe-fail",
        "test-m5-ordinal-fail",
        "test-m5-geofence"
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


def test_radial_filter_api_integration():
    """Verify end-to-end radial PFZ candidate filtering:
    - Filters targets within specified radius
    - Sorts targets by distance ascending
    - Emits SPATIAL_CANDIDATE_FILTER evidence claim
    - Enforces snapshot notice and unavailable fields
    """
    res = client.post("/api/chat", json={
        "message": "Show PFZ targets within 30 km of Kochi",
        "conversation_id": "test-m5-radial"
    })
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "pfz_radius_filter"
    assert len(data["candidate_pfzs"]) == 9

    # Verify deterministic sorting by distance
    dists = [c["distance_km"] for c in data["candidate_pfzs"]]
    assert dists == sorted(dists)

    # First two targets must be Kuzhuppilly and Cherai
    assert data["candidate_pfzs"][0]["landing_centre"] == "Kuzhuppilly"
    assert data["candidate_pfzs"][1]["landing_centre"] == "Cherai"

    # Evidence verification
    sources = [e["source"] for e in data["evidence"]]
    assert "SPATIAL_CANDIDATE_FILTER" in sources

    # Context persistence
    ctx = data["context"]
    assert ctx is not None
    assert len(ctx["candidate_pfzs"]) == 9
    assert ctx["candidate_pfzs"][0]["landing_centre"] == "Kuzhuppilly"

    # Answer text verification
    assert "9" in data["answer"]
    assert "Kuzhuppilly" in data["answer"]
    assert "Cherai" in data["answer"]
    assert "Historical snapshot notice" in data["answer"]


def test_candidate_multi_turn_flow():
    """Verify 5-turn candidate conversation flow:
    Turn 1: Radial filter ("Show PFZ targets within 30 km of Kochi")
    Turn 2: Closest referent ("Which one is closest?")
    Turn 3: Pair comparison ("Compare the first and second")
    Turn 4: Ordinal referent ("How far is the second one?")
    Turn 5: Direct-route geofence check ("Is there a restricted zone between me and that target?")
    """
    session_id = "test-m5-candidates"

    # Turn 1: Radial filter
    r1 = client.post("/api/chat", json={
        "message": "Show PFZ targets within 30 km of Kochi",
        "conversation_id": session_id
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["intent"] == "pfz_radius_filter"
    assert len(d1["candidate_pfzs"]) == 9

    # Turn 2: Which one is closest?
    r2 = client.post("/api/chat", json={
        "message": "Which one is closest?",
        "conversation_id": session_id
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "pfz_distance"
    assert "Kuzhuppilly" in d2["answer"]
    assert d2["context"]["selected_pfz"]["landing_centre"] == "Kuzhuppilly"

    # Turn 3: Compare the first and second
    r3 = client.post("/api/chat", json={
        "message": "Compare the first and second",
        "conversation_id": session_id
    })
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["intent"] == "pfz_comparison"
    assert d3["pfz_comparison"] is not None

    comp = d3["pfz_comparison"]
    assert comp["target_a"]["landing_centre"] == "Kuzhuppilly"
    assert comp["target_b"]["landing_centre"] == "Cherai"
    assert "Kuzhuppilly" in comp["closer_target"]
    assert comp["distance_difference_km"] == pytest.approx(0.09, 0.02)
    assert comp["geofence_status_a"] == "INTERSECTS_RESTRICTED_ZONE"
    assert comp["geofence_status_b"] == "INTERSECTS_RESTRICTED_ZONE"
    assert len(comp["unavailable_fields"]) >= 5
    assert "historical" in comp["disclaimer"].lower()

    sources_3 = [e["source"] for e in d3["evidence"]]
    assert "CANDIDATE_COMPARISON_ENGINE" in sources_3

    # Turn 4: How far is the second one?
    r4 = client.post("/api/chat", json={
        "message": "How far is the second one?",
        "conversation_id": session_id
    })
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["intent"] == "pfz_distance"
    assert "Cherai" in d4["answer"]
    assert d4["context"]["selected_pfz"]["landing_centre"] == "Cherai"

    # Turn 5: Is there a restricted zone between me and that target?
    r5 = client.post("/api/chat", json={
        "message": "Is there a restricted zone between me and that target?",
        "conversation_id": session_id
    })
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["intent"] == "pfz_geofence_check"
    assert d5["geospatial"]["direct_route_geofence_status"] == "INTERSECTS_RESTRICTED_ZONE"
    assert len(d5["geospatial"]["direct_route_intersected_zones"]) > 0

    sources_5 = [e["source"] for e in d5["evidence"]]
    assert "DIRECT_ROUTE_GEOFENCE_ENGINE" in sources_5
    assert "RESTRICTED ZONE INTERSECTION DETECTED" in d5["answer"]


def test_candidate_referent_safe_failure_without_candidates():
    """Verify safe failure when asking to compare candidates without prior candidates in context."""
    session_id = "test-m5-safe-fail"
    res = client.post("/api/chat", json={
        "message": "Compare the first and second",
        "conversation_id": session_id
    })
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "clarification_needed"
    assert "No candidate PFZ targets are currently active" in data["answer"]


def test_candidate_referent_ordinal_out_of_range():
    """Verify safe failure when requesting an ordinal beyond the number of candidates."""
    session_id = "test-m5-ordinal-fail"

    # Turn 1: 2 candidates within 25 km
    r1 = client.post("/api/chat", json={
        "message": "What PFZ targets are within 25 km of Kochi?",
        "conversation_id": session_id
    })
    assert r1.status_code == 200
    assert len(r1.json()["candidate_pfzs"]) == 2

    # Turn 2: Ask for 4th target (out of range)
    r2 = client.post("/api/chat", json={
        "message": "How far is the fourth one?",
        "conversation_id": session_id
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "clarification_needed"
    assert "No candidate PFZ targets are currently active" in d2["answer"]
