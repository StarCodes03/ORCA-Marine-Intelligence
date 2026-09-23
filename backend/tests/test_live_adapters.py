"""Unit tests for Open-Meteo live weather and marine adapters with mock fallback."""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.tools.weather_data import (
    WeatherDataAdapter,
    OpenMeteoWeatherAdapter,
    MockWeatherDataAdapter
)
from app.tools.ocean_data import (
    OceanDataAdapter,
    OpenMeteoMarineAdapter,
    MockOceanDataAdapter
)
from app.models.schemas import LocationCoords, WeatherData, OceanData
from app.agents.risk import RiskAssessmentAgent
from app.agents.evidence import EvidenceAgent
from app.models.schemas import PlannerOutput


# ---------------------------------------------------------------------------
# Sample Mock HTTP Payloads
# ---------------------------------------------------------------------------

SAMPLE_WEATHER_API_RESPONSE = {
    "latitude": 9.93,
    "longitude": 76.27,
    "hourly": {
        "time": [
            f"2026-09-22T{h:02d}:00" for h in range(24)
        ] + [
            f"2026-09-23T{h:02d}:00" for h in range(24)
        ],
        "wind_speed_10m": [12.5] * 48,
        "wind_direction_10m": [260.0] * 48,
        "precipitation_probability": [35.0] * 48,
        "weather_code": [80] * 48,  # Slight rain showers
        "temperature_2m": [28.2] * 48,
        "visibility": [9500.0] * 48,
    }
}

SAMPLE_MARINE_API_RESPONSE = {
    "latitude": 9.93,
    "longitude": 76.27,
    "hourly": {
        "time": [
            f"2026-09-22T{h:02d}:00" for h in range(24)
        ] + [
            f"2026-09-23T{h:02d}:00" for h in range(24)
        ],
        "wave_height": [1.4] * 48,
        "wave_direction": [215.0] * 48,
        "wave_period": [8.2] * 48,
        "ocean_current_velocity": [2.78] * 48,  # ~1.5 knots (2.78 / 1.852)
        "ocean_current_direction": [190.0] * 48,
        "sea_surface_temperature": [29.2] * 48,
        # Simulate rising tide trend around hour 32 (day 2 08:00):
        "sea_level_height_msl": [0.10 + (i * 0.03) for i in range(48)],
    }
}


# ---------------------------------------------------------------------------
# Weather Adapter Tests
# ---------------------------------------------------------------------------

def test_weather_adapter_live_parsing_mocked_http():
    """Verify live weather parsing from Open-Meteo HTTP 200 payload."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_WEATHER_API_RESPONSE

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = OpenMeteoWeatherAdapter.fetch_forecast(
            location_name="Kochi",
            latitude=9.9312,
            longitude=76.2673,
            time_range="tomorrow_morning"
        )

    assert res["source"] == "OPEN_METEO_WEATHER"
    assert res["is_mock"] is False
    assert res["wind_speed_kmh"] == 12.5
    assert res["wind_direction_deg"] == 260.0
    assert res["rain_probability"] == 35.0
    assert res["temperature_c"] == 28.2
    assert res["visibility_km"] == 9.5
    assert "rain showers" in res["weather_condition"].lower()

    # Requirement 1 & 8: Lightning must be marked unsupported, not fabricated
    assert res["lightning_risk"] == "unsupported"
    assert "raw_metadata" in res
    assert res["raw_metadata"]["provider"] == "Open-Meteo"


def test_weather_adapter_http_500_fallback():
    """Verify automatic fallback to mock data when weather API returns HTTP 500."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=mock_resp
    )

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = WeatherDataAdapter.get_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")

    assert res["source"] == "MOCK_WEATHER_DATA"
    assert res["is_mock"] is True
    assert res["wind_speed_kmh"] == 32.0  # Mock tomorrow morning default
    assert res["lightning_risk"] == "moderate"


def test_weather_adapter_timeout_fallback():
    """Verify automatic fallback when weather API call times out."""
    with patch.object(httpx.Client, "get", side_effect=httpx.TimeoutException("Connection timed out")):
        res = WeatherDataAdapter.get_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")

    assert res["source"] == "MOCK_WEATHER_DATA"
    assert res["is_mock"] is True


