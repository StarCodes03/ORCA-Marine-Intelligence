import React from 'react';
import { Database, CloudSun, Waves, MapPin, Zap, Droplets } from 'lucide-react';
import {
  deriveWeatherStatus,
  deriveOceanStatus,
  deriveGisStatus,
  deriveLightningStatus,
  deriveChlorophyllStatus,
  type ChatResponse,
  type DataSourceStatus,
} from '../services/api';

interface DataSourcesSectionProps {
  latestResponse?: ChatResponse | null;
  compact?: boolean;
}

export const DataSourcesSection: React.FC<DataSourcesSectionProps> = ({
  latestResponse,
  compact = false,
}) => {
  const weather = latestResponse?.weather;
  const ocean = latestResponse?.ocean;
  const geospatial = latestResponse?.geospatial;

  const weatherStatus: DataSourceStatus = deriveWeatherStatus(weather);
  const oceanStatus: DataSourceStatus = deriveOceanStatus(ocean);
  const gisStatus: DataSourceStatus = deriveGisStatus(geospatial);
  const lightningStatus: DataSourceStatus = deriveLightningStatus(weather);
  const chlorophyllStatus: DataSourceStatus = deriveChlorophyllStatus(ocean);

  const getStatusClass = (status: DataSourceStatus): string => {
    switch (status) {
      case 'LIVE':
        return 'status-live';
      case 'OFFICIAL SNAPSHOT':
        return 'status-snapshot';
      case 'MOCK FALLBACK':
        return 'status-fallback';
      case 'DEMO / MOCK':
        return 'status-demo';
      case 'UNAVAILABLE':
      default:
        return 'status-unavailable';
    }
  };

  const sources = [
    {
      id: 'weather',
      label: 'Weather',
      icon: <CloudSun size={13} />,
      status: weatherStatus,
      detail: weather?.source || (weatherStatus === 'LIVE' ? 'Open-Meteo' : 'Prototype Mock'),
    },
    {
      id: 'ocean',
      label: 'Marine / Ocean',
      icon: <Waves size={13} />,
      status: oceanStatus,
      detail: ocean?.source || (oceanStatus === 'LIVE' ? 'Open-Meteo Marine' : 'Prototype Mock'),
    },
    {
      id: 'gis',
      label: 'PFZ / GIS',
      icon: <MapPin size={13} />,
      status: gisStatus,
      detail: gisStatus === 'OFFICIAL SNAPSHOT'
        ? (geospatial?.advisory_date ? `INCOIS Snapshot (${geospatial.advisory_date.split('T')[0]})` : 'INCOIS Official Snapshot')
        : gisStatus === 'MOCK FALLBACK'
        ? 'Mock Fallback'
        : 'INCOIS Simulated GIS',
    },
    {
      id: 'lightning',
      label: 'Lightning',
      icon: <Zap size={13} />,
      status: lightningStatus,
      detail: lightningStatus === 'UNAVAILABLE' ? 'Unsupported by API' : 'Simulated',
    },
    {
      id: 'chlorophyll',
      label: 'Chlorophyll',
      icon: <Droplets size={13} />,
      status: chlorophyllStatus,
      detail: chlorophyllStatus === 'UNAVAILABLE' ? 'Not in live feed' : 'Simulated',
    },
  ];

  return (
    <div className={`data-sources-section ${compact ? 'compact' : ''}`} role="region" aria-label="Data Sources Status">
      <div className="data-sources-header">
        <div className="data-sources-title">
          <Database size={13} className="header-icon" />
          <span>DATA PROVENANCE & SOURCE STATUS</span>
        </div>
        <div className="data-sources-mode-pill">
          {weatherStatus === 'LIVE' || oceanStatus === 'LIVE' ? (
            <span className="mode-badge live-active">
              <span className="dot-pulse" /> LIVE TELEMETRY ACTIVE
            </span>
          ) : weatherStatus === 'MOCK FALLBACK' || oceanStatus === 'MOCK FALLBACK' ? (
            <span className="mode-badge fallback-active">
              <span className="dot-pulse fallback" /> FALLBACK ACTIVE
            </span>
          ) : (
            <span className="mode-badge demo-active">DEMO / MOCK MODE</span>
          )}
        </div>
      </div>

      <div className="data-sources-grid">
        {sources.map((item) => (
          <div key={item.id} className="data-source-card" title={`${item.label}: ${item.status} (${item.detail})`}>
            <div className="source-meta">
              <span className="source-icon">{item.icon}</span>
              <span className="source-name">{item.label}</span>
            </div>
            <div className={`status-pill ${getStatusClass(item.status)}`}>
              <span className="status-dot" />
              <span className="status-text">{item.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
