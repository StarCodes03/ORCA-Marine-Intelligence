"""ORCA Marine Intelligence - FastAPI Routes & Endpoints

Provides:
- POST /api/chat: Conversational marine intelligence query endpoint
- GET /api/health: System health and readiness check
- GET /api/spatial/layers: GeoJSON layers for frontend Leaflet map
"""

import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    LocationCoords,
    RiskAssessment,
    WeatherData,
    OceanData,
    GeospatialData,
    EvidenceItem,
    ConversationContext,
    TransitRoute,
    VesselProfile,
    TemporalComparisonResult,
    RouteRiskAssessment
)
from app.config.risk_thresholds import get_vessel_profile
from app.workflows.orca_graph import orca_graph
from app.tools.gis_data import gis_adapter
from app.tools.pfz_data import incois_snapshot_adapter

logger = logging.getLogger("orca.api")
router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ORCA Marine Intelligence API",
        "version": "0.1.0",
        "demo_sector": "Kochi, Kerala (Arabian Sea)",
        "mode": "Development / Demonstration"
    }


@router.get("/spatial/layers")
def get_spatial_layers():
    """Return GeoJSON layers for Leaflet map display."""
    layers = gis_adapter.get_raw_geojson_layers()
    if not incois_snapshot_adapter.is_fallback:
        layers["pfz"] = {
            "type": "FeatureCollection",
            "features": incois_snapshot_adapter.get_geojson_features()
        }
    return layers


@router.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    """Process a conversational marine intelligence query through the LangGraph agent collective."""
    logger.info(f"Incoming chat request: '{request.message}' (id={request.conversation_id})")

    try:
        initial_state = {
            "message": request.message,
            "conversation_id": request.conversation_id or "demo-001",
            "user_latitude": request.user_latitude,
            "user_longitude": request.user_longitude,
            "vessel_type": request.vessel_type,
            "language_mode": request.language_mode,
            "agent_trace": []
        }

        # Invoke LangGraph state machine
        final_state = orca_graph.invoke(initial_state)

        planner_plan = final_state.get("planner_plan", {})
        location_dict = planner_plan.get("location")
        location = LocationCoords(**location_dict) if location_dict else None

        # Parse outputs
        risk = RiskAssessment(**final_state["risk_assessment"]) if final_state.get("risk_assessment") else None
        weather = WeatherData(**final_state["weather_data"]) if final_state.get("weather_data") else None
        ocean = OceanData(**final_state["ocean_data"]) if final_state.get("ocean_data") else None
        geospatial = GeospatialData(**final_state["geospatial_data"]) if final_state.get("geospatial_data") else None
        transit_route = TransitRoute(**final_state["transit_route"]) if final_state.get("transit_route") else None
        temporal_comparison = (
            TemporalComparisonResult(**final_state["temporal_comparison"])
            if final_state.get("temporal_comparison")
            else None
        )
        route_risk = (
            RouteRiskAssessment(**final_state["route_risk"])
            if final_state.get("route_risk")
            else None
        )

        ctx_dict = final_state.get("conversation_context")
        context = ConversationContext(**ctx_dict) if ctx_dict else None

        v_type = planner_plan.get("vessel_type") or (context.vessel_type if context else None)
        v_prof_dict = get_vessel_profile(v_type)
        vessel_profile = VesselProfile(**v_prof_dict) if v_prof_dict else None

        evidence_list = [EvidenceItem(**item) for item in final_state.get("evidence_items", [])]

        # Extract candidate PFZs and comparison
        candidate_pfzs = (
            geospatial.candidate_pfzs
            if geospatial and geospatial.candidate_pfzs
            else (context.candidate_pfzs if context and context.candidate_pfzs else [])
        )
        pfz_comparison = (
            geospatial.pfz_comparison
            if geospatial and geospatial.pfz_comparison
            else (context.pfz_comparison if context and context.pfz_comparison else None)
        )

        # Spatial features bundle for instant map visualization
        spatial_features = {
            "user_location": location.model_dump() if location else None,
            "nearest_pfz": geospatial.nearest_pfz.model_dump() if geospatial and geospatial.nearest_pfz else None,
            "all_pfzs": [pfz.model_dump() for pfz in geospatial.all_pfzs] if geospatial else [],
            "candidate_pfzs": [pfz.model_dump() for pfz in candidate_pfzs],
            "pfz_comparison": pfz_comparison.model_dump() if pfz_comparison else None,
            "restricted_zone_status": geospatial.restricted_zone_check.model_dump() if geospatial else None,
            "route": transit_route.geojson_feature if transit_route else None
        }

        response = ChatResponse(
            answer=final_state.get("final_answer", "Analysis complete."),
            answer_ml=final_state.get("final_answer_ml"),
            intent=planner_plan.get("intent", "general_marine"),
            location=location,
            risk=risk,
            weather=weather,
            ocean=ocean,
            geospatial=geospatial,
            transit_route=transit_route,
            vessel_profile=vessel_profile,
            temporal_comparison=temporal_comparison,
            route_risk=route_risk,
            candidate_pfzs=candidate_pfzs,
            pfz_comparison=pfz_comparison,
            evidence=evidence_list,
            agent_trace=final_state.get("agent_trace", []),
            spatial_features=spatial_features,
            context=context
        )

        logger.info(f"Chat response completed. Trace: {response.agent_trace}")
        return response

    except Exception as e:
        logger.exception(f"Error processing chat request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while executing the agent workflow: {str(e)}"
        )
