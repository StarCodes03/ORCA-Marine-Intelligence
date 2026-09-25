"""ORCA Marine Intelligence - Chat Routing Architecture Test Suite

Verifies:
1. Casual greetings & pleasantries ("hi", "hello", "good morning", "how are you", "thanks", "bye")
   - Routes directly PlannerAgent -> EvidenceAgent -> END
   - Agent trace is strictly ['PlannerAgent', 'EvidenceAgent']
   - 0 calls to weather, ocean, geospatial, or risk agents
   - Weather, ocean, risk, geospatial, spatial_features are None
   - Alerts list is empty []
2. Supported marine-intelligence requests
   - "Is it safe to go fishing near Kochi tomorrow morning?" -> marine_safety with full collective
   - "What's the weather near Kochi tomorrow morning?" -> weather_query
   - "Find PFZs near Kochi" -> pfz_search
3. Mixed conversational + marine requests (marine intent takes priority!)
   - "Hello, is it safe to go fishing near Kochi tomorrow morning?" -> executes marine_safety workflow
   - "Hey ORCA, find PFZs near Kochi" -> executes pfz_search workflow
   - "Good morning, what's the weather near Kochi?" -> executes weather_query workflow
4. Unsupported / out-of-domain requests
   - "Who is Virat Kohli?", "What's the capital of France?", "Write a Python program", "Tell me a joke", "What's 2 + 2?"
   - Refuses politely, clearly explains ORCA's coastal Kerala marine scope, invites marine queries
   - Trace is strictly ['PlannerAgent', 'EvidenceAgent']
   - No marine data or alerts generated
5. Ambiguous requests that need clarification
   - "Is it safe?" on a fresh turn (even when frontend passes user_latitude & user_longitude)
   - Clarification needed with missing_location, does not invent a location or assume User Vessel Position
   - Turn 2 "near Kochi" correctly uses prior safety intent and executes workflow
6. Multi-turn context preservation across greetings
   - Turn 1: "Is it safe near Kochi tomorrow morning?"
   - Turn 2: "Thank you!" (greeting does not wipe context)
   - Turn 3: "What about afternoon?" (inherits Kochi and compares morning vs afternoon)
7. Explicit vessel position ("near me", "my position")
   - Correctly adopts user coordinates when requested explicitly
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.conversation_store import conversation_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_sessions():
    """Ensure clean isolated conversation sessions."""
    sessions = [
        "test-route-greeting",
        "test-route-supported",
        "test-route-mixed",
        "test-route-unsupported",
        "test-route-ambiguous",
        "test-route-multiturn-preserve",
        "test-route-user-pos",
        "test-route-standalone-referential",
        "test-route-turn-sequence",
        "test-route-weekday-telemetry"
    ]
    for sid in sessions:
        conversation_store.clear_context(sid)
    yield
    for sid in sessions:
        conversation_store.clear_context(sid)


# =========================================================================
# 1. Casual Conversation & Greetings
# =========================================================================

@pytest.mark.parametrize("greeting", [
    "hi",
    "hello",
    "hey",
    "good morning",
    "how are you?",
    "thanks",
    "bye"
])
def test_casual_greetings_do_not_execute_marine_agents(greeting: str):
    """Casual greetings must route directly to EvidenceAgent without invoking marine agents."""
    sid = "test-route-greeting"
    # Even if frontend passes default user coordinates, greetings must not default to marine query
    resp = client.post("/api/chat", json={
        "message": greeting,
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert resp.status_code == 200
    data = resp.json()

    # Intent must be conversational_greeting
    assert data["intent"] == "conversational_greeting"

    # Agent trace must strictly be PlannerAgent and EvidenceAgent only
    assert data["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]

    # Marine agent outputs must be None / empty
    assert data["weather"] is None
    assert data["ocean"] is None
    assert data["risk"] is None
    assert data["geospatial"] is None
    assert data["transit_route"] is None
    assert data["temporal_comparison"] is None
    assert data["route_risk"] is None
    assert data["location"] is None
    assert data["spatial_features"] is None
    assert data["alerts"] == []
    assert data["evidence"] == []

    # Conversational answer must be informative and friendly
    assert len(data["answer"]) > 5


def test_conversational_response_tone_and_conciseness():
    """Verify friendly, concise conversational responses without capability dumps."""
    sid = "test-route-greeting"

    # 1. Greeting -> concise friendly response
    r_hi = client.post("/api/chat", json={"message": "hi", "conversation_id": sid}).json()
    assert r_hi["intent"] == "conversational_greeting"
    assert "Hi! I'm ORCA" in r_hi["answer"]
    assert "🌊" in r_hi["answer"]
    # Must NOT contain long capabilities list or repetitive disclaimers
    assert "•" not in r_hi["answer"]
    assert "Demonstration prototype" not in r_hi["answer"]

    # 2. How are you / how are u -> friendly status response
    for phrase in ["how are you?", "how are u", "how r u", "how are you doing"]:
        r_how = client.post("/api/chat", json={"message": phrase, "conversation_id": sid}).json()
        assert r_how["intent"] == "conversational_greeting"
        assert "I'm doing well!" in r_how["answer"]
        assert "ORCA" in r_how["answer"]
        assert "sea" in r_how["answer"].lower() or "ocean" in r_how["answer"].lower()

    # 3. Thanks -> concise appreciation
    r_thanks = client.post("/api/chat", json={"message": "thanks", "conversation_id": sid}).json()
    assert r_thanks["intent"] == "conversational_greeting"
    assert "You're welcome!" in r_thanks["answer"]
    assert "🌊" in r_thanks["answer"]

    # 4. Bye -> concise safe departure
    r_bye = client.post("/api/chat", json={"message": "bye", "conversation_id": sid}).json()
    assert r_bye["intent"] == "conversational_greeting"
    assert "Goodbye!" in r_bye["answer"]
    assert "Stay safe" in r_bye["answer"]
    assert "🌊" in r_bye["answer"]


# =========================================================================
# 2. Supported Marine Intelligence Requests
# =========================================================================

def test_supported_marine_safety_query():
    """Supported marine safety query executes full collective."""
    sid = "test-route-supported"
    resp = client.post("/api/chat", json={
        "message": "Is it safe to go fishing near Kochi tomorrow morning?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "marine_safety"
    assert "WeatherAgent" in data["agent_trace"]
    assert "OceanAgent" in data["agent_trace"]
    assert "GeospatialAgent" in data["agent_trace"]
    assert "RiskAssessmentAgent" in data["agent_trace"]
    assert "EvidenceAgent" in data["agent_trace"]

    assert data["weather"] is not None
    assert data["ocean"] is not None
    assert data["risk"] is not None
    assert data["location"] is not None
    assert data["location"]["name"] == "Kochi"


def test_supported_weather_query():
    """Supported weather query executes WeatherAgent and EvidenceAgent."""
    sid = "test-route-supported"
    resp = client.post("/api/chat", json={
        "message": "What's the weather near Kochi tomorrow morning?",
        "conversation_id": sid
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "weather_query"
    assert data["agent_trace"] == ["PlannerAgent", "WeatherAgent", "EvidenceAgent"]
    assert data["weather"] is not None
    assert data["ocean"] is None


def test_supported_pfz_search():
    """Supported PFZ query executes OceanAgent and GeospatialAgent."""
    sid = "test-route-supported"
    resp = client.post("/api/chat", json={
        "message": "Find PFZs near Kochi",
        "conversation_id": sid
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "pfz_search"
    assert "OceanAgent" in data["agent_trace"]
    assert "GeospatialAgent" in data["agent_trace"]
    assert "WeatherAgent" not in data["agent_trace"]


# =========================================================================
# 3. Mixed Conversational + Marine Requests
# =========================================================================

def test_mixed_greeting_and_marine_safety():
    """'Hello, is it safe to go fishing near Kochi tomorrow morning?' -> Marine intent takes priority."""
    sid = "test-route-mixed"
    resp = client.post("/api/chat", json={
        "message": "Hello, is it safe to go fishing near Kochi tomorrow morning?",
        "conversation_id": sid
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "marine_safety"
    assert "WeatherAgent" in data["agent_trace"]
    assert "OceanAgent" in data["agent_trace"]
    assert "GeospatialAgent" in data["agent_trace"]
    assert "RiskAssessmentAgent" in data["agent_trace"]
    assert data["location"]["name"] == "Kochi"


def test_mixed_greeting_and_pfz_search():
    """'Hey ORCA, find PFZs near Kochi' -> Marine intent takes priority."""
    sid = "test-route-mixed"
    resp = client.post("/api/chat", json={
        "message": "Hey ORCA, find PFZs near Kochi",
        "conversation_id": sid
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "pfz_search"
    assert "GeospatialAgent" in data["agent_trace"]


def test_mixed_greeting_and_weather():
    """'Good morning, what's the weather near Kochi?' -> Marine intent takes priority."""
    sid = "test-route-mixed"
    resp = client.post("/api/chat", json={
        "message": "Good morning, what's the weather near Kochi?",
        "conversation_id": sid
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "weather_query"
    assert "WeatherAgent" in data["agent_trace"]


def test_mixed_greeting_and_marine_priority_short():
    """'Hello, is it safe to fish near Kochi tomorrow?' -> Marine workflow executed."""
    sid = "test-route-mixed"
    resp = client.post("/api/chat", json={
        "message": "Hello, is it safe to fish near Kochi tomorrow?",
        "conversation_id": sid
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "marine_safety"
    assert "WeatherAgent" in data["agent_trace"]
    assert "RiskAssessmentAgent" in data["agent_trace"]
    assert data["risk"] is not None


# =========================================================================
# 4. Unsupported / Out-of-Domain Requests
# =========================================================================

@pytest.mark.parametrize("query", [
    "Who is Virat Kohli?",
    "What's the capital of France?",
    "Write a Python program",
    "Tell me a joke",
    "What's 2 + 2?",
    "Who is the mayor of Kochi?"
])
def test_unsupported_domain_queries_gracefully_refused(query: str):
    """Arbitrary non-marine queries must be refused politely without executing marine agents."""
    sid = "test-route-unsupported"
    resp = client.post("/api/chat", json={
        "message": query,
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "unsupported"
    assert data["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]

    assert data["weather"] is None
    assert data["ocean"] is None
    assert data["risk"] is None
    assert data["geospatial"] is None
    assert data["spatial_features"] is None
    assert data["alerts"] == []

    # Text must explain ORCA's coastal Kerala marine scope
    ans_lower = data["answer"].lower()
    assert "specialized" in ans_lower or "assist" in ans_lower or "orca" in ans_lower
    assert "marine" in ans_lower or "kerala" in ans_lower


# =========================================================================
# 5. Ambiguous Marine Requests That Need Clarification
# =========================================================================

def test_ambiguous_safety_query_fresh_turn_requests_clarification():
    """'Is it safe?' on a fresh turn without location must request clarification, not invent a location."""
    sid = "test-route-ambiguous"
    # Even if user_latitude is sent by frontend, do not invent location without user prompt reference
    resp = client.post("/api/chat", json={
        "message": "Is it safe?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "clarification_needed"
    assert data["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]
    assert data["location"] is None
    assert "location" in data["answer"].lower() or "landing centre" in data["answer"].lower()

    # Turn 2: User clarifies with location 'near Kochi'
    resp2 = client.post("/api/chat", json={
        "message": "near Kochi",
        "conversation_id": sid
    })
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["intent"] == "marine_safety"
    assert data2["location"]["name"] == "Kochi"
    assert "WeatherAgent" in data2["agent_trace"]
    assert "RiskAssessmentAgent" in data2["agent_trace"]


# =========================================================================
# 6. Multi-turn Context Preservation Across Greetings
# =========================================================================

def test_multiturn_context_preserved_across_greetings():
    """Turn 1: Marine safety. Turn 2: 'Thank you!'. Turn 3: 'What about afternoon?'."""
    sid = "test-route-multiturn-preserve"

    # Turn 1: Establish Kochi fishing session
    resp1 = client.post("/api/chat", json={
        "message": "Is it safe to fish near Kochi tomorrow morning?",
        "conversation_id": sid
    })
    assert resp1.status_code == 200
    assert resp1.json()["location"]["name"] == "Kochi"

    # Turn 2: User says 'Thank you!'
    resp2 = client.post("/api/chat", json={
        "message": "Thank you!",
        "conversation_id": sid
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["intent"] == "conversational_greeting"
    assert data2["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]

    # Verify context still preserves Kochi in context
    ctx = conversation_store.get_context(sid)
    assert ctx is not None
    assert ctx.location.name == "Kochi"
    assert ctx.last_intent == "marine_safety"

    # Turn 3: User says 'What about afternoon?'
    resp3 = client.post("/api/chat", json={
        "message": "What about afternoon?",
        "conversation_id": sid
    })
    assert resp3.status_code == 200
    data3 = resp3.json()
    # Successfully performs temporal comparison inheriting Kochi
    assert data3["intent"] in ["marine_safety", "temporal_comparison"]
    assert data3["location"]["name"] == "Kochi"
    assert "afternoon" in data3["answer"].lower()


# =========================================================================
# 7. Explicit User Vessel Position Queries
# =========================================================================

def test_explicit_user_position_near_me():
    """'Is it safe to fish near me tomorrow morning?' adopts user GPS coordinates."""
    sid = "test-route-user-pos"
    resp = client.post("/api/chat", json={
        "message": "Is it safe to fish near me tomorrow morning?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "marine_safety"
    assert data["location"] is not None
    assert data["location"]["name"] == "User Vessel Position"
    assert data["location"]["latitude"] == 9.9312
    assert data["location"]["longitude"] == 76.2673


# =========================================================================
# 8. Standalone Referential Queries with No Prior Marine Context
# =========================================================================

@pytest.mark.parametrize("query", [
    "when would be better?",
    "what about afternoon?",
    "is it safe there?",
    "ok then when is it fine to do that",
    "when can I go?"
])
def test_standalone_referential_queries_ask_clarification(query: str):
    """Standalone referential queries with NO prior context must NOT invent context or classify as unsupported."""
    sid = "test-route-standalone-referential"
    resp = client.post("/api/chat", json={
        "message": query,
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert resp.status_code == 200
    data = resp.json()

    # Must be clarification_needed, NOT unsupported, and NOT executing marine collective
    assert data["intent"] == "clarification_needed"
    assert data["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]
    assert data["location"] is None
    assert data["weather"] is None
    assert data["ocean"] is None
    assert data["risk"] is None
    assert data["geospatial"] is None
    assert "coastal landing centre" in data["answer"].lower() or "clarify" in data["answer"].lower()


# =========================================================================
# 9. Contextual Referential Follow-Up: Full 6-Turn Sequence
# =========================================================================

def test_contextual_referential_followup_turn_sequence():
    """Verify the exact 6-turn conversation progression:
    Turn 1: 'how are u' -> conversational_greeting
    Turn 2: 'is it safe to go fishing today' -> marine_safety, Kochi, today
    Turn 3: 'ok then when is it fine to do that' -> temporal_comparison, Kochi, today_morning vs today_afternoon
    Turn 4: 'what about afternoon?' -> marine_safety, Kochi, today_afternoon
    Turn 5: 'and tomorrow?' -> marine_safety, Kochi, tomorrow
    Turn 6: 'how about evening?' -> marine_safety, Kochi, tomorrow_evening
    """
    sid = "test-route-turn-sequence"

    # Turn 1: 'how are u'
    r1 = client.post("/api/chat", json={
        "message": "how are u",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["intent"] == "conversational_greeting"
    assert d1["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]
    assert d1["location"] is None

    # Turn 2: 'is it safe to go fishing today'
    r2 = client.post("/api/chat", json={
        "message": "is it safe to go fishing today",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "marine_safety"
    assert d2["location"]["name"] == "Kochi"
    assert "WeatherAgent" in d2["agent_trace"]
    assert "OceanAgent" in d2["agent_trace"]
    assert "GeospatialAgent" in d2["agent_trace"]
    assert "RiskAssessmentAgent" in d2["agent_trace"]
    assert d2["geospatial"] is not None

    # Turn 3: 'ok then when is it fine to do that'
    r3 = client.post("/api/chat", json={
        "message": "ok then when is it fine to do that",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["intent"] == "temporal_comparison"
    assert d3["location"]["name"] == "Kochi"
    assert "WeatherAgent" in d3["agent_trace"]
    assert "OceanAgent" in d3["agent_trace"]
    assert "RiskAssessmentAgent" in d3["agent_trace"]
    assert "GeospatialAgent" not in d3["agent_trace"]
    assert "+0.0 (DETERIORATING)" not in d3["answer"]
    assert "Stable)" in d3["answer"] or "(Higher)" in d3["answer"] or "(Lower)" in d3["answer"]
    assert "Overall trend" in d3["answer"]
    assert "parameter" in d3["answer"].lower() or "comparative" in d3["answer"].lower() or "interpretation" in d3["answer"].lower()

    # Turn 4: 'what about afternoon?'
    r4 = client.post("/api/chat", json={
        "message": "what about afternoon?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["intent"] in ["marine_safety", "temporal_comparison"]
    assert d4["location"]["name"] == "Kochi"
    assert "WeatherAgent" in d4["agent_trace"]
    assert "OceanAgent" in d4["agent_trace"]
    assert "RiskAssessmentAgent" in d4["agent_trace"]
    assert "GeospatialAgent" not in d4["agent_trace"]
    assert d4["geospatial"] is not None
    assert "afternoon" in d4["answer"].lower()

    # Turn 5: 'and tomorrow?'
    r5 = client.post("/api/chat", json={
        "message": "and tomorrow?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["intent"] in ["marine_safety", "temporal_comparison"]
    assert d5["location"]["name"] == "Kochi"
    assert "WeatherAgent" in d5["agent_trace"]
    assert "OceanAgent" in d5["agent_trace"]
    assert "RiskAssessmentAgent" in d5["agent_trace"]
    assert "GeospatialAgent" not in d5["agent_trace"]
    assert d5["geospatial"] is not None
    assert "tomorrow" in d5["answer"].lower()

    # Turn 6: 'how about evening?'
    r6 = client.post("/api/chat", json={
        "message": "how about evening?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r6.status_code == 200
    d6 = r6.json()
    assert d6["intent"] in ["marine_safety", "temporal_comparison"]
    assert d6["location"]["name"] == "Kochi"
    assert "WeatherAgent" in d6["agent_trace"]
    assert "OceanAgent" in d6["agent_trace"]
    assert "RiskAssessmentAgent" in d6["agent_trace"]
    assert "GeospatialAgent" not in d6["agent_trace"]
    assert d6["geospatial"] is not None
    assert "evening" in d6["answer"].lower()


# =========================================================================
# 10. Weekday Follow-up Context Resolution
# =========================================================================

def test_weekday_followup_preserves_location_and_activity():
    """'and Saturday?' resolves context to Kochi and fishing with date='saturday'."""
    sid = "test-route-weekday-telemetry"
    # Establish Kochi fishing session
    r1 = client.post("/api/chat", json={
        "message": "Is it safe to fish near Kochi today?",
        "conversation_id": sid
    })
    assert r1.status_code == 200
    assert r1.json()["location"]["name"] == "Kochi"

    # Follow up with weekday
    r2 = client.post("/api/chat", json={
        "message": "and Saturday?",
        "conversation_id": sid
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["location"]["name"] == "Kochi"
    assert d2["intent"] in ["marine_safety", "temporal_comparison"]
    ctx = conversation_store.get_context(sid)
    assert ctx.date == "saturday"
    assert ctx.location.name == "Kochi"
    assert ctx.activity == "fishing"


# =========================================================================
# 11. Spatial Location Change in Follow-up & Temporal Internal Consistency
# =========================================================================

def test_followup_location_change_executes_geospatial():
    """When a follow-up changes the spatial location ('what about Chellanam?'), GeospatialAgent must re-execute."""
    sid = "test-route-spatial-change"
    # Turn 1: Kochi
    r1 = client.post("/api/chat", json={
        "message": "is it safe to fish near Kochi today",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r1.status_code == 200
    assert "GeospatialAgent" in r1.json()["agent_trace"]

    # Turn 2: Chellanam (spatial context changed)
    r2 = client.post("/api/chat", json={
        "message": "what about Chellanam?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["location"]["name"] == "Chellanam"
    assert "GeospatialAgent" in d2["agent_trace"]
    assert "WeatherAgent" in d2["agent_trace"]
    assert "OceanAgent" in d2["agent_trace"]
    assert "RiskAssessmentAgent" in d2["agent_trace"]


def test_temporal_comparison_internal_consistency_when_score_delta_zero():
    """Verify that when risk score delta is 0.0 but conditions worsen (e.g. wind increases),
    output does not label +0.0 as (DETERIORATING), but reports 0.0 (Stable) and clarifies trend.
    """
    sid = "test-temporal-consistency-zero-score"
    # Establish Kochi session
    r1 = client.post("/api/chat", json={
        "message": "is it safe to fish near Kochi today",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r1.status_code == 200

    # Follow up asking when it is fine
    r2 = client.post("/api/chat", json={
        "message": "when would be better?",
        "conversation_id": sid,
        "user_latitude": 9.9312,
        "user_longitude": 76.2673
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "temporal_comparison"
    ans = d2["answer"]

    # Verify no misleading "+0.0 (DETERIORATING)"
    assert "+0.0 (DETERIORATING)" not in ans

    # If risk delta is 0.0, it must be labeled Stable
    if d2.get("temporal_comparison") and d2["temporal_comparison"].get("delta_risk_score") == 0.0:
        assert "0.0 (Stable)" in ans
        assert "Overall trend" in ans


def test_marine_news_queries_unsupported_routing():
    """Verify that genuine marine-news/incident inquiries (Category A) are routed to
    unsupported capability response, NOT marine_safety, and do NOT fabricate weather,
    ocean, or geospatial risk data.
    """
    news_queries = [
        "what is new in the sea news today",
        "any marine news today?",
        "latest marine breaking news",
        "any maritime incidents today?",
        "was there a ship accident today?",
        "what happened in the sea today?",
        "latest marine news",
        "any new ocean news?",
    ]

    for q in news_queries:
        resp = client.post("/api/chat", json={
            "message": q,
            "conversation_id": f"test-news-{abs(hash(q)) % 10000}",
            "user_latitude": 9.9312,
            "user_longitude": 76.2673
        })
        assert resp.status_code == 200, f"Query '{q}' failed with status {resp.status_code}"
        data = resp.json()

        # Must be classified as unsupported news, NOT marine_safety
        assert data["intent"] in ["unsupported", "unsupported_news"], f"Query '{q}' routed to intent '{data['intent']}'"
        assert data["intent"] != "marine_safety", f"Query '{q}' incorrectly classified as marine_safety"

        # Must invoke ONLY PlannerAgent and EvidenceAgent (no weather/ocean/gis/risk agents)
        assert data["agent_trace"] == ["PlannerAgent", "EvidenceAgent"], f"Query '{q}' invoked agents: {data['agent_trace']}"

        # Must not fabricate telemetry or location
        assert data["location"] is None
        assert data["weather"] is None
        assert data["ocean"] is None
        assert data["geospatial"] is None
        assert data["risk"] is None

        # Response must clarify that live marine news is not supported
        ans = data["answer"].lower()
        assert "news" in ans
        assert "live marine-news" in ans or "news feed" in ans or "not a live news" in ans or "വാർത്ത" in (data.get("answer_ml") or "")


def test_marine_condition_update_queries_routing():
    """Verify Category B conversational marine condition inquiries:
    - 'what is new in the sea today'
    - 'what's happening in the sea today'
    - 'what's happening out at sea today'
    - 'what's new with the sea today'
    - 'tell me what's happening in the sea today'
    - 'any updates from the sea today'

    Must:
    1. Route to intent='marine_update'
    2. Invoke ONLY PlannerAgent, WeatherAgent, OceanAgent, EvidenceAgent
       (RiskAssessmentAgent and GeospatialAgent MUST NOT be executed)
    3. Return weather and ocean telemetry, but risk, geospatial, transit_route are None
    4. Provide the clear disclaimer about not having live news, while giving live forecast conditions
    5. Contain formatted table with wind, rain, wave, sea state
    6. Not fabricate news, accidents, or incidents
    """
    update_queries = [
        "what is new in the sea today",
        "what's happening in the sea today",
        "what's happening out at sea today",
        "what's new with the sea today",
        "tell me what's happening in the sea today",
        "any updates from the sea today",
    ]

    for q in update_queries:
        resp = client.post("/api/chat", json={
            "message": q,
            "conversation_id": f"test-update-{abs(hash(q)) % 10000}",
            "user_latitude": 9.9312,
            "user_longitude": 76.2673
        })
        assert resp.status_code == 200, f"Query '{q}' failed with status {resp.status_code}"
        data = resp.json()

        assert data["intent"] == "marine_update", f"Query '{q}' routed to intent '{data['intent']}'"
        assert data["agent_trace"] == ["PlannerAgent", "WeatherAgent", "OceanAgent", "EvidenceAgent"], (
            f"Query '{q}' invoked agents: {data['agent_trace']}"
        )

        # Weather and ocean telemetry MUST be present
        assert data["weather"] is not None
        assert data["weather"]["wind_speed_kmh"] is not None
        assert data["ocean"] is not None
        assert data["ocean"]["wave_height_m"] is not None

        # Risk, Geospatial, Transit Route MUST be None
        assert data["risk"] is None
        assert data["geospatial"] is None
        assert data["transit_route"] is None
        assert data["spatial_features"] is None

        # Location defaults to Kochi or user context
        assert data["location"] is not None
        assert data["location"]["name"] == "Kochi"

        # Answer must contain the honest disclaimer and live condition metrics
        ans = data["answer"]
        assert "don't have a live marine-news feed" in ans or "do not have a live marine-news feed" in ans
        assert "current marine conditions from the live forecast" in ans
        assert "Marine Update" in ans
        assert "Wind" in ans
        assert "Wave" in ans
        assert "Sea State" in ans


def test_four_key_queries_distinction():
    """Verify exact behavior of the 4 key test queries required by user:
    1. 'what is new in the sea today' -> marine_update with live forecast & news disclaimer
    2. 'any marine news today?' -> unsupported with unsupported_news scope notice
    3. 'what\'s the weather today?' -> weather_query
    4. 'is it safe to go fishing today?' -> marine_safety with full collective
    """
    sid = "test-four-queries"

    # 1. 'what is new in the sea today'
    r1 = client.post("/api/chat", json={"message": "what is new in the sea today", "conversation_id": sid + "-1"}).json()
    assert r1["intent"] == "marine_update"
    assert r1["agent_trace"] == ["PlannerAgent", "WeatherAgent", "OceanAgent", "EvidenceAgent"]
    assert "don't have a live marine-news feed" in r1["answer"]
    assert r1["weather"] is not None
    assert r1["ocean"] is not None
    assert r1["risk"] is None

    # 2. 'any marine news today?'
    r2 = client.post("/api/chat", json={"message": "any marine news today?", "conversation_id": sid + "-2"}).json()
    assert r2["intent"] == "unsupported"
    assert r2["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]
    assert "Operational Scope Notice" in r2["answer"]
    assert r2["weather"] is None
    assert r2["ocean"] is None

    # 3. 'what\'s the weather today?'
    r3 = client.post("/api/chat", json={"message": "what's the weather today?", "conversation_id": sid + "-3"}).json()
    assert r3["intent"] == "weather_query"
    assert "WeatherAgent" in r3["agent_trace"]
    assert r3["weather"] is not None

    # 4. 'is it safe to go fishing today?'
    r4 = client.post("/api/chat", json={"message": "is it safe to go fishing today?", "conversation_id": sid + "-4"}).json()
    assert r4["intent"] == "marine_safety"
    assert "RiskAssessmentAgent" in r4["agent_trace"]
    assert r4["risk"] is not None
    assert r4["risk"]["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]


def test_cold_start_referential_queries_request_clarification():
    """Cold-start referential queries must request clarification rather than inventing Kochi/fishing context."""
    cold_queries = [
        "what about tomorrow?",
        "when would be better?",
        "is it safe there?"
    ]

    for q in cold_queries:
        resp = client.post("/api/chat", json={
            "message": q,
            "conversation_id": f"test-cold-referent-{abs(hash(q)) % 10000}"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "clarification_needed"
        assert data["location"] is None
        assert data["weather"] is None
        assert data["agent_trace"] == ["PlannerAgent", "EvidenceAgent"]


def test_greeting_does_not_establish_marine_context_for_referential_followup():
    """Verify that a greeting turn ('how are u') does NOT count as marine context
    for a subsequent referential follow-up ('what about tomorrow?').
    """
    sid = "test-greeting-then-referential"

    # Turn 1: 'how are u'
    r1 = client.post("/api/chat", json={"message": "how are u", "conversation_id": sid})
    assert r1.status_code == 200
    assert r1.json()["intent"] == "conversational_greeting"

    # Turn 2: 'what about tomorrow?' (referential query with NO prior marine context)
    r2 = client.post("/api/chat", json={"message": "what about tomorrow?", "conversation_id": sid})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "clarification_needed"
    assert d2["location"] is None
    assert d2["weather"] is None


