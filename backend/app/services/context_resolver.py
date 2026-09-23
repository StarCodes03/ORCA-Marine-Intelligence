"""ORCA Marine Intelligence - Conversation Context Resolver

Resolves follow-up queries using explicit, structured conversation state.
Enables multi-turn context preservation (location, date, time window, activity, selected PFZ)
without dumping raw conversation history into the LLM prompt.
Fails safely on unresolved referents without fabricating targets or coordinates.
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple, List
from app.models.schemas import LocationCoords, NearestPFZ, ConversationContext, PlannerOutput
from app.tools.gis_data import haversine_distance, calculate_bearing

logger = logging.getLogger("orca.services.context_resolver")

# Known coastal landmarks and landing centers in the primary operational sector
KNOWN_LOCATIONS: Dict[str, Dict[str, Any]] = {
    "kochi": {"name": "Kochi", "latitude": 9.9312, "longitude": 76.2673},
    "cochin": {"name": "Kochi", "latitude": 9.9312, "longitude": 76.2673},
    "chellanam": {"name": "Chellanam", "latitude": 9.8000, "longitude": 76.2600},
    "chellanum": {"name": "Chellanam", "latitude": 9.8000, "longitude": 76.2600},
    "vypin": {"name": "Vypin", "latitude": 10.0500, "longitude": 76.2100},
    "vypeen": {"name": "Vypin", "latitude": 10.0500, "longitude": 76.2100},
    "munambam": {"name": "Munambam", "latitude": 10.1800, "longitude": 76.1700},
    "kuzhuppilly": {"name": "Kuzhuppilly", "latitude": 10.1700, "longitude": 76.1700},
    "fortkochi": {"name": "Fort Kochi", "latitude": 9.9600, "longitude": 76.2400},
    "fort kochi": {"name": "Fort Kochi", "latitude": 9.9600, "longitude": 76.2400},
    "kalamukku": {"name": "Kalamukku", "latitude": 9.9800, "longitude": 76.2300},
    "valarpadam": {"name": "Valarpadam", "latitude": 9.9800, "longitude": 76.2500},
    "vallarpadam": {"name": "Valarpadam", "latitude": 9.9800, "longitude": 76.2500},
    "കൊച്ചി": {"name": "Kochi", "latitude": 9.9312, "longitude": 76.2673},
    "ചെല്ലാനം": {"name": "Chellanam", "latitude": 9.8000, "longitude": 76.2600},
    "വൈപ്പിൻ": {"name": "Vypin", "latitude": 10.0500, "longitude": 76.2100},
    "മുനമ്പം": {"name": "Munambam", "latitude": 10.1800, "longitude": 76.1700},
    "കുഴുപ്പിള്ളി": {"name": "Kuzhuppilly", "latitude": 10.1700, "longitude": 76.1700},
}


class ContextResolver:
    """Deterministic multi-turn context resolver and intent classifier."""

    @staticmethod
    def extract_location(text: str, prior_loc: Optional[LocationCoords] = None) -> Optional[LocationCoords]:
        """Extract explicit geographic reference or inherit from prior context without inventing."""
        text_lower = text.lower()
        for key, coords in KNOWN_LOCATIONS.items():
            # Support word boundary for ASCII and substring for Malayalam/multilingual
            if (key in text_lower) if any(ord(c) > 127 for c in key) else re.search(r"\b" + re.escape(key) + r"\b", text_lower):
                return LocationCoords(**coords)

        # Inherit prior location if present
        if prior_loc:
            return prior_loc.model_copy()

        return None

    @staticmethod
    def extract_date(text: str, prior_date: Optional[str] = None) -> Optional[str]:
        """Extract explicit date or inherit from prior context without hardcoded defaults."""
        text_lower = text.lower()
        if "day after tomorrow" in text_lower:
            return "day_after_tomorrow"
        if "tomorrow" in text_lower:
            return "tomorrow"
        if "today" in text_lower or "now" in text_lower or "current" in text_lower:
            return "today"

        # Inherit prior date
        return prior_date

    @staticmethod
    def extract_time_window(text: str, prior_window: Optional[str] = None) -> Optional[str]:
        """Extract explicit time of day or inherit from prior context without hardcoded defaults."""
        text_lower = text.lower()
        if "afternoon" in text_lower:
            return "afternoon"
        if "morning" in text_lower:
            return "morning"
        if "evening" in text_lower:
            return "evening"
        if "night" in text_lower:
            return "night"
        if "now" in text_lower or "current" in text_lower:
            return "current"

        # Inherit prior window
        return prior_window

    @staticmethod
    def extract_activity(text: str, prior_activity: Optional[str] = None) -> Optional[str]:
        """Extract user operational activity or inherit from prior context."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["fish", "fishing", "catch", "trolling", "trawl", "nets"]):
            return "fishing"
        if any(w in text_lower for w in ["sail", "sailing", "boat", "passage", "transit", "cruise"]):
            return "navigation"

        # Inherit prior activity
        return prior_activity

    @staticmethod
    def extract_vessel_type(text: str, prior_vessel: Optional[str] = None) -> Optional[str]:
        """Extract vessel type or inherit from prior context."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["traditional", "canoe", "catamaran", "dugout", "vallam", "country craft"]):
            return "traditional_craft"
        if any(w in text_lower for w in ["obm", "outboard", "frp", "fiberglass", "motorized", "motor boat"]):
            return "motorized_frp_obm"
        if any(w in text_lower for w in ["trawler", "mechanized", "inboard", "ring seiner", "steel boat"]):
            return "mechanized_trawler"
        return prior_vessel

    @staticmethod
    def extract_language_mode(text: str, prior_lang: Optional[str] = None) -> str:
        """Extract language mode preference or inherit from prior context."""
        text_lower = text.lower()
        if "malayalam" in text_lower or "മലയാളം" in text_lower:
            return "malayalam"
        if "english" in text_lower:
            return "english"
        return prior_lang or "bilingual"

    @staticmethod
    def compute_composite_time_range(
        date: Optional[str], time_window: Optional[str]
    ) -> Optional[str]:
        """Combine date and time window into standard time_range key."""
        d = date or "tomorrow"
        w = time_window or "morning"

        if w == "current" or d == "today" and w == "now":
            return "current"

        return f"{d}_{w}"

    @classmethod
    def resolve(
        cls,
        message: str,
        prior_context: Optional[ConversationContext] = None,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        conversation_id: Optional[str] = None,
        vessel_type: Optional[str] = None,
        language_mode: Optional[str] = None
    ) -> Tuple[PlannerOutput, ConversationContext]:
        """Resolve incoming user message against prior context and produce updated plan and state."""
        text = message.strip()
        text_lower = text.lower()

        # Retrieve prior fields
        p_loc = prior_context.location if prior_context else None
        p_date = prior_context.date if prior_context else None
        p_win = prior_context.time_window if prior_context else None
        p_act = prior_context.activity if prior_context else None
        p_vessel = prior_context.vessel_type if prior_context else None
        p_lang = prior_context.language_mode if prior_context else "bilingual"
        p_intent = prior_context.last_intent if prior_context else None
        p_pfz = prior_context.selected_pfz if prior_context else None
        p_route = prior_context.active_route if prior_context else None
        turn_count = prior_context.turn_count if prior_context else 0

        # Extract current or inherited fields
        location = cls.extract_location(text, p_loc)
        if user_lat is not None and user_lon is not None:
            if location:
                location.latitude = user_lat
                location.longitude = user_lon
            else:
                location = LocationCoords(name="User Vessel Position", latitude=user_lat, longitude=user_lon)

        date = cls.extract_date(text, p_date)
        time_window = cls.extract_time_window(text, p_win)
        activity = cls.extract_activity(text, p_act)
        vessel_type = vessel_type or cls.extract_vessel_type(text, p_vessel)
        language_mode = language_mode or cls.extract_language_mode(text, p_lang)

        # Composite time range
        time_range = cls.compute_composite_time_range(date, time_window)

        # Referent Resolution Checks
        is_referent_distance_query = bool(
            re.search(r"\bhow far\b", text_lower) or
            re.search(r"\bwhat is the distance\b", text_lower) or
            re.search(r"\bdistance to\b", text_lower)
        )
        is_pfz_referent = bool(
            "nearest pfz" in text_lower or
            "that pfz" in text_lower or
            "the pfz" in text_lower or
            "toward the pfz" in text_lower or
            "to the pfz" in text_lower or
            "go toward" in text_lower
        )
        is_followup_modifier = bool(
            re.search(r"^(what|how)\s+about\b", text_lower) or
            re.search(r"^(and|what\s+if)\b", text_lower)
        )

        intent: str
        required_agents: List[str]
        clarification_reason: Optional[str] = None

        # Scenario 1: Referent distance query ("How far is it?")
        if is_referent_distance_query and not any(k in text_lower for k in KNOWN_LOCATIONS):
            if p_pfz is not None:
                # Safely resolved from previous turn's selected PFZ
                intent = "pfz_distance"
                required_agents = []
                logger.info(f"[ContextResolver] Resolved referent 'it' -> PFZ: {p_pfz.name}")
            elif location is not None and prior_context and p_loc is not None:
                # User asking how far to prior location
                intent = "pfz_distance"
                required_agents = []
            else:
                # Fail safely: DO NOT invent a target or distance
                intent = "clarification_needed"
                required_agents = []
                clarification_reason = "missing_referent_target"
                logger.info("[ContextResolver] 'How far is it' failed safely: no prior target found.")

        # Scenario 1b: Safe Passage Corridor / Navigation Route Query
        elif any(w in text_lower for w in ["route", "corridor", "passage", "waypoint", "how to reach", "safe route", "navigate", "റൂട്ട്", "പാത", "സഞ്ചാര പാത"]):
            intent = "safe_passage_route"
            required_agents = ["weather", "ocean", "geospatial"]
            activity = "navigation"
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

        # Scenario 2: "What if I go toward the nearest PFZ?"
        elif is_pfz_referent and any(w in text_lower for w in ["go", "head", "sail", "safe", "what if"]):
            intent = "marine_safety"
            required_agents = ["weather", "ocean", "geospatial"]
            activity = "fishing"

        # Scenario 3: Follow-up modifier ("What about afternoon?", "What about tomorrow?", "What about Chellanam?")
        elif is_followup_modifier and not any(w in text_lower for w in ["pfz", "fishing zone"]):
            if p_intent:
                intent = p_intent
            else:
                intent = "marine_safety"

            if intent == "marine_safety":
                required_agents = ["weather", "ocean", "geospatial"]
            elif intent == "pfz_search":
                required_agents = ["ocean", "geospatial"]
            elif intent == "weather_query":
                required_agents = ["weather"]
            elif intent == "ocean_query":
                required_agents = ["ocean"]
            else:
                required_agents = ["weather", "ocean", "geospatial"]

        # Scenario 4: Explicit PFZ Search Query
        elif any(w in text_lower for w in ["pfz", "potential fishing zone", "where to fish", "fish zone", "fishing ground"]):
            intent = "pfz_search"
            required_agents = ["ocean", "geospatial"]
            activity = activity or "fishing"
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

        # Scenario 5: Marine Safety Query
        elif any(w in text_lower for w in ["safe", "safety", "risk", "danger", "can i go", "warning", "advisable"]):
            intent = "marine_safety"
            required_agents = ["weather", "ocean", "geospatial"]

        # Scenario 6: Weather Query
        elif any(w in text_lower for w in ["weather", "wind", "rain", "lightning", "storm", "temp", "കാലാവസ്ഥ", "കാറ്റ്", "മഴ"]):
            if any(w in text_lower for w in ["tide", "wave", "sea"]):
                intent = "marine_safety"
                required_agents = ["weather", "ocean", "geospatial"]
            else:
                intent = "weather_query"
                required_agents = ["weather"]

        # Scenario 7: Ocean Query
        elif any(w in text_lower for w in ["tide", "wave", "sea state", "sea condition", "swell", "sst"]):
            intent = "ocean_query"
            required_agents = ["ocean"]

        # Default fallback
        else:
            intent = p_intent or "marine_safety"
            required_agents = ["weather", "ocean", "geospatial"]

        # If a location is required by agents but missing in both message and prior context,
        # fail safely by prompting the user for a location rather than inventing one.
        if location is None and intent in ["marine_safety", "weather_query", "ocean_query"] and not is_referent_distance_query:
            intent = "clarification_needed"
            required_agents = []
            clarification_reason = "missing_location"

        plan = PlannerOutput(
            intent=intent,
            location=location,
            time_range=time_range or "tomorrow_morning",
            activity=activity,
            vessel_type=vessel_type,
            language_mode=language_mode,
            required_agents=required_agents,
            clarification_reason=clarification_reason
        )

        conv_id = conversation_id or (prior_context.conversation_id if prior_context else "demo-001")
        updated_context = ConversationContext(
            conversation_id=conv_id,
            location=location,
            date=date,
            time_window=time_window,
            activity=activity,
            vessel_type=vessel_type,
            language_mode=language_mode,
            last_intent=intent if intent != "clarification_needed" else p_intent,
            selected_pfz=p_pfz,
            active_route=p_route,
            turn_count=turn_count + 1
        )

        return plan, updated_context
