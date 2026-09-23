"""ORCA Marine Intelligence - Pydantic Data Models and Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LocationCoords(BaseModel):
    name: str = "Kochi"
    latitude: float = 9.9312
    longitude: float = 76.2673


class PlannerOutput(BaseModel):
    intent: str = Field(
        description="Identified user intent, e.g. marine_safety, pfz_search, weather_query, general_marine"
    )
    location: Optional[LocationCoords] = None
    time_range: Optional[str] = None
    activity: Optional[str] = None
    vessel_type: Optional[str] = None
    language_mode: str = "bilingual"
    required_agents: List[str] = Field(
        default_factory=lambda: ["weather", "ocean", "geospatial"]
    )
    clarification_reason: Optional[str] = None


class WeatherData(BaseModel):
    source: str = "MOCK_WEATHER_DATA"
    location: str = "Kochi"
    forecast_time: str = "tomorrow_morning"
    wind_speed_kmh: float
    wind_direction_deg: Optional[float] = 270.0
    rain_probability: float
    lightning_risk: str = "unsupported"
    weather_alert: Optional[str] = None
    weather_condition: Optional[str] = None
    temperature_c: Optional[float] = 29.0
    visibility_km: Optional[float] = None
    is_mock: bool = True
    raw_metadata: Optional[Dict[str, Any]] = None


class OceanData(BaseModel):
    source: str = "MOCK_OCEAN_DATA"
    location: str = "Kochi Offshore"
    sst_c: float
    wave_height_m: float
    sea_state: str
    tide: str
    chlorophyll_mg_m3: Optional[float] = None
    salinity_psu: Optional[float] = 34.8
    current_speed_knots: Optional[float] = 1.2
    current_direction_deg: Optional[float] = None
    wave_period_s: Optional[float] = None
    wave_direction_deg: Optional[float] = None
    sea_level_height_m: Optional[float] = None
    tide_note: Optional[str] = None
    is_mock: bool = True
    raw_metadata: Optional[Dict[str, Any]] = None


class NearestPFZ(BaseModel):
    pfz_id: str
    name: str
    latitude: float
    longitude: float
    distance_km: float
    bearing_deg: Optional[float] = None
    depth_m: Optional[float] = None
    sst_c: Optional[float] = None
    chlorophyll_mg_m3: Optional[float] = None
    target_species: Optional[str] = None
    confidence_score: Optional[float] = None
    landing_centre: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None


class RestrictedZoneCheck(BaseModel):
    restricted_zone_nearby: bool = False
    inside_restricted_zone: bool = False
    zone_name: Optional[str] = None
    zone_id: Optional[str] = None
    distance_to_nearest_zone_km: Optional[float] = None


class GeospatialData(BaseModel):
    source: str = "INCOIS"
    source_type: str = "OFFICIAL_SNAPSHOT"
    advisory_date: Optional[str] = None
    valid_until: Optional[str] = None
    is_live: bool = False
    is_mock: bool = False
    user_location: LocationCoords
    nearest_pfz: Optional[NearestPFZ] = None
    all_pfzs: List[NearestPFZ] = Field(default_factory=list)
    restricted_zone_check: RestrictedZoneCheck = Field(default_factory=RestrictedZoneCheck)


class RiskEvidenceItem(BaseModel):
    metric: str
    value: Any
    threshold: str
    contribution: float = 0.0
    source: str


class ScoreFactorItem(BaseModel):
    factor: str
    metric: str
    value: Any
    threshold: str
    contribution: float


class ScoreBreakdown(BaseModel):
    factors: List[ScoreFactorItem] = Field(default_factory=list)
    factor_scores: Dict[str, float] = Field(default_factory=dict)
    total_score: float = 0.0


class RiskAssessment(BaseModel):
    risk_level: str = "LOW"  # LOW, MODERATE, HIGH, CRITICAL
    risk_score: float = 0.0
    vessel_type: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    evidence: List[RiskEvidenceItem] = Field(default_factory=list)
    score_breakdown: Optional[ScoreBreakdown] = None


class EvidenceItem(BaseModel):
    category: str  # observed, calculated, rule_evaluation, source_metadata
    claim: str
    source: str
    raw_data: Optional[Dict[str, Any]] = None


class VesselProfile(BaseModel):
    vessel_type: str
    name: str
    name_ml: Optional[str] = None
    description: Optional[str] = None
    parameter_notice: str = "Configurable prototype/demo parameter for research and demonstration only; not an official maritime regulation or authoritative seaworthiness limit."
    wave_max_safe: float
    wave_max_moderate: float
    wind_max_safe: float
    wind_max_moderate: float
    cruising_speed_knots: float
    fuel_consumption_l_per_hour: float
    fuel_type: str
    fuel_estimate_note: Optional[str] = None


class TransitWaypoint(BaseModel):
    name: str
    latitude: float
    longitude: float
    description: Optional[str] = None


class TransitRoute(BaseModel):
    origin: LocationCoords
    destination: NearestPFZ
    waypoints: List[TransitWaypoint] = Field(default_factory=list)
    total_distance_km: float
    total_distance_nm: float
    estimated_duration_hours: float
    estimated_fuel_litres: Optional[float] = None
    fuel_type: Optional[str] = None
    geofence_avoidance_applied: bool = False
    avoided_zones: List[str] = Field(default_factory=list)
    clearance_buffer_km: float = 1.5
    geojson_feature: Dict[str, Any] = Field(default_factory=dict)
    fuel_estimate_note: str = ""


class ConversationContext(BaseModel):
    conversation_id: str
    location: Optional[LocationCoords] = None
    date: Optional[str] = None
    time_window: Optional[str] = None
    activity: Optional[str] = None
    vessel_type: Optional[str] = None
    language_mode: str = "bilingual"
    last_intent: Optional[str] = None
    selected_pfz: Optional[NearestPFZ] = None
    active_route: Optional[TransitRoute] = None
    turn_count: int = 0
    updated_at: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "demo-001"
    user_latitude: Optional[float] = None
    user_longitude: Optional[float] = None
    vessel_type: Optional[str] = None
    language_mode: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    answer_ml: Optional[str] = None
    intent: str
    location: Optional[LocationCoords] = None
    risk: Optional[RiskAssessment] = None
    weather: Optional[WeatherData] = None
    ocean: Optional[OceanData] = None
    geospatial: Optional[GeospatialData] = None
    transit_route: Optional[TransitRoute] = None
    vessel_profile: Optional[VesselProfile] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    agent_trace: List[str] = Field(default_factory=list)
    spatial_features: Optional[Dict[str, Any]] = None
    context: Optional[ConversationContext] = None
