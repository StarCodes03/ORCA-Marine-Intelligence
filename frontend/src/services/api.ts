/**
 * ORCA Marine Intelligence API Client
 */

export interface LocationCoords {
  name: string;
  latitude: number;
  longitude: number;
}

export type DataSourceStatus = 'LIVE' | 'DEMO / MOCK' | 'MOCK FALLBACK' | 'UNAVAILABLE' | 'UNSUPPORTED' | 'OFFICIAL SNAPSHOT' | 'READY';

export type GlobalSourceStatus = 'READY' | 'LIVE (HYBRID)' | 'MOCK FALLBACK' | 'OFFICIAL SNAPSHOT' | 'DEMO / MOCK';

export interface UnitMetadata {
  value: number | string | null;
  unit: string;
}

export interface WeatherData {
  source: string;
  location: string;
  forecast_time: string;
  forecast_timestamp?: string | null;
  retrieved_at?: string | null;
  wind_speed_kmh: number;
  wind_direction_deg?: number;
  rain_probability: number;
  lightning_risk: string;
  weather_alert?: string | null;
  weather_condition?: string | null;
  temperature_c?: number;
  visibility_km?: number | null;
  is_mock: boolean;
  is_fallback?: boolean;
  units?: Record<string, UnitMetadata> | null;
  raw_metadata?: Record<string, any> | null;
}

export interface OceanData {
  source: string;
  location: string;
  forecast_time?: string;
  forecast_timestamp?: string | null;
  retrieved_at?: string | null;
  sst_c: number;
  wave_height_m: number;
  sea_state: string;
  tide: string;
  chlorophyll_mg_m3?: number | null;
  salinity_psu?: number;
  current_speed_knots?: number;
  current_direction_deg?: number;
  wave_period_s?: number;
  wave_direction_deg?: number;
  sea_level_height_m?: number | null;
  tide_note?: string | null;
  is_mock: boolean;
  is_fallback?: boolean;
  units?: Record<string, UnitMetadata> | null;
  raw_metadata?: Record<string, any> | null;
}

export function deriveGlobalSourceStatus(
  latestResponse?: ChatResponse | null,
  hasQueried: boolean = false
): GlobalSourceStatus {
  // 1. Before first successful query/response, return neutral READY state
  if (!hasQueried || !latestResponse) {
    return 'READY';
  }

  // Validate that response contains actual completed intelligence
  const hasValidResponse = Boolean(
    latestResponse.answer ||
    (latestResponse.agent_trace && latestResponse.agent_trace.length > 0) ||
    latestResponse.intent
  );
  if (!hasValidResponse) {
    return 'READY';
  }

  const weather = latestResponse.weather;
  const ocean = latestResponse.ocean;
  const geospatial = latestResponse.geospatial;

  // 2. MOCK FALLBACK: only when a live adapter actually failed and the response indicates fallback
  const isWeatherFallback = Boolean(
    weather && weather.is_mock && (weather.is_fallback || weather.raw_metadata?.is_fallback)
  );
  const isOceanFallback = Boolean(
    ocean && ocean.is_mock && (ocean.is_fallback || ocean.raw_metadata?.is_fallback)
  );
  const isGisFallback = Boolean(
    geospatial && (geospatial.source_type === 'MOCK_FALLBACK' || (geospatial.is_mock && geospatial.source !== 'INCOIS'))
  );

  if (isWeatherFallback || isOceanFallback || isGisFallback) {
    return 'MOCK FALLBACK';
  }

  // 3. LIVE (HYBRID): when live Open-Meteo weather or marine data is active
  const isWeatherLive = Boolean(weather && !weather.is_mock && weather.source === 'OPEN_METEO_WEATHER');
  const isOceanLive = Boolean(ocean && !ocean.is_mock && ocean.source === 'OPEN_METEO_MARINE');

  if (isWeatherLive || isOceanLive) {
    return 'LIVE (HYBRID)';
  }

  // 4. OFFICIAL SNAPSHOT: where appropriate for PFZ-only provenance (no live weather/ocean invoked)
  const isGisSnapshot = Boolean(geospatial && geospatial.source_type === 'OFFICIAL_SNAPSHOT');
  if (isGisSnapshot) {
    return 'OFFICIAL SNAPSHOT';
  }

  // 5. DEMO / MOCK: if explicit mock demonstration data was returned
  if (weather?.is_mock || ocean?.is_mock || geospatial?.is_mock) {
    return 'DEMO / MOCK';
  }

  return 'READY';
}

