import React, { useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polygon,
  Polyline,
  CircleMarker,
  useMap
} from 'react-leaflet';
import L from 'leaflet';
import { AlertTriangle, Fish } from 'lucide-react';
import type { NearestPFZ, LocationCoords, TransitRoute } from '../services/api';

interface MarineMapProps {
  vesselLocation: LocationCoords;
  nearestPfz?: NearestPFZ | null;
  spatialLayers?: any;
  highlightRoute?: boolean;
  transitRoute?: TransitRoute | null;
  showVessel?: boolean;
  showPfz?: boolean;
  showRestricted?: boolean;
  showRoute?: boolean;
  showAlternatives?: boolean;
  radiusFilterKm?: number | null;
  onSelectPfz?: (pfz: NearestPFZ) => void;
  hideFloatingLegend?: boolean;
}

function computeDistanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Controller to smoothly pan/zoom map and fit bounds when target PFZ or route updates
function MapViewController({
  vesselCoords,
  targetPfz,
  transitRoute,
}: {
  vesselCoords: [number, number];
  targetPfz?: NearestPFZ | null;
  transitRoute?: TransitRoute | null;
}) {
  const map = useMap();

  useEffect(() => {
    const points: [number, number][] = [vesselCoords];

    if (transitRoute && transitRoute.waypoints?.length > 0) {
      transitRoute.waypoints.forEach((wp) => {
        points.push([wp.latitude, wp.longitude]);
      });
    }

    if (targetPfz && targetPfz.latitude && targetPfz.longitude) {
      points.push([targetPfz.latitude, targetPfz.longitude]);
    }

    if (points.length > 1) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 11, animate: true });
    } else {
      map.panTo(vesselCoords, { animate: true });
    }
  }, [vesselCoords, targetPfz, transitRoute, map]);

  return null;
}

