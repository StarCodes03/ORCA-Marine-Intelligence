"""ORCA Marine Intelligence - Central Risk Thresholds Configuration

All marine safety rules and threshold boundaries must be defined here.
Do NOT scatter hardcoded values across agents.
"""

from typing import Dict, Any, Optional

# Wind speed thresholds (km/h) based on coastal artisanal/mechanized vessel safety
WIND_THRESHOLDS: Dict[str, float] = {
    "safe_max": 25.0,        # < 25 km/h: Safe for all standard fishing vessels
    "moderate_max": 35.0,    # 25 - 35 km/h: Caution advised for small craft
    "high_max": 50.0,        # 35 - 50 km/h: High risk, warning issued
    # > 50 km/h: Gale / Storm / Critical
}

# Significant Wave Height thresholds (meters)
WAVE_HEIGHT_THRESHOLDS: Dict[str, float] = {
    "safe_max": 1.5,         # < 1.5 m: Slight / normal sea condition
    "moderate_max": 2.2,     # 1.5 - 2.2 m: Moderate sea, rough chop
    "high_max": 3.2,         # 2.2 - 3.2 m: Rough sea, high risk for small boats
    # > 3.2 m: Very rough / Dangerous
}

# Rain Probability thresholds (%)
RAIN_PROBABILITY_THRESHOLDS: Dict[str, float] = {
    "low_max": 30.0,         # <= 30%: Low probability
    "moderate_max": 65.0,    # 31% - 65%: Moderate rain likelihood
    # > 65%: High rain likelihood (reduced visibility)
}

# Lightning Risk Weights
LIGHTNING_RISK_SCORES: Dict[str, int] = {
    "none": 0,
    "low": 1,
    "moderate": 2,
    "high": 3,
    "severe": 4,
}

# Sea State Risk Mapping
SEA_STATE_SCORES: Dict[str, int] = {
    "calm": 0,
    "smooth": 0,
    "slight": 1,
    "moderate": 2,
    "rough": 3,
    "very_rough": 4,
    "high": 5,
}

# Proximity to Restricted Maritime Zone (km)
RESTRICTED_ZONE_THRESHOLDS: Dict[str, float] = {
    "buffer_warning_km": 3.0,   # Within 3 km of boundary triggers warning
    "inside_penalty_score": 8.0, # Inside restricted zone immediately triggers HIGH/CRITICAL risk
}

# Overall Risk Level Mapping from Composite Score (0 - 10+)
RISK_LEVEL_CUTOFFS = [
    (3.0, "LOW"),
    (6.0, "MODERATE"),
    (9.0, "HIGH"),
    (999, "CRITICAL"),
]

# Vessel Seaworthiness Profiles (M4)
# Configurable prototype/demo parameters for research and demonstration purposes only.
# NOT official maritime regulations, statutory safety requirements, or authoritative seaworthiness limits.
PROTOTYPE_PARAMETER_NOTICE = (
    "Configurable prototype/demo parameter for research and demonstration only; "
    "not an official maritime regulation or authoritative seaworthiness limit."
)

VESSEL_PROFILES: Dict[str, Dict[str, Any]] = {
    "traditional_craft": {
        "vessel_type": "traditional_craft",
        "name": "Artisanal Traditional Craft",
        "name_ml": "പരമ്പരാഗത വള്ളം (തടി/കട്ടമരം)",
        "description": "Non-motorized dugout canoe, catamaran, or plank-built craft (< 8 meters).",
        "parameter_notice": PROTOTYPE_PARAMETER_NOTICE,
        "wave_max_safe": 1.0,
        "wave_max_moderate": 1.5,
        "wind_max_safe": 20.0,
        "wind_max_moderate": 28.0,
        "cruising_speed_knots": 3.5,
        "fuel_consumption_l_per_hour": 0.0,
        "fuel_type": "Manual / Sail",
        "fuel_estimate_note": "Non-motorized craft (zero fuel consumption; configurable prototype parameter)."
    },
    "motorized_frp_obm": {
        "vessel_type": "motorized_frp_obm",
        "name": "Motorized FRP Canoe (OBM)",
        "name_ml": "മോട്ടോർ ഘടിപ്പിച്ച എഫ്.ആർ.പി വള്ളം (OBM)",
        "description": "Fiberglass reinforced plastic (FRP) canoe (8–10 meters) with 9.9–25 HP outboard motor.",
        "parameter_notice": PROTOTYPE_PARAMETER_NOTICE,
        "wave_max_safe": 1.6,
        "wave_max_moderate": 2.2,
        "wind_max_safe": 30.0,
        "wind_max_moderate": 38.0,
        "cruising_speed_knots": 7.5,
        "fuel_consumption_l_per_hour": 6.5,
        "fuel_type": "Kerosene / Petrol Mix",
        "fuel_estimate_note": "Demonstration/prototype estimate (~6.5 L/hr nominal at cruising throttle; not authoritative fuel planning)."
    },
    "mechanized_trawler": {
        "vessel_type": "mechanized_trawler",
        "name": "Mechanized Trawler / Ring Seiner",
        "name_ml": "യന്ത്രവൽകൃത ബോട്ട് / ട്രോളർ",
        "description": "Inboard diesel mechanized fishing vessel (10–25 meters) with forward wheelhouse.",
        "parameter_notice": PROTOTYPE_PARAMETER_NOTICE,
        "wave_max_safe": 2.5,
        "wave_max_moderate": 3.2,
        "wind_max_safe": 42.0,
        "wind_max_moderate": 52.0,
        "cruising_speed_knots": 9.0,
        "fuel_consumption_l_per_hour": 18.0,
        "fuel_type": "High Speed Marine Diesel",
        "fuel_estimate_note": "Demonstration/prototype estimate (~18.0 L/hr nominal inboard diesel consumption; not authoritative fuel planning)."
    }
}

# Routing & Obstacle Clearance Parameters (M4)
ROUTING_CONFIG: Dict[str, Any] = {
    "default_clearance_buffer_km": 1.5,     # Configurable safety margin around restricted boundaries
    "waypoint_spacing_resolution_deg": 0.015, # Geometric search resolution (~1.6 km)
    "nautical_mile_km": 1.852,               # Standard 1 International Nautical Mile = 1.852 km
    "fuel_disclaimer": "Demonstration/prototype estimate based on nominal calm-water cruising consumption. Not official maritime navigation guidance or authoritative reserve planning."
}


def get_vessel_profile(vessel_type: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retrieve extensible vessel profile definition by key."""
    if not vessel_type:
        return None
    key = str(vessel_type).lower().strip()
    return VESSEL_PROFILES.get(key)

