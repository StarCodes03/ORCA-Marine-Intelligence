"""ORCA Marine Intelligence - LangGraph Workflow Orchestrator

Explicit multi-agent workflow powered by LangGraph.
Implements conditional routing based on PlannerAgent intent analysis:
- Marine Safety: Weather -> Ocean -> Geospatial -> Risk -> Evidence -> END
- PFZ Search: Ocean -> Geospatial -> Evidence -> END
- Weather Only: Weather -> Evidence -> END
- Ocean Only: Ocean -> Evidence -> END

Preserves full execution trace in agent_trace.
"""

from typing import TypedDict, List, Optional, Dict, Any
import logging
from langgraph.graph import StateGraph, START, END

from app.models.schemas import (
    PlannerOutput,
    WeatherData,
    OceanData,
    GeospatialData,
    RiskAssessment,
    LocationCoords,
    EvidenceItem,
    ConversationContext,
    TransitRoute,
    TemporalComparisonResult,
    RouteRiskAssessment,
    TimeWindowMetrics,
    NearestPFZ,
    PFZComparisonResult
)
from app.agents.planner import PlannerAgent
from app.agents.weather import WeatherAgent
from app.agents.ocean import OceanAgent
from app.agents.geospatial import GeospatialAgent
from app.agents.risk import RiskAssessmentAgent
from app.agents.evidence import EvidenceAgent
from app.tools.temporal_reasoning import TemporalReasoningEngine
from app.tools.route_risk import RouteRiskCalculator
from app.services.conversation_store import conversation_store

logger = logging.getLogger("orca.workflow")


class OrcaState(TypedDict, total=False):
    """LangGraph state schema representing shared blackboard between agents."""
    message: str
    conversation_id: str
    user_latitude: Optional[float]
    user_longitude: Optional[float]
    vessel_type: Optional[str]
    language_mode: Optional[str]
    
    # Agent Artifacts
    planner_plan: Optional[Dict[str, Any]]
    weather_data: Optional[Dict[str, Any]]
    weather_data_w2: Optional[Dict[str, Any]]
    ocean_data: Optional[Dict[str, Any]]
    ocean_data_w2: Optional[Dict[str, Any]]
    geospatial_data: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    transit_route: Optional[Dict[str, Any]]
    temporal_comparison: Optional[Dict[str, Any]]
    route_risk: Optional[Dict[str, Any]]
    candidate_pfzs: Optional[List[Dict[str, Any]]]
    pfz_comparison: Optional[Dict[str, Any]]
    evidence_items: Optional[List[Dict[str, Any]]]
    conversation_context: Optional[Dict[str, Any]]
    
    # Audit Trace
    agent_trace: List[str]
    
    # Final Output
    final_answer: Optional[str]
    final_answer_ml: Optional[str]


# Agent and engine instances
planner_agent = PlannerAgent()
weather_agent = WeatherAgent()
ocean_agent = OceanAgent()
geospatial_agent = GeospatialAgent()
risk_agent = RiskAssessmentAgent()
evidence_agent = EvidenceAgent()
temporal_engine = TemporalReasoningEngine()
route_risk_calculator = RouteRiskCalculator()


def planner_node(state: OrcaState) -> OrcaState:
    """Execute PlannerAgent with multi-turn conversation context."""
    trace = list(state.get("agent_trace", []))
    trace.append(planner_agent.AGENT_NAME)

    conv_id = state.get("conversation_id", "demo-001")
    prior_ctx = conversation_store.get_context(conv_id)

    plan, updated_ctx = planner_agent.plan(
        message=state["message"],
        user_lat=state.get("user_latitude"),
        user_lon=state.get("user_longitude"),
        prior_context=prior_ctx,
        conversation_id=conv_id,
        vessel_type=state.get("vessel_type"),
        language_mode=state.get("language_mode")
    )

    return {
        "planner_plan": plan.model_dump(),
        "conversation_context": updated_ctx.model_dump(),
        "agent_trace": trace
    }


