import React from 'react';
import { Navigation, ShieldCheck, Fuel, Clock, ArrowRight } from 'lucide-react';
import type { TransitRoute } from '../../services/api';
import type { RoleChatExperience } from '../../config/roleExperience';

interface InlineRouteCardProps {
  route?: TransitRoute | null;
  roleExperience?: RoleChatExperience;
  onNavigateToRoute?: () => void;
}

export const InlineRouteCard: React.FC<InlineRouteCardProps> = ({
  route,
  roleExperience,
  onNavigateToRoute
}) => {
  if (!route) {
    return null;
  }

  const title = roleExperience?.preferredTerminology?.routeLabel || 'SAFE PASSAGE CORRIDOR';

  return (
    <div
      className="inline-route-card"
      style={{
        background: 'rgba(15, 23, 42, 0.8)',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        borderRadius: '8px',
        padding: '12px 14px',
        margin: '8px 0',
        color: '#e2e8f0'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Navigation size={14} color="#10b981" />
          <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#34d399', letterSpacing: '0.03em' }}>
            {title}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.66rem', color: '#10b981', fontWeight: 600 }}>
          <ShieldCheck size={13} />
          <span>Clearance Buffer: {route.clearance_buffer_km || 1.5} km</span>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))', gap: '8px', marginBottom: '10px' }}>
        <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
          <span style={{ color: '#94a3b8', fontSize: '0.62rem', display: 'block' }}>Distance</span>
          <strong style={{ fontSize: '0.9rem', color: '#f8fafc' }}>
            {route.total_distance_km.toFixed(1)} <span style={{ fontSize: '0.65rem' }}>km</span>
          </strong>
          <span style={{ fontSize: '0.62rem', color: '#64748b', display: 'block' }}>
            ({route.total_distance_nm.toFixed(1)} NM)
          </span>
        </div>

        <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
          <span style={{ color: '#94a3b8', fontSize: '0.62rem', display: 'flex', alignItems: 'center', gap: '3px' }}>
            <Clock size={10} /> Duration
          </span>
          <strong style={{ fontSize: '0.9rem', color: '#38bdf8' }}>
            {route.estimated_duration_hours.toFixed(1)} <span style={{ fontSize: '0.65rem' }}>hrs</span>
          </strong>
          <span style={{ fontSize: '0.62rem', color: '#64748b', display: 'block' }}>
            Estimated transit
          </span>
        </div>

        {route.estimated_fuel_litres != null && route.estimated_fuel_litres > 0 && (
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
            <span style={{ color: '#94a3b8', fontSize: '0.62rem', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <Fuel size={10} /> Est. Fuel
            </span>
            <strong style={{ fontSize: '0.9rem', color: '#fbbf24' }}>
              ~{route.estimated_fuel_litres.toFixed(1)} <span style={{ fontSize: '0.65rem' }}>L</span>
            </strong>
            <span style={{ fontSize: '0.62rem', color: '#64748b', display: 'block' }}>
              {route.fuel_type || 'Fuel mix'}
            </span>
          </div>
        )}
      </div>

      {/* Geofence notice */}
      {route.avoided_zones && route.avoided_zones.length > 0 && (
        <div style={{ fontSize: '0.66rem', color: '#94a3b8', marginBottom: '8px' }}>
          🛡️ Diverted around {route.avoided_zones.join(', ')} with {route.clearance_buffer_km} km margin.
        </div>
      )}

      {/* Navigate button */}
      {onNavigateToRoute && (
        <button
          type="button"
          onClick={onNavigateToRoute}
          style={{
            width: '100%',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#34d399',
            borderRadius: '6px',
            padding: '6px 12px',
            fontSize: '0.72rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            cursor: 'pointer',
            transition: 'background 0.15s ease'
          }}
        >
          <span>Open Full Route in Passage Planning</span>
          <ArrowRight size={12} />
        </button>
      )}
    </div>
  );
};
