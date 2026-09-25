import React from 'react';
import { MapPin, Compass, Fish, ArrowRight } from 'lucide-react';
import type { NearestPFZ } from '../../services/api';
import type { RoleChatExperience } from '../../config/roleExperience';

interface InlinePfzCardProps {
  nearestPfz?: NearestPFZ | null;
  candidatePfzs?: NearestPFZ[] | null;
  roleExperience?: RoleChatExperience;
  onSelectPfz?: (pfz: NearestPFZ) => void;
  onNavigateToMarine?: () => void;
}

export const InlinePfzCard: React.FC<InlinePfzCardProps> = ({
  nearestPfz,
  candidatePfzs,
  roleExperience,
  onSelectPfz,
  onNavigateToMarine
}) => {
  const pfz = nearestPfz || (candidatePfzs && candidatePfzs.length > 0 ? candidatePfzs[0] : null);
  const count = candidatePfzs?.length || 0;

  if (!pfz) {
    return null;
  }

  const landingLabel = roleExperience?.preferredTerminology?.landingCenterLabel || 'Landing Centre';

  return (
    <div
      className="inline-pfz-card"
      style={{
        background: 'rgba(15, 23, 42, 0.8)',
        border: '1px solid rgba(6, 182, 212, 0.3)',
        borderRadius: '8px',
        padding: '12px 14px',
        margin: '8px 0',
        color: '#e2e8f0'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <MapPin size={14} color="#06b6d4" />
          <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#38bdf8', letterSpacing: '0.03em' }}>
            POTENTIAL FISHING ZONE (PFZ)
          </span>
        </div>
        {count > 1 && (
          <span style={{ fontSize: '0.66rem', color: '#06b6d4', background: 'rgba(6, 182, 212, 0.15)', padding: '2px 6px', borderRadius: '4px' }}>
            {count} Targets in Sector
          </span>
        )}
      </div>

      {/* Target Details */}
      <div style={{ marginBottom: '8px' }}>
        <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc', marginBottom: '2px' }}>
          {pfz.name}
        </div>
        <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
          {landingLabel}: <strong>{pfz.landing_centre || 'Kochi Harbour'}</strong>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '6px', marginBottom: '10px' }}>
        <div style={{ background: 'rgba(0,0,0,0.25)', padding: '5px 7px', borderRadius: '6px' }}>
          <span style={{ color: '#94a3b8', fontSize: '0.6rem', display: 'block' }}>Distance</span>
          <strong style={{ fontSize: '0.9rem', color: '#06b6d4' }}>
            {pfz.distance_km.toFixed(1)} <span style={{ fontSize: '0.62rem' }}>km</span>
          </strong>
        </div>

        {pfz.bearing_deg != null && (
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '5px 7px', borderRadius: '6px' }}>
            <span style={{ color: '#94a3b8', fontSize: '0.6rem', display: 'flex', alignItems: 'center', gap: '2px' }}>
              <Compass size={10} /> Bearing
            </span>
            <strong style={{ fontSize: '0.9rem', color: '#f8fafc' }}>
              {pfz.bearing_deg.toFixed(0)}° <span style={{ fontSize: '0.62rem' }}>{pfz.direction || ''}</span>
            </strong>
          </div>
        )}

        {pfz.depth_m != null && (
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '5px 7px', borderRadius: '6px' }}>
            <span style={{ color: '#94a3b8', fontSize: '0.6rem', display: 'block' }}>Depth</span>
            <strong style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>
              {pfz.depth_m} <span style={{ fontSize: '0.62rem' }}>m</span>
            </strong>
          </div>
        )}

        {pfz.sst_c != null && (
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: '5px 7px', borderRadius: '6px' }}>
            <span style={{ color: '#94a3b8', fontSize: '0.6rem', display: 'block' }}>SST</span>
            <strong style={{ fontSize: '0.9rem', color: '#f59e0b' }}>
              {pfz.sst_c} <span style={{ fontSize: '0.62rem' }}>°C</span>
            </strong>
          </div>
        )}
      </div>

      {pfz.target_species && (
        <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Fish size={12} color="#06b6d4" />
          <span>Target Pelagic Species: <strong style={{ color: '#cbd5e1' }}>{pfz.target_species}</strong></span>
        </div>
      )}

      {/* Action button */}
      <div style={{ display: 'flex', gap: '6px' }}>
        {onSelectPfz && (
          <button
            type="button"
            onClick={() => onSelectPfz(pfz)}
            style={{
              flex: 1,
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              color: '#38bdf8',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '0.7rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              cursor: 'pointer'
            }}
          >
            <span>Focus Target on Map</span>
            <ArrowRight size={11} />
          </button>
        )}

        {count > 1 && onNavigateToMarine && (
          <button
            type="button"
            onClick={onNavigateToMarine}
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#e2e8f0',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '0.7rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            All {count} Targets
          </button>
        )}
      </div>
    </div>
  );
};
