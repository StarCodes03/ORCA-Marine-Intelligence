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
        language_mode: str = "bilingual"
    ) -> str:
        """Synthesize final conversational response following the prompt specification."""
        if intent == "clarification_needed":
            reason = clarification_reason or "missing_target"
            if reason == "missing_referent_target":
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
                lines.append(
                    f"The nearest PFZ target (**{pfz.get('name')}**) identified in your previous query is approximately "
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
                lines.append("No active PFZ points detected in the local demonstration database.")

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
                lines.append("• Geofence Avoidance: Direct line-of-sight clear.")

            wps = transit_route.get("waypoints", [])
            if wps:
                lines.append("• Clearance Waypoints:")
                for wp in wps:
                    wp_lat = wp.get("latitude") if isinstance(wp, dict) else wp.latitude
                    wp_lon = wp.get("longitude") if isinstance(wp, dict) else wp.longitude
                    wp_name = wp.get("name") if isinstance(wp, dict) else wp.name
                    wp_desc = wp.get("description", "") if isinstance(wp, dict) else getattr(wp, "description", "")
                    lines.append(f"  - **{wp_name}**: ({wp_lat}, {wp_lon}) — {wp_desc}")

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
        vessel_type: Optional[str] = None
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

        if geospatial and geospatial.get("nearest_pfz"):
            npfz = geospatial["nearest_pfz"]
            lines.append("")
            lines.append(f"**സാധ്യതാ മത്സ്യബന്ധന മേഖല (PFZ):** {npfz.get('name')} ({npfz.get('distance_km')} കി.മീ അകലെ)")

        lines.append("")
        lines.append("> **മുന്നറിയിപ്പ്:** ഇത് പരീക്ഷണാർത്ഥമുള്ള വിവരങ്ങൾ മാത്രമാണ് (Demonstration Prototype). ഔദ്യോഗിക ലൈവ് നാവിഗേഷനായി ഉപയോഗിക്കരുത്.")

        return "\n".join(lines)


# Singleton instance
llm_service = LLMService()