def weather_node(state: OrcaState) -> OrcaState:
    """Execute WeatherAgent."""
    trace = list(state.get("agent_trace", []))
    trace.append(weather_agent.AGENT_NAME)

    plan_dict = state["planner_plan"]
    if not plan_dict.get("location"):
        return {"agent_trace": trace}
    loc_coords = LocationCoords(**plan_dict["location"])
    time_range = plan_dict.get("time_range", "tomorrow_morning")

    weather_data = weather_agent.execute(
        location=loc_coords,
        time_range=time_range
    )

    result: OrcaState = {
        "weather_data": weather_data.model_dump(),
        "agent_trace": trace
    }

    # If comparing windows, fetch second window
    compare_windows = plan_dict.get("compare_windows")
    if compare_windows and len(compare_windows) >= 2:
        w2_time_range = compare_windows[1]
        weather_data_w2 = weather_agent.execute(
            location=loc_coords,
            time_range=w2_time_range
        )
        result["weather_data_w2"] = weather_data_w2.model_dump()

    return result


def ocean_node(state: OrcaState) -> OrcaState:
    """Execute OceanAgent."""
    trace = list(state.get("agent_trace", []))
    trace.append(ocean_agent.AGENT_NAME)

    plan_dict = state["planner_plan"]
    if plan_dict.get("location"):
        loc_coords = LocationCoords(**plan_dict["location"])
    else:
        loc_coords = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    time_range = plan_dict.get("time_range", "tomorrow_morning")

    ocean_data = ocean_agent.execute(
        location=loc_coords,
        time_range=time_range
    )

    result: OrcaState = {
        "ocean_data": ocean_data.model_dump(),
        "agent_trace": trace
    }

    # If comparing windows, fetch second window
    compare_windows = plan_dict.get("compare_windows")
    if compare_windows and len(compare_windows) >= 2:
        w2_time_range = compare_windows[1]
        ocean_data_w2 = ocean_agent.execute(
            location=loc_coords,
            time_range=w2_time_range
        )
        result["ocean_data_w2"] = ocean_data_w2.model_dump()

    return result


def geospatial_node(state: OrcaState) -> OrcaState:
    """Execute GeospatialAgent, record selected/candidate PFZs, and compute safe passage route."""
    trace = list(state.get("agent_trace", []))
    trace.append(geospatial_agent.AGENT_NAME)

    plan_dict = state["planner_plan"]
    if plan_dict.get("location"):
        loc_coords = LocationCoords(**plan_dict["location"])
    else:
        loc_coords = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

    ctx_dict = dict(state.get("conversation_context") or {})
    candidate_ctx = [NearestPFZ(**item) for item in ctx_dict.get("candidate_pfzs", [])]
    selected_target = NearestPFZ(**ctx_dict["selected_pfz"]) if ctx_dict.get("selected_pfz") else None

    # Resolve target ordinal if planner specified target_ordinal
    target_ord = plan_dict.get("target_ordinal")
    if target_ord is not None and candidate_ctx and len(candidate_ctx) > target_ord:
        selected_target = candidate_ctx[target_ord]

    intent = plan_dict.get("intent")
    radius_km = plan_dict.get("radius_km")
    compare_targets = plan_dict.get("compare_targets")

    geo_data = geospatial_agent.execute(
        location=loc_coords,
        radius_km=radius_km,
        intent=intent,
        candidate_context=candidate_ctx,
        selected_target=selected_target,
        compare_targets=compare_targets
    )

    # Capture candidate PFZs into conversation context
    if geo_data.candidate_pfzs:
        ctx_dict["candidate_pfzs"] = [c.model_dump() for c in geo_data.candidate_pfzs]

    # Capture selected PFZ into conversation context
    if selected_target:
        ctx_dict["selected_pfz"] = selected_target.model_dump()
    elif geo_data.nearest_pfz:
        ctx_dict["selected_pfz"] = geo_data.nearest_pfz.model_dump()

    # Capture candidate comparison into conversation context
    if geo_data.pfz_comparison:
        ctx_dict["pfz_comparison"] = geo_data.pfz_comparison.model_dump()
        ctx_dict["compared_pfzs"] = [
            geo_data.pfz_comparison.target_a.model_dump(),
            geo_data.pfz_comparison.target_b.model_dump()
        ]

    # Plan safe passage corridor route if nearest PFZ or selected target is identified
    transit_route_dict = None
    target_for_routing = selected_target or geo_data.nearest_pfz
    if target_for_routing and intent not in ["pfz_radius_filter", "pfz_comparison", "pfz_geofence_check"]:
        vessel_type = plan_dict.get("vessel_type") or ctx_dict.get("vessel_type")
        route = geospatial_agent.plan_route(
            origin=loc_coords,
            destination=target_for_routing,
            vessel_type=vessel_type
        )
        transit_route_dict = route.model_dump()
        ctx_dict["active_route"] = transit_route_dict

    return {
        "geospatial_data": geo_data.model_dump(),
        "transit_route": transit_route_dict,
        "candidate_pfzs": [c.model_dump() for c in geo_data.candidate_pfzs] if geo_data.candidate_pfzs else None,
        "pfz_comparison": geo_data.pfz_comparison.model_dump() if geo_data.pfz_comparison else None,
        "conversation_context": ctx_dict,
        "agent_trace": trace
    }


