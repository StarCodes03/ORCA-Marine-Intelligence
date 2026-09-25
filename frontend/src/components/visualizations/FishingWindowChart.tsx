import React from 'react';
import { Sun, Sunset, ArrowUpRight, ArrowDownRight, ArrowRight, Sparkles } from 'lucide-react';
import type { TemporalComparisonResult, WeatherData, OceanData, RiskAssessment } from '../../services/api';

interface FishingWindowChartProps {
  temporalComparison?: TemporalComparisonResult | null;
  weather?: WeatherData | null;
  ocean?: OceanData | null;
  risk?: RiskAssessment | null;
}

export const FishingWindowChart: React.FC<FishingWindowChartProps> = ({
  temporalComparison,
  weather,
  ocean,
  risk
}) => {
  if (!temporalComparison && !weather && !ocean) {
    return null;
  }

  // 1. Dual-window comparison when temporal comparison data is available
  if (temporalComparison) {
    const w1 = temporalComparison.window_1;
    const w2 = temporalComparison.window_2;
    const trend = (temporalComparison.trend || 'STABLE').toUpperCase();

    const getTrendBadge = (t: string) => {
      if (t === 'IMPROVING') {
        return {
          label: 'FAVORABLE / IMPROVING',
          color: '#10b981',
          bg: 'rgba(16, 185, 129, 0.15)',
          border: 'rgba(16, 185, 129, 0.35)',
          icon: <ArrowDownRight size={13} />
        };
      }
      if (t === 'DETERIORATING') {
        return {
          label: 'DETERIORATING / CAUTION',
          color: '#f59e0b',
          bg: 'rgba(245, 158, 11, 0.15)',
          border: 'rgba(245, 158, 11, 0.35)',
          icon: <ArrowUpRight size={13} />
        };
      }
      return {
        label: 'STABLE / MINIMAL DELTA',
        color: '#38bdf8',
        bg: 'rgba(56, 189, 248, 0.15)',
        border: 'rgba(56, 189, 248, 0.35)',
        icon: <ArrowRight size={13} />
      };
    };

    const trendBadge = getTrendBadge(trend);

    const formatDelta = (val: number, unit: string) => {
      const sign = val > 0 ? '+' : '';
      return `${sign}${val.toFixed(1)} ${unit}`;
    };

    return (
      <div
        className="fishing-window-card"
        style={{
          background: 'rgba(15, 23, 42, 0.8)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '8px',
          padding: '12px 14px',
          margin: '8px 0',
          color: '#e2e8f0'
        }}
      >
        {/* Header with Trend Badge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sun size={15} color="#f59e0b" />
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.03em' }}>
              FISHING WINDOW COMPARISON
            </span>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '0.66rem',
              fontWeight: 700,
              color: trendBadge.color,
              background: trendBadge.bg,
              border: `1px solid ${trendBadge.border}`
            }}
          >
            {trendBadge.icon}
            <span>{trendBadge.label}</span>
          </div>
        </div>

        {/* Side-by-Side Windows */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
          {/* Window 1 */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '6px',
              padding: '8px 10px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '6px' }}>
              <Sun size={13} color="#f59e0b" />
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#e2e8f0', textTransform: 'capitalize' }}>
                {w1.time_window.replace(/_/g, ' ')}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.68rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Wave:</span>
                <span style={{ fontWeight: 700, color: '#38bdf8' }}>{w1.wave_height_m} m ({w1.sea_state})</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Wind:</span>
                <span style={{ fontWeight: 700, color: '#f8fafc' }}>{w1.wind_speed_kmh} km/h</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Rain:</span>
                <span style={{ fontWeight: 700, color: '#cbd5e1' }}>{w1.rain_probability}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px', paddingTop: '3px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ color: '#94a3b8' }}>Risk:</span>
                <span style={{ fontWeight: 800, color: w1.risk_level === 'LOW' ? '#34d399' : '#fbbf24' }}>
                  {w1.risk_level} ({w1.risk_score.toFixed(1)})
                </span>
              </div>
            </div>
          </div>

          {/* Window 2 */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '6px',
              padding: '8px 10px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '6px' }}>
              <Sunset size={13} color="#f97316" />
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#e2e8f0', textTransform: 'capitalize' }}>
                {w2.time_window.replace(/_/g, ' ')}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.68rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Wave:</span>
                <span style={{ fontWeight: 700, color: '#38bdf8' }}>{w2.wave_height_m} m ({w2.sea_state})</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Wind:</span>
                <span style={{ fontWeight: 700, color: '#f8fafc' }}>{w2.wind_speed_kmh} km/h</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Rain:</span>
                <span style={{ fontWeight: 700, color: '#cbd5e1' }}>{w2.rain_probability}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px', paddingTop: '3px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ color: '#94a3b8' }}>Risk:</span>
                <span style={{ fontWeight: 800, color: w2.risk_level === 'LOW' ? '#34d399' : '#fbbf24' }}>
                  {w2.risk_level} ({w2.risk_score.toFixed(1)})
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Metric Deltas Strip */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px', fontSize: '0.65rem' }}>
          <span style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(0, 0, 0, 0.3)', color: '#94a3b8' }}>
            Δ Wave: <strong style={{ color: temporalComparison.delta_wave_m > 0 ? '#f59e0b' : '#34d399' }}>{formatDelta(temporalComparison.delta_wave_m, 'm')}</strong>
          </span>
          <span style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(0, 0, 0, 0.3)', color: '#94a3b8' }}>
            Δ Wind: <strong style={{ color: temporalComparison.delta_wind_kmh > 0 ? '#f59e0b' : '#34d399' }}>{formatDelta(temporalComparison.delta_wind_kmh, 'km/h')}</strong>
          </span>
          <span style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(0, 0, 0, 0.3)', color: '#94a3b8' }}>
            Δ Rain: <strong style={{ color: temporalComparison.delta_rain_pct > 0 ? '#f59e0b' : '#34d399' }}>{formatDelta(temporalComparison.delta_rain_pct, '%')}</strong>
          </span>
          <span style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(0, 0, 0, 0.3)', color: '#94a3b8' }}>
            Δ Risk: <strong style={{ color: temporalComparison.delta_risk_score > 0 ? '#f59e0b' : '#34d399' }}>{formatDelta(temporalComparison.delta_risk_score, 'pts')}</strong>
          </span>
        </div>

        {/* Practical Recommendation */}
        {temporalComparison.recommendation && (
          <div
            style={{
              fontSize: '0.72rem',
              color: '#38bdf8',
              lineHeight: 1.4,
              padding: '6px 8px',
              borderRadius: '4px',
              background: 'rgba(56, 189, 248, 0.08)',
              borderLeft: '2px solid #0284c7'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px', fontWeight: 600 }}>
              <Sparkles size={11} />
              <span>Operational Guidance:</span>
            </div>
            <span>{temporalComparison.recommendation}</span>
          </div>
        )}
      </div>
    );
  }

  // 2. Single-window fallback when temporal comparison query was not run
  return (
    <div
      className="fishing-window-card"
      style={{
        background: 'rgba(15, 23, 42, 0.7)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '8px',
        padding: '10px 12px',
        margin: '8px 0',
        color: '#e2e8f0'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Sun size={14} color="#f59e0b" />
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f8fafc' }}>
            OBSERVED CONDITIONS SNAPSHOT
          </span>
        </div>
        {risk && (
          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: risk.risk_level === 'LOW' ? '#34d399' : '#fbbf24' }}>
            Risk: {risk.risk_level} ({risk.risk_score}/10)
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '6px', fontSize: '0.68rem' }}>
        {ocean && (
          <div style={{ padding: '4px 6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
            <span style={{ color: '#94a3b8', display: 'block', fontSize: '0.6rem' }}>Wave</span>
            <strong style={{ color: '#38bdf8' }}>{ocean.wave_height_m} m</strong>
          </div>
        )}
        {ocean && (
          <div style={{ padding: '4px 6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
            <span style={{ color: '#94a3b8', display: 'block', fontSize: '0.6rem' }}>Sea State</span>
            <strong style={{ color: '#e2e8f0', textTransform: 'capitalize' }}>{ocean.sea_state}</strong>
          </div>
        )}
        {weather && (
          <div style={{ padding: '4px 6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
            <span style={{ color: '#94a3b8', display: 'block', fontSize: '0.6rem' }}>Wind</span>
            <strong style={{ color: '#f8fafc' }}>{weather.wind_speed_kmh} km/h</strong>
          </div>
        )}
        {weather && (
          <div style={{ padding: '4px 6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
            <span style={{ color: '#94a3b8', display: 'block', fontSize: '0.6rem' }}>Rain Prob</span>
            <strong style={{ color: '#cbd5e1' }}>{weather.rain_probability}%</strong>
          </div>
        )}
      </div>
      <div style={{ fontSize: '0.62rem', color: '#64748b', marginTop: '6px' }}>
        Single-window observation. Ask <em>&quot;Compare morning and afternoon&quot;</em> to view multi-window deltas.
      </div>
    </div>
  );
};