def test_weather_adapter_invalid_response_fallback():
    """Verify fallback when weather API returns malformed or empty JSON."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"hourly": {}}  # Missing time array

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = WeatherDataAdapter.get_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")

    assert res["source"] == "MOCK_WEATHER_DATA"
    assert res["is_mock"] is True


# ---------------------------------------------------------------------------
# Marine Adapter Tests
# ---------------------------------------------------------------------------

def test_marine_adapter_live_parsing_mocked_http():
    """Verify live marine telemetry parsing from Open-Meteo Marine HTTP 200 payload."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_MARINE_API_RESPONSE

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = OpenMeteoMarineAdapter.fetch_conditions(
            location_name="Kochi Offshore",
            latitude=9.9312,
            longitude=76.2673,
            time_range="tomorrow_morning"
        )

    assert res["source"] == "OPEN_METEO_MARINE"
    assert res["is_mock"] is False
    assert res["wave_height_m"] == 1.4
    assert res["sea_state"] == "moderate"  # 1.25m to 2.5m = moderate
    assert res["wave_direction_deg"] == 215.0
    assert res["wave_period_s"] == 8.2
    assert res["sst_c"] == 29.2
    assert res["current_speed_knots"] == 1.5  # 2.78 km/h / 1.852 ≈ 1.5 knots

    # Requirement 2: Forecast sea-level trend tide label
    assert "rising (forecast sea-level trend)" in res["tide"]
    assert res["sea_level_height_m"] is not None
    assert "Not authoritative coastal navigation" in res["tide_note"]

    # Requirement 8: Chlorophyll must NOT be fabricated from Open-Meteo
    assert res["chlorophyll_mg_m3"] is None


def test_marine_adapter_falling_sea_level_trend():
    """Verify falling sea level trend calculation when adjacent values decrease."""
    falling_payload = {
        "hourly": {
            "time": [f"2026-09-22T{h:02d}:00" for h in range(24)] + [f"2026-09-23T{h:02d}:00" for h in range(24)],
            "wave_height": [1.0] * 48,
            "sea_level_height_msl": [1.0 - (i * 0.03) for i in range(48)],
        }
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = falling_payload

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = OpenMeteoMarineAdapter.fetch_conditions("Kochi Offshore", 9.9312, 76.2673, "tomorrow_morning")

    assert res["tide"] == "falling (forecast sea-level trend)"


def test_marine_adapter_http_error_fallback():
    """Verify fallback when marine API returns HTTP 502 Bad Gateway."""
    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Gateway", request=MagicMock(), response=mock_resp
    )

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = OceanDataAdapter.get_ocean_conditions("Kochi Offshore", 9.9312, 76.2673, "tomorrow_morning")

    assert res["source"] == "MOCK_OCEAN_DATA"
    assert res["is_mock"] is True
    assert res["wave_height_m"] == 1.8
    assert res["chlorophyll_mg_m3"] == 0.72


def test_marine_adapter_timeout_fallback():
    """Verify fallback when marine API request times out."""
    with patch.object(httpx.Client, "get", side_effect=httpx.TimeoutException("Marine API timeout")):
        res = OceanDataAdapter.get_ocean_conditions("Kochi Offshore", 9.9312, 76.2673, "tomorrow_morning")

    assert res["source"] == "MOCK_OCEAN_DATA"
    assert res["is_mock"] is True


def test_marine_adapter_invalid_json_fallback():
    """Verify fallback when marine API returns invalid JSON structure."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": True}

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = OceanDataAdapter.get_ocean_conditions("Kochi Offshore", 9.9312, 76.2673, "tomorrow_morning")

    assert res["source"] == "MOCK_OCEAN_DATA"
    assert res["is_mock"] is True


# ---------------------------------------------------------------------------
# Risk Engine & Evidence Handling with Live Adapters
# ---------------------------------------------------------------------------

def test_unsupported_lightning_does_not_score_and_is_not_treated_as_low():
    """Adjustment 1: Ensure unsupported lightning risk contributes 0.0 and threshold is N/A."""
    risk_agent = RiskAssessmentAgent()

    weather = WeatherData(
        source="OPEN_METEO_WEATHER",
        location="Kochi",
        forecast_time="tomorrow_morning",
        wind_speed_kmh=15.0,
        rain_probability=10.0,
        lightning_risk="unsupported",
        is_mock=False
    )

    assessment = risk_agent.assess(weather=weather, ocean=None, geospatial=None)

    # Lightning contribution must be 0.0 and threshold must NOT be labeled as "low"
    lightning_factor = next(f for f in assessment.score_breakdown.factors if f.factor == "lightning_risk")
    assert lightning_factor.contribution == 0.0
    assert "unsupported" in lightning_factor.threshold.lower()
    assert "low" not in lightning_factor.threshold.lower()

    # Evidence item must indicate unsupported
    evidence_agent = EvidenceAgent()
    plan = PlannerOutput(intent="marine_safety", location=LocationCoords())
    synth = evidence_agent.synthesize(planner_plan=plan, weather=weather)

    weather_evidence = next(e for e in synth["evidence"] if "Wind speed" in e.claim)
    assert "Lightning risk was not provided by the selected live source" in weather_evidence.claim