export function deriveWeatherStatus(weather?: WeatherData | null, hasQueried: boolean = false): DataSourceStatus {
  if (!weather) {
    return hasQueried ? 'UNAVAILABLE' : 'READY';
  }
  const src = (weather.source || '').toUpperCase();
  if ((src.includes('OPEN_METEO') || src.includes('OPEN-METEO')) && !weather.is_mock) {
    return 'LIVE';
  }
  if (weather.is_mock) {
    if (weather.raw_metadata?.is_fallback || weather.is_fallback) {
      return 'MOCK FALLBACK';
    }
    return 'DEMO / MOCK';
  }
  return 'UNAVAILABLE';
}

export function deriveOceanStatus(ocean?: OceanData | null, hasQueried: boolean = false): DataSourceStatus {
  if (!ocean) {
    return hasQueried ? 'UNAVAILABLE' : 'READY';
  }
  const src = (ocean.source || '').toUpperCase();
  if ((src.includes('OPEN_METEO') || src.includes('OPEN-METEO')) && !ocean.is_mock) {
    return 'LIVE';
  }
  if (ocean.is_mock) {
    if (ocean.raw_metadata?.is_fallback || ocean.is_fallback) {
      return 'MOCK FALLBACK';
    }
    return 'DEMO / MOCK';
  }
  return 'UNAVAILABLE';
}

export function deriveGisStatus(geospatial?: GeospatialData | null, hasQueried: boolean = false): DataSourceStatus {
  if (!geospatial) {
    return hasQueried ? 'OFFICIAL SNAPSHOT' : 'READY';
  }
  if (geospatial.source_type === 'OFFICIAL_SNAPSHOT') {
    return 'OFFICIAL SNAPSHOT';
  }
  if (geospatial.source_type === 'MOCK_FALLBACK' || (geospatial.is_mock && geospatial.source !== 'INCOIS')) {
    return 'MOCK FALLBACK';
  }
  if (geospatial.is_mock || geospatial.source === 'DEMO_GIS_DATA') {
    return 'DEMO / MOCK';
  }
  return 'OFFICIAL SNAPSHOT';
}

export function deriveLightningStatus(weather?: WeatherData | null, hasQueried: boolean = false): DataSourceStatus {
  if (!hasQueried) return 'READY';
  if (weather?.is_mock) {
    return (weather.raw_metadata?.is_fallback || weather.is_fallback)
      ? 'MOCK FALLBACK'
      : 'DEMO / MOCK';
  }
  return 'UNSUPPORTED';
}

export function deriveChlorophyllStatus(ocean?: OceanData | null, hasQueried: boolean = false): DataSourceStatus {
  if (!hasQueried) return 'READY';
  if (!ocean || ocean.chlorophyll_mg_m3 == null) {
    return 'UNAVAILABLE';
  }
  if (ocean.is_mock) {
    return (ocean.raw_metadata?.is_fallback || ocean.is_fallback)
      ? 'MOCK FALLBACK'
      : 'DEMO / MOCK';
  }
  return 'LIVE';
}

export interface NearestPFZ {
  pfz_id: string;
  name: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  bearing_deg?: number;
  direction?: string;
  depth_m?: number;
  sst_c?: number;
  chlorophyll_mg_m3?: number;
  target_species?: string;
  confidence_score?: number;
  landing_centre?: string;
  source?: string;
  source_type?: string;
}

export interface RestrictedZoneCheck {
  restricted_zone_nearby: boolean;
  inside_restricted_zone: boolean;
  zone_name?: string | null;
  zone_id?: string | null;
  distance_to_nearest_zone_km?: number | null;
}

export interface PFZComparisonResult {
  target_a: NearestPFZ;
  target_b: NearestPFZ;
  closer_target: string;
  distance_difference_km: number;
  bearing_difference_deg?: number | null;
  depth_comparison: string;
  geofence_status_a: string;
  geofence_status_b: string;
  intersected_zones_a: string[];
  intersected_zones_b: string[];
  direct_route_intersects_a: boolean;
  direct_route_intersects_b: boolean;
  unavailable_fields: string[];
  disclaimer: string;
}

export interface GeospatialData {
  source: string;
  source_type?: string;
  advisory_date?: string | null;
  valid_until?: string | null;
  is_live?: boolean;
  user_location: LocationCoords;
  nearest_pfz?: NearestPFZ | null;
  all_pfzs: NearestPFZ[];
  restricted_zone_check: RestrictedZoneCheck;
  is_mock: boolean;
}

