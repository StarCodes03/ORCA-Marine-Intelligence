"""ORCA Marine Intelligence - M5 Advanced Marine Reasoning Regression Suite

Tests cover:
1. Destination-aware routing (place names, coordinates, PFZ referents).
2. Route alternatives generation (Direct vs Safe Corridor vs Seaward clearance).
3. Corridor environmental sampling points and explicit limitation disclosure.
4. Temporal route risk reasoning (multi-window route risk delta).
5. Route alternative comparison queries and provenance audit.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.context_resolver import ContextResolver
from app.models.schemas import LocationCoords, ConversationContext, NearestPFZ
from app.tools.routing import routing_engine
from app.tools.route_risk import route_risk_calculator

client = TestClient(app)


def test_destination_extraction_named_places():
    """Verify destination resolution for coastal ports and landing centres."""
    text1 = "Calculate safe passage corridor from Kochi to Munambam"
    plan1, _ = ContextResolver.resolve(message=text1)
    assert plan1.location is not None
    assert plan1.location.name == "Kochi"
    assert plan1.destination is not None
    assert plan1.destination.name == "Munambam"
    assert round(plan1.destination.latitude, 2) == 10.18
    assert round(plan1.destination.longitude, 2) == 76.17

    text2 = "Plan a route from Chellanam to Vypin"
    plan2, _ = ContextResolver.resolve(message=text2)
    assert plan2.location.name == "Chellanam"
    assert plan2.destination.name == "Vypin"


def test_destination_extraction_coordinates():
    """Verify destination resolution using explicit latitude/longitude."""
    text = "Plot a safe route from Kochi to 9.8500, 76.1500"
    plan, _ = ContextResolver.resolve(message=text)
    assert plan.location.name == "Kochi"
    assert plan.destination is not None
    assert plan.destination.latitude == 9.85
    assert plan.destination.longitude == 76.15


def test_route_alternatives_generation():
    """Verify routing engine generates Direct, Safe Corridor, and Seaward alternatives."""
    origin = LocationCoords(name="Kochi Port", latitude=9.9312, longitude=76.2673)
    dest = LocationCoords(name="Munambam Harbor", latitude=10.1800, longitude=76.1700)

    route = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="motorized_frp_obm"
    )

    assert route.total_distance_km > 0
    assert len(route.alternatives) == 3

    alt_ids = [a.alternative_id for a in route.alternatives]
    assert "direct" in alt_ids
    assert "safe_corridor" in alt_ids
    assert "high_clearance" in alt_ids

    # Safe corridor alternative checks
    safe_alt = next(a for a in route.alternatives if a.alternative_id == "safe_corridor")
    assert safe_alt.total_distance_km > 0
    assert safe_alt.estimated_duration_hours > 0
    assert safe_alt.estimated_fuel_litres > 0
    assert safe_alt.is_recommended is True

    # Seaward high-clearance check
    sea_alt = next(a for a in route.alternatives if a.alternative_id == "high_clearance")
    assert sea_alt.total_distance_km >= safe_alt.total_distance_km


def test_environmental_sampling_and_limitation():
    """Verify discrete route corridor evaluation points and explicit limitation disclosure."""
    origin = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    dest = LocationCoords(name="Munambam", latitude=10.1800, longitude=76.1700)

    route = routing_engine.plan_safe_transit_route(
        origin=origin,
        destination=dest,
        vessel_type="traditional_craft"
    )

    assert route.environmental_evaluations is not None
    assert len(route.environmental_evaluations) == 3
    labels = [ep["label"] for ep in route.environmental_evaluations]
    assert "Departure Sector" in labels
    assert "Corridor Midpoint" in labels
    assert "Target Destination" in labels

    # Explicit limitation disclosure
    assert route.evaluation_limitation is not None
    assert "continuous real-time buoy or satellite observations are not deployed" in route.evaluation_limitation


def test_route_risk_temporal_comparison():
    """Verify multi-window route risk delta comparison."""
    origin = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    dest = LocationCoords(name="Munambam", latitude=10.1800, longitude=76.1700)
    route = routing_engine.plan_safe_transit_route(origin=origin, destination=dest)

    res_w1 = route_risk_calculator.assess_route_risk(
        origin=origin,
        transit_route=route,
        weather=None,
        ocean=None,
        risk_assessment=None,
        vessel_type="motorized_frp_obm"
    )

    # Simulate second window with higher score
    res_w2 = route_risk_calculator.assess_route_risk(
        origin=origin,
        transit_route=route,
        weather=None,
        ocean=None,
        risk_assessment=None,
        vessel_type="motorized_frp_obm"
    )
    res_w2.prototype_route_risk_index = round(res_w1.prototype_route_risk_index + 2.5, 1)
    res_w2.risk_level = "HIGH"

    comp = route_risk_calculator.compare_temporal_route_risk(
        risk_w1=res_w1,
        risk_w2=res_w2,
        window_1_name="tomorrow_morning",
        window_2_name="tomorrow_afternoon"
    )

    assert comp["trend"] == "INCREASING_RISK"
    assert comp["delta_risk_index"] == 2.5
    assert comp["departure_window"] == "tomorrow_morning"
    assert comp["arrival_window"] == "tomorrow_afternoon"


def test_api_route_alternatives_query():
    """Test full multi-turn conversation resolving route alternatives."""
    session_id = "test-m5-alts"

    # Turn 1: Plan route to Munambam
    r1 = client.post("/api/chat", json={
        "message": "Plan a safe passage route from Kochi to Munambam",
        "conversation_id": session_id,
        "vessel_type": "motorized_frp_obm"
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["transit_route"] is not None
    assert len(d1["transit_route"]["alternatives"]) == 3

    # Turn 2: Query alternatives comparison
    r2 = client.post("/api/chat", json={
        "message": "Compare the route alternatives",
        "conversation_id": session_id
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "route_alternatives"
    assert "Alternative" in d2["answer"]
    assert "Direct Route" in d2["answer"]
    assert "Safe Passage Corridor" in d2["answer"]


def test_api_destination_referent_to_pfz_target_2():
    """Test multi-turn route to specific target ordinal ('Route to target 2')."""
    session_id = "test-m5-tgt2"

    # Turn 1: Find candidates
    r1 = client.post("/api/chat", json={
        "message": "Show PFZ targets within 40 km of Kochi",
        "conversation_id": session_id
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["candidate_pfzs"]) >= 2

    # Turn 2: Route to second target
    r2 = client.post("/api/chat", json={
        "message": "Plot a safe route to target 2",
        "conversation_id": session_id,
        "vessel_type": "mechanized_trawler"
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["transit_route"] is not None
    assert d2["transit_route"]["total_distance_km"] > 0
    assert d2["transit_route"]["destination"]["name"] == d1["candidate_pfzs"][1]["name"]
