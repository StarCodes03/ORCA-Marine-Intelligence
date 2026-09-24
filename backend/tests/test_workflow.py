"""Integration tests for LangGraph multi-agent workflow orchestration."""

import pytest
from app.workflows.orca_graph import orca_graph


def test_marine_safety_workflow():
    """Acceptance Query 1:
    'Is it safe to go fishing near Kochi tomorrow morning?'
    Expected trace: PlannerAgent -> WeatherAgent -> OceanAgent -> GeospatialAgent -> RiskAssessmentAgent -> EvidenceAgent
    """
    initial_state = {
        "message": "Is it safe to go fishing near Kochi tomorrow morning?",
        "conversation_id": "test-safety-001",
        "agent_trace": []
    }

    result = orca_graph.invoke(initial_state)

    trace = result["agent_trace"]
    assert "PlannerAgent" in trace
    assert "WeatherAgent" in trace
    assert "OceanAgent" in trace
    assert "GeospatialAgent" in trace
    assert "RiskAssessmentAgent" in trace
    assert "EvidenceAgent" in trace

    assert result["planner_plan"]["intent"] == "marine_safety"
    assert result["planner_plan"]["location"]["name"] == "Kochi"

    # Risk level check
    assert result["risk_assessment"]["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]

    # Verification of final answer contents
    final_answer = result["final_answer"]
    assert any(f"ENVIRONMENTAL CONDITION RISK: {lvl}" in final_answer for lvl in ["LOW", "MODERATE", "HIGH", "CRITICAL"])
    assert ("OPEN_METEO_WEATHER" in final_answer or "MOCK_WEATHER_DATA" in final_answer)
    assert ("OPEN_METEO_MARINE" in final_answer or "MOCK_OCEAN_DATA" in final_answer)
    assert ("INCOIS" in final_answer or "DEMO_GIS_DATA" in final_answer)


def test_marine_safety_workflow_mock_fallback(monkeypatch):
    """Test full workflow in explicit mock fallback mode."""
    monkeypatch.setenv("ORCA_ENABLE_LIVE_WEATHER", "false")
    monkeypatch.setenv("ORCA_ENABLE_LIVE_OCEAN", "false")

    initial_state = {
        "message": "Is it safe to go fishing near Kochi tomorrow morning?",
        "conversation_id": "test-fallback-001",
        "agent_trace": []
    }

    result = orca_graph.invoke(initial_state)

    assert result["risk_assessment"]["risk_level"] == "HIGH"
    final_answer = result["final_answer"]
    assert "ENVIRONMENTAL CONDITION RISK: HIGH" in final_answer
    assert "MOCK_WEATHER_DATA" in final_answer
    assert "MOCK_OCEAN_DATA" in final_answer
    assert ("INCOIS" in final_answer or "DEMO_GIS_DATA" in final_answer)


def test_pfz_search_workflow():
    """Acceptance Query 2:
    'Where is the nearest potential fishing zone?'
    Expected trace: PlannerAgent -> OceanAgent -> GeospatialAgent -> EvidenceAgent
    WeatherAgent and RiskAssessmentAgent must NOT be called.
    """
    initial_state = {
        "message": "Where is the nearest potential fishing zone?",
        "conversation_id": "test-pfz-002",
        "agent_trace": []
    }

    result = orca_graph.invoke(initial_state)

    trace = result["agent_trace"]
    assert "PlannerAgent" in trace
    assert "OceanAgent" in trace
    assert "GeospatialAgent" in trace
    assert "EvidenceAgent" in trace

    # Ensure specialized selective routing: Weather and Risk should NOT be in trace
    assert "WeatherAgent" not in trace
    assert "RiskAssessmentAgent" not in trace

    assert result["planner_plan"]["intent"] == "pfz_search"
    assert result["geospatial_data"]["nearest_pfz"] is not None
    nearest_name = result["geospatial_data"]["nearest_pfz"]["name"]
    assert ("Kuzhuppilly" in nearest_name or "PFZ off" in nearest_name or "Chellanam" in nearest_name)

    # Final answer checks
    final_answer = result["final_answer"]
    assert ("Kuzhuppilly" in final_answer or "PFZ off" in final_answer or "Chellanam" in final_answer)
    assert "km" in final_answer
    assert ("INCOIS" in final_answer or "DEMO_GIS_DATA" in final_answer)