export interface RiskEvidenceItem {
  metric: string;
  value: any;
  threshold: string;
  contribution: number | string;
  source: string;
}

export interface ScoreFactorItem {
  factor: string;
  metric: string;
  value: any;
  threshold: string;
  contribution: number;
}

export interface ScoreBreakdown {
  factors: ScoreFactorItem[];
  factor_scores: Record<string, number>;
  total_score: number;
}

export interface RiskAssessment {
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  risk_score: number;
  reasons: string[];
  evidence: RiskEvidenceItem[];
  score_breakdown?: ScoreBreakdown | null;
}

export interface EvidenceItem {
  category: string;
  claim: string;
  source: string;
  timestamp?: string;
  raw_data?: Record<string, any>;
}

export interface RouteRiskAssessment {
  prototype_route_risk_index: number;
  risk_level: string;
  evaluation_point: LocationCoords;
  vessel_type?: string | null;
  wave_stress_ratio: number;
  wind_stress_ratio: number;
  factor_breakdown: Record<string, number>;
  limiting_factor: string;
  reasons: string[];
  disclaimer: string;
}

export interface TimeWindowMetrics {
  time_window: string;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  wave_height_m: number;
  sea_state: string;
  rain_probability: number;
  risk_score: number;
  risk_level: string;
  source_weather: string;
  source_ocean: string;
}

export interface TemporalComparisonResult {
  evaluation_point: LocationCoords;
  window_1: TimeWindowMetrics;
  window_2: TimeWindowMetrics;
  delta_wind_kmh: number;
  delta_wave_m: number;
  delta_rain_pct: number;
  delta_risk_score: number;
  trend: string;
  recommendation: string;
  tolerances_applied?: Record<string, number>;
  provenance_notice: string;
}

export interface VesselProfile {
  vessel_type: string;
  name: string;
  name_ml?: string;
  description?: string;
  parameter_notice?: string;
  wave_max_safe: number;
  wave_max_moderate: number;
  wind_max_safe: number;
  wind_max_moderate: number;
  cruising_speed_knots: number;
  fuel_consumption_l_per_hour: number;
  fuel_type: string;
  fuel_estimate_note?: string;
}

export interface CanonicalVesselProfile extends VesselProfile {
  icon: string;
}

export const CANONICAL_VESSEL_PROFILES: Record<string, CanonicalVesselProfile> = {
  traditional_craft: {
    vessel_type: 'traditional_craft',
    name: 'Artisanal Traditional Craft',
    name_ml: 'പരമ്പരാഗത വള്ളം (തടി/കട്ടമരം)',
    icon: '🛶',
    description: 'Non-motorized dugout canoe, catamaran, or plank-built craft (< 8 meters).',
    parameter_notice: 'Configurable prototype/demo parameter for research and demonstration only; not an official maritime regulation or authoritative seaworthiness limit.',
    wave_max_safe: 1.0,
    wave_max_moderate: 1.5,
    wind_max_safe: 20.0,
    wind_max_moderate: 28.0,
    cruising_speed_knots: 3.5,
    fuel_consumption_l_per_hour: 0.0,
    fuel_type: 'Manual / Sail',
    fuel_estimate_note: 'Non-motorized craft (zero fuel consumption; configurable prototype parameter).'
  },
  motorized_frp_obm: {
    vessel_type: 'motorized_frp_obm',
    name: 'Motorized FRP Canoe (OBM)',
    name_ml: 'മോട്ടോർ ഘടിപ്പിച്ച എഫ്.ആർ.പി വള്ളം (OBM)',
    icon: '🚤',
    description: 'Fiberglass reinforced plastic (FRP) canoe (8–10 meters) with 9.9–25 HP outboard motor.',
    parameter_notice: 'Configurable prototype/demo parameter for research and demonstration only; not an official maritime regulation or authoritative seaworthiness limit.',
    wave_max_safe: 1.6,
    wave_max_moderate: 2.2,
    wind_max_safe: 30.0,
    wind_max_moderate: 38.0,
    cruising_speed_knots: 7.5,
    fuel_consumption_l_per_hour: 6.5,
    fuel_type: 'Kerosene / Petrol Mix',
    fuel_estimate_note: 'Demonstration/prototype estimate (~6.5 L/hr nominal at cruising throttle; not authoritative fuel planning).'
  },
  mechanized_trawler: {
    vessel_type: 'mechanized_trawler',
    name: 'Mechanized Trawler / Ring Seiner',
    name_ml: 'യന്ത്രവൽകൃത ബോട്ട് / ട്രോളർ',
    icon: '🚢',
    description: 'Inboard diesel mechanized fishing vessel (10–25 meters) with forward wheelhouse.',
    parameter_notice: 'Configurable prototype/demo parameter for research and demonstration only; not an official maritime regulation or authoritative seaworthiness limit.',
    wave_max_safe: 2.5,
    wave_max_moderate: 3.2,
    wind_max_safe: 42.0,
    wind_max_moderate: 52.0,
    cruising_speed_knots: 9.0,
    fuel_consumption_l_per_hour: 18.0,
    fuel_type: 'High Speed Marine Diesel',
    fuel_estimate_note: 'Demonstration/prototype estimate (~18.0 L/hr nominal inboard diesel consumption; not authoritative fuel planning).'
  }
};

