import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts';
import { Waves, CheckCircle2, AlertTriangle } from 'lucide-react';
import type { OceanData, TemporalComparisonResult } from '../../services/api';
import { CANONICAL_VESSEL_PROFILES } from '../../services/api';

interface WaveTrendChartProps {
  ocean?: OceanData | null;
  temporalComparison?: TemporalComparisonResult | null;
  selectedVessel?: string;
}

const WaveCustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid rgba(14, 165, 233, 0.4)',
          borderRadius: '6px',
          padding: '6px 10px',
          fontSize: '0.68rem',
          color: '#f8fafc',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: '3px', textTransform: 'capitalize' }}>{label}</div>
        <div style={{ color: '#38bdf8' }}>Wave Height: <strong>{payload[0].value} m</strong></div>
        {payload[0].payload.seaState && (
          <div style={{ color: '#94a3b8', textTransform: 'capitalize' }}>
            Sea State: {payload[0].payload.seaState}
          </div>
        )}
      </div>
    );
  }
  return null;
};

export const WaveTrendChart: React.FC<WaveTrendChartProps> = ({
  ocean,
  temporalComparison,
  selectedVessel = 'motorized_frp_obm'
}) => {
  if (!ocean && !temporalComparison) {
    return null;
  }

  const profile = CANONICAL_VESSEL_PROFILES[selectedVessel] || CANONICAL_VESSEL_PROFILES.motorized_frp_obm;
  const safeThreshold = profile.wave_max_safe;

  // Extract wave data points
  let waveData: Array<{ time: string; wave: number; seaState: string }> = [];

  if (temporalComparison) {
    const w1 = temporalComparison.window_1;
    const w2 = temporalComparison.window_2;
    waveData = [
      {
        time: w1.time_window.replace(/_/g, ' '),
        wave: w1.wave_height_m,
        seaState: w1.sea_state
      },
      {
        time: w2.time_window.replace(/_/g, ' '),
        wave: w2.wave_height_m,
        seaState: w2.sea_state
      }
    ];
  } else if (ocean?.raw_metadata?.hourly_series && Array.isArray(ocean.raw_metadata.hourly_series)) {
    waveData = ocean.raw_metadata.hourly_series.map((item: any) => ({
      time: item.time,
      wave: item.wave_height ?? item.wave ?? 0,
      seaState: ocean.sea_state
    }));
  }

  const currentWave = ocean?.wave_height_m ?? (temporalComparison ? temporalComparison.window_1.wave_height_m : 0);
  const exceedsSafe = currentWave > safeThreshold;

  return (
    <div
      className="wave-trend-chart-card"
      style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid rgba(14, 165, 233, 0.25)',
        borderRadius: '8px',
        padding: '12px 14px',
        margin: '8px 0',
        color: '#e2e8f0'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Waves size={15} color="#38bdf8" />
          <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.03em' }}>
            WAVE DYNAMICS & SWELL
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.66rem' }}>
          {exceedsSafe ? (
            <span style={{ color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
              <AlertTriangle size={12} color="#fbbf24" /> Exceeds Safe Limit ({safeThreshold}m)
            </span>
          ) : (
            <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
              <CheckCircle2 size={12} color="#34d399" /> Within Craft Threshold ({safeThreshold}m)
            </span>
          )}
        </div>
      </div>

      {waveData.length >= 2 ? (
        <div style={{ width: '100%', height: 140 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={waveData} margin={{ top: 10, right: 12, left: -22, bottom: 0 }}>
              <defs>
                <linearGradient id="waveGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0284c7" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis domain={[0, Math.max(3.0, safeThreshold + 0.5)]} stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <Tooltip content={<WaveCustomTooltip />} />
              <ReferenceLine
                y={safeThreshold}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                label={{ value: `Safe Max (${safeThreshold}m)`, fill: '#fbbf24', fontSize: 9, position: 'insideTopRight' }}
              />
              <Area
                type="monotone"
                dataKey="wave"
                name="Wave Height"
                unit="m"
                stroke="#38bdf8"
                fillOpacity={1}
                fill="url(#waveGradient)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        /* Single Observation Wave Snapshot */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))', gap: '8px', marginTop: '6px' }}>
          {ocean && (
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.64rem' }}>Significant Wave</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#38bdf8', marginTop: '2px' }}>
                {ocean.wave_height_m} <span style={{ fontSize: '0.65rem' }}>m</span>
              </div>
              <div style={{ fontSize: '0.6rem', color: '#64748b' }}>
                Limit: {safeThreshold} m ({profile.name.split(' ')[0]})
              </div>
            </div>
          )}

          {ocean && (
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.64rem' }}>Douglas Sea State</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#e2e8f0', marginTop: '2px', textTransform: 'capitalize' }}>
                {ocean.sea_state}
              </div>
              <div style={{ fontSize: '0.6rem', color: '#64748b' }}>
                Period: {ocean.wave_period_s != null ? `${ocean.wave_period_s}s` : 'Coastal swell'}
              </div>
            </div>
          )}

          {ocean?.tide && (
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.64rem' }}>Sea-Level Trend</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#34d399', marginTop: '2px', textTransform: 'capitalize' }}>
                {ocean.tide.includes('(') ? ocean.tide.split('(')[0].trim() : ocean.tide}
              </div>
              <div style={{ fontSize: '0.6rem', color: '#64748b' }}>
                Harmonic trend
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
