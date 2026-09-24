import React, { useState } from 'react';
import {
  Database,
  CloudSun,
  Waves,
  MapPin,
  Zap,
  Droplets,
  Cpu,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  Shield,
  Layers,
  Terminal,
  Clock,
  Navigation
} from 'lucide-react';
import {
  deriveWeatherStatus,
  deriveOceanStatus,
  deriveGisStatus,
  deriveLightningStatus,
  deriveChlorophyllStatus,
  type ChatResponse,
  type DataSourceStatus,
} from '../services/api';

interface DataEvidenceDashboardProps {
  latestResponse: ChatResponse | null;
}

const AGENT_PIPELINE_ORDER = [
  'PlannerAgent',
  'WeatherAgent',
  'OceanAgent',
  'GeospatialAgent',
  'RiskAssessmentAgent',
  'EvidenceAgent',
];

export const DataEvidenceDashboard: React.FC<DataEvidenceDashboardProps> = ({ latestResponse }) => {
  const [selectedAgent, setSelectedAgent] = useState<string>('PlannerAgent');

  const weather = latestResponse?.weather;
  const ocean = latestResponse?.ocean;
  const geospatial = latestResponse?.geospatial;
  const trace = latestResponse?.agent_trace || [];
  const evidence = latestResponse?.evidence || [];
  const context = latestResponse?.context || null;

  const weatherStatus: DataSourceStatus = deriveWeatherStatus(weather);
  const oceanStatus: DataSourceStatus = deriveOceanStatus(ocean);
  const gisStatus: DataSourceStatus = deriveGisStatus(geospatial);
  const lightningStatus: DataSourceStatus = deriveLightningStatus(weather);
  const chlorophyllStatus: DataSourceStatus = deriveChlorophyllStatus(ocean);

  const sources = [
    {
      id: 'weather',
      label: 'Atmospheric Weather',
      icon: <CloudSun size={15} />,
      status: weatherStatus,
      endpoint: 'Open-Meteo Weather API v1',
      parameters: 'wind_speed_10m, precipitation_probability, weather_code, temperature_2m',
      detail: weather?.retrieved_at
        ? `${weather.source || 'Open-Meteo'} (Retrieved: ${new Date(weather.retrieved_at).toLocaleTimeString()})`
        : weather?.source || (weatherStatus === 'LIVE' ? 'Open-Meteo Live' : 'Demonstration Mock'),
      coverage: 'Global / Kochi Coordinates (9.9312° N, 76.2673° E)',
    },
    {
      id: 'ocean',
      label: 'Oceanographic & Marine',
      icon: <Waves size={15} />,
      status: oceanStatus,
      endpoint: 'Open-Meteo Marine API v1',
      parameters: 'wave_height, wave_direction, wave_period, ocean_current_velocity, sea_surface_temperature',
      detail: ocean?.retrieved_at
        ? `${ocean.source || 'Open-Meteo Marine'} (Retrieved: ${new Date(ocean.retrieved_at).toLocaleTimeString()})`
        : ocean?.source || (oceanStatus === 'LIVE' ? 'Open-Meteo Marine Live' : 'Demonstration Mock'),
      coverage: 'Arabian Sea Offshore Grid',
    },
    {
      id: 'gis',
      label: 'PFZ / Geospatial Snapshots',
      icon: <MapPin size={15} />,
      status: gisStatus,
      endpoint: 'ESSO-INCOIS Advisory Archive',
      parameters: 'pfz_id, landing_centre, distance_km, bearing_deg, water_depth, direction',
      detail: gisStatus === 'OFFICIAL SNAPSHOT'
        ? `INCOIS Official Snapshot (${geospatial?.advisory_date?.split('T')[0] || 'Historical'})`
        : 'INCOIS Simulated GIS',
      coverage: 'Kerala Coastal Sector (Ernakulam / Kochi District)',
    },
    {
      id: 'lightning',
      label: 'Lightning Strike Risk',
      icon: <Zap size={15} />,
      status: lightningStatus,
      endpoint: 'N/A (Simulated telemetry field)',
      parameters: 'Derived or unsupported in free tier',
      detail: 'Unsupported by upstream free API; simulated fallback if enabled',
      coverage: 'Coastal sector',
    },
    {
      id: 'chlorophyll',
      label: 'Chlorophyll-a Biomass',
      icon: <Droplets size={15} />,
      status: chlorophyllStatus,
      endpoint: 'N/A (Ocean color sensor)',
      parameters: 'Remote sensing chlorophyll concentration',
      detail: 'Not provided in live open forecast feed; historical INCOIS model estimate',
      coverage: 'Offshore',
    },
  ];

  const getAgentPayload = (agentName: string) => {
    if (!latestResponse) return null;
    switch (agentName) {
      case 'PlannerAgent':
        return {
          intent: latestResponse.intent,
          location: latestResponse.location,
          detected_vessel: latestResponse.context?.vessel_type,
          language_mode: latestResponse.context?.language_mode,
          trace: latestResponse.agent_trace,
        };
      case 'WeatherAgent':
        return latestResponse.weather || { status: 'Not invoked for this query' };
      case 'OceanAgent':
        return latestResponse.ocean || { status: 'Not invoked for this query' };
      case 'GeospatialAgent':
        return {
          geospatial: latestResponse.geospatial || { status: 'Not invoked' },
          spatial_features: latestResponse.spatial_features || null,
          candidate_count: latestResponse.context?.candidate_pfzs?.length || 0,
        };
      case 'RiskAssessmentAgent':
        return {
          standard_risk: latestResponse.risk || null,
          prototype_route_risk: latestResponse.context?.route_risk || null,
        };
      case 'EvidenceAgent':
        return {
          evidence_count: latestResponse.evidence.length,
          evidence_items: latestResponse.evidence,
          final_answer: latestResponse.answer,
        };
      default:
        return null;
    }
  };

  return (
    <div className="workspace-pane evidence-workspace-pane">
      {/* Top Header */}
      <div className="workspace-header">
        <div className="workspace-header-title">
          <Database size={17} color="#06b6d4" />
          <span>DATA PROVENANCE & EVIDENCE AUDIT</span>
          <span className="workspace-header-badge">TECHNICAL TRANSPARENCY</span>
        </div>
        <div className="workspace-header-meta">
          <span>Judge-Facing Audit • Deterministic Reasoning Transparency</span>
        </div>
      </div>

      <div className="evidence-dashboard-scrollable">
        {/* SECTION 1: DATA SOURCES & PROVENANCE GRID */}
        <section className="evidence-section">
          <div className="evidence-section-header">
            <Layers size={15} color="#38bdf8" />
            <h3>1. TELEMETRY DATA PROVENANCE & FEED STATUS</h3>
          </div>
          <div className="sources-detailed-grid">
            {sources.map((s) => (
              <div key={s.id} className="source-detailed-card">
                <div className="source-card-top">
                  <div className="source-title-group">
                    <span className="source-icon-wrap">{s.icon}</span>
                    <span className="source-name">{s.label}</span>
                  </div>
                  <span className={`status-pill status-${s.status.toLowerCase().replace(/[^a-z]/g, '')}`}>
                    <span className="status-dot" />
                    <span>{s.status}</span>
                  </span>
                </div>
                <div className="source-card-body">
                  <div className="source-detail-row">
                    <span className="detail-key">Endpoint:</span>
                    <span className="detail-val font-mono">{s.endpoint}</span>
                  </div>
                  <div className="source-detail-row">
                    <span className="detail-key">Telemetry:</span>
                    <span className="detail-val">{s.parameters}</span>
                  </div>
                  <div className="source-detail-row">
                    <span className="detail-key">Feed Status:</span>
                    <span className="detail-val">{s.detail}</span>
                  </div>
                  <div className="source-detail-row">
                    <span className="detail-key">Coverage:</span>
                    <span className="detail-val">{s.coverage}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* SECTION 2: PFZ HISTORICAL SNAPSHOT PROVENANCE */}
        <section className="evidence-section">
          <div className="evidence-section-header">
            <FileCheck size={15} color="#10b981" />
            <h3>2. ESSO-INCOIS PFZ ADVISORY SNAPSHOT PROVENANCE</h3>
          </div>
          <div className="incois-provenance-box">
            <div className="provenance-fields-grid">
              <div className="prov-field">
                <span className="prov-key">Source Authority:</span>
                <span className="prov-val font-semibold">ESSO - Indian National Centre for Ocean Information Services (INCOIS)</span>
              </div>
              <div className="prov-field">
                <span className="prov-key">Ministry:</span>
                <span className="prov-val">Ministry of Earth Sciences, Government of India</span>
              </div>
              <div className="prov-field">
                <span className="prov-key">Dataset Type:</span>
                <span className="prov-val font-mono">Official Historical Multi-Point Sector Snapshot (GeoJSON)</span>
              </div>
              <div className="prov-field">
                <span className="prov-key">Target Sector:</span>
                <span className="prov-val">Kerala Coastal Waters • Ernakulam / Kochi Sub-Sector</span>
              </div>
              <div className="prov-field">
                <span className="prov-key">Associated Landing Centres:</span>
                <span className="prov-val font-mono">Munambam, Cochin Fisheries Harbour, Chellanam, Vypeen, Kuzhuppilly</span>
              </div>
              <div className="prov-field">
                <span className="prov-key">Snapshot Status:</span>
                <span className="prov-val text-amber-400">Archived Demonstrational Snapshot (Not a Live Real-Time Broadcast)</span>
              </div>
            </div>
            <div className="provenance-disclaimer-banner">
              <AlertCircle size={14} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span>
                <strong>Mandatory Verification Notice:</strong> PFZ targets in this prototype originate from an authentic historical INCOIS landing-centre-associated advisory snapshot. In accordance with maritime transparency guidelines, this prototype strictly refrains from labeling historical targets as "active", "current", or "high-probability fishing zones".
              </span>
            </div>
          </div>
        </section>

        {/* SECTION 3: MULTI-AGENT EXECUTION PIPELINE (LANGGRAPH) */}
        <section className="evidence-section">
          <div className="evidence-section-header">
            <Cpu size={15} color="#06b6d4" />
            <h3>3. MULTI-AGENT EXECUTION CHAIN (LANGGRAPH WORKFLOW)</h3>
          </div>
          <div className="pipeline-container">
            {/* Visual execution chain */}
            <div className="pipeline-steps-bar">
              {AGENT_PIPELINE_ORDER.map((agent, idx) => {
                const wasExecuted = trace.includes(agent);
                const isSelected = selectedAgent === agent;
                return (
                  <React.Fragment key={agent}>
                    <button
                      type="button"
                      className={`pipeline-agent-chip ${isSelected ? 'selected' : ''} ${wasExecuted ? 'executed' : 'skipped'}`}
                      onClick={() => setSelectedAgent(agent)}
                    >
                      <div className="chip-header">
                        <Cpu size={12} />
                        <span>{agent}</span>
                      </div>
                      <div className="chip-status">
                        {wasExecuted ? (
                          <span className="chip-badge executed">
                            <CheckCircle2 size={10} /> Executed
                          </span>
                        ) : (
                          <span className="chip-badge skipped">Skipped / Idle</span>
                        )}
                      </div>
                    </button>
                    {idx < AGENT_PIPELINE_ORDER.length - 1 && (
                      <span className="pipeline-arrow">&rarr;</span>
                    )}
                  </React.Fragment>
                );
              })}
            </div>

            {/* Selected Agent Output Inspector */}
            <div className="agent-payload-viewer">
              <div className="payload-viewer-header">
                <Terminal size={13} color="#06b6d4" />
                <span>Execution Output Payload: <strong>{selectedAgent}</strong></span>
              </div>
              <pre className="payload-code-box">
                {JSON.stringify(getAgentPayload(selectedAgent), null, 2)}
              </pre>
            </div>
          </div>
        </section>

        {/* SECTION 4: EVIDENTIARY CLAIMS & DETERMINISTIC CALCULATIONS */}
        <section className="evidence-section">
          <div className="evidence-section-header">
            <Shield size={15} color="#a855f7" />
            <h3>4. STRUCTURED EVIDENCE AUDIT & DETERMINISTIC ENGINES</h3>
          </div>

          <div className="evidence-cards-grid">
            {/* Temporal Reasoning Engine Card */}
            {context?.temporal_comparison && (
              <div className="evidence-card">
                <div className="evidence-card-title">
                  <Clock size={14} color="#38bdf8" />
                  <span>Temporal Reasoning Engine</span>
                </div>
                <div className="evidence-metric-table">
                  <div>Trend: <strong>{context.temporal_comparison.trend}</strong></div>
                  <div>Wind &Delta;: <strong>{context.temporal_comparison.delta_wind_kmh.toFixed(1)} km/h</strong></div>
                  <div>Wave &Delta;: <strong>{context.temporal_comparison.delta_wave_m.toFixed(2)} m</strong></div>
                  <div>Risk &Delta;: <strong>{context.temporal_comparison.delta_risk_score.toFixed(1)}</strong></div>
                </div>
                <div className="evidence-provenance-tag">
                  {context.temporal_comparison.provenance_notice}
                </div>
              </div>
            )}

            {/* Prototype Route Risk Index Card */}
            {context?.route_risk && (
              <div className="evidence-card">
                <div className="evidence-card-title">
                  <Navigation size={14} color="#f59e0b" />
                  <span>Prototype Route Risk Engine</span>
                </div>
                <div className="evidence-metric-table">
                  <div>Score: <strong>{context.route_risk.prototype_route_risk_index.toFixed(1)} / 10</strong></div>
                  <div>Risk Level: <strong>{context.route_risk.risk_level}</strong></div>
                  <div>Wave Stress Ratio: <strong>{context.route_risk.wave_stress_ratio.toFixed(2)}</strong></div>
                  <div>Wind Stress Ratio: <strong>{context.route_risk.wind_stress_ratio.toFixed(2)}</strong></div>
                </div>
                <div className="evidence-provenance-tag">
                  Deterministic 4-factor formula (Weights in risk_thresholds.py)
                </div>
              </div>
            )}

            {/* Claims emitted by EvidenceAgent */}
            <div className="evidence-card full-width">
              <div className="evidence-card-title">
                <FileCheck size={14} color="#10b981" />
                <span>Evidence Items Emitted by EvidenceAgent ({evidence.length})</span>
              </div>
              {evidence.length > 0 ? (
                <div className="claims-list">
                  {evidence.map((item, idx) => (
                    <div key={idx} className="claim-item">
                      <div className="claim-header">
                        <span className="claim-source font-mono">{item.source}</span>
                        <span className="claim-time">{item.timestamp?.split('T')[1]?.substring(0, 8)}</span>
                      </div>
                      <div className="claim-text">{item.claim}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  No evidence items recorded yet. Submit a query in Chat to inspect agent synthesis claims.
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
