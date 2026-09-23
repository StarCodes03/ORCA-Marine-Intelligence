"""ORCA Marine Intelligence - Milestone 3 Integration Tests
Multi-turn Conversation Context Verification

Verifies:
1. Multi-turn context preservation (location, date, time window, activity, selected PFZ)
2. Follow-up modifiers ("What about afternoon?", "What about tomorrow?")
3. Referent resolution ("How far is it?") with safe failure when missing prior target
4. Multi-turn transit query ("What if I go toward the nearest PFZ?")
5. Session isolation across distinct conversation IDs
6. Nullable defaults without invented locations or hardcoded assumptions
7. Behavior-based PFZ assertion compliance (Kuzhuppilly, INCOIS, OFFICIAL_SNAPSHOT)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.conversation_store import conversation_store
from app.workflows.orca_graph import orca_graph

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_conversation_store():
    """Ensure clean conversation store for every test."""
    test_sessions = [
        "test-turn-flow",
        "test-safe-fail",
        "test-transit-flow",
        "test-iso-A",
        "test-iso-B",
        "test-defaults",
        "test-pfz-context"
    ]
    for sid in test_sessions:
        conversation_store.clear_context(sid)
    yield
    for sid in test_sessions:
        conversation_store.clear_context(sid)


def test_turn1_establishes_structured_context():
    """Turn 1: 'Is it safe to fish near Kochi tomorrow morning?'
    Establishes location=Kochi, activity=fishing, date=tomorrow, time_window=morning.
    """
    session_id = "test-turn-flow"
    response = client.post("/api/chat", json={
        "message": "Is it safe to fish near Kochi tomorrow morning?",
        "conversation_id": session_id
    })
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "marine_safety"
    ctx = data.get("context")
    assert ctx is not None
    assert ctx["conversation_id"] == session_id
    assert ctx["location"]["name"] == "Kochi"
    assert ctx["activity"] == "fishing"
    assert ctx["date"] == "tomorrow"
    assert ctx["time_window"] == "morning"
    assert ctx["turn_count"] == 1


def test_turn2_followup_modifier_afternoon():
    """Turn 2: 'What about afternoon?'
    Preserves Kochi + fishing + tomorrow and updates time_window to afternoon.
    """
    session_id = "test-turn-flow"
    # Turn 1
    client.post("/api/chat", json={
        "message": "Is it safe to fish near Kochi tomorrow morning?",
        "conversation_id": session_id
    })

    # Turn 2: Follow-up modifier
    response2 = client.post("/api/chat", json={
        "message": "What about afternoon?",
        "conversation_id": session_id
    })
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2["intent"] == "marine_safety"
    ctx2 = data2.get("context")
    assert ctx2 is not None
    # Preserved fields
    assert ctx2["location"]["name"] == "Kochi"
    assert ctx2["activity"] == "fishing"
    assert ctx2["date"] == "tomorrow"
    # Modified field
    assert ctx2["time_window"] == "afternoon"
    assert ctx2["turn_count"] == 2

    # Verify response reflects afternoon conditions
    assert "Tomorrow Afternoon" in data2["answer"] or "afternoon" in data2["answer"].lower()


def test_turn3_followup_modifier_date():
    """Turn 3: 'What about day after tomorrow?'
    Preserves location + activity + time_window and updates date.
    """
    session_id = "test-turn-flow"
    # Setup Turn 1 & 2
    client.post("/api/chat", json={
        "message": "Is it safe to fish near Kochi tomorrow morning?",
        "conversation_id": session_id
    })
    client.post("/api/chat", json={
        "message": "What about afternoon?",
        "conversation_id": session_id
    })

    # Turn 3
    response3 = client.post("/api/chat", json={
        "message": "What about day after tomorrow?",
        "conversation_id": session_id
    })
    assert response3.status_code == 200
    data3 = response3.json()

    ctx3 = data3.get("context")
    assert ctx3 is not None
    assert ctx3["location"]["name"] == "Kochi"
    assert ctx3["activity"] == "fishing"
    assert ctx3["date"] == "day_after_tomorrow"
    assert ctx3["time_window"] == "afternoon"
    assert ctx3["turn_count"] == 3


def test_pfz_capture_and_behavior_based_assertions():
    """Verify behavior-based PFZ assertions:
    - selected_pfz is not None
    - landing_centre == 'Kuzhuppilly'
    - source == 'INCOIS'
    - source_type == 'OFFICIAL_SNAPSHOT'
    (Does not tie to an internal PFZ ID).
    """
    session_id = "test-pfz-context"
    response = client.post("/api/chat", json={
        "message": "Where is the nearest potential fishing zone to Kochi?",
        "conversation_id": session_id
    })
    assert response.status_code == 200
    data = response.json()

    ctx = data.get("context")
    assert ctx is not None
    assert ctx["selected_pfz"] is not None

    pfz = ctx["selected_pfz"]
    assert pfz["landing_centre"] == "Kuzhuppilly"
    # Provenance assertions
    assert data["geospatial"]["source"] == "INCOIS"
    assert data["geospatial"]["source_type"] == "OFFICIAL_SNAPSHOT"


def test_referent_resolution_how_far_is_it():
    """Turn 4: 'How far is it?'
    Resolves referent 'it' to the previously selected PFZ without re-asking or user restating target.
    """
    session_id = "test-pfz-context"
    # Turn 1: establish PFZ context
    client.post("/api/chat", json={
        "message": "Where is the nearest potential fishing zone to Kochi?",
        "conversation_id": session_id
    })

    # Turn 2: Referent query
    response2 = client.post("/api/chat", json={
        "message": "How far is it?",
        "conversation_id": session_id
    })
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2["intent"] == "pfz_distance"
    # Verification of referent resolution in final answer
    assert "Kuzhuppilly" in data2["answer"]
    assert "km" in data2["answer"]
    # Evidence must contain the calculated distance item
    calculated_items = [e for e in data2["evidence"] if e["category"] == "calculated"]
    assert len(calculated_items) > 0
    assert "Kuzhuppilly" in calculated_items[0]["claim"]


def test_referent_resolution_safe_failure():
    """Safe Failure Requirement:
    'How far is it?' with no previous selected PFZ or resolved target
    must ask for clarification and must NOT invent a target or distance.
    """
    session_id = "test-safe-fail"
    # Fresh conversation without any target
    response = client.post("/api/chat", json={
        "message": "How far is it?",
        "conversation_id": session_id
    })
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "clarification_needed"
    # Must ask for clarification
    assert "clarify" in data["answer"].lower()
    # Must NOT invent distance or coordinates
    assert "km" not in data["answer"]
    assert "bearing" not in data["answer"].lower()


def test_transit_query_what_if_i_go_toward_nearest_pfz():
    """Multi-turn transit query:
    'What if I go toward the nearest PFZ?'
    Resolves 'nearest PFZ' from current context and evaluates marine safety.
    """
    session_id = "test-transit-flow"
    # Turn 1: Establish Kochi fishing session
    client.post("/api/chat", json={
        "message": "Is it safe to fish near Kochi tomorrow morning?",
        "conversation_id": session_id
    })

    # Turn 2: Transit query toward nearest PFZ
    response2 = client.post("/api/chat", json={
        "message": "What if I go toward the nearest PFZ?",
        "conversation_id": session_id
    })
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2["intent"] == "marine_safety"
    assert "WeatherAgent" in data2["agent_trace"]
    assert "OceanAgent" in data2["agent_trace"]
    assert "GeospatialAgent" in data2["agent_trace"]
    assert "RiskAssessmentAgent" in data2["agent_trace"]

    ctx2 = data2.get("context")
    assert ctx2 is not None
    assert ctx2["location"]["name"] == "Kochi"
    assert ctx2["selected_pfz"] is not None
    assert ctx2["selected_pfz"]["landing_centre"] == "Kuzhuppilly"


def test_session_isolation_across_conversation_ids():
    """Verify session isolation between distinct conversation IDs."""
    session_A = "test-iso-A"
    session_B = "test-iso-B"

    # Session A: Kochi, tomorrow morning
    client.post("/api/chat", json={
        "message": "Is it safe to fish near Kochi tomorrow morning?",
        "conversation_id": session_A
    })

    # Session B: Chellanam, today afternoon
    client.post("/api/chat", json={
        "message": "Is it safe to fish near Chellanam today afternoon?",
        "conversation_id": session_B
    })

    ctx_A = conversation_store.get_context(session_A)
    ctx_B = conversation_store.get_context(session_B)

    assert ctx_A.location.name == "Kochi"
    assert ctx_A.date == "tomorrow"
    assert ctx_A.time_window == "morning"

    assert ctx_B.location.name == "Chellanam"
    assert ctx_B.date == "today"
    assert ctx_B.time_window == "afternoon"

    # Modifying Session A should not mutate Session B
    client.post("/api/chat", json={
        "message": "What about night?",
        "conversation_id": session_A
    })

    ctx_A_updated = conversation_store.get_context(session_A)
    ctx_B_unchanged = conversation_store.get_context(session_B)

    assert ctx_A_updated.time_window == "night"
    assert ctx_B_unchanged.time_window == "afternoon"


def test_nullable_defaults_without_invented_locations():
    """Verify that a new conversation starts with nullable fields and does NOT invent a location."""
    session_id = "test-defaults"
    # Query without any geographic or temporal keywords
    response = client.post("/api/chat", json={
        "message": "Can I go out?",
        "conversation_id": session_id
    })
    assert response.status_code == 200
    data = response.json()

    # Intent should fail safely requesting clarification rather than assuming a location
    assert data["intent"] == "clarification_needed"
    assert "location" in data["answer"].lower() or "landing centre" in data["answer"].lower()

    ctx = data.get("context")
    assert ctx is not None
    assert ctx["location"] is None
    assert ctx["date"] is None
    assert ctx["time_window"] is None