// Custom DivIcons
const vesselIcon = L.divIcon({
  className: 'custom-vessel-marker',
  html: `<div style="
    background: #0284c7;
    border: 2px solid #ffffff;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 10px #0284c7;
    color: white;
    font-size: 12px;
  ">⛵</div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const pfzIcon = L.divIcon({
  className: 'custom-pfz-marker',
  html: `<div style="
    background: #10b981;
    border: 2px solid #ffffff;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 12px #10b981;
    color: white;
    font-size: 13px;
  ">🐟</div>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

const activePfzIcon = L.divIcon({
  className: 'custom-pfz-marker-active',
  html: `<div style="
    background: #06b6d4;
    border: 3px solid #f8fafc;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 20px #06b6d4;
    color: white;
    font-size: 16px;
    animation: pulse 1.5s infinite;
  ">🎯</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const portIcon = L.divIcon({
  className: 'custom-port-marker',
  html: `<div style="
    background: #475569;
    border: 2px solid #ffffff;
    width: 22px;
    height: 22px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 11px;
  ">⚓</div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

const waypointIcon = L.divIcon({
  className: 'custom-wp-marker',
  html: `<div style="
    background: #f59e0b;
    border: 2px solid #ffffff;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 10px #f59e0b;
    color: white;
    font-size: 10px;
    font-weight: 800;
  ">WP</div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

export const MarineMap: React.FC<MarineMapProps> = ({
  vesselLocation,
  nearestPfz,
  spatialLayers,
  highlightRoute = true,
  transitRoute,
  showVessel = true,
  showPfz = true,
  showRestricted = true,
  showRoute = true,
  showAlternatives = true,
  radiusFilterKm = null,
  onSelectPfz,
  hideFloatingLegend = false,
}) => {
  const defaultCenter: [number, number] = [9.9312, 76.2673]; // Kochi
  const vesselCoords: [number, number] = [
    vesselLocation.latitude,
    vesselLocation.longitude,
  ];

  // Extract PFZ features, ensuring nearestPfz is always represented
  const rawFeatures = spatialLayers?.pfz?.features || [];
  let pfzFeatures = [...rawFeatures];
  if (
    nearestPfz &&
    !pfzFeatures.some(
      (f: any) =>
        (f.properties?.pfz_id || f.pfz_id) === nearestPfz.pfz_id ||
        (f.properties?.name || f.name) === nearestPfz.name
    )
  ) {
    pfzFeatures.push({
      type: 'Feature',
      properties: { ...nearestPfz, source: 'DEMO_GIS_DATA' },
      geometry: {
        type: 'Point',
        coordinates: [nearestPfz.longitude, nearestPfz.latitude],
      },
    });
  }

  // Apply radius filter if specified
  if (radiusFilterKm != null && radiusFilterKm > 0) {
    pfzFeatures = pfzFeatures.filter((feat: any) => {
      const pt = feat.geometry?.coordinates || [feat.longitude, feat.latitude] || [0, 0];
      const dist = computeDistanceKm(vesselCoords[0], vesselCoords[1], pt[1], pt[0]);
      const isTarget = Boolean(
        nearestPfz &&
        ((feat.properties?.pfz_id || feat.pfz_id) === nearestPfz.pfz_id ||
         (feat.properties?.name || feat.name) === nearestPfz.name)
      );
      return dist <= radiusFilterKm || isTarget;
    });
  }

  // Extract Restricted Zone features
  const restrictedFeatures = spatialLayers?.restricted_zones?.features || [];

  return (
    <div className="map-pane">
      {/* Floating Legend / Quick Layer Status */}
      {!hideFloatingLegend && (
        <div className="map-floating-overlay">
          <div className="map-legend-item">
            <span className="legend-swatch" style={{ background: '#0284c7' }} />
            <span>Vessel Location</span>
          </div>
          <div className="map-legend-item">
            <span className="legend-swatch" style={{ background: '#10b981' }} />
            <span>PFZ Targets</span>
          </div>
          <div className="map-legend-item">
            <span className="legend-swatch" style={{ background: 'rgba(239, 68, 68, 0.4)', border: '1px solid #ef4444' }} />
            <span>Restricted Maritime Zones</span>
          </div>
        </div>
      )}

      <MapContainer
        center={defaultCenter}
        zoom={10}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        <MapViewController vesselCoords={vesselCoords} targetPfz={nearestPfz} transitRoute={transitRoute} />

        {/* Base Tile Layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Kochi Reference Station Marker */}
        <Marker position={defaultCenter} icon={portIcon}>
          <Popup>
            <div style={{ padding: '4px' }}>
              <strong style={{ color: '#38bdf8' }}>Kochi Coastal Reference Base</strong>
              <p style={{ fontSize: '11px', color: '#94a3b8', margin: '4px 0 0 0' }}>
                Coordinates: 9.9312° N, 76.2673° E<br />
                Source: DEMO_GIS_DATA
              </p>
            </div>
          </Popup>
        </Marker>

        {/* User / Demo Vessel Marker */}
        {showVessel && (
          <Marker position={vesselCoords} icon={vesselIcon}>
            <Popup>
              <div style={{ padding: '4px' }}>
                <strong style={{ color: '#0284c7' }}>Operational Vessel (Demo)</strong>
                <p style={{ fontSize: '11px', color: '#cbd5e1', margin: '4px 0 0 0' }}>
                  Status: Underway / Standby<br />
                  Position: {vesselCoords[0].toFixed(4)}° N, {vesselCoords[1].toFixed(4)}° E
                </p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Restricted Maritime Zones Polygons */}
        {showRestricted &&
          restrictedFeatures.map((feat: any, idx: number) => {
            const coords = feat.geometry?.coordinates?.[0] || [];
            // Leaflet expects [lat, lng] while GeoJSON is [lng, lat]
            const latLngs: [number, number][] = coords.map((pt: [number, number]) => [pt[1], pt[0]]);
            const props = feat.properties || {};

            return (
              <Polygon
                key={props.zone_id || idx}
                positions={latLngs}
                pathOptions={{
                  color: '#ef4444',
                  fillColor: '#dc2626',
                  fillOpacity: 0.25,
                  weight: 2,
                  dashArray: '4, 4',
                }}
              >
                <Popup>
                  <div style={{ padding: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f87171' }}>
                      <AlertTriangle size={15} />
                      <strong>{props.name}</strong>
                    </div>
                    <p style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
                      <strong>Restriction:</strong> {props.restriction_level}<br />
                      <strong>Category:</strong> {props.category}<br />
                      <span style={{ color: '#94a3b8' }}>Source: {props.source || 'DEMO_GIS_DATA'}</span>
                    </p>
                  </div>
                </Popup>
              </Polygon>
            );
          })}

        {/* Potential Fishing Zones (PFZs) */}
        {showPfz &&
          pfzFeatures.map((feat: any, idx: number) => {
            const pt = feat.geometry?.coordinates || [feat.longitude, feat.latitude] || [0, 0];
            const lat = pt[1];
            const lon = pt[0];
            const props = feat.properties || feat || {};
            const isTarget = Boolean(
              nearestPfz &&
              ((props.pfz_id && nearestPfz.pfz_id === props.pfz_id) ||
               (props.name && nearestPfz.name === props.name))
            );

            return (
              <React.Fragment key={`${props.pfz_id || idx}-${isTarget ? 'active' : 'normal'}`}>
                <Marker
                  position={[lat, lon]}
                  icon={isTarget ? activePfzIcon : pfzIcon}
                  zIndexOffset={isTarget ? 1000 : 10}
                >
                  <Popup>
                    <div style={{ padding: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: isTarget ? '#06b6d4' : '#10b981' }}>
                        <Fish size={15} />
                        <strong>{props.name}</strong>
                        {isTarget && (
                          <span style={{
                            background: '#06b6d4',
                            color: '#ffffff',
                            fontSize: '9px',
                            fontWeight: 700,
                            padding: '1px 5px',
                            borderRadius: '3px'
                          }}>
                            TARGET PFZ
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '6px', lineHeight: 1.4 }}>
                        <div><strong>ID:</strong> {props.pfz_id}</div>
                        {props.landing_centre && <div><strong>Associated Landing Centre:</strong> {props.landing_centre}</div>}
                        {props.distance_km && <div><strong>Distance from LC:</strong> {props.distance_km}</div>}
                        {props.bearing_deg != null && <div><strong>Bearing:</strong> {props.bearing_deg}° {props.direction || ''}</div>}
                        {props.depth_m && <div><strong>Depth:</strong> {props.depth_m}</div>}
                        {props.target_species && <div><strong>Target Species:</strong> {props.target_species}</div>}
                        {props.sst_c != null && <div><strong>SST:</strong> {props.sst_c} °C</div>}
                        {props.chlorophyll_mg_m3 != null && <div><strong>Chlorophyll:</strong> {props.chlorophyll_mg_m3} mg/m³</div>}
                        {props.confidence_score != null && <div><strong>Confidence:</strong> {Math.round(props.confidence_score * 100)}%</div>}
                        <div style={{ marginTop: '4px', color: '#94a3b8' }}>
                          Source: {props.source || 'DEMO_GIS_DATA'}
                          {props.source_type && ` (${props.source_type})`}
                        </div>
                        {onSelectPfz && !isTarget && (
                          <button
                            type="button"
                            onClick={() => onSelectPfz(props)}
                            style={{
                              marginTop: '6px',
                              background: '#0284c7',
                              color: '#ffffff',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '3px 8px',
                              fontSize: '10px',
                              cursor: 'pointer'
                            }}
                          >
                            Set as Focus Target
                          </button>
                        )}
                        <div style={{
                          fontSize: '10px',
                          color: '#7dd3fc',
                          marginTop: '6px',
                          fontStyle: 'italic',
                          borderTop: '1px solid rgba(255,255,255,0.1)',
                          paddingTop: '4px'
                        }}>
                          Historical INCOIS landing-centre-associated PFZ target — not a live fishing advisory.
                        </div>
                      </div>
                    </div>
                  </Popup>
                </Marker>

                {/* Pulsing ring around target PFZ */}
                {isTarget && (
                  <CircleMarker
                    center={[lat, lon]}
                    radius={24}
                    pathOptions={{
                      color: '#06b6d4',
                      fillColor: '#06b6d4',
                      fillOpacity: 0.1,
                      weight: 1.5,
                      dashArray: '3, 3'
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}

        {/* Safe Passage Transit Corridor Route (M4) */}
        {showRoute && highlightRoute && transitRoute?.geojson_feature?.geometry?.coordinates && (
          <Polyline
            positions={transitRoute.geojson_feature.geometry.coordinates.map((coord: number[]) => [coord[1], coord[0]])}
            pathOptions={{
              color: transitRoute.geofence_avoidance_applied ? '#f59e0b' : '#06b6d4',
              weight: 3.5,
              dashArray: '8, 6',
              opacity: 0.95
            }}
          />
        )}

        {/* Route Alternatives (Direct & High-Clearance Seaward) */}
        {showRoute && showAlternatives && transitRoute?.alternatives?.map((alt) => {
          if (alt.alternative_id === 'safe_corridor') return null;
          const coords = alt.geojson_feature?.geometry?.coordinates;
          if (!coords || coords.length === 0) return null;
          const isDirect = alt.alternative_id === 'direct';
          return (
            <Polyline
              key={alt.alternative_id}
              positions={coords.map((c: number[]) => [c[1], c[0]])}
              pathOptions={{
                color: isDirect ? '#f87171' : '#c084fc',
                weight: 2.5,
                dashArray: isDirect ? '4, 4' : '6, 6',
                opacity: 0.8
              }}
            >
              <Popup>
                <div style={{ padding: '4px', fontSize: '11px', color: '#cbd5e1' }}>
                  <strong style={{ color: isDirect ? '#f87171' : '#c084fc' }}>
                    {isDirect ? 'Direct Line-of-Sight' : 'High-Clearance Seaward Corridor'}
                  </strong>
                  <div>Distance: {alt.total_distance_km} km ({alt.total_distance_nm} nm)</div>
                  <div>Est. Duration: ~{alt.estimated_duration_hours} hrs</div>
                  {alt.estimated_fuel_litres != null && <div>Est. Fuel: ~{alt.estimated_fuel_litres} L</div>}
                  <div style={{ color: alt.intersects_restricted_zone ? '#ef4444' : '#10b981', marginTop: '2px' }}>
                    {alt.intersects_restricted_zone ? '⚠️ Traverses Restricted Zone' : '✅ Clear of Restricted Perimeters'}
                  </div>
                  {alt.route_risk_index != null && (
                    <div>Risk Index: {alt.route_risk_index}/10 ({alt.route_risk_level})</div>
                  )}
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {/* Clearance Waypoints (M4) */}
        {showRoute && highlightRoute && transitRoute?.waypoints?.map((wp, idx) => (
          <Marker
            key={`wp-${idx}`}
            position={[wp.latitude, wp.longitude]}
            icon={waypointIcon}
            zIndexOffset={500}
          >
            <Popup>
              <div style={{ padding: '4px', fontSize: '11px', color: '#cbd5e1' }}>
                <strong style={{ color: '#f59e0b' }}>📍 {wp.name}</strong>
                <div>Coordinates: {wp.latitude}° N, {wp.longitude}° E</div>
                {wp.description && <div style={{ marginTop: '4px', color: '#e2e8f0' }}>{wp.description}</div>}
                <div style={{ marginTop: '4px', color: '#94a3b8' }}>
                  Safety buffer: {transitRoute.clearance_buffer_km} km
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Fallback Direct line between vessel and nearest PFZ if no transitRoute */}
        {showRoute && highlightRoute && !transitRoute && nearestPfz && (
          <Polyline
            positions={[vesselCoords, [nearestPfz.latitude, nearestPfz.longitude]]}
            pathOptions={{
              color: '#06b6d4',
              weight: 3,
              dashArray: '6, 8',
              opacity: 0.85
            }}
          />
        )}
      </MapContainer>
    </div>
  );
};
