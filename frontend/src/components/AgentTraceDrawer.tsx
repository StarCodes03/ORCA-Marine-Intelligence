import React, { useState } from 'react';
import { ChevronUp, ChevronDown, Terminal, Cpu, Database, CheckCircle2 } from 'lucide-react';
import type { ChatResponse } from '../services/api';

interface AgentTraceDrawerProps {
  latestResponse: ChatResponse | null;
}

export const AgentTraceDrawer: React.FC<AgentTraceDrawerProps> = ({ latestResponse }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  const trace = latestResponse?.agent_trace || [];

  const getAgentPayload = (agentName: string) => {
    if (!latestResponse) return null;
    switch (agentName) {
      case 'PlannerAgent':
        return {
          intent: latestResponse.intent,
          location: latestResponse.location,
          required_agents: latestResponse.agent_trace.filter(
            a => !['PlannerAgent', 'RiskAssessmentAgent', 'EvidenceAgent'].includes(a)
          ),
        };
      case 'WeatherAgent':
        return latestResponse.weather || { status: 'Not invoked for this query' };
      case 'OceanAgent':
        return latestResponse.ocean || { status: 'Not invoked for this query' };
      case 'GeospatialAgent':
        return latestResponse.geospatial || { status: 'Not invoked for this query' };
      case 'RiskAssessmentAgent':
        return latestResponse.risk || { status: 'Not invoked for this query' };
      case 'EvidenceAgent':
        return {
          evidence_items: latestResponse.evidence,
          final_answer_length: latestResponse.answer.length,
        };
      default:
        return null;
    }
  };

  return (
    <div className={`trace-drawer ${isExpanded ? 'expanded' : 'collapsed'}`}>
      {/* Drawer Header */}
      <div className="trace-drawer-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="trace-drawer-title">
          <Terminal size={14} />
          <span>Developer Audit Trace & Multi-Agent Pipeline</span>
          {trace.length > 0 && (
            <span style={{ fontSize: '0.7rem', color: '#94a3b8', marginLeft: '8px' }}>
              ({trace.length} agents executed)
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8' }}>
          <span style={{ fontSize: '0.72rem' }}>{isExpanded ? 'Collapse' : 'Inspect Trace'}</span>
          {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
        </div>
      </div>

      {/* Pipeline Steps Sequence */}
      {isExpanded && (
        <>
          <div className="trace-pipeline">
            {trace.length === 0 ? (
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                No queries executed yet. Submit a prompt to view the LangGraph execution flow.
              </span>
            ) : (
              trace.map((agent, idx) => {
                const isSel = (selectedAgent || trace[0]) === agent;
                return (
                  <React.Fragment key={agent + idx}>
                    <div
                      className={`pipeline-step ${isSel ? 'active' : ''}`}
                      onClick={() => setSelectedAgent(agent)}
                      style={{ cursor: 'pointer' }}
                    >
                      <Cpu size={12} />
                      <span>{agent}</span>
                      <CheckCircle2 size={11} color="#10b981" />
                    </div>
                    {idx < trace.length - 1 && (
                      <span style={{ color: '#475569', fontSize: '10px' }}>➔</span>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </div>

          {/* Trace Content / Payload Viewer */}
          <div className="trace-drawer-content">
            {trace.length > 0 && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                  <Database size={13} color="#06b6d4" />
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e2e8f0' }}>
                    Agent Output Payload: {selectedAgent || trace[0]}
                  </span>
                </div>
                <div className="trace-json-box">
                  {JSON.stringify(getAgentPayload(selectedAgent || trace[0]), null, 2)}
                </div>
              </div>
            )}

            {/* Evidence Audit Items */}
            {latestResponse?.evidence && latestResponse.evidence.length > 0 && (
              <div style={{ marginTop: '4px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e2e8f0' }}>
                  Evidentiary Claims ({latestResponse.evidence.length}):
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
                  {latestResponse.evidence.map((ev, i) => (
                    <div
                      key={i}
                      style={{
                        fontSize: '0.72rem',
                        padding: '4px 8px',
                        background: '#090e1a',
                        borderLeft: '3px solid #0284c7',
                        borderRadius: '3px',
                      }}
                    >
                      <span style={{ color: '#38bdf8', fontWeight: 600 }}>[{ev.category.toUpperCase()}]</span>{' '}
                      <span style={{ color: '#cbd5e1' }}>{ev.claim}</span>{' '}
                      <span style={{ color: '#64748b' }}>({ev.source})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
