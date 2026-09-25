import React from 'react';
import { Database, CloudSun, Waves, MapPin, Zap, Droplets } from 'lucide-react';
import {
  deriveWeatherStatus,
  deriveOceanStatus,
  deriveGisStatus,
  deriveLightningStatus,
  deriveChlorophyllStatus,
  deriveGlobalSourceStatus,
  type ChatResponse,
  type DataSourceStatus,
  type GlobalSourceStatus,
} from '../services/api';

interface DataSourcesSectionProps {
  latestResponse?: ChatResponse | null;
  compact?: boolean;
  hasQueried?: boolean;
}

export const DataSourcesSection: React.FC<DataSourcesSectionProps> = ({
  latestResponse,
  compact = false,
  hasQueried = false,
}) => {
  const weather = latestResponse?.weather;
  const ocean = latestResponse?.ocean;
  const geospatial = latestResponse?.geospatial;

  const globalStatus: GlobalSourceStatus = deriveGlobalSourceStatus(latestResponse, hasQueried);
  const weatherStatus: DataSourceStatus = deriveWeatherStatus(weather, hasQueried);
  const oceanStatus: DataSourceStatus = deriveOceanStatus(ocean, hasQueried);
  const gisStatus: DataSourceStatus = deriveGisStatus(geospatial, hasQueried);
  const lightningStatus: DataSourceStatus = deriveLightningStatus(weather, hasQueried);
  const chlorophyllStatus: DataSourceStatus = deriveChlorophyllStatus(ocean, hasQueried);

  const getStatusClass = (status: DataSourceStatus): string => {
    switch (status) {
      case 'READY':
        return 'status-ready';
      case 'LIVE':
        return 'status-live';
      case 'OFFICIAL SNAPSHOT':
        return 'status-snapshot';
      case 'MOCK FALLBACK':
        return 'status-fallback';
      case 'DEMO / MOCK':
        return 'status-demo';
      case 'UNSUPPORTED':
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
      detail: weatherStatus === 'READY'
        ? 'Awaiting query'
        : weather?.retrieved_at
        ? `Open-Meteo (Retrieved: ${new Date(weather.retrieved_at).toLocaleTimeString()})`
        : weatherStatus === 'LIVE'
        ? 'Open-Meteo Weather API'
        : weatherStatus === 'MOCK FALLBACK'
        ? 'Mock Fallback'
        : 'Prototype Mock',
    },
    {
      id: 'ocean',
      label: 'Marine / Ocean',
      icon: <Waves size={13} />,
      status: oceanStatus,
      detail: oceanStatus === 'READY'
        ? 'Awaiting query'
        : ocean?.retrieved_at
        ? `Open-Meteo Marine (Retrieved: ${new Date(ocean.retrieved_at).toLocaleTimeString()})`
        : oceanStatus === 'LIVE'
        ? 'Open-Meteo Marine API'
        : oceanStatus === 'MOCK FALLBACK'
        ? 'Mock Fallback'
        : 'Prototype Mock',
    },
    {
      id: 'gis',
      label: 'PFZ / GIS',
      icon: <MapPin size={13} />,
      status: gisStatus,
      detail: gisStatus === 'READY'
        ? 'Awaiting query'
        : gisStatus === 'OFFICIAL SNAPSHOT'
        ? (geospatial?.advisory_date ? `INCOIS Snapshot (${geospatial.advisory_date.split('T')[0]})` : 'INCOIS historical snapshot')
        : gisStatus === 'MOCK FALLBACK'
        ? 'Mock Fallback'
        : 'INCOIS historical snapshot',
    },
    {
      id: 'lightning',
      label: 'Lightning',
      icon: <Zap size={13} />,
      status: lightningStatus,
      detail: lightningStatus === 'READY'
        ? 'Awaiting query'
        : 'Unsupported by current upstream source',
    },
    {
      id: 'chlorophyll',
      label: 'Chlorophyll',
      icon: <Droplets size={13} />,
      status: chlorophyllStatus,
      detail: chlorophyllStatus === 'READY'
        ? 'Awaiting query'
        : 'Not available from current live feed',
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
          {globalStatus === 'READY' ? (
            <span className="mode-badge ready-active">
              <span className="dot-pulse ready" /> SOURCE: READY
            </span>
          ) : globalStatus === 'LIVE (HYBRID)' ? (
            <span className="mode-badge live-active">
              <span className="dot-pulse" /> LIVE FORECAST FEED ACTIVE
            </span>
          ) : globalStatus === 'OFFICIAL SNAPSHOT' ? (
            <span className="mode-badge snapshot-active">
              <span className="dot-pulse snapshot" /> OFFICIAL SNAPSHOT
            </span>
          ) : globalStatus === 'MOCK FALLBACK' ? (
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
