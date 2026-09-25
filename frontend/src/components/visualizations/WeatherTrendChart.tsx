import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import { CloudRain, Wind, Thermometer } from 'lucide-react';
import type { WeatherData, TemporalComparisonResult } from '../../services/api';

interface WeatherTrendChartProps {
  weather?: WeatherData | null;
  temporalComparison?: TemporalComparisonResult | null;
}

const WeatherCustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid rgba(56, 189, 248, 0.4)',
          borderRadius: '6px',
          padding: '6px 10px',
          fontSize: '0.68rem',
          color: '#f8fafc',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: '3px', textTransform: 'capitalize' }}>{label}</div>
        {payload.map((entry: any, index: number) => (
          <div key={`item-${index}`} style={{ color: entry.color, display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
            <span>{entry.name}:</span>
            <strong>{entry.value} {entry.unit}</strong>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export const WeatherTrendChart: React.FC<WeatherTrendChartProps> = ({
  weather,
  temporalComparison
}) => {
  if (!weather && !temporalComparison) {
    return null;
  }

  // Extract chart points from temporal comparison or fallback to single point
  let chartData: Array<{ time: string; wind: number; rain: number; temp?: number }> = [];

  if (temporalComparison) {
    const w1 = temporalComparison.window_1;
    const w2 = temporalComparison.window_2;
    chartData = [
      {
        time: w1.time_window.replace(/_/g, ' '),
        wind: w1.wind_speed_kmh,
        rain: w1.rain_probability,
        temp: weather?.temperature_c ?? 28.5
      },
      {
        time: w2.time_window.replace(/_/g, ' '),
        wind: w2.wind_speed_kmh,
        rain: w2.rain_probability,
        temp: weather?.temperature_c ? weather.temperature_c - 0.5 : 28.0
      }
    ];
  } else if (weather?.raw_metadata?.hourly_series && Array.isArray(weather.raw_metadata.hourly_series)) {
    chartData = weather.raw_metadata.hourly_series.map((item: any) => ({
      time: item.time,
      wind: item.wind_speed ?? item.wind ?? 0,
      rain: item.rain_prob ?? item.rain ?? 0,
      temp: item.temp_c ?? item.temp
    }));
  }

  return (
    <div
      className="weather-trend-chart-card"
      style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid rgba(56, 189, 248, 0.2)',
        borderRadius: '8px',
        padding: '12px 14px',
        margin: '8px 0',
        color: '#e2e8f0'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Wind size={14} color="#06b6d4" />
          <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.03em' }}>
            WEATHER & WIND OBSERVATION
          </span>
        </div>
        {weather && (
          <span style={{ fontSize: '0.66rem', color: '#38bdf8' }}>
            {weather.location} • {weather.forecast_time.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      {chartData.length >= 2 ? (
        <div style={{ width: '100%', height: 140 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 12, left: -22, bottom: 0 }}>
              <defs>
                <linearGradient id="windGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="rainGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <Tooltip content={<WeatherCustomTooltip />} />
              <Area
                type="monotone"
                dataKey="wind"
                name="Wind Speed"
                unit="km/h"
                stroke="#06b6d4"
                fillOpacity={1}
                fill="url(#windGradient)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="rain"
                name="Rain Prob"
                unit="%"
                stroke="#38bdf8"
                fillOpacity={1}
                fill="url(#rainGradient)"
                strokeWidth={1.5}
                strokeDasharray="4 2"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        /* Single Observation Metric Tiles */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))', gap: '8px', marginTop: '6px' }}>
          {weather && (
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8', fontSize: '0.64rem' }}>
                <Wind size={12} color="#06b6d4" />
                <span>Wind Speed</span>
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#06b6d4', marginTop: '2px' }}>
                {weather.wind_speed_kmh} <span style={{ fontSize: '0.65rem' }}>km/h</span>
              </div>
              <div style={{ fontSize: '0.6rem', color: '#64748b' }}>
                Dir: {weather.wind_direction_deg != null ? `${weather.wind_direction_deg}°` : 'W'}
              </div>
            </div>
          )}

          {weather && (
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8', fontSize: '0.64rem' }}>
                <CloudRain size={12} color="#38bdf8" />
                <span>Rain Likelihood</span>
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#38bdf8', marginTop: '2px' }}>
                {weather.rain_probability} <span style={{ fontSize: '0.65rem' }}>%</span>
              </div>
              <div style={{ fontSize: '0.6rem', color: '#64748b' }}>
                {weather.weather_condition || 'Standard coastal sky'}
              </div>
            </div>
          )}

          {weather?.temperature_c != null && (
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8', fontSize: '0.64rem' }}>
                <Thermometer size={12} color="#f59e0b" />
                <span>Air Temp</span>
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f59e0b', marginTop: '2px' }}>
                {weather.temperature_c} <span style={{ fontSize: '0.65rem' }}>°C</span>
              </div>
              <div style={{ fontSize: '0.6rem', color: '#64748b' }}>
                Visibility: {weather.visibility_km != null ? `${weather.visibility_km} km` : 'Standard'}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Weather alert banner if active */}
      {weather?.weather_alert && (
        <div
          style={{
            marginTop: '8px',
            padding: '5px 8px',
            borderRadius: '4px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            fontSize: '0.68rem',
            color: '#fca5a5'
          }}
        >
          ⚠️ {weather.weather_alert}
        </div>
      )}
    </div>
  );
};