def risk_node(state: OrcaState) -> OrcaState:
    """Execute RiskAssessmentAgent with vessel seaworthiness profiling and M5 deterministic reasoning."""
    trace = list(state.get("agent_trace", []))
    trace.append(risk_agent.AGENT_NAME)

    weather_obj = WeatherData(**state["weather_data"]) if state.get("weather_data") else None
    ocean_obj = OceanData(**state["ocean_data"]) if state.get("ocean_data") else None
    geo_obj = GeospatialData(**state["geospatial_data"]) if state.get("geospatial_data") else None

    plan_dict = state.get("planner_plan", {})
    ctx_dict = state.get("conversation_context", {})
    vessel_type = plan_dict.get("vessel_type") or (ctx_dict.get("vessel_type") if ctx_dict else None)

    assessment = risk_agent.assess(
        weather=weather_obj,
        ocean=ocean_obj,
        geospatial=geo_obj,
        vessel_type=vessel_type
    )

    result: OrcaState = {
        "risk_assessment": assessment.model_dump(),
        "agent_trace": trace
    }

    # Location coordinates for evaluation point
    if plan_dict.get("location"):
        loc_coords = LocationCoords(**plan_dict["location"])
    elif ctx_dict.get("location"):
        loc_coords = LocationCoords(**ctx_dict["location"])
    else:
        loc_coords = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

    # 1. Deterministic Temporal Reasoning if comparing windows
    compare_windows = plan_dict.get("compare_windows")
    if compare_windows and len(compare_windows) >= 2 and state.get("weather_data_w2") and state.get("ocean_data_w2"):
        w1_name = compare_windows[0]
        w2_name = compare_windows[1]
        weather_w2 = WeatherData(**state["weather_data_w2"])
        ocean_w2 = OceanData(**state["ocean_data_w2"])
        assessment_w2 = risk_agent.assess(
            weather=weather_w2,
            ocean=ocean_w2,
            geospatial=None,
            vessel_type=vessel_type
        )
        if weather_obj and ocean_obj:
            m1 = temporal_engine.extract_window_metrics(
                time_window=w1_name,
                weather=weather_obj,
                ocean=ocean_obj,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level
            )
            m2 = temporal_engine.extract_window_metrics(
                time_window=w2_name,
                weather=weather_w2,
                ocean=ocean_w2,
                risk_score=assessment_w2.risk_score,
                risk_level=assessment_w2.risk_level
            )
            comp_result = temporal_engine.compare_time_windows(
                evaluation_point=loc_coords,
                window_1=m1,
                window_2=m2
            )
            result["temporal_comparison"] = comp_result.model_dump()

    # 2. Deterministic Prototype Route Risk Index
    transit_route_data = state.get("transit_route") or (ctx_dict.get("active_route") if ctx_dict else None)
    if transit_route_data:
        route_obj = TransitRoute(**transit_route_data)
        route_risk = route_risk_calculator.assess_route_risk(
            origin=loc_coords,
            transit_route=route_obj,
            weather=weather_obj,
            ocean=ocean_obj,
            risk_assessment=assessment,
            vessel_type=vessel_type
        )
        result["route_risk"] = route_risk.model_dump()

    return result


