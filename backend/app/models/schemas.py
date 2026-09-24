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
    compare_windows: Optional[List[str]] = None
    radius_km: Optional[float] = None
    target_ordinal: Optional[int] = None
    compare_targets: Optional[List[int]] = None
    clarification_reason: Optional[str] = None


class WeatherData(BaseModel):
    source: str = "MOCK_WEATHER_DATA"
    location: str = "Kochi"
    forecast_time: str = "tomorrow_morning"
    forecast_timestamp: Optional[str] = None
    retrieved_at: Optional[str] = None
    wind_speed_kmh: float
    wind_direction_deg: Optional[float] = 270.0
    rain_probability: float
    lightning_risk: str = "unsupported"
    weather_alert: Optional[str] = None
    weather_condition: Optional[str] = None
    temperature_c: Optional[float] = 29.0
    visibility_km: Optional[float] = None
    is_mock: bool = True
    units: Optional[Dict[str, Dict[str, Any]]] = None
    raw_metadata: Optional[Dict[str, Any]] = None


class OceanData(BaseModel):
    source: str = "MOCK_OCEAN_DATA"
    location: str = "Kochi Offshore"
    forecast_time: Optional[str] = None
    forecast_timestamp: Optional[str] = None
    retrieved_at: Optional[str] = None
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
    units: Optional[Dict[str, Dict[str, Any]]] = None
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


class PFZComparisonResult(BaseModel):
    target_a: NearestPFZ
    target_b: NearestPFZ
    closer_target: str
    distance_difference_km: float
    bearing_difference_deg: Optional[float] = None
    depth_comparison: str
    geofence_status_a: str  # CLEAR or INTERSECTS_RESTRICTED_ZONE
    geofence_status_b: str  # CLEAR or INTERSECTS_RESTRICTED_ZONE
    intersected_zones_a: List[str] = Field(default_factory=list)
    intersected_zones_b: List[str] = Field(default_factory=list)
    direct_route_intersects_a: bool = False
    direct_route_intersects_b: bool = False
    unavailable_fields: List[str] = Field(
        default_factory=lambda: [
            "sst_c (not in snapshot)",
            "chlorophyll_mg_m3 (not in snapshot)",
            "target_species (not in snapshot)",
            "confidence_score (not in snapshot)",
            "fish_abundance (not in snapshot)",
            "real_time_validity (historical snapshot)"
        ]
    )
    disclaimer: str = (
        "Historical INCOIS landing-centre-associated PFZ target comparison — not a live fishing advisory. "
        "Proximity does not imply biological suitability or present-day fishing potential."
    )


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
    candidate_pfzs: List[NearestPFZ] = Field(default_factory=list)
    pfz_comparison: Optional[PFZComparisonResult] = None
    direct_route_geofence_status: Optional[str] = None
    direct_route_intersected_zones: List[str] = Field(default_factory=list)
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


class TimeWindowMetrics(BaseModel):
    time_window: str
    wind_speed_kmh: float
    wind_direction_deg: float
    wave_height_m: float
    sea_state: str
    rain_probability: float
    risk_score: float
    risk_level: str
    source_weather: str
    source_ocean: str


class TemporalComparisonResult(BaseModel):
    evaluation_point: LocationCoords
    window_1: TimeWindowMetrics
    window_2: TimeWindowMetrics
    delta_wind_kmh: float
    delta_wave_m: float
    delta_rain_pct: float
    delta_risk_score: float
    trend: str  # IMPROVING, DETERIORATING, STABLE, INDETERMINATE
    recommendation: str
    tolerances_applied: Dict[str, float] = Field(default_factory=dict)
    provenance_notice: str = "Derived calculation comparing forecast horizons at evaluation point."


class RouteRiskAssessment(BaseModel):
    prototype_route_risk_index: float  # 0.0 - 10.0
    risk_level: str                    # LOW, MODERATE, HIGH, CRITICAL
    evaluation_point: LocationCoords
    vessel_type: Optional[str] = None
    wave_stress_ratio: float
    wind_stress_ratio: float
    factor_breakdown: Dict[str, float] = Field(default_factory=dict)
    limiting_factor: str
    reasons: List[str] = Field(default_factory=list)
    disclaimer: str


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
    candidate_pfzs: List[NearestPFZ] = Field(default_factory=list)
    compared_pfzs: Optional[List[NearestPFZ]] = None
    pfz_comparison: Optional[PFZComparisonResult] = None
    active_route: Optional[TransitRoute] = None
    temporal_comparison: Optional[TemporalComparisonResult] = None
    route_risk: Optional[RouteRiskAssessment] = None
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
    temporal_comparison: Optional[TemporalComparisonResult] = None
    route_risk: Optional[RouteRiskAssessment] = None
    candidate_pfzs: List[NearestPFZ] = Field(default_factory=list)
    pfz_comparison: Optional[PFZComparisonResult] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    agent_trace: List[str] = Field(default_factory=list)
    spatial_features: Optional[Dict[str, Any]] = None
    context: Optional[ConversationContext] = None
