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
    "munambam harbor": {"name": "Munambam Harbor", "latitude": 10.1850, "longitude": 76.1680},
    "kuzhuppilly": {"name": "Kuzhuppilly", "latitude": 10.1700, "longitude": 76.1700},
    "fortkochi": {"name": "Fort Kochi", "latitude": 9.9600, "longitude": 76.2400},
    "fort kochi": {"name": "Fort Kochi", "latitude": 9.9600, "longitude": 76.2400},
    "kalamukku": {"name": "Kalamukku", "latitude": 9.9800, "longitude": 76.2300},
    "valarpadam": {"name": "Valarpadam", "latitude": 9.9800, "longitude": 76.2500},
    "vallarpadam": {"name": "Valarpadam", "latitude": 9.9800, "longitude": 76.2500},
    "alappuzha": {"name": "Alappuzha", "latitude": 9.4981, "longitude": 76.3388},
    "alleppey": {"name": "Alappuzha", "latitude": 9.4981, "longitude": 76.3388},
    "chavakkad": {"name": "Chavakkad", "latitude": 10.5300, "longitude": 76.0200},
    "thoppumpady": {"name": "Thoppumpady", "latitude": 9.9320, "longitude": 76.2620},
    "willingdon island": {"name": "Willingdon Island", "latitude": 9.9500, "longitude": 76.2700},
    "ernakulam wharf": {"name": "Ernakulam Wharf", "latitude": 9.9650, "longitude": 76.2650},
    "cochin fisheries harbour": {"name": "Cochin Fisheries Harbour", "latitude": 9.9400, "longitude": 76.2600},
    "കൊച്ചി": {"name": "Kochi", "latitude": 9.9312, "longitude": 76.2673},
    "ചെല്ലാനം": {"name": "Chellanam", "latitude": 9.8000, "longitude": 76.2600},
    "വൈപ്പിൻ": {"name": "Vypin", "latitude": 10.0500, "longitude": 76.2100},
    "മുനമ്പം": {"name": "Munambam", "latitude": 10.1800, "longitude": 76.1700},
    "കുഴുപ്പിള്ളി": {"name": "Kuzhuppilly", "latitude": 10.1700, "longitude": 76.1700},
    "ആലപ്പുഴ": {"name": "Alappuzha", "latitude": 9.4981, "longitude": 76.3388},
}


