import React from 'react';
import { Compass, Shield, AlertTriangle, Radio } from 'lucide-react';
import { deriveGlobalSourceStatus, type ChatResponse, type GlobalSourceStatus } from '../services/api';
import type { RoleConfig } from '../config/roles';

interface HeaderProps {
  systemHealthy: boolean;
  sectorName?: string;
  latestResponse?: ChatResponse | null;
  hasQueried?: boolean;
  activeRole?: RoleConfig;
  onSwitchRole?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  systemHealthy,
  sectorName = 'Kochi Coastal Sector, Kerala',
  latestResponse,
  hasQueried = false,
  activeRole,
  onSwitchRole,
}) => {
  const globalStatus: GlobalSourceStatus = deriveGlobalSourceStatus(latestResponse, hasQueried);

  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo-icon">
          <Compass size={20} />
        </div>
        <div className="brand-titles">
          <h1>ORCA</h1>
          <span>Marine Ecosystem Reasoning with Collaborative Agents</span>
        </div>
      </div>

      <div className="header-status-pills">
        {/* Role Selector Pill */}
        {activeRole && (
          <button
            type="button"
            className="pill-badge role-header-pill"
            onClick={onSwitchRole}
            title={`Active Persona: ${activeRole.displayName}. Click to switch role.`}
          >
            <span className="role-header-icon">{activeRole.icon}</span>
            <span className="role-header-name">{activeRole.displayName}</span>
            <span className="role-header-switch-tag">Switch</span>
          </button>
        )}

        <div className="pill-badge sector">
          <Shield size={13} />
          <span>Sector: {sectorName}</span>
        </div>

        {/* Dynamic Data Provenance Status Indicator */}
        {globalStatus === 'READY' ? (
          <div className="pill-badge ready-source-badge" title="ORCA agent collective ready. Awaiting user query.">
            <Radio size={13} className="ready-icon" />
            <span>SOURCE: READY</span>
          </div>
        ) : globalStatus === 'LIVE (HYBRID)' ? (
          <div className="pill-badge live-source-badge" title="Live Open-Meteo forecast feeds active for Weather and Marine layers + Official INCOIS snapshot">
            <Radio size={13} className="live-icon-pulse" />
            <span>SOURCE: LIVE (HYBRID)</span>
          </div>
        ) : globalStatus === 'OFFICIAL SNAPSHOT' ? (
          <div className="pill-badge snapshot-badge" title="Historical INCOIS landing-centre PFZ advisory snapshot active">
            <Radio size={13} />
            <span>SOURCE: OFFICIAL SNAPSHOT</span>
          </div>
        ) : globalStatus === 'MOCK FALLBACK' ? (
          <div className="pill-badge fallback-badge" title="Live API call failed; automatic fallback to demonstration mock data active">
            <AlertTriangle size={13} />
            <span>SOURCE: MOCK FALLBACK</span>
          </div>
        ) : (
          <div className="pill-badge demo-mock-badge" title="Prototype Demonstration Data Only">
            <AlertTriangle size={13} />
            <span>SOURCE: DEMO / MOCK</span>
          </div>
        )}

        <div className="pill-badge">
          <span className={`pulsing-dot ${systemHealthy ? '' : 'bg-red-500'}`} />
          <span>{systemHealthy ? 'Agents Online' : 'Connecting...'}</span>
        </div>
      </div>
    </header>
  );
};
