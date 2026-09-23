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
    TransitRoute
)
from app.agents.planner import PlannerAgent
from app.agents.weather import WeatherAgent
from app.agents.ocean import OceanAgent
from app.agents.geospatial import GeospatialAgent
from app.agents.risk import RiskAssessmentAgent
from app.agents.evidence import EvidenceAgent
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
    ocean_data: Optional[Dict[str, Any]]
    geospatial_data: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    transit_route: Optional[Dict[str, Any]]
    evidence_items: Optional[List[Dict[str, Any]]]
    conversation_context: Optional[Dict[str, Any]]
    
    # Audit Trace
    agent_trace: List[str]
    
    # Final Output
    final_answer: Optional[str]
    final_answer_ml: Optional[str]


# Agent instances
planner_agent = PlannerAgent()
weather_agent = WeatherAgent()
ocean_agent = OceanAgent()
geospatial_agent = GeospatialAgent()
risk_agent = RiskAssessmentAgent()
evidence_agent = EvidenceAgent()


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

    return {
        "weather_data": weather_data.model_dump(),
        "agent_trace": trace
    }


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

    return {
        "ocean_data": ocean_data.model_dump(),
        "agent_trace": trace
    }


def geospatial_node(state: OrcaState) -> OrcaState:
    """Execute GeospatialAgent, record selected PFZ, and compute safe passage route."""
    trace = list(state.get("agent_trace", []))
    trace.append(geospatial_agent.AGENT_NAME)

    plan_dict = state["planner_plan"]
    if plan_dict.get("location"):
        loc_coords = LocationCoords(**plan_dict["location"])
    else:
        loc_coords = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

    geo_data = geospatial_agent.execute(location=loc_coords)

    # Capture nearest PFZ into conversation context
    ctx_dict = dict(state.get("conversation_context") or {})
    if geo_data.nearest_pfz:
        ctx_dict["selected_pfz"] = geo_data.nearest_pfz.model_dump()

    # Plan safe passage corridor route if nearest PFZ is identified
    transit_route_dict = None
    if geo_data.nearest_pfz:
        vessel_type = plan_dict.get("vessel_type") or ctx_dict.get("vessel_type")
        route = geospatial_agent.plan_route(
            origin=loc_coords,
            destination=geo_data.nearest_pfz,
            vessel_type=vessel_type
        )
        transit_route_dict = route.model_dump()
        ctx_dict["active_route"] = transit_route_dict

    return {
        "geospatial_data": geo_data.model_dump(),
        "transit_route": transit_route_dict,
        "conversation_context": ctx_dict,
        "agent_trace": trace
    }


def risk_node(state: OrcaState) -> OrcaState:
    """Execute RiskAssessmentAgent with vessel seaworthiness profiling."""
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

    return {
        "risk_assessment": assessment.model_dump(),
        "agent_trace": trace
    }


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

    ctx_dict = state.get("conversation_context")
    context_obj = ConversationContext(**ctx_dict) if ctx_dict else None

    synth = evidence_agent.synthesize(
        planner_plan=plan_obj,
        weather=weather_obj,
        ocean=ocean_obj,
        geospatial=geo_obj,
        risk=risk_obj,
        context=context_obj,
        transit_route=route_obj
    )

    # Persist updated conversation context to session store
    if context_obj:
        conversation_store.save_context(context_obj)

    return {
        "final_answer": synth["answer"],
        "final_answer_ml": synth.get("answer_ml"),
        "evidence_items": [item.model_dump() for item in synth["evidence"]],
        "conversation_context": context_obj.model_dump() if context_obj else None,
        "transit_route": route_obj.model_dump() if route_obj else None,
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

    if "geospatial" in req:
        return "geospatial_node"
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