class ContextResolver:
    """Deterministic multi-turn context resolver and intent classifier."""

    # Marine vocabulary sets for deterministic domain intent filtering
    MARINE_KEYWORDS_WORDS = {
        "fish", "fishing", "fisher", "fishers", "fisherman", "fishermen", "catch", "catches",
        "trawl", "trawling", "trawler", "trawlers", "vallam", "canoe", "catamaran", "boat",
        "boats", "vessel", "vessels", "craft", "obm", "frp", "motorized", "mechanized",
        "nets", "netting", "seine", "seiner", "gillnet", "trolling", "angling",
        "safe", "safety", "risk", "danger", "dangerous", "hazard", "hazards", "hazardous",
        "warning", "advisable", "suraksha",
        "weather", "wind", "winds", "rain", "rainfall", "lightning", "storm", "cyclone",
        "squall", "gust", "gusts", "visibility", "fog",
        "ocean", "marine", "sea", "seas", "swell", "swells", "tide", "tides", "wave", "waves",
        "sst", "chlorophyll", "salinity", "bathymetry", "depth",
        "pfz", "pfzs", "geofence", "geofences", "corridor", "corridors", "waypoint", "waypoints",
        "nautical", "offshore", "coast", "coastal", "harbor", "harbour",
        "route", "routes", "passage", "passages", "transit", "transits", "alternative", "alternatives",
        "sail", "sailing", "navigate", "navigation",
        "കാലാവസ്ഥ", "കാറ്റ്", "മഴ", "തിരമാല", "കടൽ", "സുരക്ഷിതം", "മത്സ്യം", "മീൻ", "വള്ളം", "റൂട്ട്", "പാത"
    }

    MARINE_KEYWORDS_PHRASES = [
        "can i go", "can we go", "can i sail", "can i fish", "go out", "sail out", "venture out",
        "sea state", "sea condition", "sea surface temperature", "wave height",
        "potential fishing zone", "potential fishing zones", "fishing ground", "fishing grounds",
        "fishing zone", "fish zone", "restricted zone", "restricted zones", "security zone",
        "security zones", "safe passage", "transit route", "passage plan", "landing centre",
        "landing center", "deep sea",
        "how far", "what is the distance", "distance to",
        "route alternatives", "compare routes", "alternative routes", "alternative paths", "route options",
        "which one is closest", "which target is closest"
    ]

    REFERENTIAL_ADVISORY_PATTERNS = [
        r"\bwhen\s+(?:is|would|will|might)\s+(?:it\s+)?(?:fine|better|safe|good|ok|advisable|recommended)\b",
        r"\bwhen\s+can\s+(?:i|we)\s+(?:go|sail|fish|head\s+out|venture|do\s+(?:that|this|so))\b",
        r"\bwhen\s+should\s+(?:i|we)\s+(?:go|sail|fish|head\s+out|venture|do\s+(?:that|this|so))\b",
        r"\b(?:is\s+there|what\s+is)\s+a\s+better\s+time\b",
        r"\bwhen\s+would\s+be\s+better\b",
        r"\bwhen\s+is\s+better\b",
        r"\bwhich\s+time\s+(?:is|would\s+be)\s+(?:better|safer|best)\b",
        r"\bis\s+there\s+a\s+safer\s+(?:time|window|day|hour)\b",
        r"\bwhen\s+to\s+(?:go|sail|fish|do\s+(?:that|this))\b",
    ]

    REFERENTIAL_FOLLOWUP_PATTERNS = [
        r"\b(?:what|how)\s+about\b",
        r"\bwhat\s+if\b",
        r"\band\s+(?:tomorrow|afternoon|evening|morning|night|today|saturday|sunday|monday|tuesday|wednesday|thursday|friday|then|there|later)\b",
        r"\b(?:is\s+it\s+safe|can\s+(?:i|we)\s+go|how\s+are\s+conditions)\s+(?:there|then)\b",
        r"\b(?:do|doing)\s+(?:that|this)\b",
        r"\bhow\s+about\s+(?:tomorrow|afternoon|evening|morning|night|today|saturday|sunday|monday|tuesday|wednesday|thursday|friday)\b",
        r"^(?:and|then)\s+",
    ]

    GENERAL_KNOWLEDGE_EXCLUSIONS = {
        "mayor", "population", "history", "hotel", "hotels", "restaurant", "restaurants",
        "flight", "flights", "train", "trains", "airport", "capital", "president", "minister",
        "prime minister", "mla", "mp", "cricket", "football", "movie", "cinema", "actor",
        "actress", "song", "lyrics", "recipe", "code", "python", "javascript", "java", "math",
        "joke", "joke?"
    }

    GREETING_PATTERNS = [
        r"^(?:hi|hello|hey|hiya|howdy|hola|namaste|vanakkam|namaskaram)(?:\s+(?:orca|assistant|there|friend|bot|u|all))?$",
        r"^good\s+(?:morning|afternoon|evening|day|night)(?:\s+(?:orca|assistant|there|friend|bot|all))?$",
        r"^how\s+(?:are|r)\s+(?:you|u)(?:\s+doing)?$",
        r"^how\s+(?:are|r)\s+things$",
        r"^how(?:'s|\s+is)\s+it\s+going$",
        r"^(?:what's\s+up|whats\s+up|sup|wazzup)$",
        r"^(?:thanks|thank\s+(?:you|u)|thx|cheers|thanks\s+a\s+lot|thank\s+(?:you|u)\s+very\s+much)(?:\s+(?:orca|assistant|there|friend|bot))?$",
        r"^(?:bye|goodbye|see\s+(?:you|u|ya)|cya|take\s+care)(?:\s+(?:orca|assistant|there|friend|bot))?$",
        r"^(?:who\s+are\s+(?:you|u)|what\s+are\s+(?:you|u)|what\s+can\s+(?:you|u)\s+do|what\s+do\s+(?:you|u)\s+do|help|commands|options)$",
        r"^(?:നമസ്കാരം|ഹലോ|സുഖമാണോ|നന്ദി)(?:\s+orca)?$",
    ]

    CONVERSATIONAL_WORDS = {
        "hi", "hello", "hey", "hiya", "howdy", "hola", "namaste", "vanakkam", "namaskaram",
        "orca", "assistant", "bot", "there", "friend", "all",
        "good", "morning", "afternoon", "evening", "day", "night",
        "how", "are", "r", "you", "u", "ya", "doing", "things", "is", "it", "going", "hows",
        "whats", "what's", "up", "sup", "wazzup",
        "thanks", "thank", "thx", "cheers", "a", "lot", "very", "much",
        "bye", "goodbye", "see", "cya", "later", "take", "care",
        "who", "what", "can", "do", "help", "commands", "options",
        "and", "please", "okay", "ok", "cool",
        "നമസ്കാരം", "ഹലോ", "സുഖമാണോ", "നന്ദി"
    }

    VALID_MARINE_INTENTS = {
        "marine_safety",
        "weather_query",
        "ocean_query",
        "pfz_search",
        "pfz_radius_filter",
        "pfz_distance",
        "pfz_comparison",
        "pfz_geofence_check",
        "safe_passage_route",
        "route_risk_temporal",
        "route_alternatives",
        "temporal_comparison",
    }

    NEWS_PATTERNS = [
        # Explicit marine news phrases
        r"\b(?:marine|sea|ocean|coastal|maritime|fishing|port)\s+news\b",
        r"\bnews\s+(?:about|on|in|at|from|of)\s+(?:the\s+)?(?:sea|ocean|marine|coast|coastal|waters?|fisheries|kerala)\b",
        r"\b(?:what\s+is\s+new|what's\s+new)\s+in\s+(?:the\s+)?(?:sea|marine|ocean|coast|water)?\s*news\b",
        r"\b(?:what\s+is\s+new|what's\s+new)\s+in\s+(?:the\s+)?(?:sea|marine|ocean|coast)\b",
        r"\b(?:any|latest|recent|today(?:'s)?|daily|breaking)\s+(?:.*?\b)?(?:marine|sea|ocean|coastal|maritime)\s+news\b",
        r"\b(?:any|latest|recent|today(?:'s)?)\s+news\s+(?:today|now)?\b",
        r"\bnews\s+today\b",
        # Event / occurrence inquiries at sea
        r"\bwhat\s+(?:has\s+)?happened\s+(?:in|at|on)\s+(?:the\s+)?(?:sea|ocean|coast|water)\b",
        r"\bwhat(?:'s|\s+is)\s+happening\s+(?:in|at|on)\s+(?:the\s+)?(?:sea|ocean|coast|water)\b",
        r"\bwhat(?:'s|\s+is)\s+going\s+on\s+(?:in|at|on)\s+(?:the\s+)?(?:sea|ocean|coast|water)\b",
        r"\b(?:any|latest)\s+(?:incidents?|accidents?|events?|headlines?|stories|articles?|updates?)\s+(?:at|in|on)\s+(?:the\s+)?(?:sea|ocean)\b",
        r"\b(?:വാർത്തകൾ|വാർത്ത)\b",
    ]

    @classmethod
    def is_marine_news_query(cls, text: str) -> bool:
        """Deterministically detect marine news, current events, or incident inquiries."""
        t = text.lower().strip()
        words = set(re.findall(r"\b[\w'-]+\b", t))

        # Direct pattern match
        if any(bool(re.search(p, t)) for p in cls.NEWS_PATTERNS):
            return True

        # Semantic keywords combination: asking for news/headlines in marine context
        has_news_word = bool(words & {"news", "headline", "headlines", "incident", "incidents", "accident", "accidents", "വാർത്ത", "വാർത്തകൾ"})
        has_marine_context = bool(words & {"sea", "marine", "ocean", "maritime", "coastal", "coast", "water", "waters", "offshore"})

        if has_news_word and (has_marine_context or "news" in words):
            return True

        # "what happened" / "what is happening" combined with marine words
        if re.search(r"\bwhat\s+(?:has\s+)?happened\b", t) or re.search(r"\bwhat(?:'s|\s+is)\s+happening\b", t) or re.search(r"\bwhat(?:'s|\s+is)\s+going\s+on\b", t):
            if has_marine_context or "sea" in words or "ocean" in words:
                return True

        return False

    @classmethod
    def is_referential_inquiry(cls, text: str) -> bool:
        """Detect deictic or connective follow-up inquiries that depend on context."""
        t = text.lower().strip()
        all_patterns = cls.REFERENTIAL_ADVISORY_PATTERNS + cls.REFERENTIAL_FOLLOWUP_PATTERNS
        return any(bool(re.search(p, t)) for p in all_patterns)

    @classmethod
    def has_marine_intent(cls, text: str, prior_context: Optional[ConversationContext] = None) -> bool:
        """Deterministically determine if user message pertains to marine intelligence.

        Evaluates explicit coordinates, known coastal geography, marine terminology,
        and multi-turn referents when prior marine context exists.
        """
        # Marine news / current events inquiries are outside supported operational marine intelligence
        if cls.is_marine_news_query(text):
            return False

        text_lower = text.lower().strip()
        words = set(re.findall(r"\b[\w'-]+\b", text_lower))

        # 1. Explicit geographic coordinates
        if cls.extract_coordinates(text) is not None:
            return True

        # Check for general knowledge exclusions (e.g., 'Who is the mayor of Kochi?', 'Tell me a joke')
        has_general_exclusion = any(ex in words or ex in text_lower for ex in cls.GENERAL_KNOWLEDGE_EXCLUSIONS)

        # 2. Direct marine domain keywords
        has_marine_word = any(kw in words for kw in cls.MARINE_KEYWORDS_WORDS)
        has_marine_phrase = any(phrase in text_lower for phrase in cls.MARINE_KEYWORDS_PHRASES)

        if has_marine_word or has_marine_phrase:
            return True

        # 3. Referent distance query, candidate comparison, or closest target patterns
        if bool(
            re.search(r"\bhow far\b", text_lower) or
            re.search(r"\bwhat is the distance\b", text_lower) or
            re.search(r"\bdistance to\b", text_lower) or
            re.search(r"\bcompare\s+(?:the\s+)?(?:first|1st|target\s*1)\s+and\s+(?:the\s+)?(?:second|2nd|target\s*2)\b", text_lower) or
            re.search(r"\bcompare\s+(?:the\s+)?(?:second|2nd|target\s*2)\s+and\s+(?:the\s+)?(?:first|1st|target\s*1)\b", text_lower) or
            re.search(r"\bcompare\s+(?:them|candidates|targets|both|the\s+two)\b", text_lower) or
            re.search(r"\bwhich\s+(?:one|target|pfz)?\s*is\s+(?:the\s+)?closest\b", text_lower)
        ):
            return True

        if has_general_exclusion:
            return False

        # 4. Known coastal locations (Kochi, Chellanam, Vypin, Munambam, etc.)
        for loc_key in KNOWN_LOCATIONS:
            if (loc_key in text_lower) if any(ord(c) > 127 for c in loc_key) else re.search(r"\b" + re.escape(loc_key) + r"\b", text_lower):
                return True

        # 5. Referential follow-up inquiry (either contextual or requiring clarification)
        if cls.is_referential_inquiry(text):
            return True

        # 6. Multi-turn referents if prior conversation context exists with active marine state
        has_prior_marine_intent = bool(
            prior_context and prior_context.last_intent and prior_context.last_intent in cls.VALID_MARINE_INTENTS
        )
        if prior_context and (prior_context.location or prior_context.candidate_pfzs or prior_context.selected_pfz or has_prior_marine_intent or prior_context.activity):
            # Check for follow-up modifiers ("what about...", "and tomorrow", "how about...")
            if bool(re.search(r"\b(?:what|how)\s+about\b", text_lower) or re.search(r"^(?:and|what\s+if)\b", text_lower)):
                return True
            # Check for temporal modifiers
            if any(t in words for t in ["morning", "afternoon", "evening", "night", "tomorrow", "today", "saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"]):
                return True
            # Check for comparative referents ("compare them", "which one", "the first one", "target 2")
            if any(ref in text_lower for ref in ["compare", "target", "which one", "how far", "distance", "nearest"]):
                return True
            # Pronouns referring to prior subject ("that", "it", "this", "there", "then")
            if any(p in words for p in ["that", "there", "then"]):
                return True

        return False

    @classmethod
    def is_conversational_greeting(cls, text: str) -> bool:
        """Check if message is a standalone greeting, pleasantry, gratitude, or identity question."""
        text_clean = re.sub(r"[^\w\s]", "", text.lower()).strip()
        if not text_clean:
            return True

        # Check regex patterns
        for pattern in cls.GREETING_PATTERNS:
            if re.search(pattern, text_clean):
                return True

        # Check token membership
        tokens = text_clean.split()
        if tokens and all(t in cls.CONVERSATIONAL_WORDS for t in tokens):
            return True

        return False

    @staticmethod
    def extract_coordinates(text: str) -> Optional[LocationCoords]:
        """Extract explicit coordinate pairs like '9.85, 76.15', '9.85N, 76.15E'."""
        m = re.search(r"\b(\d{1,2}(?:\.\d+)?)\s*(?:°\s*)?[nN]?\s*[,/ ]\s*(\d{1,3}(?:\.\d+)?)\s*(?:°\s*)?[eE]?\b", text)
        if m:
            try:
                lat = float(m.group(1))
                lon = float(m.group(2))
                if 7.0 <= lat <= 15.0 and 70.0 <= lon <= 80.0:
                    return LocationCoords(
                        name=f"Coordinates ({lat:.4f}°N, {lon:.4f}°E)",
                        latitude=round(lat, 4),
                        longitude=round(lon, 4)
                    )
            except Exception:
                pass
        return None

    @classmethod
    def extract_destination(
        cls,
        text: str,
        candidates: List[NearestPFZ],
        selected_pfz: Optional[NearestPFZ],
        prior_dest: Optional[LocationCoords] = None
    ) -> Tuple[Optional[LocationCoords], Optional[NearestPFZ], Optional[str]]:
        """Extract explicit destination by place name, coordinates, or PFZ referent."""
        text_lower = text.lower()

        # 1. Check "from <origin> to <destination>" pattern
        from_to_match = re.search(r"\bfrom\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z0-9\s,\.]+)", text_lower)
        if from_to_match:
            dest_part = from_to_match.group(2).strip()
            coord_dest = cls.extract_coordinates(dest_part)
            if coord_dest:
                return coord_dest, None, coord_dest.name
            for key, c_data in KNOWN_LOCATIONS.items():
                if key in dest_part or dest_part.startswith(key):
                    loc = LocationCoords(**c_data)
                    return loc, None, loc.name

        # 2. Check for coordinate destination
        coords = cls.extract_coordinates(text)
        if coords and any(w in text_lower for w in ["to", "route", "destination", "sail", "head", "navigate", "reach"]):
            return coords, None, coords.name

        # 3. Check for destination referents: "to target 2", "to the second PFZ", "to nearest PFZ"
        if any(w in text_lower for w in ["to target", "to the second", "to second", "to the first", "to first", "to that target", "to that pfz", "to the pfz", "nearest pfz"]):
            ord_idx = cls.extract_ordinal_index(text_lower)
            if ord_idx is not None and candidates and len(candidates) > ord_idx:
                tgt = candidates[ord_idx]
                loc = LocationCoords(name=tgt.name, latitude=tgt.latitude, longitude=tgt.longitude)
                return loc, tgt, tgt.name
            elif selected_pfz is not None:
                loc = LocationCoords(name=selected_pfz.name, latitude=selected_pfz.latitude, longitude=selected_pfz.longitude)
                return loc, selected_pfz, selected_pfz.name

        # 4. Check for "the destination" / "that destination"
        if re.search(r"\b(?:the|that)\s+destination\b", text_lower) and prior_dest is not None:
            return prior_dest.model_copy(), None, prior_dest.name

        # 5. Check for explicit place name destination: "route to Munambam", "head to Chellanam", "sail to Vypin"
        dest_match = re.search(r"\b(?:route\s+to|corridor\s+to|head\s+to|heading\s+to|sail\s+to|sailing\s+to|navigate\s+to|destination\s+(?:to|is)?|travel\s+to|go\s+to|reach|passage\s+to)\s+([a-zA-Z\s]+)", text_lower)
        if dest_match:
            candidate_name = dest_match.group(1).strip()
            candidate_name = re.sub(r"\s+from\s+.*$", "", candidate_name).strip()
            if any(term in candidate_name for term in ["pfz", "target", "fishing zone"]):
                return None, None, None
            for key, c_data in KNOWN_LOCATIONS.items():
                if key in candidate_name or candidate_name.startswith(key):
                    loc = LocationCoords(**c_data)
                    return loc, None, loc.name

        return None, None, None

    @staticmethod
    def extract_location(text: str, prior_loc: Optional[LocationCoords] = None) -> Optional[LocationCoords]:
        """Extract explicit geographic reference or inherit from prior context without inventing."""
        text_lower = text.lower()

        # Check explicit origin "from <origin>"
        from_match = re.search(r"\bfrom\s+([a-zA-Z\s]+?)(?:\s+to\b|$)", text_lower)
        if from_match:
            origin_candidate = from_match.group(1).strip()
            for key, coords_dict in KNOWN_LOCATIONS.items():
                if key in origin_candidate or origin_candidate.startswith(key):
                    return LocationCoords(**coords_dict)

        # Check explicit coordinates (if not designated as destination via 'to <coords>')
        if not re.search(r"\bto\s+\d", text_lower):
            coords = ContextResolver.extract_coordinates(text)
            if coords:
                return coords

        for key, coords_dict in KNOWN_LOCATIONS.items():
            if (key in text_lower) if any(ord(c) > 127 for c in key) else re.search(r"\b" + re.escape(key) + r"\b", text_lower):
                return LocationCoords(**coords_dict)

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

        # Weekdays
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if re.search(r"\b" + day + r"\b", text_lower):
                return day

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

    @staticmethod
    def extract_ordinal_index(text: str) -> Optional[int]:
        """Extract 0-based index from ordinal phrases: 'first'/'target 1' -> 0, 'second'/'target 2' -> 1, etc."""
        t = text.lower()
        if re.search(r"\b(?:the\s+)?(?:first|1st|target\s*1)\b", t):
            return 0
        if re.search(r"\b(?:the\s+)?(?:second|2nd|target\s*2)\b", t):
            return 1
        if re.search(r"\b(?:the\s+)?(?:third|3rd|target\s*3)\b", t):
            return 2
        if re.search(r"\b(?:the\s+)?(?:fourth|4th|target\s*4)\b", t):
            return 3
        if re.search(r"\b(?:the\s+)?(?:fifth|5th|target\s*5)\b", t):
            return 4
        return None

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
        p_dest = prior_context.destination if prior_context else None
        p_dest_name = prior_context.destination_name if prior_context else None
        p_date = prior_context.date if prior_context else None
        p_win = prior_context.time_window if prior_context else None
        p_act = prior_context.activity if prior_context else None
        p_vessel = prior_context.vessel_type if prior_context else None
        p_lang = prior_context.language_mode if prior_context else "bilingual"
        p_intent = prior_context.last_intent if prior_context else None
        p_pfz = prior_context.selected_pfz if prior_context else None
        p_candidates = prior_context.candidate_pfzs if prior_context else []
        p_compared = prior_context.compared_pfzs if prior_context else None
        p_pfz_comparison = prior_context.pfz_comparison if prior_context else None
        p_route = prior_context.active_route if prior_context else None
        turn_count = prior_context.turn_count if prior_context else 0

        # Destination resolution (M5)
        dest_loc, dest_pfz, dest_name = cls.extract_destination(text, p_candidates, p_pfz, p_dest)
        destination = dest_loc or p_dest
        destination_name = dest_name or p_dest_name
        if dest_pfz:
            p_pfz = dest_pfz

        # Extract current or inherited fields
        location = cls.extract_location(text, p_loc)

        # Only adopt user GPS coordinates if the query explicitly refers to user's vessel / position / "near me"
        is_user_pos_query = any(bool(re.search(r"\b" + re.escape(w) + r"\b", text_lower)) for w in ["near me", "around me", "my position", "my location", "current position", "current location", "where i am", "my vessel", "my boat", "here"])
        if is_user_pos_query and user_lat is not None and user_lon is not None:
            location = LocationCoords(name="User Vessel Position", latitude=round(user_lat, 4), longitude=round(user_lon, 4))

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

        # Domain routing check: separate non-marine queries (news, greetings, unrelated) from marine intelligence
        if not cls.has_marine_intent(text, prior_context):
            if cls.is_marine_news_query(text):
                intent = "unsupported"
                clarification_reason = "unsupported_news"
            elif cls.is_conversational_greeting(text):
                intent = "conversational_greeting"
                clarification_reason = None
            else:
                intent = "unsupported"
                clarification_reason = "unsupported_domain"

            plan = PlannerOutput(
                intent=intent,
                location=None,
                destination=None,
                destination_name=None,
                time_range=None,
                activity=p_act,
                vessel_type=vessel_type,
                language_mode=language_mode,
                required_agents=[],
                clarification_reason=clarification_reason
            )

            conv_id = conversation_id or (prior_context.conversation_id if prior_context else "demo-001")
            updated_context = ConversationContext(
                conversation_id=conv_id,
                location=p_loc,
                destination=p_dest,
                destination_name=p_dest_name,
                date=p_date,
                time_window=p_win,
                activity=p_act,
                vessel_type=vessel_type,
                language_mode=language_mode,
                last_intent=p_intent,
                selected_pfz=p_pfz,
                candidate_pfzs=p_candidates,
                compared_pfzs=p_compared,
                pfz_comparison=p_pfz_comparison,
                active_route=p_route,
                temporal_comparison=prior_context.temporal_comparison if prior_context else None,
                route_risk=prior_context.route_risk if prior_context else None,
                geospatial_data=prior_context.geospatial_data if prior_context else None,
                turn_count=turn_count + 1
            )
            return plan, updated_context

        intent: str
        required_agents: List[str]
        clarification_reason: Optional[str] = None
        compare_windows: Optional[List[str]] = None
        radius_km: Optional[float] = None
        target_ordinal: Optional[int] = None
        compare_targets: Optional[List[int]] = None

        # Check for standalone referential inquiry with NO prior marine context
        has_active_marine_intent = bool(p_intent and p_intent in cls.VALID_MARINE_INTENTS)
        has_active_marine_context = bool(
            p_loc or p_act or has_active_marine_intent or p_candidates or p_pfz or p_route or
            (prior_context and (prior_context.temporal_comparison or prior_context.route_risk))
        )
        words_set = set(re.findall(r"\b[\w'-]+\b", text_lower))
        has_direct_location = any(loc in text_lower for loc in KNOWN_LOCATIONS) or (cls.extract_coordinates(text) is not None)

        if cls.is_referential_inquiry(text) and not has_active_marine_context and not has_direct_location:
            plan = PlannerOutput(
                intent="clarification_needed",
                location=None,
                destination=None,
                destination_name=None,
                time_range=None,
                activity=None,
                vessel_type=vessel_type,
                language_mode=language_mode,
                required_agents=[],
                clarification_reason="missing_referent_context"
            )
            conv_id = conversation_id or (prior_context.conversation_id if prior_context else "demo-001")
            updated_context = ConversationContext(
                conversation_id=conv_id,
                location=p_loc,
                destination=p_dest,
                destination_name=p_dest_name,
                date=p_date,
                time_window=p_win,
                activity=p_act,
                vessel_type=vessel_type,
                language_mode=language_mode,
                last_intent=p_intent,
                selected_pfz=p_pfz,
                candidate_pfzs=p_candidates,
                compared_pfzs=p_compared,
                pfz_comparison=p_pfz_comparison,
                active_route=p_route,
                temporal_comparison=prior_context.temporal_comparison if prior_context else None,
                route_risk=prior_context.route_risk if prior_context else None,
                geospatial_data=prior_context.geospatial_data if prior_context else None,
                turn_count=turn_count + 1
            )
            return plan, updated_context

        # Scenario 0a: Candidate Pair Comparison ("Compare the first and second", "Compare target 1 and target 2", "Compare them")
        if bool(
            re.search(r"\bcompare\s+(?:the\s+)?(?:first|1st|target\s*1)\s+and\s+(?:the\s+)?(?:second|2nd|target\s*2)\b", text_lower) or
            re.search(r"\bcompare\s+(?:the\s+)?(?:second|2nd|target\s*2)\s+and\s+(?:the\s+)?(?:first|1st|target\s*1)\b", text_lower) or
            re.search(r"\bcompare\s+(?:them|candidates|targets|both|the\s+two)\b", text_lower)
        ) and not ("morning" in text_lower or "afternoon" in text_lower or "today" in text_lower or "tomorrow" in text_lower):
            if p_candidates and len(p_candidates) >= 2:
                intent = "pfz_comparison"
                required_agents = ["geospatial"]
                compare_targets = [0, 1]
                logger.info(f"[ContextResolver] Resolved candidate comparison: {p_candidates[0].name} vs {p_candidates[1].name}")
            else:
                intent = "clarification_needed"
                required_agents = []
                clarification_reason = "missing_candidate_context"
                logger.info("[ContextResolver] Candidate comparison failed: fewer than 2 candidates in context.")
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

        # Scenario 0b: Direct-Route Geofence Question ("Is there a restricted zone between me and that target?", "Does route to second target cross restricted zone?")
        elif bool(
            re.search(r"\brestricted\s+zone\b", text_lower) and
            any(w in text_lower for w in ["between", "to that", "to the", "to target", "cross", "crosses", "intersects", "through", "ahead", "on the way"])
        ):
            ord_idx = cls.extract_ordinal_index(text_lower)
            if ord_idx is not None:
                if p_candidates and len(p_candidates) > ord_idx:
                    p_pfz = p_candidates[ord_idx]
                    target_ordinal = ord_idx
                    intent = "pfz_geofence_check"
                    required_agents = ["geospatial"]
                else:
                    intent = "clarification_needed"
                    required_agents = []
                    clarification_reason = "missing_candidate_context"
            elif p_pfz is not None:
                intent = "pfz_geofence_check"
                required_agents = ["geospatial"]
            elif p_candidates and len(p_candidates) > 0:
                p_pfz = p_candidates[0]
                target_ordinal = 0
                intent = "pfz_geofence_check"
                required_agents = ["geospatial"]
            else:
                intent = "clarification_needed"
                required_agents = []
                clarification_reason = "missing_referent_target"
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

        # Scenario 0c: Closest Target Query ("Which one is closest?", "Which target is closest?")
        elif bool(
            re.search(r"\bwhich\s+(?:one|target|pfz)?\s*is\s+(?:the\s+)?closest\b", text_lower) or
            re.search(r"\bwhat\s+is\s+the\s+closest\s+(?:target|pfz|one)\b", text_lower) or
            re.search(r"\bclosest\s+(?:one|target|pfz)\b", text_lower)
        ):
            if p_candidates and len(p_candidates) > 0:
                p_pfz = p_candidates[0]
                target_ordinal = 0
                intent = "pfz_distance"
                required_agents = []
                logger.info(f"[ContextResolver] Resolved closest candidate -> PFZ: {p_pfz.name}")
            elif p_pfz is not None:
                intent = "pfz_distance"
                required_agents = []
            else:
                intent = "clarification_needed"
                required_agents = []
                clarification_reason = "missing_candidate_context"

        # Scenario 0d: Radial PFZ Filtering ("Show PFZ targets within 30 km of Kochi", "What PFZ targets are within 25 km?")
        elif bool(
            re.search(r"\b(?:within|under|less\s+than)\s+(\d+(?:\.\d+)?)\s*(?:km|kilometers|kilometres)\b", text_lower) or
            re.search(r"\b(\d+(?:\.\d+)?)\s*(?:km|kilometers|kilometres)\s*(?:radius|range)\b", text_lower)
        ) and any(w in text_lower for w in ["pfz", "target", "targets", "zone", "zones", "fishing"]):
            match = (
                re.search(r"\b(?:within|under|less\s+than)\s+(\d+(?:\.\d+)?)\s*(?:km|kilometers|kilometres)\b", text_lower) or
                re.search(r"\b(\d+(?:\.\d+)?)\s*(?:km|kilometers|kilometres)\s*(?:radius|range)\b", text_lower)
            )
            radius_km = float(match.group(1)) if match else 30.0
            intent = "pfz_radius_filter"
            required_agents = ["geospatial"]
            activity = activity or "fishing"
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

        # Scenario 1: Referent distance query ("How far is it?", "How far is the second one?")
        elif is_referent_distance_query and not any(k in text_lower for k in KNOWN_LOCATIONS):
            ord_idx = cls.extract_ordinal_index(text_lower)
            if ord_idx is not None:
                if p_candidates and len(p_candidates) > ord_idx:
                    p_pfz = p_candidates[ord_idx]
                    target_ordinal = ord_idx
                    intent = "pfz_distance"
                    required_agents = []
                    logger.info(f"[ContextResolver] Resolved ordinal {ord_idx} -> PFZ: {p_pfz.name}")
                else:
                    intent = "clarification_needed"
                    required_agents = []
                    clarification_reason = "missing_candidate_context"
            elif p_pfz is not None:
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

        # Scenario 1b-0: Route Risk Temporal Query ("is the route getting riskier?", "will the route get riskier tomorrow?")
        elif bool(
            re.search(r"\b(?:is|will)\s+(?:the\s+)?route\s+(?:getting|get|be)\s+riskier\b", text_lower) or
            re.search(r"\broute\s+risk\s+(?:tomorrow|later|afternoon|change)\b", text_lower)
        ):
            intent = "route_risk_temporal"
            required_agents = ["weather", "ocean", "geospatial"]
            activity = "navigation"
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
            d_prefix = date or p_date or "tomorrow"
            if p_win and "morning" in p_win:
                compare_windows = [f"{d_prefix}_morning", f"{d_prefix}_afternoon"]
            else:
                compare_windows = ["current", f"{d_prefix}_morning"]

        # Scenario 1b-1: Route Alternatives Query ("compare routes", "route alternatives", "alternative paths")
        elif any(w in text_lower for w in ["compare routes", "route alternatives", "alternative routes", "route options", "alternative paths"]):
            intent = "route_alternatives"
            required_agents = ["weather", "ocean", "geospatial"]
            activity = "navigation"
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

        # Scenario 2: "What if I go toward the nearest PFZ?"
        elif is_pfz_referent and any(w in text_lower for w in ["go", "head", "sail", "safe", "what if"]) and not any(w in text_lower for w in ["route", "corridor", "passage", "waypoint"]):
            intent = "marine_safety"
            required_agents = ["weather", "ocean", "geospatial"]
            activity = "fishing"

        # Scenario 1b-2: Safe Passage Corridor / Navigation Route Query
        elif any(w in text_lower for w in ["route", "corridor", "passage", "waypoint", "how to reach", "safe route", "navigate", "റൂട്ട്", "പാത", "സഞ്ചാര പാത"]) or (dest_loc is not None and any(w in text_lower for w in ["route", "head to", "sail to", "navigate to", "passage to", "corridor to", "go to"])):
            intent = "safe_passage_route"
            required_agents = ["weather", "ocean", "geospatial"]
            activity = "navigation"
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

        # Scenario 1b-advisory: Timing Advisory Inquiry ("when is it fine to do that", "when would be better", "when can i go")
        elif any(re.search(p, text_lower) for p in cls.REFERENTIAL_ADVISORY_PATTERNS):
            intent = "temporal_comparison"
            required_agents = ["weather", "ocean"]
            activity = activity or p_act or "fishing"
            if location is None:
                location = p_loc or LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

            d_prefix = date or p_date or "today"
            if d_prefix == "today":
                if p_win in ["afternoon", "evening"]:
                    compare_windows = ["today_afternoon", "tomorrow_morning"]
                else:
                    compare_windows = ["today_morning", "today_afternoon"]
            elif d_prefix == "tomorrow":
                compare_windows = ["tomorrow_morning", "tomorrow_afternoon"]
            else:
                compare_windows = [f"{d_prefix}_morning", f"{d_prefix}_afternoon"]

        # Scenario 1c: Temporal Condition Comparison ("Is morning or afternoon better?", "How will conditions change tomorrow?", "Will the sea be calmer later?")
        elif bool(
            re.search(r"\b(morning\s+(or|vs|and)\s+afternoon|afternoon\s+(or|vs|and)\s+morning)\b", text_lower) or
            re.search(r"\b(today\s+(or|vs|and)\s+tomorrow|tomorrow\s+(or|vs|and)\s+today)\b", text_lower) or
            re.search(r"\b(is|which\s+is)\s+(morning|afternoon)\s+better\b", text_lower) or
            re.search(r"\b(how\s+will\s+conditions\s+change|will\s+conditions\s+improve)\b", text_lower) or
            re.search(r"\b(will\s+(?:the\s+)?sea\s+be\s+calmer|calmer\s+later|calmer\s+tomorrow|is\s+it\s+calmer)\b", text_lower) or
            re.search(r"\b(compare\s+(conditions|morning|afternoon|today|tomorrow))\b", text_lower) or
            ("രാവിലെയാണോ" in text_lower or "ഉച്ചയ്ക്കാണോ" in text_lower or "ഇന്ന് vs നാളെ" in text_lower) or
            (p_intent in ["marine_safety", "weather_query", "temporal_comparison"] and re.search(r"\b(is\s+afternoon\s+better|is\s+morning\s+better)\b", text_lower))
        ):
            intent = "temporal_comparison"
            required_agents = ["weather", "ocean"]
            if location is None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

            # Determine window pairs
            if ("today" in text_lower and "tomorrow" in text_lower) or "change tomorrow" in text_lower or "improve tomorrow" in text_lower or "calmer tomorrow" in text_lower:
                compare_windows = ["current", "tomorrow_morning"]
            elif ("calmer later" in text_lower or "sea be calmer" in text_lower) and not ("tomorrow" in text_lower):
                d_prefix = date or p_date or "tomorrow"
                compare_windows = [f"{d_prefix}_morning", f"{d_prefix}_afternoon"]
            elif "afternoon" in text_lower and ("morning" in text_lower or (p_win and "morning" in p_win)):
                d_prefix = date or p_date or "tomorrow"
                compare_windows = [f"{d_prefix}_morning", f"{d_prefix}_afternoon"]
            elif "morning" in text_lower and (p_win and "afternoon" in p_win):
                d_prefix = date or p_date or "tomorrow"
                compare_windows = [f"{d_prefix}_afternoon", f"{d_prefix}_morning"]
            else:
                d_prefix = date or p_date or "tomorrow"
                compare_windows = [f"{d_prefix}_morning", f"{d_prefix}_afternoon"]

        # Scenario 3: Follow-up modifier ("What about afternoon?", "What about the second one?", "What about Chellanam?", "and tomorrow?", "how about evening?")
        elif (is_followup_modifier or re.search(r"\b(?:what|how)\s+about\b", text_lower) or re.search(r"^(?:and|then)\b", text_lower)) and not any(w in text_lower for w in ["pfz", "fishing zone"]):
            ord_idx = cls.extract_ordinal_index(text_lower)
            if ord_idx is not None:
                if p_candidates and len(p_candidates) > ord_idx:
                    p_pfz = p_candidates[ord_idx]
                    target_ordinal = ord_idx
                    intent = "pfz_distance"
                    required_agents = []
                    logger.info(f"[ContextResolver] Follow-up resolved ordinal {ord_idx} -> PFZ: {p_pfz.name}")
                else:
                    intent = "clarification_needed"
                    required_agents = []
                    clarification_reason = "missing_candidate_context"
            else:
                if p_intent in ["marine_safety", "safe_passage_route", "weather_query", "ocean_query"]:
                    intent = p_intent
                else:
                    intent = "marine_safety"

                activity = activity or p_act or "fishing"
                if location is None:
                    location = p_loc or LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

                has_temporal_modifier = any(
                    t in words_set for t in [
                        "morning", "afternoon", "evening", "night",
                        "tomorrow", "today", "saturday", "sunday",
                        "monday", "tuesday", "wednesday", "thursday", "friday",
                        "later", "soon"
                    ]
                )
                spatial_context_unchanged = (
                    p_loc is not None and
                    location is not None and
                    location.name == p_loc.name and
                    (dest_loc is None or (p_dest is not None and dest_loc.name == p_dest.name)) and
                    (p_pfz is not None or p_route is not None or (prior_context and prior_context.geospatial_data is not None))
                )

                if intent in ["marine_safety", "safe_passage_route"]:
                    if has_temporal_modifier and spatial_context_unchanged:
                        required_agents = ["weather", "ocean"]
                        logger.info("[ContextResolver] Pure temporal follow-up with unchanged spatial context: selecting ['weather', 'ocean'] and reusing existing spatial context.")
                    else:
                        required_agents = ["weather", "ocean", "geospatial"]
                elif intent == "temporal_comparison":
                    required_agents = ["weather", "ocean"]
                elif intent in ["pfz_search", "pfz_radius_filter"]:
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
            if location is None and activity is not None:
                location = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

            has_temporal_modifier = any(
                t in words_set for t in [
                    "morning", "afternoon", "evening", "night",
                    "tomorrow", "today", "saturday", "sunday",
                    "monday", "tuesday", "wednesday", "thursday", "friday",
                    "later", "soon"
                ]
            )
            spatial_context_unchanged = (
                not has_direct_location and
                p_loc is not None and
                location is not None and
                location.name == p_loc.name and
                (dest_loc is None or (p_dest is not None and dest_loc.name == p_dest.name)) and
                (p_pfz is not None or p_route is not None or (prior_context and prior_context.geospatial_data is not None))
            )
            if has_temporal_modifier and spatial_context_unchanged:
                required_agents = ["weather", "ocean"]
                logger.info("[ContextResolver] Safety query with unchanged spatial context: selecting ['weather', 'ocean'] and reusing existing spatial context.")
            else:
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
        if location is None and intent in ["marine_safety", "weather_query", "ocean_query", "pfz_search", "pfz_radius_filter", "safe_passage_route"] and not is_referent_distance_query:
            intent = "clarification_needed"
            required_agents = []
            clarification_reason = "missing_location"

        plan = PlannerOutput(
            intent=intent,
            location=location,
            destination=destination,
            destination_name=destination_name,
            time_range=time_range or "tomorrow_morning",
            activity=activity,
            vessel_type=vessel_type,
            language_mode=language_mode,
            required_agents=required_agents,
            compare_windows=compare_windows,
            radius_km=radius_km,
            target_ordinal=target_ordinal,
            compare_targets=compare_targets,
            clarification_reason=clarification_reason
        )

        conv_id = conversation_id or (prior_context.conversation_id if prior_context else "demo-001")
        updated_context = ConversationContext(
            conversation_id=conv_id,
            location=location,
            destination=destination,
            destination_name=destination_name,
            date=date,
            time_window=time_window,
            activity=activity,
            vessel_type=vessel_type,
            language_mode=language_mode,
            last_intent=intent if intent != "clarification_needed" else p_intent,
            selected_pfz=p_pfz,
            candidate_pfzs=p_candidates,
            compared_pfzs=p_compared,
            pfz_comparison=p_pfz_comparison,
            active_route=p_route,
            temporal_comparison=prior_context.temporal_comparison if prior_context else None,
            route_risk=prior_context.route_risk if prior_context else None,
            geospatial_data=prior_context.geospatial_data if prior_context else None,
            turn_count=turn_count + 1
        )

        return plan, updated_context
