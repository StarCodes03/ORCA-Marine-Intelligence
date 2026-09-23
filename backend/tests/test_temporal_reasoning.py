"""ORCA Marine Intelligence - Isolated Unit Tests for Temporal Reasoning Engine (M5)

Verifies:
1. Deterministic delta calculations (wind, wave, rain, risk) between time windows.
2. 4-state trend classification (STABLE, IMPROVING, DETERIORATING, INDETERMINATE).
3. Configurable tolerance thresholds behavior.
4. Correct attribution of evaluation point coordinates and provenance notices.
5. Extraction helper from WeatherData and OceanData.
"""

import pytest

from app.models.schemas import (
    LocationCoords,
    TimeWindowMetrics,
    WeatherData,
    OceanData
)
from app.tools.temporal_reasoning import temporal_engine, TemporalReasoningEngine


@pytest.fixture
def eval_point():
    return LocationCoords(name="Kochi Coast", latitude=9.9312, longitude=76.2673)


def test_morning_vs_afternoon_deterministic_comparison(eval_point):
    """Verify deterministic delta math and deterioration classification for squally afternoon."""
    w1 = TimeWindowMetrics(
        time_window="tomorrow_morning",
        wind_speed_kmh=18.0,
        wind_direction_deg=270.0,
        wave_height_m=1.1,
        sea_state="slight",
        rain_probability=15.0,
        risk_score=2.0,
        risk_level="LOW",
        source_weather="OPEN_METEO_WEATHER",
        source_ocean="OPEN_METEO_MARINE"
    )
    w2 = TimeWindowMetrics(
        time_window="tomorrow_afternoon",
        wind_speed_kmh=36.0,
        wind_direction_deg=290.0,
        wave_height_m=2.3,
        sea_state="rough",
        rain_probability=70.0,
        risk_score=6.5,
        risk_level="HIGH",
        source_weather="OPEN_METEO_WEATHER",
        source_ocean="OPEN_METEO_MARINE"
    )

    result = temporal_engine.compare_time_windows(eval_point, w1, w2)

    assert result.evaluation_point.name == "Kochi Coast"
    assert result.delta_wind_kmh == 18.0
    assert result.delta_wave_m == 1.2
    assert result.delta_rain_pct == 55.0
    assert result.delta_risk_score == 4.5
    assert result.trend == "DETERIORATING"
    assert "Tomorrow Morning" in result.recommendation
    assert "deteriorate" in result.recommendation.lower()


def test_temporal_tolerance_and_four_trend_states(eval_point):
    """Verify STABLE, IMPROVING, and INDETERMINATE classifications based on configurable tolerances."""
    engine = TemporalReasoningEngine(tolerances={
        "wave_delta_m": 0.15,
        "wind_delta_kmh": 3.0,
        "rain_delta_pct": 10.0,
        "risk_score_delta": 0.5
    })

    # Case A: STABLE conditions (all deltas <= tolerance)
    w_base = TimeWindowMetrics(
        time_window="today",
        wind_speed_kmh=20.0,
        wind_direction_deg=260.0,
        wave_height_m=1.20,
        sea_state="slight",
        rain_probability=20.0,
        risk_score=2.5,
        risk_level="LOW",
        source_weather="OPEN_METEO",
        source_ocean="OPEN_METEO"
    )
    w_stable = TimeWindowMetrics(
        time_window="tomorrow",
        wind_speed_kmh=22.0,       # delta = +2.0 <= 3.0
        wind_direction_deg=260.0,
        wave_height_m=1.25,        # delta = +0.05 <= 0.15
        sea_state="slight",
        rain_probability=25.0,     # delta = +5.0 <= 10.0
        risk_score=2.7,            # delta = +0.2 <= 0.5
        risk_level="LOW",
        source_weather="OPEN_METEO",
        source_ocean="OPEN_METEO"
    )
    res_stable = engine.compare_time_windows(eval_point, w_base, w_stable)
    assert res_stable.trend == "STABLE"
    assert "remain stable" in res_stable.recommendation.lower()

    # Case B: IMPROVING conditions (risk drops significantly, wave & wind improve)
    w_improving = TimeWindowMetrics(
        time_window="tomorrow",
        wind_speed_kmh=12.0,       # delta = -8.0
        wind_direction_deg=260.0,
        wave_height_m=0.80,        # delta = -0.40
        sea_state="smooth",
        rain_probability=10.0,
        risk_score=1.0,            # delta = -1.5 < -0.5
        risk_level="LOW",
        source_weather="OPEN_METEO",
        source_ocean="OPEN_METEO"
    )
    res_improving = engine.compare_time_windows(eval_point, w_base, w_improving)
    assert res_improving.trend == "IMPROVING"
    assert "improved" in res_improving.recommendation.lower()

    # Case C: INDETERMINATE conditions (conflicting trade-offs: wave drops significantly, but wind surges)
    w_divergent = TimeWindowMetrics(
        time_window="tomorrow",
        wind_speed_kmh=35.0,       # wind surges (+15 km/h > 3.0)
        wind_direction_deg=260.0,
        wave_height_m=0.80,        # wave calms (-0.40 m < -0.15)
        sea_state="smooth",
        rain_probability=20.0,
        risk_score=2.5,            # risk score net unchanged
        risk_level="LOW",
        source_weather="OPEN_METEO",
        source_ocean="OPEN_METEO"
    )
    res_divergent = engine.compare_time_windows(eval_point, w_base, w_divergent)
    assert res_divergent.trend == "INDETERMINATE"
    assert "trade-offs" in res_divergent.recommendation.lower()


