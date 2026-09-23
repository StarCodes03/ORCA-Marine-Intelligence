/**
 * ORCA Marine Intelligence API Client
 */

export interface LocationCoords {
  name: string;
  latitude: number;
  longitude: number;
}

export type DataSourceStatus = 'LIVE' | 'DEMO / MOCK' | 'MOCK FALLBACK' | 'UNAVAILABLE' | 'OFFICIAL SNAPSHOT';

export interface WeatherData {
  source: string;
  location: string;
  forecast_time: string;
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
  raw_metadata?: Record<string, any> | null;
}

export interface OceanData {
  source: string;
  location: string;
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
  raw_metadata?: Record<string, any> | null;
}

export function deriveWeatherStatus(weather?: WeatherData | null): DataSourceStatus {
  if (!weather) return 'DEMO / MOCK';
  if (weather.source === 'OPEN_METEO_WEATHER' && !weather.is_mock) {
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

export function deriveOceanStatus(ocean?: OceanData | null): DataSourceStatus {
  if (!ocean) return 'DEMO / MOCK';
  if (ocean.source === 'OPEN_METEO_MARINE' && !ocean.is_mock) {
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

export function deriveGisStatus(geospatial?: GeospatialData | null): DataSourceStatus {
  if (!geospatial) return 'OFFICIAL SNAPSHOT';
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

export function deriveLightningStatus(weather?: WeatherData | null): DataSourceStatus {
  if (!weather) return 'UNAVAILABLE';
  const val = (weather.lightning_risk || '').toLowerCase();
  if (val === 'unsupported' || val === 'unavailable' || val === 'n/a' || val === '') {
    return 'UNAVAILABLE';
  }
  if (weather.is_mock) {
    return (weather.raw_metadata?.is_fallback || weather.is_fallback)
      ? 'MOCK FALLBACK'
      : 'DEMO / MOCK';
  }
  return 'UNAVAILABLE';
}

export function deriveChlorophyllStatus(ocean?: OceanData | null): DataSourceStatus {
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
  raw_data?: Record<string, any>;
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

export interface TransitWaypoint {
  name: string;
  latitude: number;
  longitude: number;
  description?: string;
}

export interface TransitRoute {
  origin: LocationCoords;
  destination: NearestPFZ;
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
  active_route?: TransitRoute | null;
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