def evidence_node(state: OrcaState) -> OrcaState:
    """Execute EvidenceAgent and commit structured context to session store."""
    trace = list(state.get("agent_trace", []))
    trace.append(evidence_agent.AGENT_NAME)

    plan_obj = PlannerOutput(**state["planner_plan"])
    weather_obj = WeatherData(**state["weather_data"]) if state.get("weather_data") else None
    ocean_obj = OceanData(**state["ocean_data"]) if state.get("ocean_data") else None
    geo_obj = GeospatialData(**state["geospatial_data"]) if state.get("geospatial_data") else None
    risk_obj = RiskAssessment(**state["risk_assessment"]) if state.get("risk_assessment") else None
    route_obj = TransitRoute(**state["transit_route"]) if state.get("transit_route") else None

    # M5 models
    temp_comp_data = state.get("temporal_comparison")
    temporal_comp_obj = TemporalComparisonResult(**temp_comp_data) if temp_comp_data else None

    route_risk_data = state.get("route_risk")
    route_risk_obj = RouteRiskAssessment(**route_risk_data) if route_risk_data else None

    candidate_pfzs_data = state.get("candidate_pfzs") or (
        state.get("geospatial_data", {}).get("candidate_pfzs")
        if state.get("geospatial_data") else None
    )
    candidate_pfzs_obj = [NearestPFZ(**c) for c in candidate_pfzs_data] if candidate_pfzs_data else []

    pfz_comp_data = state.get("pfz_comparison") or (
        state.get("geospatial_data", {}).get("pfz_comparison")
        if state.get("geospatial_data") else None
    )
    pfz_comp_obj = PFZComparisonResult(**pfz_comp_data) if pfz_comp_data else None

    ctx_dict = state.get("conversation_context")
    context_obj = ConversationContext(**ctx_dict) if ctx_dict else None

    synth = evidence_agent.synthesize(
        planner_plan=plan_obj,
        weather=weather_obj,
        ocean=ocean_obj,
        geospatial=geo_obj,
        risk=risk_obj,
        context=context_obj,
        transit_route=route_obj,
        temporal_comparison=temporal_comp_obj,
        route_risk=route_risk_obj,
        candidate_pfzs=candidate_pfzs_obj,
        pfz_comparison=pfz_comp_obj
    )

    # Persist updated conversation context to session store
    if context_obj:
        if temporal_comp_obj:
            context_obj.temporal_comparison = temporal_comp_obj
        if route_risk_obj:
            context_obj.route_risk = route_risk_obj
        if candidate_pfzs_obj:
            context_obj.candidate_pfzs = candidate_pfzs_obj
        if pfz_comp_obj:
            context_obj.pfz_comparison = pfz_comp_obj
            context_obj.compared_pfzs = [pfz_comp_obj.target_a, pfz_comp_obj.target_b]
        conversation_store.save_context(context_obj)

    return {
        "final_answer": synth["answer"],
        "final_answer_ml": synth.get("answer_ml"),
        "evidence_items": [item.model_dump() for item in synth["evidence"]],
        "conversation_context": context_obj.model_dump() if context_obj else None,
        "transit_route": route_obj.model_dump() if route_obj else None,
        "temporal_comparison": temporal_comp_obj.model_dump() if temporal_comp_obj else None,
        "route_risk": route_risk_obj.model_dump() if route_risk_obj else None,
        "candidate_pfzs": [c.model_dump() for c in candidate_pfzs_obj] if candidate_pfzs_obj else None,
        "pfz_comparison": pfz_comp_obj.model_dump() if pfz_comp_obj else None,
        "agent_trace": trace
    }


