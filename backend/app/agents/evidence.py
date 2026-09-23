"""ORCA Marine Intelligence - Evidence & Synthesis Agent

Synthesizes outputs across the entire agent collective, preserving exact source
provenance, differentiating observed data from calculated facts and rule evaluations,
and assembling the final conversational response.
"""

import logging
from typing import Optional, List, Dict, Any
from app.models.schemas import (
    WeatherData,
    OceanData,
    GeospatialData,
    RiskAssessment,
    PlannerOutput,
    EvidenceItem,
    ConversationContext,
    TransitRoute,
    TemporalComparisonResult,
    RouteRiskAssessment
)
from app.services.llm_service import llm_service

logger = logging.getLogger("orca.agents.evidence")


class EvidenceAgent:
    """Agent responsible for explanation synthesis and evidentiary audit trail."""

    AGENT_NAME = "EvidenceAgent"

    def __init__(self):
        self.llm = llm_service

    def synthesize(
        self,
        planner_plan: PlannerOutput,
        weather: Optional[WeatherData] = None,
        ocean: Optional[OceanData] = None,
        geospatial: Optional[GeospatialData] = None,
        risk: Optional[RiskAssessment] = None,
        context: Optional[ConversationContext] = None,
        transit_route: Optional[TransitRoute] = None,
        temporal_comparison: Optional[TemporalComparisonResult] = None,
        route_risk: Optional[RouteRiskAssessment] = None
    ) -> Dict[str, Any]:
        """Produce structured evidence breakdown and final conversational message."""
        logger.info(f"[{self.AGENT_NAME}] Synthesizing multi-agent outputs.")

        evidence_items: List[EvidenceItem] = []

        # Handle early clarification needed
        if planner_plan.intent == "clarification_needed":
            reason = planner_plan.clarification_reason or "missing_information"
            evidence_items.append(EvidenceItem(
                category="rule_evaluation",
                claim=f"Clarification required from user: {reason}",
                source="CONTEXT_RESOLVER",
                raw_data={"clarification_reason": reason}
            ))
            final_answer = self.llm.synthesize_response(
                intent="clarification_needed",
                location=planner_plan.location.model_dump() if planner_plan.location else {},
                time_range=planner_plan.time_range or "",
                clarification_reason=planner_plan.clarification_reason
            )
            lang_mode = planner_plan.language_mode or (context.language_mode if context else "bilingual")
            ml_clarification = (
                "ദയവായി ഒരു കടലോര കേന്ദ്രം (ഉദാഹരണത്തിന്: കൊച്ചി, ചെല്ലാനം, വൈപ്പിൻ) വ്യക്തമാക്കുക."
                if reason == "missing_location"
                else "ദയവായി കൂടുതൽ വിവരങ്ങൾ നൽകുക."
            )
            if lang_mode == "malayalam":
                return {
                    "answer": ml_clarification,
                    "answer_ml": ml_clarification,
                    "evidence": evidence_items
                }
            elif lang_mode == "english":
                return {
                    "answer": final_answer,
                    "answer_ml": None,
                    "evidence": evidence_items
                }
            else:
                return {
                    "answer": final_answer,
                    "answer_ml": ml_clarification,
                    "evidence": evidence_items
                }

        # Handle referent PFZ distance query
        if planner_plan.intent == "pfz_distance":
            pfz = context.selected_pfz if context else None
            origin_name = (planner_plan.location.name if planner_plan.location else (context.location.name if context and context.location else "Kochi"))
            if pfz:
                evidence_items.append(EvidenceItem(
                    category="calculated",
                    claim=f"Resolved distance referent: {pfz.name} is {pfz.distance_km} km away at bearing {pfz.bearing_deg}° from {origin_name}",
                    source="CONTEXT_RESOLVER",
                    raw_data=pfz.model_dump()
                ))
            final_answer = self.llm.synthesize_response(
                intent="pfz_distance",
                location=planner_plan.location.model_dump() if planner_plan.location else {"name": origin_name},
                time_range=planner_plan.time_range or "",
                selected_pfz=pfz.model_dump() if pfz else None
            )
            return {
                "answer": final_answer,
                "answer_ml": None,
                "evidence": evidence_items
            }


        # 1. Weather evidence
        if weather:
            if (weather.lightning_risk or "").lower() in ["unsupported", "unavailable", "not_provided", "n/a"]:
                lightning_claim = "Lightning risk was not provided by the selected live source (Open-Meteo)"
            else:
                lightning_claim = f"Lightning risk '{weather.lightning_risk}'"

            evidence_items.append(EvidenceItem(
                category="observed",
                claim=f"Wind speed measured at {weather.wind_speed_kmh} km/h, Rain probability at {weather.rain_probability}%, {lightning_claim}",
                source=weather.source,
                raw_data={
                    "wind_speed_kmh": weather.wind_speed_kmh,
                    "rain_probability": weather.rain_probability,
                    "lightning_risk": weather.lightning_risk,
                    "forecast_time": weather.forecast_time
                }
            ))

        # 2. Oceanographic evidence
        if ocean:
            if ocean.chlorophyll_mg_m3 is not None:
                chloro_claim = f"; Chlorophyll at {ocean.chlorophyll_mg_m3} mg/m³"
            else:
                chloro_claim = "; Chlorophyll data not provided by live marine feed"

            evidence_items.append(EvidenceItem(
                category="observed",
                claim=f"Significant wave height at {ocean.wave_height_m} m with '{ocean.sea_state}' sea state; SST at {ocean.sst_c}°C{chloro_claim}",
                source=ocean.source,
                raw_data={
                    "sst_c": ocean.sst_c,
                    "wave_height_m": ocean.wave_height_m,
                    "sea_state": ocean.sea_state,
                    "tide": ocean.tide,
                    "chlorophyll_mg_m3": ocean.chlorophyll_mg_m3
                }
            ))

        # 3. Calculated geospatial facts
        if geospatial:
            if geospatial.nearest_pfz:
                npfz = geospatial.nearest_pfz
                evidence_items.append(EvidenceItem(
                    category="calculated",
                    claim=f"Calculated geodesic distance to nearest Potential Fishing Zone '{npfz.name}' is {npfz.distance_km} km at bearing {npfz.bearing_deg}°",
                    source=geospatial.source,
                    raw_data={
                        "pfz_id": npfz.pfz_id,
                        "distance_km": npfz.distance_km,
                        "bearing_deg": npfz.bearing_deg,
                        "target_species": npfz.target_species
                    }
                ))

            rz = geospatial.restricted_zone_check
            evidence_items.append(EvidenceItem(
                category="calculated",
                claim=f"Geofence analysis: Inside restricted zone = {rz.inside_restricted_zone}, Nearby = {rz.restricted_zone_nearby}",
                source=geospatial.source,
                raw_data={
                    "inside_restricted_zone": rz.inside_restricted_zone,
                    "restricted_zone_nearby": rz.restricted_zone_nearby,
                    "zone_name": rz.zone_name,
                    "distance_to_nearest_zone_km": rz.distance_to_nearest_zone_km
                }
            ))

            # PFZ Provenance Evidence Claim
            if geospatial.source_type == "OFFICIAL_SNAPSHOT":
                evidence_items.append(EvidenceItem(
                    category="source_metadata",
                    claim=f"PFZ Data: Retrieved from official INCOIS historical snapshot (advisory date: {geospatial.advisory_date}, valid until: {geospatial.valid_until}) — not a live fishing advisory.",
                    source=geospatial.source,
                    raw_data={
                        "source": geospatial.source,
                        "source_type": geospatial.source_type,
                        "advisory_date": geospatial.advisory_date,
                        "valid_until": geospatial.valid_until,
                        "is_live": geospatial.is_live,
                        "is_mock": geospatial.is_mock
                    }
                ))
            elif geospatial.source_type == "MOCK_FALLBACK":
                evidence_items.append(EvidenceItem(
                    category="source_metadata",
                    claim="PFZ snapshot unavailable; automatically reverted to simulated mock PFZ dataset.",
                    source=geospatial.source,
                    raw_data={
                        "source": geospatial.source,
                        "source_type": geospatial.source_type,
                        "is_live": False,
                        "is_mock": True
                    }
                ))

        # 4. Rule-based risk evaluation
        if risk:
            evidence_items.append(EvidenceItem(
                category="rule_evaluation",
                claim=f"Composite risk score {risk.risk_score} mapped to risk level '{risk.risk_level}'. Contributing factors: {', '.join(risk.reasons)}",
                source="RULE_BASED_RISK_ENGINE",
                raw_data={
                    "risk_level": risk.risk_level,
                    "risk_score": risk.risk_score,
                    "vessel_type": risk.vessel_type,
                    "reasons": risk.reasons,
                    "score_breakdown": risk.score_breakdown.model_dump() if risk.score_breakdown else None
                }
            ))

            # Craft seaworthiness evidence item
            if risk.vessel_type:
                evidence_items.append(EvidenceItem(
                    category="rule_evaluation",
                    claim=f"Vessel seaworthiness assessment for craft '{risk.vessel_type}': evaluated against configurable prototype/demo wave and wind limits (not official maritime regulations or authoritative seaworthiness limits).",
                    source="VESSEL_SEAWORTHINESS_ENGINE",
                    raw_data={
                        "vessel_type": risk.vessel_type,
                        "risk_level": risk.risk_level,
                        "reasons": risk.reasons
                    }
                ))

        # 5. Safe passage corridor routing evidence
        if transit_route:
            avoidance_claim = (
                f"Corridor diverted around {', '.join(transit_route.avoided_zones)} with {transit_route.clearance_buffer_km} km buffer"
                if transit_route.geofence_avoidance_applied and transit_route.avoided_zones
                else f"Direct route clear of restricted zones ({transit_route.clearance_buffer_km} km buffer)"
            )
            evidence_items.append(EvidenceItem(
                category="calculated",
                claim=(
                    f"Safe passage corridor planned: {transit_route.origin.name} to {transit_route.destination.name}. "
                    f"Total distance {transit_route.total_distance_km} km ({transit_route.total_distance_nm} nm), "
                    f"duration ~{transit_route.estimated_duration_hours} h, "
                    f"fuel ~{transit_route.estimated_fuel_litres} L ({transit_route.fuel_type or 'N/A'}). {avoidance_claim}."
                ),
                source="GEOMETRIC_ROUTING_ENGINE",
                raw_data=transit_route.model_dump()
            ))

        # 6. Temporal comparison evidence
        if temporal_comparison:
            evidence_items.append(EvidenceItem(
                category="derived_calculation",
                claim=(
                    f"Temporal comparison between {temporal_comparison.window_1.time_window} and {temporal_comparison.window_2.time_window}: "
                    f"Overall trend '{temporal_comparison.trend}', recommendation '{temporal_comparison.recommendation}'. "
                    f"Provenance: {temporal_comparison.provenance_notice}"
                ),
                source="TEMPORAL_REASONING_ENGINE",
                raw_data=temporal_comparison.model_dump()
            ))

        # 7. Prototype Route Risk Index evidence
        if route_risk:
            evidence_items.append(EvidenceItem(
                category="rule_evaluation",
                claim=(
                    f"Prototype Route Risk Index: {route_risk.prototype_route_risk_index}/10 ({route_risk.risk_level}). "
                    f"Dominant limiting factor: {route_risk.limiting_factor}. "
                    f"Evaluation point: ({route_risk.evaluation_point.latitude:.4f}, {route_risk.evaluation_point.longitude:.4f}). "
                    f"Notice: {route_risk.disclaimer}"
                ),
                source="PROTOTYPE_ROUTE_RISK_ENGINE",
                raw_data=route_risk.model_dump()
            ))

        # 8. Conversational response generation with language mode handling
        lang_mode = planner_plan.language_mode or (context.language_mode if context else "bilingual")
        v_type = planner_plan.vessel_type or (context.vessel_type if context else (risk.vessel_type if risk else None))

        final_answer_en = self.llm.synthesize_response(
            intent=planner_plan.intent,
            location=planner_plan.location.model_dump() if planner_plan.location else {"name": "Kochi"},
            time_range=planner_plan.time_range or "tomorrow_morning",
            weather=weather.model_dump() if weather else None,
            ocean=ocean.model_dump() if ocean else None,
            geospatial=geospatial.model_dump() if geospatial else None,
            risk=risk.model_dump() if risk else None,
            transit_route=transit_route.model_dump() if transit_route else None,
            vessel_type=v_type,
            language_mode=lang_mode,
            temporal_comparison=temporal_comparison.model_dump() if temporal_comparison else None,
            route_risk=route_risk.model_dump() if route_risk else None
        )

        final_answer_ml = self.llm.synthesize_malayalam_advisory(
            intent=planner_plan.intent,
            location=planner_plan.location.model_dump() if planner_plan.location else {"name": "Kochi"},
            time_range=planner_plan.time_range or "tomorrow_morning",
            weather=weather.model_dump() if weather else None,
            ocean=ocean.model_dump() if ocean else None,
            geospatial=geospatial.model_dump() if geospatial else None,
            risk=risk.model_dump() if risk else None,
            transit_route=transit_route.model_dump() if transit_route else None,
            vessel_type=v_type,
            temporal_comparison=temporal_comparison.model_dump() if temporal_comparison else None,
            route_risk=route_risk.model_dump() if route_risk else None
        )

        if lang_mode == "malayalam":
            final_answer = final_answer_ml
            answer_ml = final_answer_ml
        elif lang_mode == "english":
            final_answer = final_answer_en
            answer_ml = None
        else:  # "bilingual" (default)
            final_answer = final_answer_en
            answer_ml = final_answer_ml

        return {
            "answer": final_answer,
            "answer_ml": answer_ml,
            "evidence": evidence_items
        }