def test_temporal_comparison_preserves_provenance(eval_point):
    """Verify that provenance notice and underlying source labels are preserved."""
    w1 = TimeWindowMetrics(
        time_window="morning",
        wind_speed_kmh=15.0,
        wind_direction_deg=270.0,
        wave_height_m=1.0,
        sea_state="slight",
        rain_probability=10.0,
        risk_score=1.5,
        risk_level="LOW",
        source_weather="OPEN_METEO_WEATHER",
        source_ocean="OPEN_METEO_MARINE"
    )
    w2 = TimeWindowMetrics(
        time_window="afternoon",
        wind_speed_kmh=16.0,
        wind_direction_deg=270.0,
        wave_height_m=1.05,
        sea_state="slight",
        rain_probability=12.0,
        risk_score=1.6,
        risk_level="LOW",
        source_weather="OPEN_METEO_WEATHER",
        source_ocean="OPEN_METEO_MARINE"
    )

    res = temporal_engine.compare_time_windows(eval_point, w1, w2)
    assert res.provenance_notice == "Derived calculation comparing forecast horizons at evaluation point."
    assert res.window_1.source_weather == "OPEN_METEO_WEATHER"
    assert res.window_2.source_ocean == "OPEN_METEO_MARINE"


def test_temporal_custom_tolerances(eval_point):
    """Verify that tighter custom tolerances alter STABLE classification to DETERIORATING."""
    w1 = TimeWindowMetrics(
        time_window="today",
        wind_speed_kmh=20.0,
        wind_direction_deg=270.0,
        wave_height_m=1.0,
        sea_state="slight",
        rain_probability=10.0,
        risk_score=2.0,
        risk_level="LOW",
        source_weather="MOCK",
        source_ocean="MOCK"
    )
    w2 = TimeWindowMetrics(
        time_window="tomorrow",
        wind_speed_kmh=22.0,       # delta = +2.0
        wind_direction_deg=270.0,
        wave_height_m=1.12,        # delta = +0.12
        sea_state="slight",
        rain_probability=10.0,
        risk_score=2.3,            # delta = +0.3
        risk_level="LOW",
        source_weather="MOCK",
        source_ocean="MOCK"
    )

    # With default tolerances (wave tol=0.15, wind tol=3.0, risk tol=0.5): STABLE
    res_default = temporal_engine.compare_time_windows(eval_point, w1, w2)
    assert res_default.trend == "STABLE"

    # With tight custom tolerances (wave tol=0.05, wind tol=1.0, risk tol=0.2): DETERIORATING
    tight_tols = {
        "wave_delta_m": 0.05,
        "wind_delta_kmh": 1.0,
        "rain_delta_pct": 5.0,
        "risk_score_delta": 0.2
    }
    res_tight = temporal_engine.compare_time_windows(eval_point, w1, w2, tolerances=tight_tols)
    assert res_tight.trend == "DETERIORATING"


def test_extract_window_metrics_helper(eval_point):
    """Verify that extract_window_metrics correctly translates WeatherData and OceanData."""
    weather = WeatherData(
        temperature_c=29.2,
        wind_speed_kmh=24.6,
        wind_direction_deg=285.0,
        rain_probability=35.0,
        lightning_risk="none",
        source="OPEN_METEO_WEATHER"
    )
    ocean = OceanData(
        sst_c=28.4,
        wave_height_m=1.65,
        sea_state="moderate",
        tide="falling",
        source="OPEN_METEO_MARINE"
    )

    metrics = temporal_engine.extract_window_metrics(
        time_window="tomorrow_morning",
        weather=weather,
        ocean=ocean,
        risk_score=3.5,
        risk_level="MODERATE"
    )

    assert metrics.time_window == "tomorrow_morning"
    assert metrics.wind_speed_kmh == 24.6
    assert metrics.wave_height_m == 1.65
    assert metrics.risk_score == 3.5
    assert metrics.risk_level == "MODERATE"
    assert metrics.source_weather == "OPEN_METEO_WEATHER"
    assert metrics.source_ocean == "OPEN_METEO_MARINE"
