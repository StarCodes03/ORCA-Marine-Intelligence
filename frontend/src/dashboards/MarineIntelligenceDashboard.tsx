import React, { useState } from 'react';
import { Layers, Sliders, MapPin, Compass, Navigation, Info } from 'lucide-react';
import { MarineMap } from '../map/MarineMap';
import type { LocationCoords, NearestPFZ, TransitRoute } from '../services/api';

interface MarineIntelligenceDashboardProps {
  vesselLocation: LocationCoords;
  nearestPfz: NearestPFZ | null;
  spatialLayers: any;
  transitRoute?: TransitRoute | null;
  onSelectPfz: (pfz: NearestPFZ) => void;
  onNavigateToRoute?: () => void;
}

const RADIUS_OPTIONS = [
  { label: 'All', value: null },
  { label: '15 km', value: 15 },
  { label: '25 km', value: 25 },
  { label: '30 km', value: 30 },
  { label: '50 km', value: 50 },
];

export const MarineIntelligenceDashboard: React.FC<MarineIntelligenceDashboardProps> = ({
  vesselLocation,
  nearestPfz,
  spatialLayers,
  transitRoute,
  onSelectPfz,
  onNavigateToRoute,
}) => {
  const [showPfz, setShowPfz] = useState<boolean>(true);
  const [showRestricted, setShowRestricted] = useState<boolean>(true);
  const [showVessel, setShowVessel] = useState<boolean>(true);
  const [showRoute, setShowRoute] = useState<boolean>(true);
  const [selectedRadius, setSelectedRadius] = useState<number | null>(null);
  const [isLayerPanelOpen, setIsLayerPanelOpen] = useState<boolean>(true);

  // Fallback target if none selected yet
  const displayTarget = nearestPfz || (spatialLayers?.pfz?.features?.[0]?.properties as NearestPFZ) || null;

  return (
    <div className="workspace-pane marine-workspace-pane">
      {/* Top Workspace Header */}
      <div className="workspace-header">
        <div className="workspace-header-title">
          <Compass size={17} color="#06b6d4" />
          <span>MARINE INTELLIGENCE</span>
          <span className="workspace-header-badge">GIS & SPATIAL DOMAIN</span>
        </div>
        <div className="workspace-header-meta">
          <span>Sector: Kochi Coastal Waters / Arabian Sea</span>
        </div>
      </div>

      {/* Main Workspace Body with Map and Overlays */}
      <div className="marine-map-wrapper">
        {/* Floating Layer & Filter Control Panel */}
        <div className={`marine-controls-card ${isLayerPanelOpen ? 'expanded' : 'collapsed'}`}>
          <div
            className="marine-controls-header"
            onClick={() => setIsLayerPanelOpen(!isLayerPanelOpen)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Layers size={14} color="#06b6d4" />
              <span>LAYERS & FILTERS</span>
            </div>
            <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
              {isLayerPanelOpen ? 'Hide' : 'Show'}
            </span>
          </div>

          {isLayerPanelOpen && (
            <div className="marine-controls-body">
              {/* Layer Toggles */}
              <div className="control-section">
                <div className="control-section-label">MAP LAYERS</div>
                <label className="layer-checkbox-label">
                  <input
                    type="checkbox"
                    checked={showPfz}
                    onChange={(e) => setShowPfz(e.target.checked)}
                  />
                  <span className="layer-swatch" style={{ background: '#10b981' }} />
                  <span>PFZ Targets (INCOIS)</span>
                </label>
                <label className="layer-checkbox-label">
                  <input
                    type="checkbox"
                    checked={showRestricted}
                    onChange={(e) => setShowRestricted(e.target.checked)}
                  />
                  <span className="layer-swatch" style={{ background: '#ef4444' }} />
                  <span>Restricted Zones</span>
                </label>
                <label className="layer-checkbox-label">
                  <input
                    type="checkbox"
                    checked={showVessel}
                    onChange={(e) => setShowVessel(e.target.checked)}
                  />
                  <span className="layer-swatch" style={{ background: '#0284c7' }} />
                  <span>Vessel Location</span>
                </label>
                <label className="layer-checkbox-label">
                  <input
                    type="checkbox"
                    checked={showRoute}
                    onChange={(e) => setShowRoute(e.target.checked)}
                  />
                  <span className="layer-swatch" style={{ background: '#f59e0b' }} />
                  <span>Safe Passage Corridor</span>
                </label>
              </div>

              {/* Radius Filter */}
              <div className="control-section">
                <div className="control-section-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Sliders size={11} />
                  <span>DISTANCE FILTER</span>
                </div>
                <div className="radius-pills-grid">
                  {RADIUS_OPTIONS.map((opt) => (
                    <button
                      key={opt.label}
                      type="button"
                      className={`radius-pill ${selectedRadius === opt.value ? 'active' : ''}`}
                      onClick={() => setSelectedRadius(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                {selectedRadius && (
                  <div style={{ fontSize: '0.64rem', color: '#38bdf8', marginTop: '4px' }}>
                    Showing targets within {selectedRadius} km
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Large Marine Map */}
        <MarineMap
          vesselLocation={vesselLocation}
          nearestPfz={nearestPfz}
          spatialLayers={spatialLayers}
          highlightRoute={Boolean(nearestPfz || transitRoute)}
          transitRoute={transitRoute}
          showVessel={showVessel}
          showPfz={showPfz}
          showRestricted={showRestricted}
          showRoute={showRoute}
          radiusFilterKm={selectedRadius}
          onSelectPfz={onSelectPfz}
          hideFloatingLegend={true}
        />

        {/* Bottom Selected PFZ Target Details Bar */}
        <div className="selected-target-bar">
          <div className="target-bar-main">
            <div className="target-bar-header">
              <div className="target-bar-badge">
                <MapPin size={12} />
                <span>SELECTED PFZ TARGET</span>
              </div>
              {displayTarget?.name && (
                <div className="target-bar-title">{displayTarget.name}</div>
              )}
            </div>

            {displayTarget ? (
              <div className="target-metrics-row">
                {displayTarget.distance_km != null && (
                  <div className="target-metric-item">
                    <span className="metric-label">DISTANCE FROM VESSEL</span>
                    <span className="metric-value">{displayTarget.distance_km} km</span>
                  </div>
                )}
                {displayTarget.bearing_deg != null && (
                  <div className="target-metric-item">
                    <span className="metric-label">BEARING</span>
                    <span className="metric-value">
                      {displayTarget.bearing_deg}° {displayTarget.direction || ''}
                    </span>
                  </div>
                )}
                {displayTarget.landing_centre && (
                  <div className="target-metric-item">
                    <span className="metric-label">ASSOCIATED LANDING CENTRE</span>
                    <span className="metric-value">{displayTarget.landing_centre}</span>
                  </div>
                )}
                {displayTarget.depth_m && (
                  <div className="target-metric-item">
                    <span className="metric-label">WATER DEPTH</span>
                    <span className="metric-value">{displayTarget.depth_m}</span>
                  </div>
                )}
                {displayTarget.latitude != null && displayTarget.longitude != null && (
                  <div className="target-metric-item">
                    <span className="metric-label">COORDINATES</span>
                    <span className="metric-value font-mono">
                      {displayTarget.latitude.toFixed(4)}° N, {displayTarget.longitude.toFixed(4)}° E
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="target-none-text">
                No PFZ Target selected. Click a green marker on the map to inspect snapshot target details.
              </div>
            )}

            {/* Mandatory Historical Snapshot Notice */}
            <div className="target-disclaimer-note">
              <Info size={11} color="#38bdf8" />
              <span>
                Historical INCOIS landing-centre-associated PFZ target • Demonstrational snapshot data • Not a live fishing advisory.
              </span>
            </div>
          </div>

          {/* Action Button: Navigate to Route Dashboard */}
          {onNavigateToRoute && displayTarget && (
            <button
              type="button"
              className="target-route-btn"
              onClick={onNavigateToRoute}
              title="Inspect Safe Passage Corridor and Seaworthiness"
            >
              <Navigation size={14} />
              <span>Inspect Route</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
