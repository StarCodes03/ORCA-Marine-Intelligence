import React from 'react';

export type MetricStatus = 'safe' | 'caution' | 'warning' | 'danger' | 'neutral';

interface MarineMetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  status?: MetricStatus;
  subtext?: string;
  onClick?: () => void;
}

export const MarineMetricCard: React.FC<MarineMetricCardProps> = ({
  label,
  value,
  unit,
  icon,
  status = 'neutral',
  subtext,
  onClick
}) => {
  const getStatusBorder = () => {
    switch (status) {
      case 'safe':
        return 'rgba(16, 185, 129, 0.4)';
      case 'caution':
        return 'rgba(245, 158, 11, 0.4)';
      case 'warning':
      case 'danger':
        return 'rgba(239, 68, 68, 0.4)';
      case 'neutral':
      default:
        return 'rgba(255, 255, 255, 0.1)';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'safe':
        return '#34d399';
      case 'caution':
        return '#fbbf24';
      case 'warning':
      case 'danger':
        return '#f87171';
      case 'neutral':
      default:
        return '#38bdf8';
    }
  };

  return (
    <div
      className={`marine-metric-card ${onClick ? 'clickable' : ''}`}
      onClick={onClick}
      style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: `1px solid ${getStatusBorder()}`,
        borderRadius: '8px',
        padding: '8px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '3px',
        minWidth: '110px',
        flex: '1 1 120px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 0.15s ease, border-color 0.15s ease'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.66rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
          {label}
        </span>
        {icon && <span style={{ opacity: 0.85 }}>{icon}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
        <span style={{ fontSize: '1.05rem', fontWeight: 800, color: getStatusText() }}>
          {value}
        </span>
        {unit && (
          <span style={{ fontSize: '0.68rem', color: '#cbd5e1', fontWeight: 500 }}>
            {unit}
          </span>
        )}
      </div>

      {subtext && (
        <span style={{ fontSize: '0.63rem', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {subtext}
        </span>
      )}
    </div>
  );
};
