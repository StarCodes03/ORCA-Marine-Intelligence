import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  ShieldCheck,
  ShieldAlert,
  Anchor,
  Languages,
  ChevronDown,
  ChevronUp,
  Navigation,
  Sparkles,
  Database,
  MapPin,
  Info
} from 'lucide-react';
import type { ChatResponse } from '../services/api';
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
  'What is the safest route to the nearest PFZ Target?',
  'Where is the nearest PFZ Target?',
  'What are the weather and sea conditions?'
];

const VESSEL_OPTIONS = [
  { id: 'traditional_craft', label: 'Traditional (വള്ളം)', icon: '🛶' },
  { id: 'motorized_frp_obm', label: 'Motorized FRP (എഫ്.ആർ.പി)', icon: '🚤' },
  { id: 'mechanized_trawler', label: 'Trawler (ട്രോളർ)', icon: '🚢' },
];

const LANGUAGE_OPTIONS = [
  { id: 'english', label: 'English' },
  { id: 'malayalam', label: 'മലയാളം' },
  { id: 'bilingual', label: 'Bilingual' },
];

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onSelectPfz,
  latestResponse,
  selectedVessel = 'motorized_frp_obm',
  onVesselChange,
  selectedLanguage = 'english',
  onLanguageChange,
}) => {
  const [inputText, setInputText] = useState('');
  const [localVessel, setLocalVessel] = useState<string>(selectedVessel);
  const [localLanguage, setLocalLanguage] = useState<string>(selectedLanguage);

  // Secondary Collapsible Drawers (collapsed by default to preserve chat height)
  const [isPromptsOpen, setIsPromptsOpen] = useState<boolean>(false);
  const [isSourcesOpen, setIsSourcesOpen] = useState<boolean>(false);
  const [isContextOpen, setIsContextOpen] = useState<boolean>(false);
  const [expandedMl, setExpandedMl] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll strictly to newest message in message feed
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
    setIsPromptsOpen(false);
  };

  const toggleMalayalam = (msgId: string) => {
    setExpandedMl((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  // Helper to format prose markdown text cleanly
  const renderProse = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const rendered = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (line.startsWith('>')) {
        return (
          <div key={idx} className="prose-note">
            {rendered}
          </div>
        );
      }
      if (line.startsWith('•') || line.startsWith('-')) {
        return (
          <div key={idx} className="prose-bullet">
            {rendered}
          </div>
        );
      }
      if (!line.trim()) {
        return <div key={idx} className="prose-space" />;
      }
      return (
        <p key={idx} className="prose-line">
          {rendered}
        </p>
      );
    });
  };

  const hasContext = Boolean(
    latestResponse?.context &&
    (latestResponse.context.location ||
      latestResponse.context.vessel_type ||
      latestResponse.context.date ||
      latestResponse.context.selected_pfz)
  );

  return (
    <div className="chat-pane">
      {/* 1. Chat Console Header */}
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="chat-avatar-icon">
            <Bot size={17} color="#06b6d4" />
          </div>
          <div>
            <h2 style={{ fontSize: '0.88rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
              ORCA Marine Assistant
            </h2>
            <span style={{ fontSize: '0.68rem', color: '#38bdf8' }}>
              Conversational Decision Support
            </span>
          </div>
        </div>
      </div>

      {/* 2. Always-Visible Control Bar: Vessel & Language Selectors */}
      <div className="chat-controls-bar">
        {/* Vessel Selector */}
        <div className="control-group">
          <span className="control-label">
            <Anchor size={12} color="#38bdf8" /> Vessel:
          </span>
          <div className="control-pills">
            {VESSEL_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={`control-pill ${localVessel === opt.id ? 'active' : ''}`}
                onClick={() => handleVesselSelect(opt.id)}
              >
                <span>{opt.icon}</span>
                <span>{opt.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Language Selector */}
        <div className="control-group">
          <span className="control-label">
            <Languages size={12} color="#10b981" /> Language:
          </span>
          <div className="control-pills">
            {LANGUAGE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={`control-pill lang ${localLanguage === opt.id ? 'active-lang' : ''}`}
                onClick={() => handleLanguageSelect(opt.id)}
              >
                <span>{opt.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Secondary Metadata Toolbar (Collapsible Drawers) */}
      <div className="secondary-toolbar">
        <button
          type="button"
          className={`secondary-toggle-btn ${isPromptsOpen ? 'active' : ''}`}
          onClick={() => {
            setIsPromptsOpen(!isPromptsOpen);
            setIsSourcesOpen(false);
            setIsContextOpen(false);
          }}
        >
          <Sparkles size={12} />
          <span>Suggested Queries</span>
          {isPromptsOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        <button
          type="button"
          className={`secondary-toggle-btn ${isSourcesOpen ? 'active' : ''}`}
          onClick={() => {
            setIsSourcesOpen(!isSourcesOpen);
            setIsPromptsOpen(false);
            setIsContextOpen(false);
          }}
        >
          <Database size={12} />
          <span>Data Sources</span>
          {isSourcesOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {hasContext && (
          <button
            type="button"
            className={`secondary-toggle-btn ${isContextOpen ? 'active' : ''}`}
            onClick={() => {
              setIsContextOpen(!isContextOpen);
              setIsPromptsOpen(false);
              setIsSourcesOpen(false);
            }}
          >
            <MapPin size={12} />
            <span>Active Context</span>
            {isContextOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        )}
      </div>

      {/* Drawer: Suggested Queries */}
      {isPromptsOpen && (
        <div className="secondary-drawer-panel">
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: '6px', fontWeight: 600 }}>
            CLICK TO ASK ORCA:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="drawer-prompt-btn"
                onClick={() => handleQuickPrompt(prompt)}
                disabled={isLoading}
              >
                <span>👉 {prompt}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Drawer: Data Sources & Provenance */}
      {isSourcesOpen && (
        <div className="secondary-drawer-panel">
          <DataSourcesSection latestResponse={latestResponse} compact={true} />
        </div>
      )}

      {/* Drawer: Active Context */}
      {isContextOpen && latestResponse?.context && (
        <div className="secondary-drawer-panel">
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: '6px', fontWeight: 600 }}>
            CURRENT MULTI-TURN SESSION CONTEXT:
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
            {latestResponse.context.location && (
              <span className="context-chip">📍 {latestResponse.context.location.name}</span>
            )}
            {latestResponse.context.vessel_type && (
              <span className="context-chip">⛵ {latestResponse.context.vessel_type.replace(/_/g, ' ')}</span>
            )}
            {latestResponse.context.language_mode && (
              <span className="context-chip">🌐 {latestResponse.context.language_mode}</span>
            )}
            {latestResponse.context.date && (
              <span className="context-chip">📅 {latestResponse.context.date.replace(/_/g, ' ')}</span>
            )}
            {latestResponse.context.time_window && (
              <span className="context-chip">⏰ {latestResponse.context.time_window}</span>
            )}
            {latestResponse.context.selected_pfz && (
              <span className="context-chip">🐟 PFZ: {latestResponse.context.selected_pfz.name}</span>
            )}
            {latestResponse.context.candidate_pfzs && latestResponse.context.candidate_pfzs.length > 0 && (
              <span className="context-chip">🎯 {latestResponse.context.candidate_pfzs.length} Candidates</span>
            )}
          </div>
        </div>
      )}

      {/* Initial Clean Session Quick Prompts (Only shown before conversation starts) */}
      {messages.length <= 1 && !isPromptsOpen && (
        <div className="initial-prompts-strip">
          <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px' }}>
            Suggested questions to get started:
          </div>
          <div className="quick-chips-row">
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="quick-chip"
                onClick={() => handleQuickPrompt(prompt)}
                disabled={isLoading}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 4. Dedicated Independently Scrollable Message Feed */}
      <div className="chat-messages">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          const msgWeather = msg.responsePayload?.weather;
          const msgOcean = msg.responsePayload?.ocean;
          const msgRisk = msg.responsePayload?.risk;
          const msgRoute = msg.responsePayload?.transit_route;
          const msgVessel = msg.responsePayload?.vessel_profile;

          return (
            <div key={msg.id} className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
              {isUser ? (
                /* User Chat Bubble */
                <div className="user-bubble">
                  <div className="bubble-text">{msg.text}</div>
                  <div className="bubble-time">{msg.timestamp}</div>
                </div>
              ) : (
                /* ORCA Assistant Message Card */
                <div className="assistant-card">
                  {/* Assistant Header */}
                  <div className="assistant-header">
                    <div className="assistant-title">
                      <Bot size={14} color="#06b6d4" />
                      <span>ORCA Advisor</span>
                    </div>
                    <span style={{ fontSize: '0.65rem', color: '#64748b' }}>{msg.timestamp}</span>
                  </div>

                  {/* Compact Risk Badge (Supporting Context) */}
                  {msgRisk && (
                    <div className={`risk-badge-compact ${msgRisk.risk_level}`}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        {msgRisk.risk_level === 'LOW' ? (
                          <ShieldCheck size={14} />
                        ) : (
                          <ShieldAlert size={14} />
                        )}
                        <span>ASSESSED RISK: {msgRisk.risk_level}</span>
                      </div>
                      <span style={{ fontSize: '0.72rem', opacity: 0.9 }}>
                        Score: {msgRisk.risk_score}/10
                      </span>
                    </div>
                  )}

                  {/* Primary Conversational Text */}
                  <div className="message-text">
                    {renderProse(msg.text)}
                  </div>

                  {/* Compact Telemetry Strip (Supporting Context) */}
                  {(msgWeather || msgOcean) && (
                    <div className="compact-telemetry-strip">
                      {msgWeather && (
                        <div className="telemetry-pill">
                          <span className="telemetry-pill-label">Wind</span>
                          <span>{msgWeather.wind_speed_kmh} km/h</span>
                        </div>
                      )}
                      {msgWeather && (
                        <div className="telemetry-pill">
                          <span className="telemetry-pill-label">Rain</span>
                          <span>{msgWeather.rain_probability}%</span>
                        </div>
                      )}
                      {msgOcean && (
                        <div className="telemetry-pill">
                          <span className="telemetry-pill-label">Wave</span>
                          <span>{msgOcean.wave_height_m} m</span>
                        </div>
                      )}
                      {msgOcean && (
                        <div className="telemetry-pill">
                          <span className="telemetry-pill-label">Sea</span>
                          <span style={{ textTransform: 'capitalize' }}>{msgOcean.sea_state}</span>
                        </div>
                      )}
                      {msgOcean?.tide && (
                        <div className="telemetry-pill">
                          <span className="telemetry-pill-label">Tide</span>
                          <span style={{ textTransform: 'capitalize' }}>{msgOcean.tide}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Vessel Profile Card (when queried) */}
                  {msgVessel && (
                    <div className="vessel-profile-compact">
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#38bdf8', fontWeight: 600 }}>
                        <span>⛵ {msgVessel.name}</span>
                        <span style={{ fontSize: '0.62rem', background: 'rgba(56, 189, 248, 0.15)', padding: '1px 5px', borderRadius: '3px' }}>
                          PROTOTYPE PARAMETERS
                        </span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px', marginTop: '4px', fontSize: '0.72rem', color: '#cbd5e1' }}>
                        <div>Wave Limit: &le; <strong>{msgVessel.wave_max_safe} m</strong></div>
                        <div>Wind Limit: &le; <strong>{msgVessel.wind_max_safe} km/h</strong></div>
                        <div>Cruising Speed: <strong>{msgVessel.cruising_speed_knots} kn</strong></div>
                        <div>Fuel Rate: <strong>{msgVessel.fuel_consumption_l_per_hour} L/h</strong></div>
                      </div>
                    </div>
                  )}

                  {/* Safe Passage Corridor Card (when queried) */}
                  {msgRoute && (
                    <div className="corridor-summary-compact">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: msgRoute.geofence_avoidance_applied ? '#f59e0b' : '#06b6d4', fontWeight: 600 }}>
                          <Navigation size={13} />
                          <span>Safe Passage Corridor</span>
                        </div>
                        <span style={{ fontSize: '0.65rem', padding: '1px 6px', borderRadius: '4px', background: msgRoute.geofence_avoidance_applied ? 'rgba(245, 158, 11, 0.2)' : 'rgba(6, 182, 212, 0.2)', color: msgRoute.geofence_avoidance_applied ? '#f59e0b' : '#06b6d4' }}>
                          {msgRoute.geofence_avoidance_applied ? 'AVOIDANCE ACTIVE' : 'DIRECT TRANSIT'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '12px', fontSize: '0.72rem', color: '#cbd5e1' }}>
                        <div>Distance: <strong>{msgRoute.total_distance_km} km</strong></div>
                        <div>Duration: <strong>~{msgRoute.estimated_duration_hours} h</strong></div>
                        <div>Fuel: <strong>~{msgRoute.estimated_fuel_litres} L</strong></div>
                      </div>
                    </div>
                  )}

                  {/* Malayalam Advisory Drawer (if present) */}
                  {msg.responsePayload?.answer_ml && (
                    <div className="malayalam-advisory-container">
                      <button
                        type="button"
                        className="malayalam-toggle-btn"
                        onClick={() => toggleMalayalam(msg.id)}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <Languages size={13} />
                          മലയാളം നാവിക റിപ്പോർട്ട് (Malayalam Advisory)
                        </span>
                        {expandedMl[msg.id] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>
                      {expandedMl[msg.id] && (
                        <div className="malayalam-text-box">
                          {msg.responsePayload.answer_ml}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Focus Map Button */}
                  {(msg.responsePayload?.spatial_features?.nearest_pfz || msg.responsePayload?.geospatial?.nearest_pfz) && onSelectPfz && (
                    <button
                      type="button"
                      className="focus-map-btn"
                      onClick={() => {
                        const pfz = msg.responsePayload?.spatial_features?.nearest_pfz || msg.responsePayload?.geospatial?.nearest_pfz;
                        if (pfz) onSelectPfz(pfz);
                      }}
                    >
                      <MapPin size={12} />
                      <span>Focus map on target ({msg.responsePayload?.spatial_features?.nearest_pfz?.name || msg.responsePayload?.geospatial?.nearest_pfz?.name})</span>
                    </button>
                  )}

                  {/* Subtle Historical Snapshot Notice */}
                  {msg.responsePayload?.geospatial?.source_type === 'OFFICIAL_SNAPSHOT' && (
                    <div className="snapshot-notice-subtle">
                      <Info size={11} />
                      <span>INCOIS historical PFZ snapshot — not a live fishing advisory.</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="message-bubble assistant">
            <div className="assistant-card" style={{ padding: '0.65rem 0.9rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '0.78rem' }}>
                <span className="pulsing-dot" />
                <span>ORCA reasoning in progress (Weather, Ocean, GIS)...</span>
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* 5. Fixed Chat Input Bar at Bottom */}
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input-field"
          placeholder="Ask ORCA about marine conditions, safety, or routes..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={isLoading || !inputText.trim()}
          title="Send message"
        >
          <Send size={15} />
        </button>
      </form>

      {/* 6. Discreet Prototype Footer Notice */}
      <div className="chat-footer-disclaimer">
        ORCA Prototype • Configurable Advisory & Decision Support • Not for Live Maritime Navigation
      </div>
    </div>
  );
};
