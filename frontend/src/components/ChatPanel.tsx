import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Info,
  Anchor,
  Languages,
  ChevronDown,
  ChevronUp,
  Navigation
} from 'lucide-react';
import type { ChatResponse } from '../services/api';
import {
  deriveWeatherStatus,
  deriveOceanStatus,
  deriveLightningStatus,
  deriveChlorophyllStatus,
} from '../services/api';
import { DataSourcesSection } from './DataSourcesSection';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  responsePayload?: ChatResponse;
  timestamp: string;
}

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (msg: string, vesselType?: string, languageMode?: string) => void;
  isLoading: boolean;
  onSelectPfz?: (pfz: any) => void;
  latestResponse?: ChatResponse | null;
  selectedVessel?: string;
  onVesselChange?: (vessel: string) => void;
  selectedLanguage?: string;
  onLanguageChange?: (lang: string) => void;
}

const QUICK_PROMPTS = [
  'Is it safe to go fishing near Kochi tomorrow morning?',
  'What is the safe route and passage corridor to the nearest PFZ?',
  'Where is the nearest Potential Fishing Zone?',
  'What are the tide, weather and sea conditions near my fishing location?',
];

const VESSEL_OPTIONS = [
  { id: 'traditional_craft', label: 'Traditional Craft (വള്ളം)', icon: '🛶' },
  { id: 'motorized_frp_obm', label: 'Motorized FRP OBM (എഫ്.ആർ.പി)', icon: '🚤' },
  { id: 'mechanized_trawler', label: 'Mechanized Trawler (ട്രോളർ)', icon: '🚢' },
];