export interface TransitWaypoint {
  name: string;
  latitude: number;
  longitude: number;
  description?: string;
}

export interface RouteAlternative {
  alternative_id: string;
  name: string;
  total_distance_km: number;
  total_distance_nm: number;
  estimated_duration_hours: number;
  estimated_fuel_litres?: number | null;
  fuel_type?: string | null;
  intersects_restricted_zone: boolean;
  intersected_zones: string[];
  route_risk_index?: number | null;
  route_risk_level?: string | null;
  waypoints: TransitWaypoint[];
  geojson_feature: Record<string, any>;
  is_recommended: boolean;
  recommendation_reason?: string | null;
}

export interface TransitRoute {
  origin: LocationCoords;
  destination: NearestPFZ | LocationCoords;
  waypoints: TransitWaypoint[];
  total_distance_km: number;
  total_distance_nm: number;
  estimated_duration_hours: number;
  estimated_fuel_litres?: number | null;
  fuel_type?: string | null;
  geofence_avoidance_applied: boolean;
  avoided_zones: string[];
  clearance_buffer_km: number;
  geojson_feature: Record<string, any>;
  fuel_estimate_note: string;
  alternatives?: RouteAlternative[];
  environmental_evaluations?: Array<Record<string, any>>;
  evaluation_limitation?: string | null;
}

export interface ConversationContext {
  conversation_id: string;
  location?: LocationCoords | null;
  date?: string | null;
  time_window?: string | null;
  activity?: string | null;
  vessel_type?: string | null;
  language_mode?: string;
  last_intent?: string | null;
  selected_pfz?: NearestPFZ | null;
  candidate_pfzs?: NearestPFZ[] | null;
  compared_pfzs?: NearestPFZ[] | null;
  active_route?: TransitRoute | null;
  temporal_comparison?: TemporalComparisonResult | null;
  route_risk?: RouteRiskAssessment | null;
  turn_count: number;
  updated_at?: string | null;
}

export interface ChatResponse {
  answer: string;
  answer_ml?: string | null;
  intent: string;
  location?: LocationCoords | null;
  risk?: RiskAssessment | null;
  weather?: WeatherData | null;
  ocean?: OceanData | null;
  geospatial?: GeospatialData | null;
  transit_route?: TransitRoute | null;
  vessel_profile?: VesselProfile | null;
  temporal_comparison?: TemporalComparisonResult | null;
  route_risk?: RouteRiskAssessment | null;
  candidate_pfzs?: NearestPFZ[];
  pfz_comparison?: PFZComparisonResult | null;
  evidence: EvidenceItem[];
  agent_trace: string[];
  spatial_features?: {
    user_location?: LocationCoords | null;
    nearest_pfz?: NearestPFZ | null;
    all_pfzs: NearestPFZ[];
    restricted_zone_status?: RestrictedZoneCheck | null;
    route?: Record<string, any> | null;
  } | null;
  context?: ConversationContext | null;
  alerts?: Array<Record<string, any>>;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function checkHealth(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function getSpatialLayers(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/spatial/layers`);
  if (!res.ok) throw new Error('Failed to fetch spatial layers');
  return res.json();
}

export async function sendChatMessage(
  message: string,
  conversationId: string = 'demo-001',
  userLat?: number,
  userLon?: number,
  vesselType?: string,
  languageMode?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      user_latitude: userLat,
      user_longitude: userLon,
      vessel_type: vesselType,
      language_mode: languageMode
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Chat API error (${res.status}): ${errText}`);
  }

  return res.json();
}
