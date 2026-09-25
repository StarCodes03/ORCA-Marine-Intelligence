import React, { useState } from 'react';
import {
  Waves,
  Wind,
  Compass,
  Thermometer,
  Layers
} from 'lucide-react';
import type { WeatherData, OceanData, TemporalComparisonResult } from '../../services/api';
import type { RoleChatExperience } from '../../config/roleExperience';
import { MarineMetricCard } from './MarineMetricCard';

interface MarineConditionsChartProps {
  weather?: WeatherData | null;
  ocean?: OceanData | null;
  temporalComparison?: TemporalComparisonResult | null;
  roleExperience?: RoleChatExperience;
}

export const MarineConditionsChart: React.FC<MarineConditionsChartProps> = ({
  weather,
  ocean,
  temporalComparison,
  roleExperience
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'hydro' | 'atmos'>('all');

  if (!weather && !ocean) {
    return null;
  }

  // Derive status ratings based on marine thresholds
  const getWaveStatus = (h: number) => {
    if (h > 2.2) return 'danger';
    if (h > 1.5) return 'caution';
    return 'safe';
  };

  const getWindStatus = (w: number) => {
    if (w > 35) return 'danger';
    if (w > 25) return 'caution';
    return 'safe';
  };

  const getRainStatus = (r: number) => {
    if (r > 65) return 'warning';
    if (r > 30) return 'caution';
    return 'safe';
  };

  const currentWave = ocean?.wave_height_m ?? (temporalComparison ? temporalComparison.window_1.wave_height_m : 0);
  const currentWind = weather?.wind_speed_kmh ?? (temporalComparison ? temporalComparison.window_1.wind_speed_kmh : 0);
  const currentRain = weather?.rain_probability ?? (temporalComparison ? temporalComparison.window_1.rain_probability : 0);

  const title = roleExperience?.responseHeading || 'LIVE MARINE CONDITIONS';

  return (
    <div
      className="marine-conditions-chart-card"
      style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid rgba(56, 189, 248, 0.22)',
        borderRadius: '8px',
        padding: '12px 14px',
        margin: '8px 0',
        color: '#e2e8f0'
      }}
    >
      {/* Header and Filter Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Layers size={15} color="#38bdf8" />
          <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.03em' }}>
            {title}
          </span>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', gap: '3px', background: 'rgba(0,0,0,0.3)', padding: '2px', borderRadius: '6px' }}>
          <button
            type="button"
            style={{
              background: activeTab === 'all' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
              color: activeTab === 'all' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              borderRadius: '4px',
              padding: '2px 8px',
              fontSize: '0.62rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            onClick={() => setActiveTab('all')}
          >
            Overview
          </button>
          <button
            type="button"
            style={{
              background: activeTab === 'hydro' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
              color: activeTab === 'hydro' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              borderRadius: '4px',
              padding: '2px 8px',
              fontSize: '0.62rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            onClick={() => setActiveTab('hydro')}
          >
            Hydrodynamics
          </button>
          <button
            type="button"
            style={{
              background: activeTab === 'atmos' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
              color: activeTab === 'atmos' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              borderRadius: '4px',
              padding: '2px 8px',
              fontSize: '0.62rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            onClick={() => setActiveTab('atmos')}
          >
            Atmospheric
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
        {/* Wave Height (Hydro) */}
        {(activeTab === 'all' || activeTab === 'hydro') && (
          <MarineMetricCard
            label="Wave Height"
            value={currentWave}
            unit="m"
            status={getWaveStatus(currentWave)}
            icon={<Waves size={14} color="#38bdf8" />}
            subtext={ocean ? `Sea: ${ocean.sea_state}` : 'Significant wave'}
          />
        )}

        {/* Wind Speed (Atmos) */}
        {(activeTab === 'all' || activeTab === 'atmos') && (
          <MarineMetricCard
            label="Wind Speed"
            value={currentWind}
            unit="km/h"
            status={getWindStatus(currentWind)}
            icon={<Wind size={14} color="#06b6d4" />}
            subtext={weather?.wind_direction_deg != null ? `${weather.wind_direction_deg}° bearing` : 'Westerly'}
          />
        )}

        {/* Rain Likelihood (Atmos) */}
        {(activeTab === 'all' || activeTab === 'atmos') && (
          <MarineMetricCard
            label="Rain Prob"
            value={currentRain}
            unit="%"
            status={getRainStatus(currentRain)}
            icon={<Compass size={14} color="#38bdf8" />}
            subtext={weather?.weather_condition || 'Precipitation'}
          />
        )}

        {/* Sea Surface Temp (Hydro) */}
        {(activeTab === 'all' || activeTab === 'hydro') && ocean?.sst_c != null && (
          <MarineMetricCard
            label="Sea Surface Temp"
            value={ocean.sst_c}
            unit="°C"
            status="neutral"
            icon={<Thermometer size={14} color="#f59e0b" />}
            subtext="Copernicus / Open-Meteo"
          />
        )}

        {/* Air Temperature (Atmos) */}
        {activeTab === 'atmos' && weather?.temperature_c != null && (
          <MarineMetricCard
            label="Air Temp"
            value={weather.temperature_c}
            unit="°C"
            status="neutral"
            icon={<Thermometer size={14} color="#fbbf24" />}
            subtext="Ambient 2m"
          />
        )}

        {/* Swell Period (Hydro) */}
        {activeTab === 'hydro' && ocean?.wave_period_s != null && (
          <MarineMetricCard
            label="Swell Period"
            value={ocean.wave_period_s}
            unit="s"
            status="neutral"
            icon={<Waves size={14} color="#38bdf8" />}
            subtext="Dominant wave period"
          />
        )}
      </div>

      {/* Provenance Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.62rem', color: '#64748b', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
        <span>
          Sources: {weather?.source === 'OPEN_METEO_WEATHER' ? 'Open-Meteo Weather' : 'Weather Feed'} • {ocean?.source === 'OPEN_METEO_MARINE' ? 'Open-Meteo Marine' : 'Marine Feed'}
        </span>
        {(weather?.retrieved_at || ocean?.retrieved_at) && (
          <span>
            Updated {new Date(weather?.retrieved_at || ocean?.retrieved_at || '').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  );
};