const LANGUAGE_OPTIONS = [
  { id: 'bilingual', label: 'Bilingual (ദ്വിഭാഷ)' },
  { id: 'english', label: 'English' },
  { id: 'malayalam', label: 'മലയാളം' },
];

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onSelectPfz,
  latestResponse,
  selectedVessel = 'motorized_frp_obm',
  onVesselChange,
  selectedLanguage = 'bilingual',
  onLanguageChange,
}) => {
  const [inputText, setInputText] = useState('');
  const [localVessel, setLocalVessel] = useState<string>(selectedVessel);
  const [localLanguage, setLocalLanguage] = useState<string>(selectedLanguage);
  const [expandedMl, setExpandedMl] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleVesselSelect = (v: string) => {
    setLocalVessel(v);
    if (onVesselChange) onVesselChange(v);
  };

  const handleLanguageSelect = (l: string) => {
    setLocalLanguage(l);
    if (onLanguageChange) onLanguageChange(l);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim(), localVessel, localLanguage);
    setInputText('');
  };

  const handleQuickPrompt = (prompt: string) => {
    if (isLoading) return;
    onSendMessage(prompt, localVessel, localLanguage);
  };

  const toggleMalayalam = (msgId: string) => {
    setExpandedMl((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="chat-pane">
      {/* Chat Header */}
      <div className="chat-header">
        <h2>
          <Bot size={18} color="#06b6d4" />
          <span>ORCA Marine Intelligence Console</span>
        </h2>
      </div>

      {/* M4 Vessel & Language Selectors */}
      <div style={{
        padding: '6px 12px',
        background: 'rgba(15, 23, 42, 0.75)',
        borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}>
        {/* Vessel Category Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
            <Anchor size={12} color="#38bdf8" /> Vessel:
          </span>
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {VESSEL_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => handleVesselSelect(opt.id)}
                style={{
                  fontSize: '0.7rem',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: localVessel === opt.id ? '1px solid #38bdf8' : '1px solid rgba(148, 163, 184, 0.2)',
                  background: localVessel === opt.id ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.5)',
                  color: localVessel === opt.id ? '#38bdf8' : '#cbd5e1',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {opt.icon} {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Language Mode Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
            <Languages size={12} color="#38bdf8" /> Language:
          </span>
          <div style={{ display: 'flex', gap: '4px' }}>
            {LANGUAGE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => handleLanguageSelect(opt.id)}
                style={{
                  fontSize: '0.7rem',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: localLanguage === opt.id ? '1px solid #10b981' : '1px solid rgba(148, 163, 184, 0.2)',
                  background: localLanguage === opt.id ? 'rgba(16, 185, 129, 0.15)' : 'rgba(30, 41, 59, 0.5)',
                  color: localLanguage === opt.id ? '#10b981' : '#cbd5e1',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Action Prompt Chips */}
      <div className="quick-prompts-container">
        <div className="quick-prompts-label">Operational Demo Queries:</div>
        <div className="quick-prompt-buttons">
          {QUICK_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              className="prompt-btn"
              onClick={() => handleQuickPrompt(prompt)}
              disabled={isLoading}
              title={prompt}
            >
              <span>{prompt}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Prototype Demonstration Disclaimer Banner */}
      <div className="chat-demo-disclaimer" role="note" aria-label="Demo Data Disclaimer">
        <AlertTriangle size={14} className="disclaimer-icon" />
        <span>
          <strong>Prototype demonstration</strong> — marine, weather, ocean, vessel profiles, and corridor routing data shown here are demonstration estimates and not for live marine navigation.
        </span>
      </div>

      {/* Compact Data Sources & Provenance Section */}
      <DataSourcesSection latestResponse={latestResponse} />

      {/* Multi-turn Active Conversation Context Chips */}
      {latestResponse?.context && (
        latestResponse.context.location ||
        latestResponse.context.date ||
        latestResponse.context.time_window ||
        latestResponse.context.activity ||
        latestResponse.context.selected_pfz ||
        latestResponse.context.vessel_type ||
        latestResponse.context.active_route
      ) && (
        <div className="active-context-bar" style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px',
          padding: '6px 12px',
          background: 'rgba(15, 23, 42, 0.65)',
          borderRadius: '6px',
          fontSize: '0.75rem',
          color: '#94a3b8',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          alignItems: 'center',
          margin: '4px 0 8px 0'
        }}>
          <span style={{ fontWeight: 600, color: '#38bdf8', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Active Context:
          </span>
          {latestResponse.context.location && (
            <span style={{ background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#e0f2fe' }}>
              📍 {latestResponse.context.location.name}
            </span>
          )}
          {latestResponse.context.vessel_type && (
            <span style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.3)', color: '#fef3c7' }}>
              ⛵ {latestResponse.context.vessel_type.replace(/_/g, ' ')}
            </span>
          )}
          {latestResponse.context.language_mode && (
            <span style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#d1fae5' }}>
              🌐 {latestResponse.context.language_mode}
            </span>
          )}
          {latestResponse.context.date && (
            <span style={{ background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#e0f2fe' }}>
              📅 {latestResponse.context.date.replace(/_/g, ' ')}
            </span>
          )}
          {latestResponse.context.time_window && (
            <span style={{ background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#e0f2fe' }}>
              ⏰ {latestResponse.context.time_window}
            </span>
          )}
          {latestResponse.context.activity && (
            <span style={{ background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#e0f2fe' }}>
              🎯 {latestResponse.context.activity}
            </span>
          )}
          {latestResponse.context.selected_pfz && (
            <span style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#a7f3d0' }}>
              🐟 PFZ: {latestResponse.context.selected_pfz.name}
            </span>
          )}
          {latestResponse.context.active_route && (
            <span style={{ background: 'rgba(6, 182, 212, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(6, 182, 212, 0.3)', color: '#cffafe' }}>
              🧭 Corridor: {latestResponse.context.active_route.total_distance_km} km
            </span>
          )}
        </div>
      )}

      {/* Messages Feed */}
      <div className="chat-messages">
        {messages.map((msg) => {
          const msgWeather = msg.responsePayload?.weather;
          const msgOcean = msg.responsePayload?.ocean;
          const msgWeatherStatus = deriveWeatherStatus(msgWeather);
          const msgOceanStatus = deriveOceanStatus(msgOcean);
          const msgLightningStatus = deriveLightningStatus(msgWeather);
          const msgChlorophyllStatus = deriveChlorophyllStatus(msgOcean);

          return (
            <div key={msg.id} className={`message-bubble ${msg.sender}`}>
              {msg.sender === 'user' ? (
                <div className="user-content">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px', fontSize: '0.7rem', opacity: 0.8 }}>
                    <User size={12} />
                    <span>Navigator</span>
                  </div>
                  <div>{msg.text}</div>
                </div>
              ) : (
                <div className="assistant-card">
                  {/* Risk Level Badge if risk assessment exists */}
                  {msg.responsePayload?.risk && (
                    <div className={`risk-badge-banner ${msg.responsePayload.risk.risk_level}`}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {msg.responsePayload.risk.risk_level === 'LOW' ? (
                          <ShieldCheck size={18} />
                        ) : (
                          <ShieldAlert size={18} />
                        )}
                        <span>ASSESSED RISK: {msg.responsePayload.risk.risk_level}</span>
                      </div>
                      <span style={{ fontSize: '0.75rem', opacity: 0.9 }}>
                        Score: {msg.responsePayload.risk.risk_score}
                      </span>
                    </div>
                  )}

                  {/* Key Marine Metrics Telemetry Card */}
                  {(msgWeather || msgOcean) && (
                    <div className="telemetry-grid">
                      {msgWeather && (
                        <>
                          <div className="telemetry-cell">
                            <div className="telemetry-cell-header">
                              <span className="telemetry-label">Wind Speed</span>
                              <span className={`cell-tag tag-${msgWeatherStatus.toLowerCase().replace(/[^a-z]/g, '-')}`}>
                                {msgWeatherStatus}
                              </span>
                            </div>
                            <div className="telemetry-val">
                              {msgWeather.wind_speed_kmh} <span style={{ fontSize: '0.7rem' }}>km/h</span>
                            </div>
                          </div>
                          <div className="telemetry-cell">
                            <div className="telemetry-cell-header">
                              <span className="telemetry-label">Rain Prob.</span>
                              <span className={`cell-tag tag-${msgWeatherStatus.toLowerCase().replace(/[^a-z]/g, '-')}`}>
                                {msgWeatherStatus}
                              </span>
                            </div>
                            <div className="telemetry-val">
                              {msgWeather.rain_probability}%
                            </div>
                          </div>
                          <div className="telemetry-cell">
                            <div className="telemetry-cell-header">
                              <span className="telemetry-label">Lightning</span>
                              <span className={`cell-tag tag-${msgLightningStatus.toLowerCase().replace(/[^a-z]/g, '-')}`}>
                                {msgLightningStatus}
                              </span>
                            </div>
                            <div className="telemetry-val">
                              {msgLightningStatus === 'UNAVAILABLE' ? (
                                <span className="telemetry-unavailable">UNAVAILABLE</span>
                              ) : (
                                <span style={{ textTransform: 'capitalize' }}>
                                  {msgWeather.lightning_risk}
                                </span>
                              )}
                            </div>
                          </div>
                        </>
                      )}

                      {msgOcean && (
                        <>
                          <div className="telemetry-cell">
                            <div className="telemetry-cell-header">
                              <span className="telemetry-label">Wave Height</span>
                              <span className={`cell-tag tag-${msgOceanStatus.toLowerCase().replace(/[^a-z]/g, '-')}`}>
                                {msgOceanStatus}
                              </span>
                            </div>
                            <div className="telemetry-val">
                              {msgOcean.wave_height_m} <span style={{ fontSize: '0.7rem' }}>m</span>
                            </div>
                          </div>
                          <div className="telemetry-cell">
                            <div className="telemetry-cell-header">
                              <span className="telemetry-label">Sea State</span>
                              <span className={`cell-tag tag-${msgOceanStatus.toLowerCase().replace(/[^a-z]/g, '-')}`}>
                                {msgOceanStatus}
                              </span>
                            </div>
                            <div className="telemetry-val" style={{ textTransform: 'capitalize' }}>
                              {msgOcean.sea_state}
                            </div>
                          </div>
                          <div className="telemetry-cell">
                            <div className="telemetry-cell-header">
                              <span className="telemetry-label">Chlorophyll</span>
                              <span className={`cell-tag tag-${msgChlorophyllStatus.toLowerCase().replace(/[^a-z]/g, '-')}`}>
                                {msgChlorophyllStatus}
                              </span>
                            </div>
                            <div className="telemetry-val">
                              {msgChlorophyllStatus === 'UNAVAILABLE' ? (
                                <span className="telemetry-unavailable">UNAVAILABLE</span>
                              ) : (
                                <span>{msgOcean.chlorophyll_mg_m3} mg/m³</span>
                              )}
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {/* Vessel Seaworthiness Profile Card (M4) */}
                  {msg.responsePayload?.vessel_profile && (
                    <div style={{
                      background: 'rgba(30, 41, 59, 0.7)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: '6px',
                      padding: '8px 10px',
                      margin: '6px 0',
                      fontSize: '0.78rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#38bdf8', fontWeight: 600, marginBottom: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>⛵ {msg.responsePayload.vessel_profile.name}</span>
                          <span style={{ fontSize: '0.62rem', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>PROTOTYPE PARAMETERS</span>
                        </div>
                        {msg.responsePayload.vessel_profile.name_ml && (
                          <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{msg.responsePayload.vessel_profile.name_ml}</span>
                        )}
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px', color: '#cbd5e1', fontSize: '0.72rem' }}>
                        <div>Prototype Wave Limit: &le; <strong>{msg.responsePayload.vessel_profile.wave_max_safe} m</strong></div>
                        <div>Prototype Wind Limit: &le; <strong>{msg.responsePayload.vessel_profile.wind_max_safe} km/h</strong></div>
                        <div>Demo Cruising Speed: <strong>{msg.responsePayload.vessel_profile.cruising_speed_knots} kn</strong></div>
                        <div>Demo Fuel Rate: <strong>{msg.responsePayload.vessel_profile.fuel_consumption_l_per_hour} L/h</strong></div>
                      </div>
                      <div style={{ fontSize: '0.63rem', color: '#94a3b8', fontStyle: 'italic', marginTop: '5px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '4px' }}>
                        * Configurable prototype/demo parameters for research and demonstration only; not official maritime regulations or authoritative seaworthiness limits.
                      </div>
                    </div>
                  )}

                  {/* Safe Passage Corridor Card (M4) */}
                  {msg.responsePayload?.transit_route && (
                    <div style={{
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: msg.responsePayload.transit_route.geofence_avoidance_applied ? '1px solid #f59e0b' : '1px solid #06b6d4',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      margin: '6px 0',
                      fontSize: '0.78rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: msg.responsePayload.transit_route.geofence_avoidance_applied ? '#f59e0b' : '#06b6d4', fontWeight: 700 }}>
                          <Navigation size={14} />
                          <span>Safe Passage Corridor</span>
                        </div>
                        <span style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background: msg.responsePayload.transit_route.geofence_avoidance_applied ? 'rgba(245, 158, 11, 0.2)' : 'rgba(6, 182, 212, 0.2)',
                          color: msg.responsePayload.transit_route.geofence_avoidance_applied ? '#f59e0b' : '#06b6d4'
                        }}>
                          {msg.responsePayload.transit_route.geofence_avoidance_applied ? 'AVOIDANCE ACTIVE' : 'DIRECT TRANSIT'}
                        </span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', margin: '6px 0', color: '#cbd5e1' }}>
                        <div>
                          <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>Total Distance</div>
                          <strong>{msg.responsePayload.transit_route.total_distance_km} km</strong> ({msg.responsePayload.transit_route.total_distance_nm} nm)
                        </div>
                        <div>
                          <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>Est. Duration</div>
                          <strong>~{msg.responsePayload.transit_route.estimated_duration_hours} hrs</strong>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>Est. Fuel</div>
                          <strong>~{msg.responsePayload.transit_route.estimated_fuel_litres} L</strong>
                        </div>
                      </div>

                      {msg.responsePayload.transit_route.waypoints?.length > 0 && (
                        <div style={{ marginTop: '4px', borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: '4px' }}>
                          <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Corridor Waypoints:</span>
                          <ul style={{ margin: '2px 0 0 12px', padding: 0, fontSize: '0.7rem', color: '#e2e8f0' }}>
                            {msg.responsePayload.transit_route.waypoints.map((wp, i) => (
                              <li key={i}>
                                <strong>{wp.name}</strong> ({wp.latitude}, {wp.longitude}) — {wp.description}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {msg.responsePayload.transit_route.fuel_estimate_note && (
                        <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontStyle: 'italic', marginTop: '4px' }}>
                          * {msg.responsePayload.transit_route.fuel_estimate_note}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Malayalam Advisory View (M4) */}
                  {msg.responsePayload?.answer_ml && (
                    <div style={{
                      margin: '6px 0',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                      borderRadius: '6px',
                      background: 'rgba(6, 78, 59, 0.25)',
                      overflow: 'hidden'
                    }}>
                      <button
                        type="button"
                        onClick={() => toggleMalayalam(msg.id)}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '6px 10px',
                          background: 'transparent',
                          border: 'none',
                          color: '#6ee7b7',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          fontWeight: 600
                        }}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Languages size={14} />
                          മലയാളം നാവിക റിപ്പോർട്ട് (Malayalam Coastal Advisory)
                        </span>
                        {expandedMl[msg.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      {expandedMl[msg.id] && (
                        <div style={{
                          padding: '8px 10px',
                          borderTop: '1px solid rgba(16, 185, 129, 0.2)',
                          fontSize: '0.78rem',
                          color: '#d1fae5',
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.5
                        }}>
                          {msg.responsePayload.answer_ml}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Assistant Conversational Answer Text */}
                  <div className="message-text">{msg.text}</div>

                  {/* Official Historical INCOIS PFZ Snapshot Notice */}
                  {msg.responsePayload?.geospatial?.source_type === 'OFFICIAL_SNAPSHOT' && (
                    <div className="pfz-snapshot-banner" role="note" aria-label="PFZ Historical Snapshot Notice">
                      <Info size={14} className="pfz-snapshot-icon" />
                      <span>
                        <strong>Historical INCOIS PFZ snapshot</strong> — not a live fishing advisory.
                      </span>
                    </div>
                  )}

                {/* Nearest PFZ Map Focus Trigger */}
                {(msg.responsePayload?.spatial_features?.nearest_pfz || msg.responsePayload?.geospatial?.nearest_pfz) && onSelectPfz && (
                  <button
                    type="button"
                    className="inspect-trace-btn"
                    onClick={() => {
                      const pfz = msg.responsePayload?.spatial_features?.nearest_pfz || msg.responsePayload?.geospatial?.nearest_pfz;
                      if (pfz) onSelectPfz(pfz);
                    }}
                    style={{ alignSelf: 'flex-start', marginTop: '4px' }}
                  >
                    <span>🎯 Focus Map on {msg.responsePayload?.spatial_features?.nearest_pfz?.name || msg.responsePayload?.geospatial?.nearest_pfz?.name}</span>
                  </button>
                )}

                {/* Data Source Provenance Tags */}
                <div className="source-tags">
                  {msg.responsePayload?.weather && (
                    <span className="source-tag">{msg.responsePayload.weather.source}</span>
                  )}
                  {msg.responsePayload?.ocean && (
                    <span className="source-tag">{msg.responsePayload.ocean.source}</span>
                  )}
                  {msg.responsePayload?.geospatial && (
                    <span className="source-tag">
                      {msg.responsePayload.geospatial.source_type === 'OFFICIAL_SNAPSHOT'
                        ? 'INCOIS (OFFICIAL SNAPSHOT)'
                        : msg.responsePayload.geospatial.source}
                    </span>
                  )}
                  {msg.responsePayload?.transit_route && (
                    <span className="source-tag">ROUTING_ENGINE</span>
                  )}
                  {msg.responsePayload?.risk && (
                    <span className="source-tag">RULE_ENGINE</span>
                  )}
                </div>
              </div>
            )}
          </div>
        )})}

        {isLoading && (
          <div className="message-bubble assistant">
            <div className="assistant-card" style={{ padding: '0.75rem', color: '#94a3b8', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="pulsing-dot" />
                <span>LangGraph orchestrating agents (Planner, Weather, Ocean, GIS)...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Bar */}
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input-field"
          placeholder="Ask ORCA marine intelligence..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={isLoading || !inputText.trim()}
          title="Send query"
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );
};
