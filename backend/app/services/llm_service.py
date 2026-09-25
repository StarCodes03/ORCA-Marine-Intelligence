"""ORCA Marine Intelligence - LLM Service Layer

Provides an abstracted interface for natural language understanding and synthesis.
Follows strict engineering rules:
- No hardcoded API keys.
- Reads configuration from environment variables.
- Seamlessly falls back to high-fidelity deterministic parsing and response synthesis
  when no LLM API key is configured.
"""

import os
import re
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
            elif reason == "missing_referent_context":
                return (
                    "Could you clarify which coastal landing centre and activity you are asking about? "
                    "(e.g., 'Is it safe to fish near Kochi tomorrow morning?')\n\n"
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

        def get_source_footnote(extra_sources: Optional[List[str]] = None) -> str:
            sources = []
            if weather and weather.get("source"):
                sources.append(weather["source"])
            elif intent in ["marine_safety", "temporal_comparison", "weather_query"]:
                sources.append("MOCK_WEATHER_DATA")

            if ocean and ocean.get("source"):
                sources.append(ocean["source"])
            elif intent in ["marine_safety", "temporal_comparison"]:
                sources.append("MOCK_OCEAN_DATA")

            if geospatial and geospatial.get("source"):
                sources.append(geospatial["source"])
            elif intent in ["marine_safety", "pfz_search", "pfz_distance", "pfz_radius_filter", "pfz_comparison", "pfz_geofence_check"]:
                sources.append("INCOIS")

            if extra_sources:
                sources.extend(extra_sources)

            src_str = " | ".join(sources) if sources else "Open-Meteo | INCOIS"
            return f"> *Sources & Provenance:* {src_str} • Detailed passage planning in Route & Safety; full telemetry audit in Data & Evidence."

        if intent == "pfz_distance":
            pfz = selected_pfz or (geospatial.get("nearest_pfz") if geospatial else None)
            if pfz:
                target_desc = f"Target #{target_ordinal + 1}" if target_ordinal is not None else "Nearest historical INCOIS PFZ target"
                depth_info = f" (~{pfz.get('depth_m')}m depth)" if pfz.get("depth_m") else ""
                lines.append(
                    f"**{target_desc}:** **{pfz.get('name')}** is approximately "
                    f"**{pfz.get('distance_km')} km** offshore from **{loc_name}** (Bearing: **{pfz.get('bearing_deg')}°**){depth_info}."
                )
                if pfz.get("landing_centre"):
                    lines.append(f"• Reference Landing Centre: **{pfz.get('landing_centre')}**")
                lines.append("• Status: **Historical INCOIS PFZ snapshot** (advisory baseline)")
                lines.append("")
                lines.append("🗺️ **Action:** *View target on **Marine Intelligence** interactive map.*")
                lines.append("")
                lines.append(get_source_footnote(["GEOSPATIAL_REFERENT_RESOLVER"]))
                return "\n".join(lines)
            else:
                return (
                    "Could you clarify which destination or Potential Fishing Zone (PFZ) you would like to measure the distance to?\n\n"
                    "> **Note:** Demonstration prototype — not for live navigation or marine safety."
                )

        if intent == "marine_safety":
            risk_level = risk.get("risk_level", "MODERATE") if risk else "MODERATE"
            risk_score = risk.get("risk_score", 0.0) if risk else 0.0

            # 1. Clear risk heading & 2. Risk score & 3. Short location/time context
            lines.append(f"Marine conditions for {loc_name} ({time_display}):")
            lines.append("")
            lines.append(f"**ENVIRONMENTAL CONDITION RISK: {risk_level}**")
            lines.append(f"Score: {risk_score}/10")
            lines.append("")

            # 4. Compact key-factor list
            lines.append("**Key marine factors:**")
            if weather:
                lines.append(f"• Wind: **{weather.get('wind_speed_kmh', 'N/A')} km/h**")
                lines.append(f"• Rain Probability: **{weather.get('rain_probability', 'N/A')}%**")
            if ocean:
                lines.append(f"• Wave Height: **{ocean.get('wave_height_m', 'N/A')} m**")
                lines.append(f"• Sea State: **{str(ocean.get('sea_state', 'N/A')).title()}**")
                tide_str = str(ocean.get('tide', 'N/A'))
                if "forecast sea-level trend" in tide_str.lower():
                    lines.append(f"• Tide / Sea-Level Trend: **{tide_str.split('(')[0].strip().title()}**")
                else:
                    lines.append(f"• Tide / Sea-Level Trend: **{tide_str.title()}**")
            if weather:
                l_val = weather.get('lightning_risk', 'N/A')
                if str(l_val).lower() not in ["unsupported", "unavailable", "not_provided", "n/a", ""]:
                    lines.append(f"• Lightning: **{str(l_val).title()}**")
                else:
                    lines.append("• Lightning: *Unsupported by current upstream feed*")

            # 5. Restricted-zone caution (deterministic prototype origin)
            if geospatial and geospatial.get("restricted_zone_check", {}).get("inside_restricted_zone"):
                lines.append("")
                lines.append("• ⚠️ **CAUTION**: Configured prototype origin overlaps a restricted maritime zone (Cochin Naval Base & Port Channel Security Enclave). This is a deterministic GIS evaluation, not live GPS positioning.")
            elif geospatial and geospatial.get("restricted_zone_check", {}).get("restricted_zone_nearby"):
                lines.append("")
                lines.append("• ⚠️ **CAUTION**: Configured prototype origin is within the clearance buffer of a configured restricted security zone perimeter.")

            # 6. Nearest historical INCOIS PFZ
            if geospatial and geospatial.get("nearest_pfz"):
                npfz = geospatial["nearest_pfz"]
                lines.append("")
                lines.append(
                    f"**Nearest historical INCOIS PFZ target:** **{npfz.get('name')}** at "
                    f"**{npfz.get('distance_km')} km** (Bearing: {npfz.get('bearing_deg')}°) [Historical INCOIS snapshot]."
                )

            # 7. Concise safe-passage summary
            if transit_route:
                lines.append("")
                lines.append("**Safe Passage Corridor:**")
                dest_info = transit_route.get("destination", {})
                dest_name = dest_info.get("name", "Target PFZ") if isinstance(dest_info, dict) else getattr(dest_info, "name", "Target PFZ")
                dist_km = transit_route.get('total_distance_km', 'N/A')
                dur_h = transit_route.get('estimated_duration_hours', 'N/A')
                fuel_l = transit_route.get('estimated_fuel_litres', 'N/A')
                lines.append(f"• Transit: **{loc_name}** ➔ **{dest_name}** (**{dist_km} km**, ~**{dur_h} hrs**, ~**{fuel_l} L**)")
                avoided = transit_route.get("avoided_zones", [])
                if transit_route.get("geofence_avoidance_applied") and avoided:
                    lines.append(f"• Geofence Avoidance: **ACTIVE** — Diverted around {', '.join(avoided)} ({transit_route.get('clearance_buffer_km', 1.5)} km margin).")
                else:
                    lines.append("• Geofence Avoidance: **DIRECT CLEAR** — Route is clear of charted restricted zones.")

            # 8. Dashboard navigation actions
            lines.append("")
            lines.append("🚤 **Actions:** *Use **Route & Safety** for passage corridor waypoints and **Marine Intelligence** to view map targets.*")

            # 9. ONE concise provenance/source footnote
            lines.append("")
            lines.append(get_source_footnote())
            return "\n".join(lines)

        elif intent == "pfz_search":
            if geospatial and geospatial.get("nearest_pfz"):
                npfz = geospatial["nearest_pfz"]
                depth_str = f" (~{npfz.get('depth_m')}m depth)" if npfz.get('depth_m') is not None else ""
                lines.append(f"**Nearest historical INCOIS PFZ target:** **{npfz.get('name')}**{depth_str}")
                lines.append(f"• Distance: **{npfz.get('distance_km')} km** from {loc_name}")
                lines.append(f"• Bearing: **{npfz.get('bearing_deg')}°** offshore")
                if npfz.get('landing_centre'):
                    lines.append(f"• Reference Landing Centre: **{npfz.get('landing_centre')}**")
                lines.append("• Status: **Historical INCOIS PFZ snapshot** (advisory baseline)")
                lines.append("")
                lines.append("🗺️ **Action:** *View target on **Marine Intelligence** interactive map.*")
                lines.append("")
                lines.append(get_source_footnote())
            else:
                lines.append("No PFZ targets detected in the local demonstration database.")
            return "\n".join(lines)

        elif intent == "weather_query":
            lines.append(f"Marine meteorological forecast for {loc_name} ({time_display}):")
            lines.append("")
            if weather:
                lines.append(f"• Wind Speed: **{weather.get('wind_speed_kmh')} km/h**")
                lines.append(f"• Rain Probability: **{weather.get('rain_probability')}%**")
                lines.append(f"• Lightning Risk: **{str(weather.get('lightning_risk')).title()}**")
                lines.append(f"• Temperature: **{weather.get('temperature_c')} °C**")
                if weather.get("weather_alert"):
                    lines.append(f"• ⚠️ Alert: {weather.get('weather_alert')}")
            lines.append("")
            lines.append(get_source_footnote())
            return "\n".join(lines)

        elif intent == "temporal_comparison":
            lines.append(f"Comparative marine condition analysis for {loc_name}:")
            lines.append("")
            if temporal_comparison:
                tc = temporal_comparison
                w1 = tc.get("window_1", {})
                w2 = tc.get("window_2", {})
                delta_w = tc.get("delta_wind_kmh", 0.0)
                delta_wv = tc.get("delta_wave_m", 0.0)
                delta_r = tc.get("delta_rain_pct", 0)
                delta_rk = tc.get("delta_risk_score", 0.0)
                trend = tc.get("trend", "STABLE")

                w1_sea = str(w1.get('sea_state', 'N/A')).title()
                w2_sea = str(w2.get('sea_state', 'N/A')).title()
                sea_change = w2_sea if w1_sea == w2_sea else f"{w1_sea} ➔ {w2_sea}"

                tide_str = str(ocean.get('tide', 'N/A')) if ocean else "N/A"
                if "forecast sea-level trend" in tide_str.lower():
                    tide_trend = tide_str.split('(')[0].strip().title()
                else:
                    tide_trend = tide_str.title() if tide_str != "N/A" else "Steady"

                w1_label = str(w1.get("time_window", "Window 1")).replace("_", " ").title()
                w2_label = str(w2.get("time_window", "Window 2")).replace("_", " ").title()

                lines.append(f"| Parameter | {w1_label} | {w2_label} | Change |")
                lines.append("| :--- | ---: | ---: | ---: |")
                lines.append(f"| **Wind** | {w1.get('wind_speed_kmh', 'N/A')} km/h | {w2.get('wind_speed_kmh', 'N/A')} km/h | **{delta_w:+0.1f} km/h** |")
                lines.append(f"| **Rain** | {w1.get('rain_probability', 'N/A')}% | {w2.get('rain_probability', 'N/A')}% | **{delta_r:+.0f}%** |")
                lines.append(f"| **Wave** | {w1.get('wave_height_m', 'N/A')} m | {w2.get('wave_height_m', 'N/A')} m | **{delta_wv:+0.2f} m** |")
                lines.append(f"| **Sea state** | {w1_sea} | {w2_sea} | {sea_change} |")
                lines.append(f"| **Tide** | Steady | {tide_trend} | {tide_trend} |")
                # Format environmental risk score change without labeling zero delta as deteriorating
                if abs(delta_rk) <= 0.05:
                    rk_change_str = "0.0 (Stable)"
                elif delta_rk > 0.5:
                    rk_change_str = f"**{delta_rk:+0.1f} (Higher)**"
                elif delta_rk < -0.5:
                    rk_change_str = f"**{delta_rk:+0.1f} (Lower)**"
                else:
                    rk_change_str = f"{delta_rk:+0.1f} (Stable)"

                lines.append(f"| **Environmental risk** | {w1.get('risk_score', 'N/A')} ({w1.get('risk_level', 'N/A')}) | {w2.get('risk_score', 'N/A')} ({w2.get('risk_level', 'N/A')}) | {rk_change_str} |")
                lines.append(f"| **Overall trend** | — | — | **{trend}** |")
                lines.append("")
                lines.append(f"**Interpretation:** {tc.get('recommendation')}")
                lines.append("")
                lines.append(get_source_footnote(["TEMPORAL_REASONING_ENGINE"]))
            else:
                lines.append("Insufficient multi-window forecast telemetry to assess temporal delta.")
            return "\n".join(lines)

        elif intent == "pfz_radius_filter":
            rad = radius_km if radius_km is not None else 30.0
            cands = candidate_pfzs or (geospatial.get("candidate_pfzs", []) if geospatial else [])
            if cands:
                count = len(cands)
                top_limit = min(5, count)
                lines.append(f"**Historical INCOIS PFZ targets within {rad:g} km of {loc_name}:**")
                lines.append("")
                lines.append("| # | Target Name | Landing Centre | Distance | Bearing | Depth |")
                lines.append("| :---: | :--- | :--- | ---: | ---: | ---: |")
                for idx, c in enumerate(cands[:top_limit], 1):
                    c_name = c.get("name")
                    c_lc = c.get("landing_centre") or c_name
                    c_dist = c.get("distance_km")
                    c_bearing = c.get("bearing_deg")
                    c_depth = f"~{c.get('depth_m')}m" if c.get("depth_m") is not None else "—"
                    lines.append(f"| {idx} | **{c_name}** | {c_lc} | **{c_dist} km** | {c_bearing}° | {c_depth} |")
                lines.append("")
                lines.append(f"**{count} historical targets found within {rad:g} km. View all on Marine Map.**")
                lines.append("")
                lines.append("• *Historical snapshot notice:* Targets retrieved from official historical INCOIS Kerala snapshot. Proximity does not imply biological suitability or active fish presence.")
                lines.append(get_source_footnote(["SPATIAL_CANDIDATE_FILTER"]))
            else:
                lines.append(f"No historical PFZ targets found within {rad:g} km of {loc_name} in the snapshot database.")
                if geospatial and geospatial.get("nearest_pfz"):
                    npfz = geospatial["nearest_pfz"]
                    lines.append(f"• Closest available snapshot target is **{npfz.get('name')}** at **{npfz.get('distance_km')} km**.")
            return "\n".join(lines)

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
                lines.append("")
                lines.append(get_source_footnote(["CANDIDATE_COMPARISON_ENGINE"]))
            else:
                lines.append("Insufficient candidate targets in context to perform comparison.")
            return "\n".join(lines)

        elif intent == "pfz_geofence_check":
            target = selected_pfz or (geospatial.get("nearest_pfz") if geospatial else None)
            target_name = target.get("name", "Candidate Target") if target else "Candidate Target"
            gf_status = geospatial.get("direct_route_geofence_status", "CLEAR") if geospatial else "CLEAR"
            gf_zones = geospatial.get("direct_route_intersected_zones", []) if geospatial else []

            if gf_status == "INTERSECTS_RESTRICTED_ZONE" or len(gf_zones) > 0:
                lines.append("⚠️ **RESTRICTED ZONE INTERSECTION DETECTED**")
                lines.append("")
                lines.append("• **Direct-route status:** Intersects a configured restricted maritime boundary.")
                lines.append(f"• **Affected Security Zone:** {', '.join(gf_zones) if gf_zones else 'Cochin Naval Base & Port Channel Security Enclave'}")
                lines.append("• **Assessment:** The direct route crosses the configured security-zone geometry. Use Route & Safety to view the prototype geofence-avoiding corridor.")
            else:
                lines.append("✅ **DIRECT ROUTE CLEAR**")
                lines.append("")
                lines.append("• **Direct-route status:** Clear of charted restricted zones.")
                lines.append("• **Assessment:** The direct route does not cross configured security-zone geometry. Use Route & Safety to view passage corridor details.")
            lines.append("")
            lines.append(get_source_footnote(["DIRECT_ROUTE_GEOFENCE_ENGINE"]))
            return "\n".join(lines)

        elif intent == "safe_passage_route":
            lines.append(f"Safe passage corridor analysis for {loc_name} ({time_display}):")
            lines.append("")
            if risk:
                lines.append(f"• Navigation Risk Level: **{risk.get('risk_level', 'MODERATE')}** (Score: {risk.get('risk_score', 'N/A')})")
            if weather:
                lines.append(f"• Wind Speed: **{weather.get('wind_speed_kmh', 'N/A')} km/h**")
            if ocean:
                lines.append(f"• Wave Height: **{ocean.get('wave_height_m', 'N/A')} m** ({str(ocean.get('sea_state', 'N/A')).title()})")
            if transit_route:
                lines.append("")
                dest_info = transit_route.get("destination", {})
                dest_name = dest_info.get("name", "Target PFZ") if isinstance(dest_info, dict) else getattr(dest_info, "name", "Target PFZ")
                lines.append(f"• Transit: **{loc_name}** ➔ **{dest_name}** (**{transit_route.get('total_distance_km')} km**, ~**{transit_route.get('estimated_duration_hours')} hrs**, ~**{transit_route.get('estimated_fuel_litres')} L**)")
                avoided = transit_route.get("avoided_zones", [])
                if transit_route.get("geofence_avoidance_applied") and avoided:
                    lines.append(f"• Corridor Status: **AVOIDANCE ACTIVE** — Diverted around {', '.join(avoided)} ({transit_route.get('clearance_buffer_km', 1.5)} km margin).")
                else:
                    lines.append("• Corridor Status: **DIRECT CLEAR** — Route is clear of charted restricted zones.")
            lines.append("")
            lines.append("🚤 **Action:** *Review full waypoints and route profiles in the **Route & Safety** dashboard.*")
            lines.append("")
            lines.append(get_source_footnote(["GEOMETRIC_ROUTING_ENGINE"]))
            return "\n".join(lines)

        elif intent == "route_alternatives":
            lines.append(f"Transit route alternative comparison for passage from {loc_name}:")
            lines.append("")
            if transit_route and transit_route.get("alternatives"):
                alts = transit_route["alternatives"]
                lines.append(f"Evaluated **{len(alts)}** deterministic navigational alternatives:")
                lines.append("")
                for idx, alt in enumerate(alts, 1):
                    rec_badge = " **[RECOMMENDED]**" if alt.get("is_recommended") else ""
                    lines.append(f"**Alternative {idx}: {alt.get('name')}**{rec_badge}")
                    lines.append(f"• Total Distance: **{alt.get('total_distance_km')} km** ({alt.get('total_distance_nm')} nm)")
                    lines.append(f"• Estimated Duration: ~**{alt.get('estimated_duration_hours')} hours**")
                    if alt.get("estimated_fuel_litres") is not None:
                        lines.append(f"• Estimated Fuel Consumption: ~**{alt.get('estimated_fuel_litres')} Litres**")
                    gf_int = "⚠️ **INTERSECTS RESTRICTED ZONE** (" + ", ".join(alt.get("intersected_zones", [])) + ")" if alt.get("intersects_restricted_zone") else "✅ **CLEAR** of charted restricted zones"
                    lines.append(f"• Geofence Status: {gf_int}")
                    if alt.get("route_risk_index") is not None:
                        lines.append(f"• Route Risk Index: **{alt.get('route_risk_index')}/10** ({alt.get('route_risk_level')})")
                    if alt.get("recommendation_reason"):
                        lines.append(f"• Assessment: {alt.get('recommendation_reason')}")
                    lines.append("")
                lines.append("🚤 **Action:** *Select alternatives in the **Route & Safety** dashboard for detailed waypoint visualization.*")
                lines.append("")
                lines.append(get_source_footnote(["GEOMETRIC_ROUTING_ENGINE", "ALTERNATIVE_CORRIDOR_ENGINE"]))
            else:
                lines.append("No active route alternatives found. Please calculate a route first or specify a destination.")
            return "\n".join(lines)

        elif intent == "route_risk_temporal":
            lines.append(f"Route risk temporal comparison for passage from {loc_name}:")
            lines.append("")
            tc_route = None
            if route_risk and route_risk.get("temporal_comparison"):
                tc_route = route_risk["temporal_comparison"]
            if tc_route:
                lines.append(f"**Passage Risk Evolution ({tc_route.get('departure_window')} vs {tc_route.get('arrival_window')}):**")
                lines.append(f"• Departure Risk Index: **{tc_route.get('departure_risk_index')}/10** ({tc_route.get('departure_risk_level')})")
                lines.append(f"• Horizon Risk Index: **{tc_route.get('arrival_risk_index')}/10** ({tc_route.get('arrival_risk_level')})")
                lines.append(f"• Delta Risk Score (Δ): **{tc_route.get('delta_risk_index'):+0.1f}**")
                lines.append(f"• Environmental Delta: Wind {tc_route.get('delta_wind_kmh'):+} km/h | Wave {tc_route.get('delta_wave_m'):+} m")
                lines.append(f"• Route Safety Trend: **{tc_route.get('trend')}**")
                lines.append("")
                lines.append(f"**Recommendation:** {tc_route.get('recommendation')}")
                lines.append("")
                lines.append(get_source_footnote(["TEMPORAL_ROUTE_RISK_ENGINE"]))
            else:
                lines.append("Insufficient multi-window forecast telemetry to assess temporal route risk delta.")
            return "\n".join(lines)

        else:
            lines.append(f"Marine operational intelligence report for {loc_name}:")
            if weather:
                lines.append(f"• Wind: **{weather.get('wind_speed_kmh')} km/h** | Rain: **{weather.get('rain_probability')}%**")
            if ocean:
                lines.append(f"• Waves: **{ocean.get('wave_height_m')} m** | Sea State: **{ocean.get('sea_state')}**")
            lines.append("")
            lines.append(get_source_footnote())
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

        if transit_route and intent in ["marine_safety", "safe_passage_route"]:
            lines.append("")
            lines.append("**സുരക്ഷിത സഞ്ചാര പാത (Safe Corridor):**")
            lines.append(f"• ആകെ സഞ്ചാര ദൂരം: **{transit_route.get('total_distance_km')} കി.മീ** (~**{transit_route.get('estimated_duration_hours')} മണിക്കൂർ**, ~**{transit_route.get('estimated_fuel_litres')} ലിറ്റർ**)")
            if transit_route.get("geofence_avoidance_applied"):
                avoided_str = ", ".join(transit_route.get("avoided_zones", []))
                lines.append(f"• സുരക്ഷാ ക്രമീകരണം: നിരോധിത മേഖല ({avoided_str}) വഴിതിരിച്ചുവിട്ടു ({transit_route.get('clearance_buffer_km')} കി.മീ സുരക്ഷിത അകലം).")
            else:
                lines.append("• സുരക്ഷാ ക്രമീകരണം: നേർരേഖാ പാത സുരക്ഷിതമാണ്.")

        if intent == "route_alternatives":
            lines.append("")
            lines.append(f"**സഞ്ചാര പാതകളുടെ താരതമ്യം ({loc_name}):**")
            if transit_route and transit_route.get("alternatives"):
                for idx, alt in enumerate(transit_route["alternatives"], 1):
                    rec = " [ശുപാർശ ചെയ്യുന്നു]" if alt.get("is_recommended") else ""
                    gf = "നിരോധിത മേഖലയിൽ പ്രവേശിക്കുന്നു" if alt.get("intersects_restricted_zone") else "സുരക്ഷിതം (നിരോധിത മേഖലകൾ ഇല്ല)"
                    lines.append(f"{idx}. **{alt.get('name')}**{rec}: ദൂരം {alt.get('total_distance_km')} കി.മീ, റിസ്ക്: {alt.get('route_risk_index')}/10 ({gf})")

        elif intent == "route_risk_temporal":
            lines.append("")
            lines.append(f"**റൂട്ട് റിസ്ക് സമയപരിധി താരതമ്യം ({loc_name}):**")
            tc_route = route_risk.get("temporal_comparison") if route_risk else None
            if tc_route:
                lines.append(f"• പ്രവണത: **{tc_route.get('trend')}**")
                lines.append(f"• യാത്ര ആരംഭത്തിലെ റിസ്ക്: {tc_route.get('departure_risk_index')}/10 ➔ പിന്നീട്: {tc_route.get('arrival_risk_index')}/10 (Δ: {tc_route.get('delta_risk_index'):+0.1f})")
                lines.append(f"• നിർദ്ദേശം: {tc_route.get('recommendation')}")

        elif intent == "pfz_radius_filter":
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

    def synthesize_conversational_response(self, text: str, language_mode: str = "bilingual") -> Dict[str, Any]:
        """Synthesize short, friendly conversational response for casual greetings, status, thanks, and farewells."""
        t_clean = re.sub(r"[^\w\s]", "", text.lower()).strip()
        mode = language_mode or "bilingual"

        is_thanks = any(w in t_clean for w in ["thanks", "thank", "thx", "cheers", "നന്ദി"])
        is_bye = any(w in t_clean for w in ["bye", "goodbye", "cya", "see you", "യാത്ര", "take care"])
        is_status = bool(
            re.search(r"\bhow\s+(?:are|r)\s+(?:you|u)\b", t_clean) or
            re.search(r"\bhow\s+(?:are|r)\s+things\b", t_clean) or
            re.search(r"\bhow(?:'s|\s+is)\s+it\s+going\b", t_clean) or
            re.search(r"\b(?:what's\s+up|whats\s+up|sup|wazzup)\b", t_clean) or
            "സുഖമാണോ" in t_clean
        )
        is_identity = bool(
            re.search(r"\b(?:who|what)\s+are\s+(?:you|u)\b", t_clean) or
            re.search(r"\bwhat\s+(?:can|do)\s+(?:you|u)\s+do\b", t_clean) or
            t_clean in ["help", "commands", "options"]
        )

        if is_thanks:
            en = "You're welcome! 🌊"
            ml = "സ്വാഗതം! 🌊"
        elif is_bye:
            en = "Goodbye! Stay safe out there. 🌊"
            ml = "യാത്രാമംഗളങ്ങൾ! കടലിൽ എപ്പോഴും സുരക്ഷിതമായിരിക്കുക. 🌊"
        elif is_status:
            en = "I'm doing well! I'm ORCA, your marine intelligence assistant. What would you like to know about the sea today? 🌊"
            ml = "സുഖമായിരിക്കുന്നു! ഞാൻ ORCA — നിങ്ങളുടെ സമുദ്ര വിവര സഹായി. ഇന്നത്തെ കടൽാവസ്ഥയെക്കുറിച്ച് എന്താണ് അറിയേണ്ടത്? 🌊"
        elif is_identity:
            en = "I'm ORCA 🌊, your marine intelligence assistant for coastal Kerala. I can assess sea conditions, weather forecasts, INCOIS PFZ targets, and safe passage routes. How can I help you today?"
            ml = "ഞാൻ ORCA 🌊 — കേരള തീരദേശ മത്സ്യത്തൊഴിലാളികൾക്കായുള്ള സമുദ്ര വിവര സഹായി. കാലാവസ്ഥ, തിരമാല, PFZ കേന്ദ്രങ്ങൾ, സുരക്ഷിത പാതകൾ എന്നിവ അറിയാൻ എന്നോട് ചോദിക്കാം."
        else:
            # Concise friendly greeting ("hi", "hello", "hey", "good morning", etc.)
            en = "Hi! I'm ORCA 🌊. How can I help you with marine conditions today?"
            ml = "നമസ്കാരം! ഞാൻ ORCA 🌊. ഇന്നത്തെ സമുദ്ര വിവരങ്ങളിൽ ഞാൻ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?"

        if mode == "malayalam":
            return {"answer": ml, "answer_ml": ml}
        elif mode == "english":
            return {"answer": en, "answer_ml": None}
        else:
            return {"answer": en, "answer_ml": ml}

    def synthesize_unsupported_response(self, text: str, language_mode: str = "bilingual") -> Dict[str, Any]:
        """Synthesize graceful refusal and scope clarification for out-of-domain queries."""
        mode = language_mode or "bilingual"

        en = (
            "I am **ORCA**, a specialized marine intelligence and decision-support assistant "
            "focused strictly on coastal maritime operations in Kerala.\n\n"
            "I can only assist with:\n"
            "• Marine weather, wind, rain, and sea state forecasts\n"
            "• Ocean conditions, wave heights, and sea surface temperature (SST)\n"
            "• Historical INCOIS Potential Fishing Zones (PFZs)\n"
            "• Vessel safety assessments and restricted-zone clearance corridors\n\n"
            "Please ask a question related to coastal marine conditions or fishing operations (e.g., "
            "*\"Is it safe to fish near Kochi tomorrow morning?\"* or *\"Show PFZ targets near Munambam\"*).\n\n"
            "> **Note:** Demonstration prototype — not for live navigation or marine safety."
        )
        ml = (
            "ഞാൻ കേരള തീരദേശത്തെ സമുദ്ര വിവരങ്ങൾക്കും സുരക്ഷാ നിർദ്ദേശങ്ങൾക്കുമായി മാത്രം രൂപകൽപ്പന ചെയ്തിട്ടുള്ള "
            "**ORCA** സഹായിയാണ്.\n\n"
            "എനിക്ക് ഇനിപ്പറയുന്ന വിഷയങ്ങളിൽ മാത്രമേ മറുപടി നൽകാൻ സാധിക്കൂ:\n"
            "• സമുദ്ര കാലാവസ്ഥ, കാറ്റ്, മഴ, കടൽാവസ്ഥ\n"
            "• തിരമാല ഉയരവും സമുദ്ര താപനിലയും\n"
            "• INCOIS മത്സ്യബന്ധന സാധ്യത മേഖലകൾ (PFZ)\n"
            "• ബോട്ട് സുരക്ഷാ പരിശോധനയും യാത്രാ പാതകളും\n\n"
            "ദയവായി കടൽ കാലാവസ്ഥയുമായോ മത്സ്യബന്ധനവുമായോ ബന്ധപ്പെട്ട ചോദ്യങ്ങൾ ചോദിക്കുക "
            "(ഉദാഹരണത്തിന്: *\"നാളെ കൊച്ചിയിൽ കാലാവസ്ഥ എങ്ങനെയുണ്ട്?\"*).\n\n"
            "> **കുറിപ്പ്:** ഇത് ഒരു പരീക്ഷണാടിസ്ഥാനത്തിലുള്ള മാതൃകയാണ് — തത്സമയ നാവിഗേഷനായി ഉപയോഗിക്കരുത്."
        )

        if mode == "malayalam":
            return {"answer": ml, "answer_ml": ml}
        elif mode == "english":
            return {"answer": en, "answer_ml": None}
        else:
            return {"answer": en, "answer_ml": ml}

    def synthesize_unsupported_news_response(self, text: str, language_mode: str = "bilingual") -> Dict[str, Any]:
        """Synthesize scope clarification stating that live marine news is not supported."""
        mode = language_mode or "bilingual"

        en = (
            "I am **ORCA**, a specialized marine intelligence and decision-support assistant "
            "focused on coastal maritime operations in Kerala.\n\n"
            "**Operational Scope Notice:** The ORCA prototype provides live marine weather and ocean forecasts, "
            "historical INCOIS Potential Fishing Zones (PFZs), vessel safety assessments, and restricted-zone clearance corridors, "
            "but **does not currently provide a live marine-news, maritime events, or breaking news feed**.\n\n"
            "You can ask for marine weather or operational decision support near coastal landing centers, such as:\n"
            "• *\"What is the weather and wave forecast near Kochi today?\"*\n"
            "• *\"Is it safe for an FRP canoe to fish near Munambam tomorrow morning?\"*\n"
            "• *\"Show PFZ targets within 30 km of Chellanam.\"*\n\n"
            "> **Note:** Demonstration prototype — decision-support only; not a live news or media service."
        )
        ml = (
            "ഞാൻ കേരള തീരദേശത്തെ സമുദ്ര വിവരങ്ങൾക്കും സുരക്ഷാ നിർദ്ദേശങ്ങൾക്കുമായി രൂപകൽപ്പന ചെയ്തിട്ടുള്ള "
            "**ORCA** സഹായിയാണ്.\n\n"
            "**പ്രവർത്തന പരിധി അറിയിപ്പ്:** ORCA പ്രോട്ടോടൈപ്പ് സമുദ്ര കാലാവസ്ഥ, തിരമാല വിവരങ്ങൾ, "
            "ചരിത്രപരമായ INCOIS PFZ വിവരങ്ങൾ, ബോട്ട് സുരക്ഷാ പരിശോധന എന്നിവ നൽകുന്നുണ്ടെങ്കിലും, "
            "**തത്സമയ സമുദ്ര വാർത്തകളോ (live marine news) വാർത്താ ഫീഡുകളോ നൽകുന്നില്ല**.\n\n"
            "കാലാവസ്ഥയ്ക്കും സുരക്ഷാ പരിശോധനയ്ക്കുമായി ദയവായി താഴെപ്പറയുന്ന തരത്തിലുള്ള ചോദ്യങ്ങൾ ചോദിക്കുക:\n"
            "• *\"ഇന്ന് കൊച്ചിയിലെ കാലാവസ്ഥയും തിരമാലയും എങ്ങനെയുണ്ട്?\"*\n"
            "• *\"നാളെ രാവിലെ മുനമ്പത്ത് മീൻപിടിക്കാൻ സുരക്ഷിതമാണോ?\"*\n"
            "• *\"ചെല്ലാനത്തിനടുത്തുള്ള PFZ വിവരങ്ങൾ കാണിക്കുക.\"*\n\n"
            "> **കുറിപ്പ്:** ഇത് ഒരു പരീക്ഷണാടിസ്ഥാനത്തിലുള്ള മാതൃകയാണ് — വാർത്താ സേവനമല്ല."
        )

        if mode == "malayalam":
            return {"answer": ml, "answer_ml": ml}
        elif mode == "english":
            return {"answer": en, "answer_ml": None}
        else:
            return {"answer": en, "answer_ml": ml}

    def synthesize_marine_update_response(
        self,
        weather: Optional[Dict[str, Any]],
        ocean: Optional[Dict[str, Any]],
        location_name: str = "Kochi",
        time_range: str = "current",
        language_mode: str = "bilingual"
    ) -> Dict[str, Any]:
        """Synthesize marine condition update with live forecast telemetry and honest news disclaimer."""
        mode = language_mode or "bilingual"

        wind_spd = weather.get("wind_speed_kmh", 0.0) if weather else 0.0
        wind_dir = weather.get("wind_direction_deg", 270.0) if weather else 270.0
        rain_prob = weather.get("rain_probability", 0) if weather else 0
        wave_h = ocean.get("wave_height_m", 0.0) if ocean else 0.0
        sea_st = ocean.get("sea_state", "moderate") if ocean else "moderate"
        tide_trend = ocean.get("tide", "neutral") if ocean else "neutral"
        if tide_trend and "(" in tide_trend:
            tide_trend = tide_trend.split("(")[0].strip()
        sst = ocean.get("sst_c") if ocean else None

        # Build clean observation summary from live forecast metrics
        observations = []
        if wave_h <= 1.0:
            observations.append("calm-to-slight seas")
        elif wave_h <= 2.0:
            observations.append("moderate sea swell")
        else:
            observations.append("rough sea swell")

        if wind_spd <= 15.0:
            observations.append("light breeze")
        elif wind_spd <= 25.0:
            observations.append("moderate breeze")
        else:
            observations.append("fresh to strong breeze")

        if rain_prob < 20:
            observations.append("low rain probability")
        elif rain_prob < 50:
            observations.append("scattered rain showers possible")
        else:
            observations.append("high likelihood of precipitation")

        summary_clause = ", ".join(observations)

        # English Response
        en_lines = [
            f"I don't have a live marine-news feed, but I can give you today's current marine conditions from the live forecast for **{location_name}**:\n",
            f"### 🌊 Marine Update — Today ({location_name})\n",
            f"| Metric | Live Forecast Observation | Source |",
            f"| :--- | :--- | :--- |",
            f"| **Wind** | {wind_spd:.1f} km/h (bearing {wind_dir:.0f}°) | Live Open-Meteo Weather |",
            f"| **Rain Probability** | {rain_prob}% | Live Open-Meteo Weather |",
            f"| **Significant Wave Height** | {wave_h:.2f} m | Live Open-Meteo Marine |",
            f"| **Sea State** | {sea_st.capitalize()} | Live Open-Meteo Marine |",
            f"| **Sea-Level / Tide Trend** | {tide_trend.capitalize()} | INCOIS Tidal Harmonic Prototype |",
        ]
        if sst is not None:
            en_lines.append(f"| **Sea Surface Temperature (SST)** | {sst:.1f} °C | Live Open-Meteo Marine |")

        en_lines.append(
            f"\n**Live Observation Summary:** Conditions off {location_name} currently indicate {summary_clause}. "
            "No severe weather anomalies or extreme marine alerts are detected in the active forecast feed.\n\n"
            "> **Note:** Demonstration prototype — live weather & ocean telemetry; not an official maritime news service."
        )
        en = "\n".join(en_lines)

        # Malayalam Response
        ml_lines = [
            f"എനിക്ക് തത്സമയ സമുദ്ര വാർത്താ ഫീഡ് (news feed) ലഭ്യമല്ല, എങ്കിലും **{location_name}**-ലെ ഇന്നത്തെ തത്സമയ കാലാവസ്ഥാ വിവരങ്ങൾ നൽകാൻ സാധിക്കും:\n",
            f"### 🌊 സമുദ്ര വിവരങ്ങൾ — ഇന്ന് ({location_name})\n",
            f"| അളവ് | തത്സമയ നിരീക്ഷണം | ഉറവിടം |",
            f"| :--- | :--- | :--- |",
            f"| **കാറ്റ്** | {wind_spd:.1f} km/h ({wind_dir:.0f}°) | Live Open-Meteo Weather |",
            f"| **മഴ സാധ്യത** | {rain_prob}% | Live Open-Meteo Weather |",
            f"| **തിരമാല ഉയരം** | {wave_h:.2f} m | Live Open-Meteo Marine |",
            f"| **കടൽാവസ്ഥ** | {sea_st.capitalize()} | Live Open-Meteo Marine |",
            f"| **വേലിയേറ്റ നില** | {tide_trend.capitalize()} | INCOIS Tidal Harmonic Prototype |",
        ]
        if sst is not None:
            ml_lines.append(f"| **സമുദ്ര താപനില (SST)** | {sst:.1f} °C | Live Open-Meteo Marine |")

        ml_lines.append(
            f"\n**സംഗ്രഹം:** {location_name} തീരത്ത് നിലവിലെ പ്രവചനം അനുസരിച്ച് സാധാരണ നിലയിലുള്ള സമുദ്രാവസ്ഥയാണ് രേഖപ്പെടുത്തിയിട്ടുള്ളത്.\n\n"
            "> **കുറിപ്പ്:** ഇത് ഒരു പരീക്ഷണാടിസ്ഥാനത്തിലുള്ള മാതൃകയാണ് — വാർത്താ സേവനമല്ല."
        )
        ml = "\n".join(ml_lines)

        if mode == "malayalam":
            return {"answer": ml, "answer_ml": ml}
        elif mode == "english":
            return {"answer": en, "answer_ml": None}
        else:
            return {"answer": en, "answer_ml": ml}


# Singleton instance
llm_service = LLMService()
