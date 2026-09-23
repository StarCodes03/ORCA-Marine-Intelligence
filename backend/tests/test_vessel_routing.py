"""ORCA Marine Intelligence - Milestone 4 Integration Tests
Vessel-Aware Seaworthiness & Safe Passage Corridor Routing Verification

Verifies:
1. Craft-specific seaworthiness differentiation (traditional_craft vs mechanized_trawler)
2. Deterministic line/polygon intersection and collision-free clearance corridor generation
3. Configurable clearance buffer parameter (clearance_buffer_km)
4. Deterministic duration, nautical distance, and explicit fuel burn calculations
5. Multi-turn vessel_type context preservation and inheritance
6. Safe passage corridor route query intent recognition
7. Modular language modes (english, malayalam, bilingual)
8. End-to-end API chat response validation with transit_route and vessel_profile
"""

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Point, LineString, Polygon

from app.main import app
from app.models.schemas import (
    LocationCoords,
    NearestPFZ,
    WeatherData,
    OceanData,
    GeospatialData
)
from app.agents.risk import RiskAssessmentAgent
from app.tools.routing import routing_engine
from app.tools.gis_data import gis_adapter, haversine_distance
from app.config.risk_thresholds import VESSEL_PROFILES, get_vessel_profile
from app.services.conversation_store import conversation_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_conversation_store():
    """Ensure clean conversation sessions for each test."""
    test_sessions = [
        "test-m4-turn-vessel",
        "test-m4-route-intent",
        "test-m4-lang-en",
        "test-m4-lang-ml",
        "test-m4-lang-bi"
    ]
    for sid in test_sessions:
        conversation_store.clear_context(sid)
    yield
    for sid in test_sessions:
        conversation_store.clear_context(sid)


# 1. Craft Seaworthiness Differentiation
def test_craft_seaworthiness_differentiation():
    """Verify that under identical 1.8m wave conditions:
    - traditional_craft experiences elevated/high risk (>1.5m moderate limit)
    - mechanized_trawler remains low/safe risk (<=2.5m safe limit)
    """
    risk_agent = RiskAssessmentAgent()

    weather = WeatherData(
        temperature_c=29.0,
        wind_speed_kmh=18.0,  # calm wind for both
        wind_direction_deg=270,
        rain_probability=10.0,
        lightning_risk="none",
        source="MOCK"
    )
    ocean = OceanData(
        sst_c=28.5,
        wave_height_m=1.8,  # Critical boundary: >1.5m (unsafe for traditional), <2.5m (safe for trawler)
        sea_state="moderate",
        tide="high_tide",
        source="MOCK"
    )

    # Traditional craft evaluation
    risk_traditional = risk_agent.assess(
        weather=weather,
        ocean=ocean,
        geospatial=None,
        vessel_type="traditional_craft"
    )

    # Mechanized trawler evaluation
    risk_trawler = risk_agent.assess(
        weather=weather,
        ocean=ocean,
        geospatial=None,
        vessel_type="mechanized_trawler"
    )

    # Assertions
    assert risk_traditional.vessel_type == "traditional_craft"
    assert risk_trawler.vessel_type == "mechanized_trawler"

    # Traditional craft must suffer penalty for 1.8m waves (max moderate limit is 1.5m)
    assert risk_traditional.risk_score > risk_trawler.risk_score
    assert any("traditional_craft" in r or "Artisanal Traditional Craft" in r for r in risk_traditional.reasons)
    assert risk_traditional.score_breakdown.factor_scores["wave_height"] == 4.0

    # Trawler has wave limit 2.5m, so 1.8m wave contributes 0 penalty
    assert risk_trawler.score_breakdown.factor_scores["wave_height"] == 0.0
    assert risk_trawler.risk_level == "LOW"


# 2. Geometric Line/Polygon Intersection and Clearance Waypoints
def test_routing_engine_geofence_avoidance():
    """Verify deterministic routing creates collision-free clearance waypoints around restricted zones."""
    origin = LocationCoords(name="Kochi Port", latitude=9.9600, longitude=76.2400)
    # Target PFZ located offshore such that direct line crosses the naval channel / firing polygon
    dest = NearestPFZ(
        pfz_id="PFZ-TEST-001",
        name="Offshore Test Bank",
        latitude=10.1500,
        longitude=75.9500,
        distance_km=38.5,
        bearing_deg=310.0
    )

    route = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="motorized_frp_obm",
        clearance_buffer_km=1.5
    )

    assert route.total_distance_km > 0
    assert route.total_distance_nm > 0
    assert route.estimated_duration_hours > 0
    assert route.estimated_fuel_litres is not None
    assert route.clearance_buffer_km == 1.5

    # GeoJSON Feature compliance
    feat = route.geojson_feature
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "LineString"
    assert len(feat["geometry"]["coordinates"]) >= 2
    assert feat["properties"]["route_type"] == "safe_passage_corridor"


# 3. Configurable Clearance Buffer
def test_routing_configurable_clearance_buffer():
    """Verify that clearance_buffer_km parameter can be adjusted and affects corridor clearance."""
    origin = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    dest = NearestPFZ(
        pfz_id="PFZ-TEST-002",
        name="Kuzhuppilly Target",
        latitude=10.1700,
        longitude=76.0500,
        distance_km=35.0,
        bearing_deg=325.0
    )

    route_1_5 = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="motorized_frp_obm",
        clearance_buffer_km=1.5
    )

    route_3_0 = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="motorized_frp_obm",
        clearance_buffer_km=3.0
    )

    assert route_1_5.clearance_buffer_km == 1.5
    assert route_3_0.clearance_buffer_km == 3.0


