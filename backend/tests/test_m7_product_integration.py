"""ORCA Marine Intelligence - M7 Product Integration Test Suite

Tests:
1. Storage repository persistence (conversations, messages, vessel profiles, alerts).
2. ConversationStore rehydration across cache clears.
3. Deterministic alert engine (proximity, threshold, cross-track route deviation).
4. REST API endpoints for conversations, vessel profiles, alerts, and evaluation.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.storage import StorageRepository
from app.services.conversation_store import ConversationStore
from app.tools.alerts import AlertEngine, point_to_segment_distance_km, point_to_polyline_distance_km

client = TestClient(app)


@pytest.fixture
def temp_storage():
    """Create an isolated in-memory storage repository for testing."""
    return StorageRepository(db_url=":memory:")


def test_storage_repository_conversations_and_messages(temp_storage):
    """Test conversation state and message persistence in storage repository."""
    cid = "test-session-001"
    ctx = {
        "conversation_id": cid,
        "location": {"latitude": 9.9312, "longitude": 76.2673, "name": "Kochi"},
        "vessel_type": "motorized_frp_obm",
        "turn_count": 1
    }

    # Save and retrieve conversation
    temp_storage.save_conversation(cid, ctx)
    loaded_ctx = temp_storage.get_conversation(cid)
    assert loaded_ctx is not None
    assert loaded_ctx["vessel_type"] == "motorized_frp_obm"

    # Save messages
    mid1 = temp_storage.save_message(cid, "user", "Can I go fishing today?", "weather_query")
    mid2 = temp_storage.save_message(cid, "assistant", "Conditions are safe.", "weather_query", {"risk": "LOW"})
    assert mid1 > 0
    assert mid2 > mid1

    # List messages
    msgs = temp_storage.get_messages(cid)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"

    # List conversations
    convs = temp_storage.list_conversations()
    assert any(c["conversation_id"] == cid for c in convs)

    # Delete conversation
    deleted = temp_storage.delete_conversation(cid)
    assert deleted is True
    assert temp_storage.get_conversation(cid) is None
    assert len(temp_storage.get_messages(cid)) == 0


def test_storage_repository_vessel_profiles(temp_storage):
    """Test vessel profile retrieval and custom profile creation."""
    profiles = temp_storage.get_vessel_profiles()
    assert len(profiles) >= 3  # Seeded traditional_craft, motorized_frp_obm, mechanized_trawler

    # Create custom profile
    custom_profile = {
        "vessel_type": "deepsea_longliner_custom",
        "name": "Deep-Sea Longliner (Custom Demo)",
        "wave_max_safe": 3.0,
        "wave_max_moderate": 4.0,
        "wind_max_safe": 45.0,
        "wind_max_moderate": 55.0,
        "cruising_speed_knots": 10.5,
        "fuel_consumption_l_per_hour": 24.0,
        "fuel_type": "Marine Diesel",
        "is_custom": True
    }
    temp_storage.save_vessel_profile(custom_profile)

    saved = temp_storage.get_vessel_profile("deepsea_longliner_custom")
    assert saved is not None
    assert saved["name"] == "Deep-Sea Longliner (Custom Demo)"
    assert saved["wave_max_safe"] == 3.0


def test_conversation_store_rehydration():
    """Verify that ConversationStore rehydrates state from storage when memory cache is cleared."""
    store = ConversationStore()
    cid = "rehydration-test-session"

    # Update context
    ctx = store.get_or_create(cid)
    ctx.vessel_type = "mechanized_trawler"
    ctx.turn_count = 3
    store.save_context(ctx)

    # Clear in-memory cache to simulate restart or multi-worker reload
    store._contexts.clear()
    assert cid not in store._contexts

    # Rehydrate
    rehydrated = store.get_or_create(cid)
    assert rehydrated.vessel_type == "mechanized_trawler"
    assert rehydrated.turn_count == 3


def test_alert_engine_cross_track_geometry():
    """Test point-to-segment and point-to-polyline cross track error calculation."""
    # Polyline along longitude from (10.0, 76.0) to (10.0, 76.5)
    # Point at (10.0, 76.2) should be on segment (distance ~ 0 km)
    dist_on = point_to_segment_distance_km(10.0, 76.2, 10.0, 76.0, 10.0, 76.5)
    assert dist_on < 0.05

    # Point at (10.05, 76.2) is ~5.5 km north (0.05 deg * 110.574 km/deg)
    dist_off = point_to_segment_distance_km(10.05, 76.2, 10.0, 76.0, 10.0, 76.5)
    assert 5.0 <= dist_off <= 6.0

    # Polyline test
    poly = [(10.0, 76.0), (10.0, 76.5), (10.2, 76.5)]
    # Point deviated 2 km
    dist_poly = point_to_polyline_distance_km(10.02, 76.25, poly)
    assert dist_poly > 1.5


def test_alert_engine_evaluations(temp_storage):
    """Test deterministic alert engine: proximity, thresholds, and route deviation."""
    engine = AlertEngine(storage=temp_storage)

    # 1. Proximity: inside Kochi Naval Base Security Perimeter (~ 9.965, 76.240)
    inside_alerts = engine.evaluate_proximity_alerts(9.965, 76.240)
    assert len(inside_alerts) >= 1
    assert inside_alerts[0]["severity"] == "CRITICAL"
    assert "Naval Base" in inside_alerts[0]["title"] or "Violation" in inside_alerts[0]["title"]

    # 2. Proximity: far out in safe water (~ 9.80, 76.00)
    safe_alerts = engine.evaluate_proximity_alerts(9.80, 76.00)
    assert len(safe_alerts) == 0

    # 3. Thresholds: Artisanal Traditional Craft in high waves (2.0 m > 1.5 m max_moderate)
    thresh_crit = engine.evaluate_threshold_alerts(
        vessel_type="traditional_craft",
        wave_height_m=2.0,
        wind_speed_kmh=15.0
    )
    assert any(a["severity"] == "CRITICAL" for a in thresh_crit)

    # Moderate threshold advisory: FRP Canoe in 1.8 m wave (1.6 m safe < 1.8 m <= 2.2 m moderate)
    thresh_warn = engine.evaluate_threshold_alerts(
        vessel_type="motorized_frp_obm",
        wave_height_m=1.8,
        wind_speed_kmh=20.0
    )
    assert any(a["severity"] == "WARNING" for a in thresh_warn)

    # Safe conditions: Mechanized Trawler in 1.2 m wave and 20 km/h wind
    thresh_safe = engine.evaluate_threshold_alerts(
        vessel_type="mechanized_trawler",
        wave_height_m=1.2,
        wind_speed_kmh=20.0
    )
    assert len(thresh_safe) == 0

    # 4. Route deviation: waypoints from (9.93, 76.26) to (9.93, 76.00)
    # Vessel at (9.98, 76.15) is ~5.5 km north -> deviation alert
    route_pts = [(9.93, 76.26), (9.93, 76.00)]
    dev_alerts = engine.evaluate_route_deviation_alerts(9.98, 76.15, route_pts)
    assert len(dev_alerts) == 1
    assert dev_alerts[0]["severity"] == "WARNING"
    assert "Deviation" in dev_alerts[0]["title"]


def test_api_conversations_endpoints():
    """Test conversation management endpoints via FastAPI TestClient."""
    # Send a chat query to create a conversation
    resp = client.post("/api/chat", json={
        "message": "Can I fish off Kochi today?",
        "conversation_id": "api-conv-test-01",
        "vessel_type": "motorized_frp_obm"
    })
    assert resp.status_code == 200

    # List conversations
    list_resp = client.get("/api/conversations")
    assert list_resp.status_code == 200
    conv_list = list_resp.json()
    assert any(c["conversation_id"] == "api-conv-test-01" for c in conv_list)

    # Get specific conversation
    get_resp = client.get("/api/conversations/api-conv-test-01")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["conversation_id"] == "api-conv-test-01"
    assert len(data["messages"]) >= 2

    # Delete conversation
    del_resp = client.delete("/api/conversations/api-conv-test-01")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


def test_api_vessel_profiles_endpoints():
    """Test vessel profiles GET and POST endpoints."""
    # GET profiles
    get_resp = client.get("/api/vessel-profiles")
    assert get_resp.status_code == 200
    profiles = get_resp.json()
    assert len(profiles) >= 3

    # POST custom profile
    new_profile = {
        "vessel_type": "test_coastal_skiff",
        "name": "Test Coastal Skiff",
        "wave_max_safe": 1.2,
        "wave_max_moderate": 1.7,
        "wind_max_safe": 22.0,
        "wind_max_moderate": 30.0,
        "cruising_speed_knots": 6.0,
        "fuel_consumption_l_per_hour": 4.5,
        "fuel_type": "Petrol"
    }
    post_resp = client.post("/api/vessel-profiles", json=new_profile)
    assert post_resp.status_code == 200
    assert post_resp.json()["vessel_type"] == "test_coastal_skiff"


def test_api_alerts_endpoints():
    """Test alert evaluation and listing endpoints."""
    eval_req = {
        "vessel_latitude": 9.965,
        "vessel_longitude": 76.240,
        "vessel_type": "motorized_frp_obm",
        "wave_height_m": 2.8,
        "wind_speed_kmh": 40.0,
        "conversation_id": "api-alert-session",
        "persist": True
    }
    eval_resp = client.post("/api/alerts/evaluate", json=eval_req)
    assert eval_resp.status_code == 200
    alerts = eval_resp.json()
    assert len(alerts) >= 2  # Inside restricted zone + wave/wind threshold

    # List alerts
    list_resp = client.get("/api/alerts?conversation_id=api-alert-session")
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) >= 2
