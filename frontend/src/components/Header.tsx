import React from 'react';
import { Compass, Shield, AlertTriangle, Radio } from 'lucide-react';
import {
  deriveWeatherStatus,
  deriveOceanStatus,
  type ChatResponse,
} from '../services/api';

interface HeaderProps {
  systemHealthy: boolean;
  sectorName?: string;
  latestResponse?: ChatResponse | null;
}

export const Header: React.FC<HeaderProps> = ({
  systemHealthy,
  sectorName = 'Kochi Coastal Sector, Kerala',
  latestResponse,
}) => {
  const weatherStatus = deriveWeatherStatus(latestResponse?.weather);
  const oceanStatus = deriveOceanStatus(latestResponse?.ocean);

  const isLive = weatherStatus === 'LIVE' || oceanStatus === 'LIVE';
  const isFallback = weatherStatus === 'MOCK FALLBACK' || oceanStatus === 'MOCK FALLBACK';

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
        <div className="pill-badge sector">
          <Shield size={13} />
          <span>Sector: {sectorName}</span>
        </div>

        {/* Dynamic Data Provenance Status Indicator */}
        {isLive ? (
          <div className="pill-badge live-source-badge" title="Live Open-Meteo telemetry active for Weather and Marine layers">
            <Radio size={13} className="live-icon-pulse" />
            <span>SOURCE: LIVE (HYBRID)</span>
          </div>
        ) : isFallback ? (
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
