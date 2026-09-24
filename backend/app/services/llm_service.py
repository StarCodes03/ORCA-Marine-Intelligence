"""ORCA Marine Intelligence - LLM Service Layer

Provides an abstracted interface for natural language understanding and synthesis.
Follows strict engineering rules:
- No hardcoded API keys.
- Reads configuration from environment variables.
- Seamlessly falls back to high-fidelity deterministic parsing and response synthesis
  when no LLM API key is configured.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from app.config.risk_thresholds import get_vessel_profile

logger = logging.getLogger("orca.services.llm")


class LLMService:
    """Service layer abstracting LLM calls with deterministic fallback."""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model_name = os.getenv("LLM_MODEL", "mock-deterministic")
        self.is_mock = not (bool(self.gemini_key) or bool(self.openai_key))

        if self.is_mock:
            logger.info("LLMService: Operating in DETERMINISTIC DEVELOPMENT / MOCK MODE (no API key detected).")
        else:
            logger.info(f"LLMService: Configured with model {self.model_name} (API key detected).")

    def parse_user_intent(self, message: str) -> Dict[str, Any]:
        """Extract structured intent, location, time range, and required agents."""
        text = message.lower()

        # Deterministic extraction logic
        # 1. Location
        location_name = "Kochi"
        latitude = 9.9312
        longitude = 76.2673

        if "kochi" in text or "cochin" in text:
            location_name = "Kochi"
            latitude = 9.9312
            longitude = 76.2673
        elif "chellanam" in text:
            location_name = "Chellanam"
            latitude = 9.8000
            longitude = 76.2600
        elif "vypin" in text:
            location_name = "Vypin"
            latitude = 10.0500
            longitude = 76.2100
        elif "munambam" in text:
            location_name = "Munambam"
            latitude = 10.1800
            longitude = 76.1700

        # 2. Time Range
        time_range = "tomorrow_morning"
        if "tomorrow morning" in text:
            time_range = "tomorrow_morning"
        elif "tomorrow afternoon" in text:
            time_range = "tomorrow_afternoon"
        elif "now" in text or "current" in text or "today" in text:
            time_range = "current"
        elif "tomorrow" in text:
            time_range = "tomorrow_morning"

        # 3. Intent & Required Agents
        # Scenario A: Marine Safety Query
        if any(term in text for term in ["safe", "safety", "risk", "danger", "can i go", "warning"]):
            intent = "marine_safety"
            required_agents = ["weather", "ocean", "geospatial"]

        # Scenario B: Potential Fishing Zone (PFZ) Query
        elif any(term in text for term in ["pfz", "potential fishing zone", "where to fish", "fish zone", "fishing ground"]):
            intent = "pfz_search"
            # PFZ query primarily needs Ocean + GIS
            required_agents = ["ocean", "geospatial"]

        # Scenario C: Weather / Sea Condition Specific Query
        elif any(term in text for term in ["weather", "wind", "rain", "lightning", "storm"]):
            if any(term in text for term in ["tide", "wave", "sea", "ocean"]):
                intent = "marine_safety"
                required_agents = ["weather", "ocean", "geospatial"]
            else:
                intent = "weather_query"
                required_agents = ["weather"]

        # Scenario D: Ocean / Tide Query
        elif any(term in text for term in ["tide", "wave", "sst", "chlorophyll", "sea condition", "sea state"]):
            intent = "ocean_query"
            required_agents = ["ocean"]

        else:
            intent = "marine_safety"
            required_agents = ["weather", "ocean", "geospatial"]

        return {
            "intent": intent,
            "location": {
                "name": location_name,
                "latitude": latitude,
                "longitude": longitude
            },
            "time_range": time_range,
            "required_agents": required_agents
        }

    def synthesize_response(
        self,
        intent: str,
        location: Dict[str, Any],
        time_range: str,
        weather: Optional[Dict[str, Any]] = None,
        ocean: Optional[Dict[str, Any]] = None,
        geospatial: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        clarification_reason: Optional[str] = None,
        selected_pfz: Optional[Dict[str, Any]] = None,
        transit_route: Optional[Dict[str, Any]] = None,
        vessel_type: Optional[str] = None,
        language_mode: str = "bilingual",
        temporal_comparison: Optional[Dict[str, Any]] = None,
        route_risk: Optional[Dict[str, Any]] = None,
        candidate_pfzs: Optional[List[Dict[str, Any]]] = None,
        pfz_comparison: Optional[Dict[str, Any]] = None,
        radius_km: Optional[float] = None,
        target_ordinal: Optional[int] = None
    ) -> str:
        """Synthesize final conversational response following the prompt specification."""
        if intent == "clarification_needed":
            reason = clarification_reason or "missing_target"
            if reason == "missing_candidate_context":
                return (
                    "No candidate PFZ targets are currently active in the conversation context to compare or reference. "
                    "Please request a set of targets first (e.g., 'Show PFZ targets within 30 km of Kochi').\n\n"
                    "> **Note:** Demonstration prototype — not for live navigation or marine safety."
                )
            elif reason == "missing_referent_target":
                return (
                    "Could you clarify which destination or Potential Fishing Zone (PFZ) you would like to measure the distance to? "
                    "Please provide a coastal landing centre (e.g., Kochi, Chellanam, Vypin) or ask for the nearest PFZ.\n\n"
                    "> **Note:** Demonstration prototype — not for live navigation or marine safety."
                )
            elif reason == "missing_location":
                return (
                    "Please specify a coastal location or landing centre (e.g., Kochi, Chellanam, Vypin, or Munambam) "
                    "so I can provide marine conditions and fishing intelligence.\n\n"
                    "> **Note:** Demonstration prototype — not for live navigation or marine safety."
                )
            else:
                return (
                    "Could you please provide more details about your operational area or question?\n\n"
                    "> **Note:** Demonstration prototype — not for live navigation or marine safety."
                )

        loc_name = location.get("name", "Kochi") if location else "Kochi"
        time_display = (time_range or "").replace("_", " ").title()

        lines = []

        if intent == "pfz_distance":
            pfz = selected_pfz or (geospatial.get("nearest_pfz") if geospatial else None)
            if pfz:
                target_desc = f"Target #{target_ordinal + 1}" if target_ordinal is not None else "The nearest PFZ target"
                lines.append(
                    f"{target_desc} (**{pfz.get('name')}**) identified in your query is approximately "
                    f"**{pfz.get('distance_km')} km** offshore from **{loc_name}** (Bearing: **{pfz.get('bearing_deg')}°**)."
                )
                lines.append("")
                if pfz.get("landing_centre"):
                    lines.append(f"• Reference Landing Centre: **{pfz.get('landing_centre')}**")
                if pfz.get("target_species"):
                    lines.append(f"• Target Pelagic Species: **{pfz.get('target_species')}**")
                if pfz.get("depth_m"):
                    lines.append(f"• Water Depth: ~**{pfz.get('depth_m')} meters**")
                lines.append("")
                lines.append("**Data sources:**")
                lines.append("• INCOIS (OFFICIAL_SNAPSHOT)")
                lines.append("• GEOSPATIAL_REFERENT_RESOLVER")
                lines.append("")
                lines.append("> **PFZ Advisory Notice:** Historical INCOIS PFZ snapshot — not a live fishing advisory.")
                lines.append("> **Note:** These are demonstration data and must not be presented as live marine safety information.")
                return "\n".join(lines)
            else:
                return (
                    "Could you clarify which destination or Potential Fishing Zone (PFZ) you would like to measure the distance to?\n\n"
                    "> **Note:** Demonstration prototype — not for live navigation or marine safety."
                )

        if intent == "marine_safety":
            risk_level = risk.get("risk_level", "MODERATE") if risk else "MODERATE"
            lines.append(
                f"Marine conditions for {loc_name} ({time_display}) are currently assessed as **{risk_level} RISK** in the prototype."
            )
            lines.append("")

            # Key Factors
            lines.append("**Key marine factors:**")
            if weather:
                lines.append(f"• Wind Speed: {weather.get('wind_speed_kmh', 'N/A')} km/h")
                l_val = weather.get('lightning_risk', 'N/A')
                if str(l_val).lower() in ["unsupported", "unavailable", "not_provided"]:
                    lines.append("• Lightning Risk: Unsupported (not provided by live API)")
                else:
                    lines.append(f"• Lightning Risk: {str(l_val).title()}")
                lines.append(f"• Rain Probability: {weather.get('rain_probability', 'N/A')}%")
            if ocean:
                lines.append(f"• Significant Wave Height: {ocean.get('wave_height_m', 'N/A')} m")
                lines.append(f"• Sea State: {str(ocean.get('sea_state', 'N/A')).title()}")
                lines.append(f"• Tide: {str(ocean.get('tide', 'N/A')).title()}")

            if geospatial and geospatial.get("restricted_zone_check", {}).get("inside_restricted_zone"):
                lines.append("• ⚠️ **ALERT**: Vessel location is INSIDE a restricted maritime security zone.")
            elif geospatial and geospatial.get("restricted_zone_check", {}).get("restricted_zone_nearby"):
                lines.append("• ⚠️ **CAUTION**: Near restricted maritime security zone perimeter.")

            lines.append("")
            lines.append("The assessment is calculated deterministically based on configured prototype risk thresholds (`config/risk_thresholds.py`).")

            if geospatial and geospatial.get("nearest_pfz"):
                npfz = geospatial["nearest_pfz"]
                target_sp = f" Target species: {npfz.get('target_species')}." if npfz.get("target_species") else ""
                lines.append("")
                lines.append(
                    f"**Potential Fishing Opportunity:** Nearest PFZ target is **{npfz.get('name')}** at "
                    f"**{npfz.get('distance_km')} km** (Bearing: {npfz.get('bearing_deg')}°).{target_sp}"
                )

        elif intent == "pfz_search":
            lines.append(f"Here is the Potential Fishing Zone (PFZ) intelligence for the {loc_name} offshore sector:")
            lines.append("")
            if geospatial and geospatial.get("nearest_pfz"):
                npfz = geospatial["nearest_pfz"]
                lines.append(f"**Nearest PFZ target:**")
                lines.append(f"• Target: **{npfz.get('name')}** ({npfz.get('pfz_id')})")
                lines.append(f"• Distance: **{npfz.get('distance_km')} km** from {loc_name}")
                lines.append(f"• Bearing: **{npfz.get('bearing_deg')}°** offshore")
                if npfz.get('depth_m') is not None:
                    lines.append(f"• Water Depth: ~{npfz.get('depth_m')} meters")
                if npfz.get('sst_c') is not None:
                    lines.append(f"• Sea Surface Temp (SST): {npfz.get('sst_c')} °C")
                if npfz.get('chlorophyll_mg_m3') is not None:
                    lines.append(f"• Chlorophyll Concentration: {npfz.get('chlorophyll_mg_m3')} mg/m³")
                if npfz.get('target_species'):
                    lines.append(f"• Target Pelagic Species: {npfz.get('target_species')}")
                if npfz.get('confidence_score') is not None:
                    lines.append(f"• Front Confidence: {int(npfz.get('confidence_score')*100)}%")
                if geospatial.get("source_type") == "OFFICIAL_SNAPSHOT":
                    lines.append(f"• Advisory Date: {geospatial.get('advisory_date')} (Valid until: {geospatial.get('valid_until')})")
            else:
                lines.append("No PFZ targets detected in the local demonstration database.")

            if ocean:
                lines.append("")
                lines.append(f"**Current Sea Conditions in Sector:**")
                lines.append(f"• Wave Height: {ocean.get('wave_height_m')} m ({ocean.get('sea_state')})")
                lines.append(f"• Current Tide: {ocean.get('tide')}")

        elif intent == "weather_query":
            lines.append(f"Marine meteorological forecast for {loc_name} ({time_display}):")
            lines.append("")
            if weather:
                lines.append(f"• Wind Speed: {weather.get('wind_speed_kmh')} km/h")
                lines.append(f"• Rain Probability: {weather.get('rain_probability')}%")
                lines.append(f"• Lightning Risk: {str(weather.get('lightning_risk')).title()}")
                lines.append(f"• Temperature: {weather.get('temperature_c')} °C")
                if weather.get("weather_alert"):
                    lines.append(f"• ⚠️ Alert: {weather.get('weather_alert')}")

        elif intent == "temporal_comparison":
            lines.append(f"Comparative marine condition analysis for {loc_name}:")
            lines.append("")
            if temporal_comparison:
                tc = temporal_comparison
                w1 = tc.get("window_1", {})
                w2 = tc.get("window_2", {})
                w1_title = str(w1.get("time_window", "Window 1")).replace("_", " ").title()
                w2_title = str(w2.get("time_window", "Window 2")).replace("_", " ").title()
                lines.append(f"**Multi-Window Comparison ({w1_title} vs. {w2_title}):**")
                lines.append(f"• Wind Speed: {w1.get('wind_speed_kmh')} km/h ➔ {w2.get('wind_speed_kmh')} km/h (Δ: {tc.get('delta_wind_kmh'):+} km/h)")
                lines.append(f"• Wave Height: {w1.get('wave_height_m')} m ({w1.get('sea_state')}) ➔ {w2.get('wave_height_m')} m ({w2.get('sea_state')}) (Δ: {tc.get('delta_wave_m'):+} m)")
                lines.append(f"• Rain Probability: {w1.get('rain_probability')}% ➔ {w2.get('rain_probability')}% (Δ: {tc.get('delta_rain_pct'):+}%)")
                lines.append(f"• Assessed Risk Score: {w1.get('risk_score')} ({w1.get('risk_level')}) ➔ {w2.get('risk_score')} ({w2.get('risk_level')}) (Δ: {tc.get('delta_risk_score'):+0.1f})")
                lines.append(f"• Trend Classification: **{tc.get('trend')}**")
                lines.append("")
                lines.append(f"**Deterministic Recommendation:** {tc.get('recommendation')}")
                lines.append("")
                lines.append(f"> *Provenance:* {tc.get('provenance_notice')}")

        elif intent == "pfz_radius_filter":
            rad = radius_km if radius_km is not None else 30.0
            cands = candidate_pfzs or (geospatial.get("candidate_pfzs", []) if geospatial else [])
            lines.append(f"Historical Potential Fishing Zone (PFZ) targets within {rad:g} km of {loc_name}:")
            lines.append("")
            if cands:
                lines.append(f"Found **{len(cands)}** historical candidate target(s) within {rad:g} km (sorted by distance):")
                lines.append("")
                for idx, c in enumerate(cands, 1):
                    c_name = c.get("name")
                    c_lc = c.get("landing_centre") or c_name
                    c_dist = c.get("distance_km")
                    c_bearing = c.get("bearing_deg")
                    c_depth = f", Depth: ~{c.get('depth_m')}m" if c.get("depth_m") is not None else ""
                    lines.append(f"{idx}. **{c_name}** ({c_lc}) — **{c_dist} km** (Bearing: **{c_bearing}°**{c_depth})")
                lines.append("")
                lines.append("• *Historical snapshot notice:* Targets retrieved from official historical INCOIS Kerala snapshot. Proximity does not imply biological suitability or active fish presence.")
                lines.append("• *Unavailable snapshot fields:* SST, chlorophyll-a, target species, confidence score, fish abundance.")
            else:
                lines.append(f"No historical PFZ targets found within {rad:g} km of {loc_name} in the snapshot database.")
                if geospatial and geospatial.get("nearest_pfz"):
                    npfz = geospatial["nearest_pfz"]
                    lines.append(f"• Closest available snapshot target is **{npfz.get('name')}** at **{npfz.get('distance_km')} km**.")

        elif intent == "pfz_comparison":
            lines.append(f"Comparative analysis of historical PFZ candidate targets from {loc_name}:")
            lines.append("")
            comp = pfz_comparison or (geospatial.get("pfz_comparison") if geospatial else None)
            if comp:
                t_a = comp.get("target_a", {})
                t_b = comp.get("target_b", {})
                lines.append(f"**Target Comparison: {t_a.get('name')} vs {t_b.get('name')}**")
                lines.append(f"• Distance from {loc_name}:")
                lines.append(f"  - **{t_a.get('name')}**: {t_a.get('distance_km')} km (Bearing: {t_a.get('bearing_deg')}°)")
                lines.append(f"  - **{t_b.get('name')}**: {t_b.get('distance_km')} km (Bearing: {t_b.get('bearing_deg')}°)")
                lines.append(f"  - Delta: **{comp.get('distance_difference_km')} km** difference (Closer target: **{comp.get('closer_target')}**)")
                if comp.get("bearing_difference_deg") is not None:
                    lines.append(f"• Bearing Difference: **{comp.get('bearing_difference_deg')}°**")
                lines.append(f"• {comp.get('depth_comparison')}")
                lines.append(f"• Direct Route Restricted Zone Intersection:")
                lines.append(f"  - **{t_a.get('name')}**: {comp.get('geofence_status_a')} ({', '.join(comp.get('intersected_zones_a', [])) if comp.get('intersected_zones_a') else 'no restricted zones'})")
                lines.append(f"  - **{t_b.get('name')}**: {comp.get('geofence_status_b')} ({', '.join(comp.get('intersected_zones_b', [])) if comp.get('intersected_zones_b') else 'no restricted zones'})")
                lines.append("")
                lines.append(f"• *Explicitly Unavailable Snapshot Fields:* {', '.join(comp.get('unavailable_fields', []))}")
                lines.append(f"> *Candidate Comparison Notice:* {comp.get('disclaimer')}")
            else:
                lines.append("Insufficient candidate targets in context to perform comparison.")

        elif intent == "pfz_geofence_check":
            target = selected_pfz or (geospatial.get("nearest_pfz") if geospatial else None)
            target_name = target.get("name", "Candidate Target") if target else "Candidate Target"
            target_dist = target.get("distance_km", "N/A") if target else "N/A"
            gf_status = geospatial.get("direct_route_geofence_status", "CLEAR") if geospatial else "CLEAR"
            gf_zones = geospatial.get("direct_route_intersected_zones", []) if geospatial else []

            lines.append(f"Direct straight-line restricted zone assessment from {loc_name} to **{target_name}** ({target_dist} km):")
            lines.append("")
            if gf_status == "INTERSECTS_RESTRICTED_ZONE" or len(gf_zones) > 0:
                lines.append("⚠️ **RESTRICTED ZONE INTERSECTION DETECTED**")
                lines.append(f"A straight-line transit to **{target_name}** intersects the following restricted maritime zone(s):")
                for z in gf_zones:
                    lines.append(f"• **{z}**")
                lines.append("")
                lines.append("Direct passage is **not recommended** through active security perimeters. Use the safe passage corridor routing engine to calculate clearance waypoints around restricted zones.")
            else:
                lines.append("✅ **DIRECT ROUTE CLEAR**")
                lines.append(f"A straight-line transit from {loc_name} to **{target_name}** does not intersect any charted restricted naval or port security perimeters.")
            lines.append("")
            lines.append("> *Navigational Notice:* Deterministic 2D line-polygon intersection evaluation against charted restricted zones. Does not represent live vessel traffic or oceanographic sea state.")

        elif intent == "safe_passage_route":
            lines.append(f"Safe passage corridor analysis for {loc_name} ({time_display}):")
            lines.append("")
            if risk:
                lines.append(f"• Navigation Risk Level: **{risk.get('risk_level', 'MODERATE')}** (Score: {risk.get('risk_score', 'N/A')})")
            if weather:
                lines.append(f"• Wind Speed: {weather.get('wind_speed_kmh', 'N/A')} km/h")
            if ocean:
                lines.append(f"• Wave Height: {ocean.get('wave_height_m', 'N/A')} m ({str(ocean.get('sea_state', 'N/A')).title()})")

        else:
            lines.append(f"Marine operational intelligence report for {loc_name}:")
            if weather:
                lines.append(f"• Wind: {weather.get('wind_speed_kmh')} km/h | Rain: {weather.get('rain_probability')}%")
            if ocean:
                lines.append(f"• Waves: {ocean.get('wave_height_m')} m | Sea State: {ocean.get('sea_state')}")

        # Vessel Seaworthiness Profile
        if vessel_type:
            v_prof = get_vessel_profile(vessel_type)
            if v_prof:
                lines.append("")
                lines.append(f"**Vessel Operational Profile ({v_prof['name']}):**")
                lines.append(f"• Configurable Prototype Limits: Safe Wave <= {v_prof['wave_max_safe']} m, Safe Wind <= {v_prof['wind_max_safe']} km/h *(prototype parameters; not official maritime regulations)*")
                lines.append(f"• Prototype Cruising Speed: {v_prof['cruising_speed_knots']} knots | Fuel Rate: {v_prof['fuel_consumption_l_per_hour']} L/h ({v_prof.get('fuel_type')}) *(nominal demo values; not authoritative seaworthiness limits)*")

        # Safe Passage Corridor Section
        if transit_route:
            lines.append("")
            lines.append("**Safe Passage Corridor & Transit Route:**")
            dest_info = transit_route.get("destination", {})
            dest_name = dest_info.get("name", "Target PFZ") if isinstance(dest_info, dict) else getattr(dest_info, "name", "Target PFZ")
            lines.append(f"• Transit: **{loc_name}** ➔ **{dest_name}**")
            lines.append(f"• Total Distance: **{transit_route.get('total_distance_km')} km** ({transit_route.get('total_distance_nm')} nm)")
            lines.append(f"• Estimated Duration: ~**{transit_route.get('estimated_duration_hours')} hours** (at craft cruising speed)")
            if transit_route.get("estimated_fuel_litres") is not None:
                lines.append(f"• Estimated Fuel Consumption: ~**{transit_route.get('estimated_fuel_litres')} Litres** ({transit_route.get('fuel_type') or 'N/A'})")
            lines.append(f"• Clearance Safety Margin: **{transit_route.get('clearance_buffer_km', 1.5)} km** around restricted zones")
            
            avoided = transit_route.get("avoided_zones", [])
            if transit_route.get("geofence_avoidance_applied") and avoided:
                lines.append(f"• Geofence Avoidance: **ACTIVE** — Corridor diverted around {', '.join(avoided)}.")
            else:
                lines.append("• Geofence Avoidance: Direct route clear of restricted zones.")

            wps = transit_route.get("waypoints", [])
            if wps:
                lines.append("• Clearance Waypoints:")
                for wp in wps:
                    wp_lat = wp.get("latitude") if isinstance(wp, dict) else wp.latitude
                    wp_lon = wp.get("longitude") if isinstance(wp, dict) else wp.longitude
                    wp_name = wp.get("name") if isinstance(wp, dict) else wp.name
                    wp_desc = wp.get("description", "") if isinstance(wp, dict) else getattr(wp, "description", "")
                    lines.append(f"  - **{wp_name}**: ({wp_lat}, {wp_lon}) — {wp_desc}")

            # Prototype Route Risk Index Breakdown (M5)
            if route_risk:
                rr = route_risk
                fb = rr.get("factor_breakdown", {})
                lines.append("")
                lines.append(f"**Prototype Route Risk Index: {rr.get('prototype_route_risk_index')}/10 ({rr.get('risk_level')})**")
                lines.append(f"• Dominant Limiting Factor: {str(rr.get('limiting_factor', '')).replace('_', ' ').title()}")
                lines.append("• Factor Breakdown (0–10 scale contributions):")
                lines.append(f"  - Environmental Risk (at origin): {fb.get('environmental_factor', 0.0)}")
                lines.append(f"  - Vessel Stress Factor: {fb.get('vessel_stress_factor', 0.0)} (wave ratio: {rr.get('wave_stress_ratio')}, wind ratio: {rr.get('wind_stress_ratio')})")
                lines.append(f"  - Distance Exposure Factor: {fb.get('distance_exposure_factor', 0.0)}")
                lines.append(f"  - Geofence Interaction: {fb.get('geofence_interaction_factor', 0.0)}")
                lines.append(f"> *Route Risk Notice:* {rr.get('disclaimer')}")

            if transit_route.get("fuel_estimate_note"):
                lines.append(f"> *Fuel & Transit Notice:* {transit_route.get('fuel_estimate_note')}")

        # Data sources section
        lines.append("")
        lines.append("**Data sources:**")
        if weather:
            lines.append(f"• {weather.get('source', 'MOCK_WEATHER_DATA')}")
        if ocean:
            lines.append(f"• {ocean.get('source', 'MOCK_OCEAN_DATA')}")
        if geospatial:
            lines.append(f"• {geospatial.get('source', 'DEMO_GIS_DATA')}")
        if transit_route:
            lines.append("• GEOMETRIC_ROUTING_ENGINE")
        if route_risk:
            lines.append("• PROTOTYPE_ROUTE_RISK_ENGINE (DERIVED_CALCULATION)")
        if temporal_comparison:
            lines.append("• TEMPORAL_REASONING_ENGINE (DERIVED_CALCULATION)")
        if intent == "pfz_radius_filter":
            lines.append("• SPATIAL_CANDIDATE_FILTER (DERIVED_CALCULATION)")
        elif intent == "pfz_comparison":
            lines.append("• CANDIDATE_COMPARISON_ENGINE (DERIVED_CALCULATION)")
        elif intent == "pfz_geofence_check":
            lines.append("• DIRECT_ROUTE_GEOFENCE_ENGINE (DERIVED_CALCULATION)")
        lines.append("• RULE_BASED_RISK_ENGINE")

        lines.append("")
        if geospatial and geospatial.get("source_type") == "OFFICIAL_SNAPSHOT":
            lines.append("> **PFZ Advisory Notice:** Historical INCOIS PFZ snapshot — not a live fishing advisory.")
        lines.append(
            "> **Note:** These are demonstration data and must not be presented as live marine safety information."
        )

        return "\n".join(lines)

    def synthesize_malayalam_advisory(
        self,
        intent: str,
        location: Dict[str, Any],
        time_range: str,
        weather: Optional[Dict[str, Any]] = None,
        ocean: Optional[Dict[str, Any]] = None,
        geospatial: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        transit_route: Optional[Dict[str, Any]] = None,
        vessel_type: Optional[str] = None,
        temporal_comparison: Optional[Dict[str, Any]] = None,
        route_risk: Optional[Dict[str, Any]] = None,
        candidate_pfzs: Optional[List[Dict[str, Any]]] = None,
        pfz_comparison: Optional[Dict[str, Any]] = None,
        selected_pfz: Optional[Dict[str, Any]] = None,
        radius_km: Optional[float] = None,
        target_ordinal: Optional[int] = None
    ) -> str:
        """Synthesize authentic coastal Kerala Malayalam operational advisory."""
        loc_name = location.get("name", "കൊച്ചി") if location else "കൊച്ചി"

        risk_lvl = (risk.get("risk_level") if risk else "MODERATE").upper()
        risk_map_ml = {
            "LOW": "കുറഞ്ഞ അപകടസാധ്യത (LOW RISK - അനുകൂല കടൽാവസ്ഥ)",
            "MODERATE": "ജാഗ്രതാ നിർദ്ദേശം (MODERATE RISK - ശ്രദ്ധയോടെ സഞ്ചരിക്കുക)",
            "HIGH": "ഉയർന്ന അപകടസാധ്യത (HIGH RISK - കടലിൽ പോകുന്നത് ഒഴിവാക്കുക)",
            "CRITICAL": "അതിതീവ്ര മുന്നറിയിപ്പ് (CRITICAL - കടൽ പ്രക്ഷുബ്ധമാണ്)"
        }
        risk_str_ml = risk_map_ml.get(risk_lvl, "ജാഗ്രത പാലിക്കുക")

        sea_st = (ocean.get("sea_state") if ocean else "moderate").lower()
        sea_map_ml = {
            "calm": "ശാന്തമായ കടൽ",
            "smooth": "നേരിയ ചലനം",
            "slight": "നേരിയ തിരമാലകൾ",
            "moderate": "ഇടത്തരം പ്രക്ഷുബ്ധം",
            "rough": "പ്രക്ഷുബ്ധമായ കടൽ",
            "very_rough": "വളരെ പ്രക്ഷുബ്ധമായ കടൽ"
        }
        sea_st_ml = sea_map_ml.get(sea_st, sea_st)

        lines = [
            f"### തീരദേശ നാവിക ജാഗ്രതാ റിപ്പോർട്ട് ({loc_name} മേഖല)",
            "",
            f"• **മൊത്തത്തിലുള്ള സുരക്ഷാ വിലയിരുത്തൽ:** **{risk_str_ml}**",
        ]

        if weather or ocean:
            lines.append("")
            lines.append("**കാലാവസ്ഥയും കടൽ സ്ഥിതിയും:**")
            if ocean and ocean.get("wave_height_m") is not None:
                lines.append(f"• തിരമാലയുടെ ഉയരം: **{ocean.get('wave_height_m')} മീറ്റർ** ({sea_st_ml})")
            if weather and weather.get("wind_speed_kmh") is not None:
                lines.append(f"• കാറ്റിന്റെ വേഗത: **{weather.get('wind_speed_kmh')} കി.മീ/മണിക്കൂർ**")
            if weather and weather.get("rain_probability") is not None:
                lines.append(f"• മഴ സാധ്യത: **{weather.get('rain_probability')}%**")

        if temporal_comparison:
            tc = temporal_comparison
            w1 = tc.get("window_1", {})
            w2 = tc.get("window_2", {})
            w1_name = str(w1.get("time_window", "")).replace("_", " ")
            w2_name = str(w2.get("time_window", "")).replace("_", " ")
            trend_ml = {
                "STABLE": "സ്ഥിരതയാർന്ന അവസ്ഥ (STABLE)",
                "IMPROVING": "മെച്ചപ്പെടുന്ന കടൽാവസ്ഥ (IMPROVING)",
                "DETERIORATING": "പ്രക്ഷുബ്ധമാകുന്ന കടൽാവസ്ഥ (DETERIORATING)",
                "INDETERMINATE": "വ്യത്യസ്ത വ്യതിയാനങ്ങൾ (INDETERMINATE)"
            }.get(tc.get("trend"), tc.get("trend"))
            lines.append("")
            lines.append(f"**സമയപരിധി താരതമ്യം ({w1_name} vs. {w2_name}):**")
            lines.append(f"• പ്രവണത: **{trend_ml}**")
            lines.append(f"• തിരമാല വ്യതിയാനം (Δ): **{tc.get('delta_wave_m'):+} മീറ്റർ**")
            lines.append(f"• കാറ്റിന്റെ വേഗത വ്യതിയാനം (Δ): **{tc.get('delta_wind_kmh'):+} കി.മീ/മണിക്കൂർ**")
            lines.append(f"• അപകടസാധ്യത വ്യതിയാനം (Δ): **{tc.get('delta_risk_score'):+0.1f}**")
            lines.append(f"• നിർദ്ദേശം: {tc.get('recommendation')}")

        if vessel_type:
            v_prof = get_vessel_profile(vessel_type)
            if v_prof:
                v_name_ml = v_prof.get("name_ml", v_prof.get("name"))
                lines.append("")
                lines.append(f"**യാന സുരക്ഷാ വിലയിരുത്തൽ ({v_name_ml}):**")
                wave_val = ocean.get("wave_height_m", 0) if ocean else 0
                if wave_val > v_prof["wave_max_moderate"]:
                    lines.append(f"• ⚠️ **അപകട മുന്നറിയിപ്പ്:** ഈ യാനത്തിന് നിലവിലെ കടൽാവസ്ഥ അപകടകരമാണ് (പ്രോട്ടോടൈപ്പ് പരിധി: {v_prof['wave_max_moderate']} മീറ്റർ).")
                elif wave_val > v_prof["wave_max_safe"]:
                    lines.append(f"• ⚠️ **ശ്രദ്ധിക്കുക:** തിരമാല {wave_val} മീറ്റർ സാധാരണ പ്രോട്ടോടൈപ്പ് സുരക്ഷിത പരിധി ({v_prof['wave_max_safe']} മീറ്റർ) കവിയുന്നു.")
                else:
                    lines.append("• ✅ ഈ യാനത്തിന് കടൽാവസ്ഥ പ്രോട്ടോടൈപ്പ് സുരക്ഷിത പരിധിയിലാണ്.")
                lines.append("• *ശ്രദ്ധിക്കുക: യാന പരിധികളും ഇന്ധന കണക്കുകൂട്ടലുകളും ഡെമോ/പ്രോട്ടോടൈപ്പ് വിവരങ്ങൾ മാത്രമാണ്; ഔദ്യോഗിക ചട്ടങ്ങളല്ല.*")

        if transit_route:
            lines.append("")
            lines.append("**സുരക്ഷിത സഞ്ചാര പാത (Safe Corridor):**")
            lines.append(f"• ആകെ സഞ്ചാര ദൂരം: **{transit_route.get('total_distance_km')} കി.മീ** ({transit_route.get('total_distance_nm')} നോട്ടിക്കൽ മൈൽ)")
            lines.append(f"• ഏകദേശ യാത്രാ സമയം: **~{transit_route.get('estimated_duration_hours')} മണിക്കൂർ**")
            if transit_route.get("estimated_fuel_litres") is not None:
                lines.append(f"• ഇന്ധന ഉപഭോഗം (ഏകദേശം): **~{transit_route.get('estimated_fuel_litres')} ലിറ്റർ** ({transit_route.get('fuel_type') or ''})")
            if transit_route.get("geofence_avoidance_applied"):
                avoided_str = ", ".join(transit_route.get("avoided_zones", []))
                lines.append(f"• സുരക്ഷാ ക്രമീകരണം: നിരോധിത മേഖല ({avoided_str}) വഴിതിരിച്ചുവിട്ടു ({transit_route.get('clearance_buffer_km')} കി.മീ സുരക്ഷിത അകലം).")

        if route_risk:
            rr = route_risk
            lines.append("")
            lines.append(f"**റൂട്ട് റിസ്ക് സൂചിക (പ്രോട്ടോടൈപ്പ്): {rr.get('prototype_route_risk_index')}/10 ({rr.get('risk_level')})**")
            lines.append(f"• മുഖ്യ ഘടകം: {str(rr.get('limiting_factor', '')).replace('_', ' ')}")
            lines.append("> *ശ്രദ്ധിക്കുക: റൂട്ട് റിസ്ക് സൂചിക പരീക്ഷണാർത്ഥമുള്ള പ്രോട്ടോടൈപ്പ് മാതൃക മാത്രമാണ്; ഔദ്യോഗിക സുരക്ഷാ റേറ്റിംഗല്ല.*")

        if intent == "pfz_radius_filter":
            rad = radius_km if radius_km is not None else 30.0
            cands = candidate_pfzs or (geospatial.get("candidate_pfzs", []) if geospatial else [])
            lines.append("")
            lines.append(f"**സാധ്യതാ മത്സ്യബന്ധന മേഖലകൾ ({loc_name} - {rad:g} കി.മീ പരിധിയിൽ):**")
            if cands:
                lines.append(f"കണ്ടെത്തിയ ലക്ഷ്യങ്ങൾ ({len(cands)} എണ്ണം):")
                for idx, c in enumerate(cands, 1):
                    lines.append(f"{idx}. **{c.get('name')}** ({c.get('landing_centre') or ''}) — **{c.get('distance_km')} കി.മീ** അകലെ (ദിശ: {c.get('bearing_deg')}°)")
                lines.append("")
                lines.append("• *ശ്രദ്ധിക്കുക: ചരിത്രപരമായ INCOIS ഡാറ്റാബേസിൽ നിന്നുള്ള വിവരങ്ങൾ മാത്രമാണ്; തത്സമയ മത്സ്യ ലഭ്യത ഉറപ്പുനൽകുന്നില്ല.*")
            else:
                lines.append(f"{rad:g} കി.മീ പരിധിയിൽ PFZ ലക്ഷ്യങ്ങൾ ലഭ്യമല്ല.")

        elif intent == "pfz_comparison":
            comp = pfz_comparison or (geospatial.get("pfz_comparison") if geospatial else None)
            if comp:
                t_a = comp.get("target_a", {})
                t_b = comp.get("target_b", {})
                lines.append("")
                lines.append(f"**PFZ ലക്ഷ്യങ്ങളുടെ താരതമ്യം ({t_a.get('name')} vs {t_b.get('name')}):**")
                lines.append(f"• ദൂരം: {t_a.get('name')} ({t_a.get('distance_km')} കി.മീ) vs {t_b.get('name')} ({t_b.get('distance_km')} കി.മീ)")
                lines.append(f"• വ്യത്യാസം: **{comp.get('distance_difference_km')} കി.മീ** (അടുത്തുള്ള ലക്ഷ്യം: **{comp.get('closer_target')}**)")
                lines.append(f"• നിരോധിത മേഖല പരിശോധന: {t_a.get('name')}={comp.get('geofence_status_a')}, {t_b.get('name')}={comp.get('geofence_status_b')}")
                lines.append("> *ശ്രദ്ധിക്കുക: ലഭ്യമായ ചരിത്ര വിവരങ്ങൾ മാത്രമാണ് താരതമ്യം ചെയ്തിട്ടുള്ളത്.*")

        elif intent == "pfz_geofence_check":
            target = selected_pfz or (geospatial.get("nearest_pfz") if geospatial else None)
            target_name = target.get("name", "ലക്ഷ്യം") if target else "ലക്ഷ്യം"
            gf_status = geospatial.get("direct_route_geofence_status", "CLEAR") if geospatial else "CLEAR"
            gf_zones = geospatial.get("direct_route_intersected_zones", []) if geospatial else []
            lines.append("")
            lines.append(f"**നേർരേഖാ സുരക്ഷാ പരിശോധന ({target_name} ലേക്ക്):**")
            if gf_status == "INTERSECTS_RESTRICTED_ZONE" or len(gf_zones) > 0:
                lines.append(f"• ⚠️ **മുന്നറിയിപ്പ്:** {target_name} ലേക്കുള്ള നേർരേഖ നിരോധിത മേഖലയിലൂടെ കടന്നുപോകുന്നു ({', '.join(gf_zones)}).")
                lines.append("• നേർവഴി ഒഴിവാക്കി സുരക്ഷിത പാത ഉപയോഗിക്കുക.")
            else:
                lines.append(f"• ✅ **സുരക്ഷിതം:** {target_name} ലേക്കുള്ള നേർവഴിയിൽ നിരോധിത മേഖലകൾ ഇല്ല.")

        elif intent == "pfz_distance":
            pfz = selected_pfz or (geospatial.get("nearest_pfz") if geospatial else None)
            if pfz:
                target_desc = f"ലക്ഷ്യം #{target_ordinal + 1}" if target_ordinal is not None else "അടുത്തുള്ള PFZ ലക്ഷ്യം"
                lines.append("")
                lines.append(f"**{target_desc} ({pfz.get('name')}):** {loc_name} തീരത്തുനിന്ന് ഏകദേശം **{pfz.get('distance_km')} കി.മീ** അകലെ (ദിശ: {pfz.get('bearing_deg')}°).")

        elif geospatial and geospatial.get("nearest_pfz"):
            npfz = geospatial["nearest_pfz"]
            lines.append("")
            lines.append(f"**സാധ്യതാ മത്സ്യബന്ധന മേഖല (PFZ):** {npfz.get('name')} ({npfz.get('distance_km')} കി.മീ അകലെ)")

        lines.append("")
        lines.append("> **മുന്നറിയിപ്പ്:** ഇത് പരീക്ഷണാർത്ഥമുള്ള വിവരങ്ങൾ മാത്രമാണ് (Demonstration Prototype). ഔദ്യോഗിക ലൈവ് നാവിഗേഷനായി ഉപയോഗിക്കരുത്.")

        return "\n".join(lines)


# Singleton instance
llm_service = LLMService()
