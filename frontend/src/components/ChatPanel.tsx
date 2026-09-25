import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  Anchor,
  Languages,
  ChevronDown,
  ChevronUp,
  Navigation,
  Sparkles,
  Database,
  MapPin,
  Users
} from 'lucide-react';
import type { ChatResponse } from '../services/api';
import { DataSourcesSection } from './DataSourcesSection';
import type { RoleConfig } from '../config/roles';
import { getRoleChatExperience } from '../config/roleExperience';
import type { VisualComponentType, MetricType } from '../config/roleExperience';
import {
  RiskIndicator,
  FishingWindowChart,
  WeatherTrendChart,
  WaveTrendChart,
  MarineConditionsChart,
  InlineRouteCard,
  InlinePfzCard
} from './visualizations';

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
  hasQueried?: boolean;
  selectedVessel?: string;
  onVesselChange?: (vessel: string) => void;
  selectedLanguage?: string;
  onLanguageChange?: (lang: string) => void;
  onNavigateToMarine?: () => void;
  onNavigateToRoute?: () => void;
  activeRole?: RoleConfig;
  onSwitchRole?: () => void;
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
  hasQueried = false,
  selectedVessel = 'motorized_frp_obm',
  onVesselChange,
  selectedLanguage = 'english',
  onLanguageChange,
  onNavigateToMarine,
  onNavigateToRoute,
  activeRole,
  onSwitchRole,
}) => {
  const [inputText, setInputText] = useState('');
  const [localVessel, setLocalVessel] = useState<string>(selectedVessel);
  const [localLanguage, setLocalLanguage] = useState<string>(selectedLanguage);

  const roleExp = getRoleChatExperience(activeRole?.id);

  const effectiveQuickPrompts = (activeRole?.suggestedQuestions && activeRole.suggestedQuestions.length > 0)
    ? activeRole.suggestedQuestions
    : roleExp.suggestedFollowUps && roleExp.suggestedFollowUps.length > 0
      ? roleExp.suggestedFollowUps
      : QUICK_PROMPTS;

  const isVisuallyRelevant = (payload?: ChatResponse): boolean => {
    if (!payload) return false;
    const nonVisualIntents = [
      'greeting',
      'chitchat',
      'marine_news_unsupported',
      'general_query',
      'help'
    ];
    if (nonVisualIntents.includes(payload.intent)) {
      return false;
    }
    return Boolean(
      payload.weather ||
      payload.ocean ||
      payload.risk ||
      payload.route_risk ||
      payload.temporal_comparison ||
      payload.transit_route ||
      payload.spatial_features?.nearest_pfz ||
      payload.geospatial?.nearest_pfz ||
      (payload.candidate_pfzs && payload.candidate_pfzs.length > 0)
    );
  };

  const renderPriorityMetrics = (payload?: ChatResponse, priorityList: MetricType[] = []) => {
    if (!payload || !isVisuallyRelevant(payload)) return null;

    const weather = payload.weather;
    const ocean = payload.ocean;
    const risk = payload.risk;
    const route = payload.transit_route;
    const nearestPfz = payload.spatial_features?.nearest_pfz || payload.geospatial?.nearest_pfz;

    const metricElements: React.ReactNode[] = [];

    for (const metric of priorityList) {
      if (metric === 'wave' && ocean?.wave_height_m != null) {
        metricElements.push(
          <div key="wave" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Wave</span>
            <span className="chat-priority-pill-val">{ocean.wave_height_m} m</span>
          </div>
        );
      } else if (metric === 'sea_state' && ocean?.sea_state) {
        metricElements.push(
          <div key="sea_state" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Sea</span>
            <span className="chat-priority-pill-val" style={{ textTransform: 'capitalize' }}>{ocean.sea_state}</span>
          </div>
        );
      } else if (metric === 'wind' && weather?.wind_speed_kmh != null) {
        metricElements.push(
          <div key="wind" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Wind</span>
            <span className="chat-priority-pill-val">{weather.wind_speed_kmh} km/h</span>
          </div>
        );
      } else if (metric === 'rain' && weather?.rain_probability != null) {
        metricElements.push(
          <div key="rain" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Rain</span>
            <span className="chat-priority-pill-val">{weather.rain_probability}%</span>
          </div>
        );
      } else if (metric === 'risk' && risk) {
        metricElements.push(
          <div key="risk" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Risk</span>
            <span
              className="chat-priority-pill-val"
              style={{ color: risk.risk_level === 'LOW' ? '#34d399' : risk.risk_level === 'MODERATE' ? '#fbbf24' : '#f87171' }}
            >
              {risk.risk_level} ({risk.risk_score.toFixed(1)})
            </span>
          </div>
        );
      } else if (metric === 'sst' && ocean?.sst_c != null) {
        metricElements.push(
          <div key="sst" className="chat-priority-pill">
            <span className="chat-priority-pill-label">SST</span>
            <span className="chat-priority-pill-val">{ocean.sst_c} °C</span>
          </div>
        );
      } else if (metric === 'tide' && ocean?.tide) {
        metricElements.push(
          <div key="tide" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Tide</span>
            <span className="chat-priority-pill-val" style={{ textTransform: 'capitalize' }}>
              {ocean.tide.includes('(') ? ocean.tide.split('(')[0].trim() : ocean.tide}
            </span>
          </div>
        );
      } else if (metric === 'pfz_distance' && nearestPfz?.distance_km != null) {
        metricElements.push(
          <div key="pfz" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Nearest PFZ</span>
            <span className="chat-priority-pill-val">{nearestPfz.distance_km.toFixed(1)} km</span>
          </div>
        );
      } else if (metric === 'fuel' && route?.estimated_fuel_litres != null && route.estimated_fuel_litres > 0) {
        metricElements.push(
          <div key="fuel" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Est. Fuel</span>
            <span className="chat-priority-pill-val">~{route.estimated_fuel_litres.toFixed(1)} L</span>
          </div>
        );
      } else if (metric === 'transit_duration' && route?.estimated_duration_hours != null) {
        metricElements.push(
          <div key="duration" className="chat-priority-pill">
            <span className="chat-priority-pill-label">Duration</span>
            <span className="chat-priority-pill-val">{route.estimated_duration_hours.toFixed(1)} hrs</span>
          </div>
        );
      }
    }

    if (metricElements.length === 0) return null;

    return (
      <div className="chat-role-priority-strip">
        {metricElements}
      </div>
    );
  };

  const renderOrderedVisualizations = (
    payload: ChatResponse,
    visualOrder: VisualComponentType[],
    roleExpConfig: any
  ) => {
    if (!isVisuallyRelevant(payload)) return null;

    const weather = payload.weather;
    const ocean = payload.ocean;
    const risk = payload.risk;
    const routeRisk = payload.route_risk;
    const route = payload.transit_route;
    const temporal = payload.temporal_comparison;
    const nearestPfz = payload.spatial_features?.nearest_pfz || payload.geospatial?.nearest_pfz;
    const candidatePfzs = payload.candidate_pfzs || payload.context?.candidate_pfzs;

    const rendered: React.ReactNode[] = [];
    const seen = new Set<string>();

    for (const compType of visualOrder) {
      if (seen.has(compType)) continue;

      if (compType === 'fishing_window') {
        if (temporal) {
          seen.add(compType);
          rendered.push(
            <FishingWindowChart
              key="fishing_window"
              temporalComparison={temporal}
              weather={weather}
              ocean={ocean}
              risk={risk}
            />
          );
        }
      } else if (compType === 'marine_conditions') {
        if (weather || ocean) {
          seen.add(compType);
          rendered.push(
            <MarineConditionsChart
              key="marine_conditions"
              weather={weather}
              ocean={ocean}
              temporalComparison={temporal}
              roleExperience={roleExpConfig}
            />
          );
        }
      } else if (compType === 'wave_trend') {
        if (ocean || temporal) {
          seen.add(compType);
          rendered.push(
            <WaveTrendChart
              key="wave_trend"
              ocean={ocean}
              temporalComparison={temporal}
              selectedVessel={localVessel}
            />
          );
        }
      } else if (compType === 'weather_trend') {
        if (weather || temporal) {
          seen.add(compType);
          rendered.push(
            <WeatherTrendChart
              key="weather_trend"
              weather={weather}
              temporalComparison={temporal}
            />
          );
        }
      } else if (compType === 'risk_indicator') {
        if (risk || routeRisk) {
          seen.add(compType);
          rendered.push(
            <RiskIndicator
              key="risk_indicator"
              risk={risk}
              routeRisk={routeRisk}
              roleExperience={roleExpConfig}
              density={roleExpConfig.informationDensity}
            />
          );
        }
      } else if (compType === 'route_corridor') {
        if (route) {
          seen.add(compType);
          rendered.push(
            <InlineRouteCard
              key="route_corridor"
              route={route}
              roleExperience={roleExpConfig}
              onNavigateToRoute={onNavigateToRoute}
            />
          );
        }
      } else if (compType === 'pfz_card') {
        if (nearestPfz || (candidatePfzs && candidatePfzs.length > 0)) {
          seen.add(compType);
          rendered.push(
            <InlinePfzCard
              key="pfz_card"
              nearestPfz={nearestPfz}
              candidatePfzs={candidatePfzs}
              roleExperience={roleExpConfig}
              onSelectPfz={onSelectPfz}
              onNavigateToMarine={onNavigateToMarine}
            />
          );
        }
      }
    }

    if (rendered.length === 0) return null;

    return (
      <div className="visualizations-container">
        {rendered}
      </div>
    );
  };

  // Secondary Collapsible Drawers (collapsed by default to preserve chat height)
  const [isPromptsOpen, setIsPromptsOpen] = useState<boolean>(false);
  const [isSourcesOpen, setIsSourcesOpen] = useState<boolean>(false);
  const [isContextOpen, setIsContextOpen] = useState<boolean>(false);
  const [expandedMl, setExpandedMl] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const prevLoadingRef = useRef<boolean>(isLoading);

  // Auto-scroll strictly to newest message in message feed
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-focus chat input after message submission completes
  useEffect(() => {
    if (prevLoadingRef.current && !isLoading) {
      const active = document.activeElement;
      const isOtherInteractive = active && active !== document.body && active !== inputRef.current && (
        active.tagName === 'INPUT' || active.tagName === 'SELECT' || active.tagName === 'TEXTAREA'
      );
      if (!isOtherInteractive) {
        requestAnimationFrame(() => {
          inputRef.current?.focus();
        });
      }
    }
    prevLoadingRef.current = isLoading;
  }, [isLoading]);

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

  // Helper to format prose markdown text cleanly, including tables
  const renderProse = (content: string) => {
    const rawLines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let i = 0;

    const renderInline = (text: string) => {
      const parts = text.split(/(\*\*.*?\*\*)/g);
      return parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });
    };

    while (i < rawLines.length) {
      const line = rawLines[i];

      // Detect markdown table block (| ... |)
      if (line.trim().startsWith('|') && line.includes('|')) {
        const tableLines: string[] = [];
        while (i < rawLines.length && rawLines[i].trim().startsWith('|')) {
          tableLines.push(rawLines[i].trim());
          i++;
        }

        if (tableLines.length >= 2) {
          const parseCells = (rowStr: string) => {
            const stripped = rowStr.replace(/^\|/, '').replace(/\|$/, '');
            return stripped.split('|').map((c) => c.trim());
          };

          const headerCells = parseCells(tableLines[0]);
          // Row index 1 is header separator (| :--- | :--- |)
          const dataRows = tableLines.slice(2).map(parseCells);

          elements.push(
            <div key={`table-${i}`} className="chat-table-wrapper">
              <table className="chat-markdown-table">
                <thead>
                  <tr>
                    {headerCells.map((h, hIdx) => (
                      <th key={hIdx}>{renderInline(h)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataRows.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx}>{renderInline(cell)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
          continue;
        }
      }

      const rendered = renderInline(line);

      if (line.startsWith('>')) {
        elements.push(
          <div key={`line-${i}`} className="prose-note">
            {rendered}
          </div>
        );
      } else if (line.startsWith('•') || line.startsWith('-')) {
        elements.push(
          <div key={`line-${i}`} className="prose-bullet">
            {rendered}
          </div>
        );
      } else if (!line.trim()) {
        elements.push(<div key={`line-${i}`} className="prose-space" />);
      } else {
        elements.push(
          <p key={`line-${i}`} className="prose-line">
            {rendered}
          </p>
        );
      }
      i++;
    }

    return elements;
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

      {/* 2. Always-Visible Control Bar: Role, Vessel & Language Selectors */}
      <div className="chat-controls-bar">
        {/* Role Persona Selector */}
        {activeRole && onSwitchRole && (
          <div className="control-group">
            <span className="control-label">
              <Users size={12} color="#06b6d4" /> Role:
            </span>
            <button
              type="button"
              className="control-pill role-pill active"
              onClick={onSwitchRole}
              title={`Active Persona: ${activeRole.displayName}. Click to switch role.`}
            >
              <span>{activeRole.icon}</span>
              <span>{activeRole.shortName}</span>
              <span className="role-pill-switch-tag">Switch</span>
            </button>
          </div>
        )}

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
            {activeRole ? `SUGGESTED QUESTIONS FOR ${activeRole.displayName.toUpperCase()}:` : 'CLICK TO ASK ORCA:'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {effectiveQuickPrompts.map((prompt, idx) => (
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
          <DataSourcesSection latestResponse={latestResponse} compact={true} hasQueried={hasQueried} />
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
            {activeRole ? `Suggested questions for ${activeRole.displayName}:` : 'Suggested questions to get started:'}
          </div>
          <div className="quick-chips-row">
            {effectiveQuickPrompts.map((prompt, idx) => (
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
          const msgRoute = msg.responsePayload?.transit_route;

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
                      {activeRole && (
                        <span className="role-chat-badge" title={`Active Persona: ${activeRole.displayName}`}>
                          <span>{activeRole.icon}</span>
                          <span>{roleExp.badgeLabel}</span>
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: '0.65rem', color: '#64748b' }}>{msg.timestamp}</span>
                  </div>

                  {/* 1. Primary Conversational Text */}
                  <div className="message-text">
                    {renderProse(msg.text)}
                  </div>

                  {/* 2. Role-Prioritized Key Metrics Strip */}
                  {msg.responsePayload && renderPriorityMetrics(msg.responsePayload, roleExp.priorityMetrics)}

                  {/* 3. Role-Prioritized Ordered Visualizations */}
                  {msg.responsePayload && renderOrderedVisualizations(msg.responsePayload, roleExp.visualOrder, roleExp)}

                  {/* 4. Malayalam Advisory Drawer (if present) */}
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

                  {/* 5. Contextual Conversational Action Buttons */}
                  {(() => {
                    if (msg.responsePayload?.intent === 'marine_update') {
                      return null;
                    }
                    const cands = msg.responsePayload?.candidate_pfzs || msg.responsePayload?.context?.candidate_pfzs;
                    const candCount = cands && cands.length > 0 ? cands.length : 0;
                    const nearestPfz = msg.responsePayload?.spatial_features?.nearest_pfz || msg.responsePayload?.geospatial?.nearest_pfz;
                    const hasRouteOrCorridor = Boolean(msgRoute || msg.responsePayload?.intent === 'marine_safety' || msg.responsePayload?.intent === 'pfz_geofence_check' || msg.responsePayload?.intent === 'safe_passage_route' || msg.responsePayload?.intent === 'route_alternatives');

                    return (
                      <div className="chat-actions-strip">
                        {/* Action 1: Show all on Marine Map (for PFZ-radius queries with multiple candidates) */}
                        {candCount > 0 && onNavigateToMarine && (
                          <button
                            type="button"
                            className="chat-action-btn"
                            onClick={() => onNavigateToMarine()}
                          >
                            <MapPin size={13} />
                            <span>Show all on Marine Map ({candCount} targets)</span>
                          </button>
                        )}

                        {/* Action 2: Single Target Map Action */}
                        {candCount === 0 && nearestPfz && onSelectPfz && (
                          <button
                            type="button"
                            className="chat-action-btn"
                            onClick={() => onSelectPfz(nearestPfz)}
                          >
                            <MapPin size={13} />
                            <span>View on Marine Map ({nearestPfz.name})</span>
                          </button>
                        )}

                        {/* Action 3: Route Dashboard Action */}
                        {onNavigateToRoute && hasRouteOrCorridor && (
                          <button
                            type="button"
                            className="chat-action-btn route-action"
                            onClick={() => onNavigateToRoute()}
                          >
                            <Navigation size={13} />
                            <span>Open Safe Passage Corridor in Route & Safety</span>
                          </button>
                        )}
                      </div>
                    );
                  })()}

                  {/* 6. Role-Specific Suggested Follow-Up Questions */}
                  {roleExp.suggestedFollowUps && roleExp.suggestedFollowUps.length > 0 && (
                    <div className="chat-follow-up-strip">
                      <span className="follow-up-hint">Suggested follow-ups for {activeRole?.shortName || 'this role'}:</span>
                      <div className="follow-up-chips-row">
                        {roleExp.suggestedFollowUps.map((fu, fuIdx) => (
                          <button
                            key={fuIdx}
                            type="button"
                            className="follow-up-chip-btn"
                            onClick={() => handleQuickPrompt(fu)}
                            disabled={isLoading}
                          >
                            👉 {fu}
                          </button>
                        ))}
                      </div>
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
          ref={inputRef}
          type="text"
          className="chat-input-field"
          placeholder={roleExp.preferredTerminology.promptPlaceholder || "Ask ORCA about marine conditions, safety, or routes..."}
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
