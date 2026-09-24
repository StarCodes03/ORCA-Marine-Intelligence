import React from 'react';
import {
  Navigation,
  Anchor,
  ShieldAlert,
  AlertTriangle,
  ArrowRight,
  Info,
  Clock,
  Fuel,
  Compass,
  MessageSquare
} from 'lucide-react';
import { MarineMap } from '../map/MarineMap';
import {
  type LocationCoords,
  type NearestPFZ,
  type ChatResponse,
  CANONICAL_VESSEL_PROFILES
} from '../services/api';

interface RouteSafetyDashboardProps {
  vesselLocation: LocationCoords;
  nearestPfz: NearestPFZ | null;
  spatialLayers: any;
  latestResponse?: ChatResponse | null;
  selectedVessel: string;
  onVesselChange: (vessel: string) => void;
  onNavigateToChat?: () => void;
  onSelectPfz?: (pfz: NearestPFZ) => void;
}

export const RouteSafetyDashboard: React.FC<RouteSafetyDashboardProps> = ({
  vesselLocation,
  nearestPfz,
  spatialLayers,
  latestResponse,
  selectedVessel,
  onVesselChange,
  onNavigateToChat,
  onSelectPfz,
}) => {
  const canonical = CANONICAL_VESSEL_PROFILES[selectedVessel] || CANONICAL_VESSEL_PROFILES['motorized_frp_obm'];
  const profile = (latestResponse?.vessel_profile && latestResponse.vessel_profile.vessel_type === selectedVessel)
    ? { ...canonical, ...latestResponse.vessel_profile }
    : canonical;

  // Conditional active route check: ONLY use existing calculated route, DO NOT fabricate
  const activeRoute = latestResponse?.transit_route || latestResponse?.context?.active_route || null;

  // Route risk calculation or standard risk assessment
  const routeRisk = latestResponse?.route_risk || latestResponse?.context?.route_risk || null;
  const standardRisk = latestResponse?.risk || null;

  return (
    <div className="workspace-pane route-workspace-pane">
      {/* Top Header */}
      <div className="workspace-header">
        <div className="workspace-header-title">
          <Navigation size={17} color="#06b6d4" />
          <span>ROUTE & SAFETY INTELLIGENCE</span>
          <span className="workspace-header-badge">PASSAGE PLANNING</span>
        </div>
        <div className="workspace-header-meta">
          <span>Configurable 1.5 km Buffer Corridor • Prototype Decision Support</span>
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="route-dashboard-grid">
        {/* Left Column: Vessel Profile & Prototype Route Risk Index */}
        <div className="route-left-column">
          {/* Vessel Profile Card */}
          <div className="route-card vessel-profile-card">
            <div className="route-card-header">
              <div className="route-card-title">
                <Anchor size={14} color="#38bdf8" />
                <span>VESSEL SPECIFICATION & SEAWORTHINESS</span>
              </div>
              <span className="prototype-badge">PROTOTYPE LIMITS</span>
            </div>

            {/* Vessel Category Selector */}
            <div className="vessel-select-pills">
              {Object.entries(CANONICAL_VESSEL_PROFILES).map(([key, v]) => (
                <button
                  key={key}
                  type="button"
                  className={`vessel-pill-btn ${selectedVessel === key ? 'active' : ''}`}
                  onClick={() => onVesselChange(key)}
                >
                  <span>{v.icon}</span>
                  <span>{v.name.split('(')[0].trim()}</span>
                </button>
              ))}
            </div>

            <div className="vessel-specs-table">
              <div className="vessel-spec-row">
                <span className="spec-label">Craft Profile:</span>
                <span className="spec-value highlight">{profile.name}</span>
              </div>
              <div className="vessel-spec-row">
                <span className="spec-label">Safe Wave Limit:</span>
                <span className="spec-value">&le; {profile.wave_max_safe} m</span>
              </div>
              <div className="vessel-spec-row">
                <span className="spec-label">Safe Wind Limit:</span>
                <span className="spec-value">&le; {profile.wind_max_safe} km/h (~{(profile.wind_max_safe / 1.852).toFixed(1)} kts)</span>
              </div>
              <div className="vessel-spec-row">
                <span className="spec-label">Nominal Cruising Speed:</span>
                <span className="spec-value">{profile.cruising_speed_knots} knots (~{(profile.cruising_speed_knots * 1.852).toFixed(1)} km/h)</span>
              </div>
              <div className="vessel-spec-row">
                <span className="spec-label">Nominal Fuel Rate:</span>
                <span className="spec-value">{profile.fuel_consumption_l_per_hour} L/h ({profile.fuel_type})</span>
              </div>
            </div>

            <div className="card-disclaimer-subtle">
              <Info size={11} color="#94a3b8" />
              <span>Configurable prototype demonstration parameters — not official maritime seaworthiness certifications.</span>
            </div>
          </div>

          {/* Prototype Route Risk Index Card */}
          <div className="route-card risk-meter-card">
            <div className="route-card-header">
              <div className="route-card-title">
                <ShieldAlert size={14} color="#f59e0b" />
                <span>PROTOTYPE ROUTE RISK INDEX (0–10)</span>
              </div>
              {routeRisk ? (
                <span className={`risk-pill ${routeRisk.risk_level}`}>
                  {routeRisk.risk_level}
                </span>
              ) : standardRisk ? (
                <span className={`risk-pill ${standardRisk.risk_level}`}>
                  OVERALL: {standardRisk.risk_level}
                </span>
              ) : (
                <span className="risk-pill LOW">BASELINE</span>
              )}
            </div>

            {routeRisk ? (
              <div className="risk-assessment-body">
                <div className="risk-score-display">
                  <div className="score-big">{routeRisk.prototype_route_risk_index.toFixed(1)}</div>
                  <div className="score-meta">
                    <div className="score-label">ROUTE RISK SCORE</div>
                    <div className="score-range">0.0 (Optimal) — 10.0 (Severe Hazard)</div>
                  </div>
                </div>

                <div className="risk-breakdown-section">
                  <div className="breakdown-title">DETERMINISTIC 4-FACTOR BREAKDOWN</div>
                  <div className="breakdown-grid">
                    {Object.entries(routeRisk.factor_breakdown).map(([factor, val]) => (
                      <div key={factor} className="factor-item">
                        <span className="factor-name">{factor.replace(/_/g, ' ')}</span>
                        <span className="factor-bar-wrapper">
                          <span
                            className="factor-bar-fill"
                            style={{ width: `${Math.min(100, (Number(val) / 3.0) * 100)}%` }}
                          />
                        </span>
                        <span className="factor-val">{Number(val).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {routeRisk.limiting_factor && (
                  <div className="limiting-factor-box">
                    <strong>Primary Limiting Factor:</strong> {routeRisk.limiting_factor.replace(/_/g, ' ')}
                  </div>
                )}
              </div>
            ) : (
              <div className="risk-standby-body">
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                  {standardRisk ? (
                    <>
                      Assessed Marine Risk: <strong>{standardRisk.risk_level}</strong> (Score {standardRisk.risk_score}/10).
                      {standardRisk.reasons && standardRisk.reasons.length > 0 && (
                        <div style={{ marginTop: '6px', fontSize: '0.74rem', color: '#94a3b8' }}>
                          Limiting factors: {standardRisk.reasons.join(', ')}
                        </div>
                      )}
                    </>
                  ) : (
                    'No active route calculation in this session yet. Ask ORCA in Chat or select a PFZ target to compute the 4-factor Route Risk Index.'
                  )}
                </div>
              </div>
            )}

            <div className="card-disclaimer-subtle alert">
              <AlertTriangle size={11} color="#f59e0b" />
              <span>
                Environmental condition risk evaluates the selected time/location conditions. The Prototype Route Risk Index additionally evaluates route exposure, vessel stress, distance and geofence interaction. It is a configurable prototype decision-support metric and is NOT an official maritime safety rating, seaworthiness certification, or regulatory limit.
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Safe Passage Corridor & Interactive Route Map */}
        <div className="route-right-column">
          {activeRoute ? (
            /* Active Route Display */
            <div className="route-card active-route-card">
              <div className="route-card-header">
                <div className="route-card-title">
                  <Navigation size={14} color="#10b981" />
                  <span>SAFE PASSAGE CORRIDOR SUMMARY</span>
                </div>
                <span className={`status-badge ${activeRoute.geofence_avoidance_applied ? 'avoidance' : 'direct'}`}>
                  {activeRoute.geofence_avoidance_applied ? 'COLLISION AVOIDANCE ACTIVE' : 'DIRECT TRANSIT'}
                </span>
              </div>

              {/* Corridor Metrics */}
              <div className="corridor-metrics-strip">
                <div className="corridor-metric-box">
                  <Compass size={14} color="#38bdf8" />
                  <div>
                    <div className="metric-lbl">TOTAL DISTANCE</div>
                    <div className="metric-val">{activeRoute.total_distance_km} km ({activeRoute.total_distance_nm} nm)</div>
                  </div>
                </div>
                <div className="corridor-metric-box">
                  <Clock size={14} color="#10b981" />
                  <div>
                    <div className="metric-lbl">ESTIMATED DURATION</div>
                    <div className="metric-val">~{activeRoute.estimated_duration_hours} hours</div>
                  </div>
                </div>
                <div className="corridor-metric-box">
                  <Fuel size={14} color="#f59e0b" />
                  <div>
                    <div className="metric-lbl">ESTIMATED FUEL BURN</div>
                    <div className="metric-val">~{activeRoute.estimated_fuel_litres} L ({activeRoute.fuel_type || 'Fuel'})</div>
                  </div>
                </div>
              </div>

              {/* Clearance Buffer Notice */}
              <div className="corridor-buffer-notice">
                <span>Deterministic Line/Polygon clearance buffer: <strong>{activeRoute.clearance_buffer_km} km</strong> around restricted security zones.</span>
              </div>

              {/* Waypoints Sequence */}
              <div className="corridor-waypoints-box">
                <div className="waypoints-title">TRANSIT CORRIDOR WAYPOINTS:</div>
                <div className="waypoints-chain">
                  <span className="wp-node origin">Origin ({activeRoute.origin.name})</span>
                  {activeRoute.waypoints.map((wp, idx) => (
                    <React.Fragment key={idx}>
                      <ArrowRight size={12} color="#64748b" />
                      <span className="wp-node clearance">
                        WP-{idx + 1}: {wp.name} ({wp.latitude.toFixed(3)}°N, {wp.longitude.toFixed(3)}°E)
                      </span>
                    </React.Fragment>
                  ))}
                  <ArrowRight size={12} color="#64748b" />
                  <span className="wp-node destination">Target ({activeRoute.destination.name})</span>
                </div>
              </div>

              {/* Route Alternatives Comparison */}
              {activeRoute.alternatives && activeRoute.alternatives.length > 0 && (
                <div className="route-alternatives-section" style={{ margin: '12px 0' }}>
                  <div className="waypoints-title" style={{ marginBottom: '8px' }}>
                    ROUTE ALTERNATIVES COMPARISON ({activeRoute.alternatives.length} OPTIONS):
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px' }}>
                    {activeRoute.alternatives.map((alt) => (
                      <div
                        key={alt.alternative_id}
                        style={{
                          background: alt.is_recommended ? 'rgba(16, 185, 129, 0.12)' : 'rgba(15, 23, 42, 0.6)',
                          border: `1px solid ${alt.is_recommended ? '#10b981' : alt.intersects_restricted_zone ? '#ef4444' : '#334155'}`,
                          borderRadius: '6px',
                          padding: '10px',
                          fontSize: '0.78rem',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '4px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong style={{ color: alt.is_recommended ? '#34d399' : '#f1f5f9' }}>{alt.name}</strong>
                          {alt.is_recommended && (
                            <span style={{ background: '#10b981', color: '#0f172a', fontWeight: 700, fontSize: '0.65rem', padding: '2px 6px', borderRadius: '4px' }}>
                              RECOMMENDED
                            </span>
                          )}
                          {alt.intersects_restricted_zone && (
                            <span style={{ background: '#ef4444', color: '#ffffff', fontWeight: 600, fontSize: '0.65rem', padding: '2px 6px', borderRadius: '4px' }}>
                              INTERSECTS ZONE
                            </span>
                          )}
                        </div>
                        <div style={{ color: '#cbd5e1', fontSize: '0.74rem' }}>
                          <span>{alt.total_distance_km} km ({alt.total_distance_nm} nm)</span> • <span>~{alt.estimated_duration_hours} h</span> • <span>~{alt.estimated_fuel_litres ?? 0} L</span>
                        </div>
                        {alt.route_risk_index !== null && alt.route_risk_index !== undefined && (
                          <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                            Route Risk Index: <strong>{alt.route_risk_index.toFixed(1)}</strong> ({alt.route_risk_level || 'LOW'})
                          </div>
                        )}
                        {alt.recommendation_reason && (
                          <div style={{ fontSize: '0.7rem', color: '#6ee7b7', fontStyle: 'italic', marginTop: '2px' }}>
                            {alt.recommendation_reason}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Environmental Discrete Sampling Limitation Disclaimer */}
              {activeRoute.evaluation_limitation && (
                <div className="card-disclaimer-subtle alert" style={{ margin: '8px 0', border: '1px solid #0284c7', background: 'rgba(2, 132, 199, 0.1)' }}>
                  <Info size={12} color="#38bdf8" />
                  <span style={{ color: '#bae6fd' }}>{activeRoute.evaluation_limitation}</span>
                </div>
              )}

              {/* Embedded Route Visualization Map */}
              <div className="embedded-route-map">
                <MarineMap
                  vesselLocation={vesselLocation}
                  nearestPfz={nearestPfz}
                  spatialLayers={spatialLayers}
                  highlightRoute={true}
                  transitRoute={activeRoute}
                  showVessel={true}
                  showPfz={true}
                  showRestricted={true}
                  showRoute={true}
                  onSelectPfz={onSelectPfz}
                  hideFloatingLegend={false}
                />
              </div>

              <div className="card-disclaimer-subtle">
                <Info size={11} color="#94a3b8" />
                <span>{activeRoute.fuel_estimate_note || 'Fuel consumption is a demonstration estimate calculated at nominal calm-water cruising speed and must not replace onboard reserve planning.'}</span>
              </div>
            </div>
          ) : (
            /* Clean Empty State: Explicitly required by user when no active route exists */
            <div className="route-card route-empty-state-card">
              <div className="empty-state-icon-box">
                <Navigation size={38} color="#334e7d" />
              </div>
              <h3 className="empty-state-title">No Active Route</h3>
              <p className="empty-state-description">
                Select a destination or calculate a route from Chat or Marine Intelligence to view passage planning, corridor clearance waypoints, and fuel estimates.
              </p>
              {onNavigateToChat && (
                <button
                  type="button"
                  className="empty-state-action-btn"
                  onClick={onNavigateToChat}
                >
                  <MessageSquare size={14} />
                  <span>Ask ORCA to Plan Route in Chat</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
