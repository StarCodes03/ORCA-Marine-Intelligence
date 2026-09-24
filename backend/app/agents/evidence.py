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
    RouteRiskAssessment,
    NearestPFZ,
    PFZComparisonResult
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
        route_risk: Optional[RouteRiskAssessment] = None,
        candidate_pfzs: Optional[List[NearestPFZ]] = None,
        pfz_comparison: Optional[PFZComparisonResult] = None,
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Produce structured evidence breakdown and final conversational message."""
        logger.info(f"[{self.AGENT_NAME}] Synthesizing multi-agent outputs.")

        evidence_items: List[EvidenceItem] = []

        # Handle casual conversational greetings
        if planner_plan.intent == "conversational_greeting":
            lang_mode = planner_plan.language_mode or (context.language_mode if context else "bilingual")
            res = self.llm.synthesize_conversational_response(
                text=user_message or "",
                language_mode=lang_mode
            )
            return {
                "answer": res["answer"],
                "answer_ml": res.get("answer_ml"),
                "evidence": []
            }

        # Handle unsupported / out-of-scope domain queries
        if planner_plan.intent == "unsupported":
            lang_mode = planner_plan.language_mode or (context.language_mode if context else "bilingual")
            if planner_plan.clarification_reason == "unsupported_news":
                res = self.llm.synthesize_unsupported_news_response(
                    text=user_message or "",
                    language_mode=lang_mode
                )
            else:
                res = self.llm.synthesize_unsupported_response(
                    text=user_message or "",
                    language_mode=lang_mode
                )
            return {
                "answer": res["answer"],
                "answer_ml": res.get("answer_ml"),
                "evidence": []
            }

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
                else (
                    "താരതമ്യം ചെയ്യാനോ പരിശോധിക്കാനോ നിലവിൽ PFZ ലക്ഷ്യങ്ങൾ ലഭ്യമല്ല. ദയവായി ആദ്യം 'Show PFZ targets within 30 km of Kochi' എന്ന് നൽകുക."
                    if reason == "missing_candidate_context"
                    else (
                        "ദയവായി ഏത് ലക്ഷ്യത്തിലേക്കുള്ള ദൂരമാണ് കണക്കാക്കേണ്ടതെന്ന് വ്യക്തമാക്കുക."
                        if reason == "missing_referent_target"
                        else (
                            "ദയവായി ഏത് കടലോര കേന്ദ്രത്തെക്കുറിച്ചും പ്രവർത്തനത്തെക്കുറിച്ചുമാണ് ചോദിക്കുന്നതെന്ന് വ്യക്തമാക്കുക. (ഉദാ: 'നാളെ രാവിലെ കൊച്ചിയിൽ മീൻപിടിക്കാൻ സുരക്ഷിതമാണോ?')"
                            if reason == "missing_referent_context"
                            else "ദയവായി കൂടുതൽ വിവരങ്ങൾ നൽകുക."
                        )
                    )
                )
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

            if transit_route.alternatives:
                rec_alts = [a.name for a in transit_route.alternatives if a.is_recommended]
                rec_str = rec_alts[0] if rec_alts else transit_route.alternatives[0].name
                evidence_items.append(EvidenceItem(
                    category="calculated",
                    claim=(
                        f"Route alternatives generated: {len(transit_route.alternatives)} navigational corridor options evaluated "
                        f"(Direct, Safe Corridor, High-Clearance Seaward). Deterministically recommended option: '{rec_str}'."
                    ),
                    source="ALTERNATIVE_CORRIDOR_ENGINE",
                    raw_data={"alternatives": [a.model_dump() for a in transit_route.alternatives]}
                ))

            if transit_route.environmental_evaluations:
                evidence_items.append(EvidenceItem(
                    category="derived_calculation",
                    claim=(
                        f"Route environmental evaluation sampled at {len(transit_route.environmental_evaluations)} corridor points. "
                        f"{transit_route.evaluation_limitation or 'Sampled from coastal/forecast models.'}"
                    ),
                    source="ROUTE_ENVIRONMENTAL_SAMPLER",
                    raw_data={
                        "evaluations": transit_route.environmental_evaluations,
                        "limitation": transit_route.evaluation_limitation
                    }
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

            if route_risk.temporal_comparison:
                tr_comp = route_risk.temporal_comparison
                dep_idx = tr_comp.get("departure_risk_index") if isinstance(tr_comp, dict) else getattr(tr_comp, "departure_risk_index", 0.0)
                dep_win = tr_comp.get("departure_window") if isinstance(tr_comp, dict) else getattr(tr_comp, "departure_window", "")
                arr_idx = tr_comp.get("arrival_risk_index") if isinstance(tr_comp, dict) else getattr(tr_comp, "arrival_risk_index", 0.0)
                arr_win = tr_comp.get("arrival_window") if isinstance(tr_comp, dict) else getattr(tr_comp, "arrival_window", "")
                delta_idx = tr_comp.get("delta_risk_index", 0.0) if isinstance(tr_comp, dict) else getattr(tr_comp, "delta_risk_index", 0.0)
                rec = tr_comp.get("recommendation", "") if isinstance(tr_comp, dict) else getattr(tr_comp, "recommendation", "")
                tr_raw = tr_comp if isinstance(tr_comp, dict) else tr_comp.model_dump()
                evidence_items.append(EvidenceItem(
                    category="derived_calculation",
                    claim=(
                        f"Temporal route risk comparison: Risk index shifts from {dep_idx}/10 ({dep_win}) "
                        f"to {arr_idx}/10 ({arr_win}) (Δ: {delta_idx:+0.1f}). "
                        f"Recommendation: {rec}."
                    ),
                    source="TEMPORAL_ROUTE_RISK_ENGINE",
                    raw_data=tr_raw
                ))

        # 8. Deterministic PFZ candidate reasoning evidence (M5 Step 3)
        if planner_plan.intent == "pfz_radius_filter":
            cands = candidate_pfzs or (geospatial.candidate_pfzs if geospatial else [])
            rad = planner_plan.radius_km or 30.0
            loc_name = planner_plan.location.name if planner_plan.location else "Kochi"
            evidence_items.append(EvidenceItem(
                category="derived_calculation",
                claim=f"Mathematical radial filter: Identified {len(cands)} historical INCOIS PFZ target(s) within {rad} km of {loc_name}.",
                source="SPATIAL_CANDIDATE_FILTER",
                raw_data={
                    "radius_km": rad,
                    "count": len(cands),
                    "targets": [c.model_dump() for c in cands]
                }
            ))

        comp = pfz_comparison or (geospatial.pfz_comparison if geospatial else None)
        if comp and planner_plan.intent == "pfz_comparison":
            evidence_items.append(EvidenceItem(
                category="derived_calculation",
                claim=(
                    f"Candidate comparison: {comp.target_a.name} ({comp.target_a.distance_km} km) vs "
                    f"{comp.target_b.name} ({comp.target_b.distance_km} km). "
                    f"Closer target: {comp.closer_target}. Distance diff: {comp.distance_difference_km} km. "
                    f"Geofence statuses: {comp.target_a.name}={comp.geofence_status_a}, {comp.target_b.name}={comp.geofence_status_b}."
                ),
                source="CANDIDATE_COMPARISON_ENGINE",
                raw_data=comp.model_dump()
            ))

        if planner_plan.intent == "pfz_geofence_check":
            gf_status = (geospatial.direct_route_geofence_status if geospatial else None) or "CLEAR"
            gf_zones = (geospatial.direct_route_intersected_zones if geospatial else [])
            target_name = (
                context.selected_pfz.name if (context and context.selected_pfz)
                else (geospatial.nearest_pfz.name if (geospatial and geospatial.nearest_pfz) else "Target PFZ")
            )
            loc_name = planner_plan.location.name if planner_plan.location else "Kochi"
            evidence_items.append(EvidenceItem(
                category="derived_calculation",
                claim=(
                    f"Direct-route geofence check from {loc_name} to {target_name}: "
                    f"Status '{gf_status}', intersected zones: {', '.join(gf_zones) if gf_zones else 'none'}."
                ),
                source="DIRECT_ROUTE_GEOFENCE_ENGINE",
                raw_data={
                    "status": gf_status,
                    "intersected_zones": gf_zones,
                    "target": target_name
                }
            ))

        # 9. Conversational response generation with language mode handling
        lang_mode = planner_plan.language_mode or (context.language_mode if context else "bilingual")
        v_type = planner_plan.vessel_type or (context.vessel_type if context else (risk.vessel_type if risk else None))

        active_cands = [c.model_dump() for c in (candidate_pfzs or (geospatial.candidate_pfzs if geospatial else []))]
        active_comp = comp.model_dump() if comp else None
        active_target = (
            context.selected_pfz.model_dump() if (context and context.selected_pfz)
            else (geospatial.nearest_pfz.model_dump() if (geospatial and geospatial.nearest_pfz) else None)
        )

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
            route_risk=route_risk.model_dump() if route_risk else None,
            candidate_pfzs=active_cands,
            pfz_comparison=active_comp,
            selected_pfz=active_target,
            radius_km=planner_plan.radius_km,
            target_ordinal=planner_plan.target_ordinal
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
            route_risk=route_risk.model_dump() if route_risk else None,
            candidate_pfzs=active_cands,
            pfz_comparison=active_comp,
            selected_pfz=active_target,
            radius_km=planner_plan.radius_km,
            target_ordinal=planner_plan.target_ordinal
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
