"""ORCA Marine Intelligence - Deterministic Temporal Reasoning Engine (M5)

Performs mathematical comparisons of marine and meteorological forecasts across multiple
time horizons (e.g., morning vs. afternoon, today vs. tomorrow).

Adheres strictly to:
1. Deterministic delta calculations (wave, wind, rain, risk).
2. Configurable tolerance thresholds below which differences are marked STABLE.
3. 4-state trend classification: STABLE, IMPROVING, DETERIORATING, INDETERMINATE.
4. Attribution of conditions to the evaluation point (origin).
"""

from typing import Dict, Any, Optional
import logging

from app.models.schemas import (
    LocationCoords,
    TimeWindowMetrics,
    TemporalComparisonResult,
    WeatherData,
    OceanData
)
from app.config.risk_thresholds import TEMPORAL_TOLERANCES

logger = logging.getLogger("orca.tools.temporal_reasoning")


class TemporalReasoningEngine:
    """Deterministic comparative reasoning engine for multi-window marine conditions."""

    def __init__(self, tolerances: Optional[Dict[str, float]] = None):
        self.tolerances = tolerances or dict(TEMPORAL_TOLERANCES)

    def extract_window_metrics(
        self,
        time_window: str,
        weather: WeatherData,
        ocean: OceanData,
        risk_score: float,
        risk_level: str
    ) -> TimeWindowMetrics:
        """Create structured metrics snapshot for a specific time window at the evaluation point."""
        return TimeWindowMetrics(
            time_window=time_window,
            wind_speed_kmh=round(float(weather.wind_speed_kmh), 1),
            wind_direction_deg=round(float(weather.wind_direction_deg), 1),
            wave_height_m=round(float(ocean.wave_height_m), 2),
            sea_state=ocean.sea_state,
            rain_probability=round(float(weather.rain_probability), 1),
            risk_score=round(float(risk_score), 1),
            risk_level=risk_level,
            source_weather=weather.source,
            source_ocean=ocean.source
        )

    def compare_time_windows(
        self,
        evaluation_point: LocationCoords,
        window_1: TimeWindowMetrics,
        window_2: TimeWindowMetrics,
        tolerances: Optional[Dict[str, float]] = None
    ) -> TemporalComparisonResult:
        """Deterministically compare two time window metrics and classify condition trend."""
        tols = tolerances or self.tolerances
        tol_wave = tols.get("wave_delta_m", 0.15)
        tol_wind = tols.get("wind_delta_kmh", 3.0)
        tol_rain = tols.get("rain_delta_pct", 10.0)
        tol_risk = tols.get("risk_score_delta", 0.5)

        delta_wind = round(window_2.wind_speed_kmh - window_1.wind_speed_kmh, 1)
        delta_wave = round(window_2.wave_height_m - window_1.wave_height_m, 2)
        delta_rain = round(window_2.rain_probability - window_1.rain_probability, 1)
        delta_risk = round(window_2.risk_score - window_1.risk_score, 1)

        is_wave_stable = abs(delta_wave) <= tol_wave
        is_wind_stable = abs(delta_wind) <= tol_wind
        is_risk_stable = abs(delta_risk) <= tol_risk
        is_rain_stable = abs(delta_rain) <= tol_rain

        w1_label = window_1.time_window.replace("_", " ").title()
        w2_label = window_2.time_window.replace("_", " ").title()

        # 1. Check for STABLE conditions (all deltas within tolerance)
        if is_wave_stable and is_wind_stable and is_risk_stable:
            trend = "STABLE"
            recommendation = (
                f"Conditions remain stable between {w1_label} and {w2_label} "
                f"(wave Δ: {delta_wave:+}m, wind Δ: {delta_wind:+}km/h). "
                f"No significant operational advantage between these windows."
            )

        # 2. Check for conflicting signals (e.g., wave drops significantly but wind surges)
        elif (delta_wave < -tol_wave and delta_wind > tol_wind) or (delta_wave > tol_wave and delta_wind < -tol_wind):
            trend = "INDETERMINATE"
            if delta_wave < 0:
                trade_off = f"lower wave height ({delta_wave:+}m) but higher wind ({delta_wind:+}km/h)"
            else:
                trade_off = f"lower wind ({delta_wind:+}km/h) but higher wave height ({delta_wave:+}m)"
            recommendation = (
                f"Conditions present mixed trade-offs between {w1_label} and {w2_label}: {trade_off}. "
                f"Choose based on vessel tolerance and operational priority."
            )

        # 3. Check for IMPROVING conditions (risk drops and neither wave nor wind worsens)
        elif delta_risk < -tol_risk and delta_wave <= tol_wave and delta_wind <= tol_wind:
            trend = "IMPROVING"
            recommendation = (
                f"{w2_label} exhibits improved operational conditions with lower assessed risk "
                f"(score Δ: {delta_risk:+0.1f}, wave Δ: {delta_wave:+}m, wind Δ: {delta_wind:+}km/h). "
                f"{w2_label} is recommended."
            )

        # 4. Check for DETERIORATING conditions (risk rises or either wave or wind worsens significantly)
        elif delta_risk > tol_risk or delta_wave > tol_wave or delta_wind > tol_wind:
            trend = "DETERIORATING"
            adverse = []
            if delta_wave > tol_wave:
                adverse.append(f"higher waves ({delta_wave:+}m)")
            if delta_wind > tol_wind:
                adverse.append(f"stronger winds ({delta_wind:+}km/h)")
            if delta_risk > tol_risk:
                adverse.append(f"increased risk score ({delta_risk:+0.1f})")
            adverse_str = ", ".join(adverse)
            recommendation = (
                f"Conditions deteriorate in {w2_label} due to {adverse_str}. "
                f"{w1_label} offers more favorable conditions."
            )

        # 5. Fallback if outside strict buckets
        else:
            trend = "INDETERMINATE"
            recommendation = (
                f"Minor diverging variations between {w1_label} and {w2_label} "
                f"(wave Δ: {delta_wave:+}m, wind Δ: {delta_wind:+}km/h, risk Δ: {delta_risk:+0.1f})."
            )

        return TemporalComparisonResult(
            evaluation_point=evaluation_point,
            window_1=window_1,
            window_2=window_2,
            delta_wind_kmh=delta_wind,
            delta_wave_m=delta_wave,
            delta_rain_pct=delta_rain,
            delta_risk_score=delta_risk,
            trend=trend,
            recommendation=recommendation,
            tolerances_applied=tols,
            provenance_notice="Derived calculation comparing forecast horizons at evaluation point."
        )


# Singleton instance
temporal_engine = TemporalReasoningEngine()
