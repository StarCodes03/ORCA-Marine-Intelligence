import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, Info } from 'lucide-react';
import type { RiskAssessment, RouteRiskAssessment } from '../../services/api';
import type { RoleChatExperience } from '../../config/roleExperience';

interface RiskIndicatorProps {
  risk?: RiskAssessment | null;
  routeRisk?: RouteRiskAssessment | null;
  roleExperience?: RoleChatExperience;
  density?: 'compact' | 'balanced' | 'detailed';
}

export const RiskIndicator: React.FC<RiskIndicatorProps> = ({
  risk,
  routeRisk,
  roleExperience,
  density = 'balanced'
}) => {
  if (!risk && !routeRisk) {
    return null;
  }

  const score = risk?.risk_score ?? routeRisk?.prototype_route_risk_index ?? 0;
  const level = (risk?.risk_level ?? routeRisk?.risk_level ?? 'LOW').toUpperCase();
  const reasons = risk?.reasons ?? routeRisk?.reasons ?? [];
  const limitingFactor = routeRisk?.limiting_factor;
  const factors = risk?.score_breakdown?.factors ?? [];

  // Theme based on risk level
  const getTheme = (lvl: string) => {
    switch (lvl) {
      case 'CRITICAL':
        return {
          textColor: '#f87171',
          bg: 'rgba(239, 68, 68, 0.12)',
          border: 'rgba(239, 68, 68, 0.35)',
          barColor: '#ef4444',
          icon: <ShieldAlert size={16} color="#ef4444" />
        };
      case 'HIGH':
        return {
          textColor: '#fb923c',
          bg: 'rgba(249, 115, 22, 0.12)',
          border: 'rgba(249, 115, 22, 0.35)',
          barColor: '#f97316',
          icon: <AlertTriangle size={16} color="#f97316" />
        };
      case 'MODERATE':
        return {
          textColor: '#fbbf24',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.35)',
          barColor: '#f59e0b',
          icon: <AlertTriangle size={16} color="#f59e0b" />
        };
      case 'LOW':
      default:
        return {
          textColor: '#34d399',
          bg: 'rgba(16, 185, 129, 0.12)',
          border: 'rgba(16, 185, 129, 0.35)',
          barColor: '#10b981',
          icon: <ShieldCheck size={16} color="#10b981" />
        };
    }
  };

  const theme = getTheme(level);
  const title = roleExperience?.preferredTerminology?.riskAssessmentLabel || 'ENVIRONMENTAL CONDITION RISK';
  const percentage = Math.min(Math.max((score / 10) * 100, 4), 100);

  return (
    <div
      className="risk-indicator-card"
      style={{
        background: theme.bg,
        border: `1px solid ${theme.border}`,
        borderRadius: '8px',
        padding: density === 'compact' ? '8px 12px' : '12px 14px',
        margin: '8px 0',
        color: '#e2e8f0'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          {theme.icon}
          <span style={{ fontSize: '0.73rem', fontWeight: 700, letterSpacing: '0.04em', color: theme.textColor }}>
            {title}: {level}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 800, color: theme.textColor }}>
            {score.toFixed(1)}
          </span>
          <span style={{ fontSize: '0.65rem', color: '#94a3b8' }}>/10</span>
        </div>
      </div>

      {/* Progress Meter */}
      <div
        style={{
          width: '100%',
          height: '6px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '3px',
          overflow: 'hidden',
          marginBottom: reasons.length > 0 ? '8px' : '0'
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: '100%',
            background: theme.barColor,
            borderRadius: '3px',
            transition: 'width 0.4s ease'
          }}
        />
      </div>

      {/* Limiting Factor Callout */}
      {limitingFactor && (
        <div style={{ fontSize: '0.7rem', color: '#38bdf8', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
          <Info size={12} />
          <span>Limiting Factor: <strong>{limitingFactor.replace(/_/g, ' ')}</strong></span>
        </div>
      )}

      {/* Key Reasons (when not compact or if critical) */}
      {(density !== 'compact' || level === 'CRITICAL' || level === 'HIGH') && reasons.length > 0 && (
        <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '6px' }}>
          <ul style={{ margin: 0, paddingLeft: '16px' }}>
            {reasons.slice(0, 3).map((r, i) => (
              <li key={i} style={{ marginBottom: '2px' }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Factor Breakdown Chips for Detailed Density */}
      {density === 'detailed' && factors.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
          {factors.map((f, i) => (
            <span
              key={i}
              style={{
                fontSize: '0.64rem',
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'rgba(0, 0, 0, 0.25)',
                color: f.contribution > 0 ? theme.textColor : '#94a3b8'
              }}
            >
              {f.factor}: +{f.contribution.toFixed(1)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