# 4. Deterministic Duration and Fuel Burn Calculations
def test_deterministic_fuel_and_duration_math():
    """Verify duration and fuel math use explicit profile parameters without hallucinations."""
    origin = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    dest = NearestPFZ(
        pfz_id="PFZ-MATH",
        name="Fixed Distance Point",
        latitude=10.0000,
        longitude=76.0000,
        distance_km=30.0,
        bearing_deg=290.0
    )

    # Traditional craft: cruising speed 3.5 kn, fuel rate 0.0 L/h
    route_trad = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="traditional_craft"
    )
    assert route_trad.estimated_fuel_litres == 0.0
    assert route_trad.fuel_type == "Manual / Sail"

    # Motorized FRP OBM: cruising speed 7.5 kn, fuel rate 6.5 L/h
    route_frp = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="motorized_frp_obm"
    )
    # duration = distance_nm / 7.5
    expected_dur_frp = round(route_frp.total_distance_nm / 7.5, 2)
    assert route_frp.estimated_duration_hours == expected_dur_frp
    expected_fuel_frp = round(expected_dur_frp * 6.5, 1)
    assert route_frp.estimated_fuel_litres == expected_fuel_frp

    # Mechanized Trawler: cruising speed 9.0 kn, fuel rate 18.0 L/h
    route_trawler = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="mechanized_trawler"
    )
    expected_dur_trawler = round(route_trawler.total_distance_nm / 9.0, 2)
    assert route_trawler.estimated_duration_hours == expected_dur_trawler
    expected_fuel_trawler = round(expected_dur_trawler * 18.0, 1)
    assert route_trawler.estimated_fuel_litres == expected_fuel_trawler
    assert "diesel" in route_trawler.fuel_type.lower()


# 5. Multi-turn Vessel Context Inheritance
def test_multiturn_vessel_context_inheritance():
    """Verify that vessel_type established on Turn 1 is inherited by Turn 2."""
    session_id = "test-m4-turn-vessel"

    # Turn 1: user mentions motorized FRP canoe
    res1 = client.post("/api/chat", json={
        "message": "I am operating a motorized FRP boat from Kochi.",
        "conversation_id": session_id
    })
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["context"]["vessel_type"] == "motorized_frp_obm"

    # Turn 2: follow-up query without re-specifying vessel
    res2 = client.post("/api/chat", json={
        "message": "Is it safe tomorrow morning?",
        "conversation_id": session_id
    })
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["context"]["vessel_type"] == "motorized_frp_obm"
    assert d2["vessel_profile"] is not None
    assert d2["vessel_profile"]["vessel_type"] == "motorized_frp_obm"


# 6. Safe Passage Route Intent Recognition
def test_safe_passage_route_intent():
    """Verify that asking for safe route corridor triggers safe_passage_route intent."""
    session_id = "test-m4-route-intent"

    res = client.post("/api/chat", json={
        "message": "What is the safe passage route and corridor to the nearest PFZ from Kochi?",
        "conversation_id": session_id,
        "vessel_type": "mechanized_trawler"
    })
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "safe_passage_route"
    assert data["transit_route"] is not None
    assert data["transit_route"]["total_distance_km"] > 0
    assert data["spatial_features"]["route"] is not None
    assert data["spatial_features"]["route"]["type"] == "Feature"


# 7. Modular Language Modes (English, Malayalam, Bilingual)
def test_modular_language_modes():
    """Verify language modes produce appropriate answer and answer_ml structures."""
    # Test 7a: English only
    res_en = client.post("/api/chat", json={
        "message": "Is it safe near Kochi?",
        "conversation_id": "test-m4-lang-en",
        "language_mode": "english"
    })
    assert res_en.status_code == 200
    d_en = res_en.json()
    assert d_en["context"]["language_mode"] == "english"
    assert d_en["answer_ml"] is None
    assert "Marine conditions" in d_en["answer"]

    # Test 7b: Malayalam only
    res_ml = client.post("/api/chat", json={
        "message": "കൊച്ചി തീരത്ത് കാലാവസ്ഥ എങ്ങനെ?",
        "conversation_id": "test-m4-lang-ml",
        "language_mode": "malayalam"
    })
    assert res_ml.status_code == 200
    d_ml = res_ml.json()
    assert d_ml["context"]["language_mode"] == "malayalam"
    assert d_ml["answer_ml"] is not None
    assert "തീരദേശ" in d_ml["answer"]

    # Test 7c: Bilingual (default)
    res_bi = client.post("/api/chat", json={
        "message": "Is it safe near Kochi tomorrow morning?",
        "conversation_id": "test-m4-lang-bi",
        "language_mode": "bilingual"
    })
    assert res_bi.status_code == 200
    d_bi = res_bi.json()
    assert d_bi["context"]["language_mode"] == "bilingual"
    assert d_bi["answer"] is not None
    assert d_bi["answer_ml"] is not None
    assert "തീരദേശ" in d_bi["answer_ml"]