# Routing Condition Functions
def route_from_planner(state: OrcaState) -> str:
    """Decide starting specialized agent based on planner plan."""
    plan = state.get("planner_plan", {})
    intent = plan.get("intent", "marine_safety")
    req = plan.get("required_agents", [])

    if intent == "clarification_needed" or not req:
        return "evidence_node"

    if "weather" in req:
        return "weather_node"
    elif "ocean" in req:
        return "ocean_node"
    elif "geospatial" in req:
        return "geospatial_node"
    return "evidence_node"


def route_from_weather(state: OrcaState) -> str:
    """Route after weather telemetry."""
    plan = state.get("planner_plan", {})
    req = plan.get("required_agents", [])

    if "ocean" in req:
        return "ocean_node"
    elif "geospatial" in req:
        return "geospatial_node"
    return "evidence_node"


def route_from_ocean(state: OrcaState) -> str:
    """Route after ocean telemetry."""
    plan = state.get("planner_plan", {})
    req = plan.get("required_agents", [])
    intent = plan.get("intent", "marine_safety")

    if "geospatial" in req:
        return "geospatial_node"
    if intent == "temporal_comparison" or plan.get("compare_windows"):
        return "risk_node"
    return "evidence_node"


def route_from_geospatial(state: OrcaState) -> str:
    """Route after geospatial calculations."""
    plan = state.get("planner_plan", {})
    intent = plan.get("intent", "marine_safety")

    # If marine safety, safe passage route, or weather+ocean present, run risk assessment
    if intent in ["marine_safety", "safe_passage_route"] or (state.get("weather_data") and state.get("ocean_data")):
        return "risk_node"
    return "evidence_node"


# Build LangGraph Workflow
def build_orca_graph():
    builder = StateGraph(OrcaState)

    # Add Nodes
    builder.add_node("planner_node", planner_node)
    builder.add_node("weather_node", weather_node)
    builder.add_node("ocean_node", ocean_node)
    builder.add_node("geospatial_node", geospatial_node)
    builder.add_node("risk_node", risk_node)
    builder.add_node("evidence_node", evidence_node)

    # Add Edges
    builder.add_edge(START, "planner_node")

    # Conditional Routing from Planner
    builder.add_conditional_edges(
        "planner_node",
        route_from_planner,
        {
            "weather_node": "weather_node",
            "ocean_node": "ocean_node",
            "geospatial_node": "geospatial_node",
            "evidence_node": "evidence_node",
        }
    )

    # Conditional Routing from Weather
    builder.add_conditional_edges(
        "weather_node",
        route_from_weather,
        {
            "ocean_node": "ocean_node",
            "geospatial_node": "geospatial_node",
            "evidence_node": "evidence_node",
        }
    )

    # Conditional Routing from Ocean
    builder.add_conditional_edges(
        "ocean_node",
        route_from_ocean,
        {
            "geospatial_node": "geospatial_node",
            "risk_node": "risk_node",
            "evidence_node": "evidence_node",
        }
    )

    # Conditional Routing from Geospatial
    builder.add_conditional_edges(
        "geospatial_node",
        route_from_geospatial,
        {
            "risk_node": "risk_node",
            "evidence_node": "evidence_node",
        }
    )

    # From Risk to Evidence
    builder.add_edge("risk_node", "evidence_node")

    # From Evidence to END
    builder.add_edge("evidence_node", END)

    return builder.compile()


# Compiled singleton graph
orca_graph = build_orca_graph()
