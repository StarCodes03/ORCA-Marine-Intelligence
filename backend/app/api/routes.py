"""ORCA Marine Intelligence - FastAPI Routes & Endpoints

Provides:
- POST /api/chat: Conversational marine intelligence query endpoint
- GET /api/health: System health and readiness check
- GET /api/spatial/layers: GeoJSON layers for frontend Leaflet map
- GET /api/conversations: List active conversation sessions
- GET /api/conversations/{id}: Retrieve conversation context and turn history
- DELETE /api/conversations/{id}: Reset conversation session
- GET /api/vessel-profiles: List built-in and custom vessel profiles
- POST /api/vessel-profiles: Create or update custom vessel profile
- GET /api/alerts: List active maritime alerts
- POST /api/alerts/evaluate: Deterministically evaluate proximity, threshold, and route alerts
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

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
    RouteRiskAssessment,
    AlertEvaluationRequest,
    MaritimeAlert
)
from app.config.risk_thresholds import get_vessel_profile
from app.workflows.orca_graph import orca_graph
from app.tools.gis_data import gis_adapter
from app.tools.pfz_data import incois_snapshot_adapter
from app.tools.alerts import alert_engine
from app.services.storage import storage_repo

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


@router.get("/conversations")
def list_conversations(limit: int = Query(20, ge=1, le=100)):
    """List recent conversation sessions."""
    return storage_repo.list_conversations(limit=limit)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    """Retrieve full conversation context state and message history."""
    ctx = storage_repo.get_conversation(conversation_id)
    messages = storage_repo.get_messages(conversation_id)
    if not ctx and not messages:
        raise HTTPException(status_code=404, detail="Conversation session not found")
    return {
        "conversation_id": conversation_id,
        "context": ctx,
        "messages": messages
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete conversation session and all associated turns and alerts."""
    deleted = storage_repo.delete_conversation(conversation_id)
    return {"success": deleted, "conversation_id": conversation_id}


@router.get("/vessel-profiles")
def get_vessel_profiles():
    """List all available vessel profiles (built-in and custom)."""
    return storage_repo.get_vessel_profiles()


@router.post("/vessel-profiles")
def save_vessel_profile(profile: VesselProfile):
    """Create or update a custom vessel seaworthiness profile."""
    saved = storage_repo.save_vessel_profile(profile.model_dump())
    return saved


@router.get("/alerts")
def list_alerts(conversation_id: Optional[str] = None):
    """List active maritime alerts, optionally scoped to a conversation."""
    return storage_repo.get_active_alerts(conversation_id=conversation_id)


@router.post("/alerts/evaluate")
def evaluate_alerts(req: AlertEvaluationRequest):
    """Deterministically evaluate alerts against vessel location, limits, and routes."""
    waypoints = [(pt[0], pt[1]) for pt in req.route_waypoints] if req.route_waypoints else None
    alerts = alert_engine.evaluate_all(
        vessel_lat=req.vessel_latitude,
        vessel_lon=req.vessel_longitude,
        vessel_type=req.vessel_type,
        wave_height_m=req.wave_height_m,
        wind_speed_kmh=req.wind_speed_kmh,
        route_waypoints=waypoints,
        conversation_id=req.conversation_id,
        persist=req.persist
    )
    return alerts


@router.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    """Process a conversational marine intelligence query through the LangGraph agent collective."""
    cid = request.conversation_id or "demo-001"
    logger.info(f"Incoming chat request: '{request.message}' (id={cid})")

    try:
        initial_state = {
            "message": request.message,
            "conversation_id": cid,
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
        v_prof_dict = storage_repo.get_vessel_profile(v_type) or get_vessel_profile(v_type)
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

        # Determine if query was conversational greeting, unsupported domain, or early clarification
        intent = planner_plan.get("intent", "marine_safety")
        is_conversational_or_unsupported = intent in [
            "conversational_greeting",
            "unsupported",
            "clarification_needed"
        ]

        if is_conversational_or_unsupported:
            spatial_features = None
            detected_alerts = []
            if intent in ["conversational_greeting", "unsupported"]:
                location = None
        elif intent == "marine_update":
            spatial_features = None
            detected_alerts = []
            geospatial = None
            transit_route = None
        else:
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

            # Deterministic alert evaluation
            vessel_lat = location.latitude if location else (request.user_latitude or 9.9312)
            vessel_lon = location.longitude if location else (request.user_longitude or 76.2673)
            wave_height = ocean.wave_height_m if ocean else None
            wind_speed = weather.wind_speed_kmh if weather else None
            route_pts = None
            if transit_route and transit_route.waypoints:
                route_pts = [(wp.latitude, wp.longitude) for wp in transit_route.waypoints]

            detected_alerts = alert_engine.evaluate_all(
                vessel_lat=vessel_lat,
                vessel_lon=vessel_lon,
                vessel_type=v_type,
                wave_height_m=wave_height,
                wind_speed_kmh=wind_speed,
                route_waypoints=route_pts,
                conversation_id=cid,
                persist=True
            )

        # Persist conversation turn
        storage_repo.save_message(
            conversation_id=cid,
            role="user",
            content=request.message,
            intent=planner_plan.get("intent"),
            metadata={"vessel_type": v_type}
        )
        storage_repo.save_message(
            conversation_id=cid,
            role="assistant",
            content=final_state.get("final_answer", "Analysis complete."),
            intent=planner_plan.get("intent"),
            metadata={
                "risk_level": risk.risk_level if risk else None,
                "has_route": bool(transit_route),
                "alert_count": len(detected_alerts)
            }
        )

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
            context=context,
            alerts=detected_alerts
        )

        logger.info(f"Chat response completed. Trace: {response.agent_trace}, Alerts: {len(detected_alerts)}")
        return response

    except Exception as e:
        logger.exception(f"Error processing chat request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while executing the agent workflow: {str(e)}"
        )
