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
from app.tools.marine_cache import marine_cache


@pytest.fixture(autouse=True)
def clean_marine_cache():
    """Ensure every test executes with an isolated, clean telemetry cache."""
    marine_cache.clear()
    yield
    marine_cache.clear()


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

    # Data hardening: retrieved_at exists and is separate from forecast_timestamp
    assert res.get("retrieved_at") is not None
    assert res.get("forecast_timestamp") is not None
    assert res["retrieved_at"] != res["forecast_timestamp"]

    # Data hardening: explicit units metadata present
    assert "units" in res and res["units"] is not None
    assert res["units"]["wind_speed"] == {"value": 12.5, "unit": "km/h"}
    assert res["units"]["temperature"] == {"value": 28.2, "unit": "°C"}
    assert res["units"]["rain_probability"] == {"value": 35.0, "unit": "%"}

    # Pydantic schema validation
    w_model = WeatherData(**res)
    assert w_model.retrieved_at is not None
    assert w_model.forecast_timestamp is not None
    assert w_model.units["wind_speed"]["value"] == 12.5

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

    # Data hardening: retrieved_at exists and is separate from forecast_timestamp
    assert res.get("retrieved_at") is not None
    assert res.get("forecast_timestamp") is not None
    assert res["retrieved_at"] != res["forecast_timestamp"]

    # Data hardening: explicit units metadata present
    assert "units" in res and res["units"] is not None
    assert res["units"]["wave_height"] == {"value": 1.4, "unit": "m"}
    assert res["units"]["sea_surface_temperature"] == {"value": 29.2, "unit": "°C"}
    assert res["units"]["current_speed"] == {"value": 1.5, "unit": "knots"}

    # Pydantic schema validation
    o_model = OceanData(**res)
    assert o_model.retrieved_at is not None
    assert o_model.forecast_timestamp is not None
    assert o_model.units["wave_height"]["value"] == 1.4

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


# ---------------------------------------------------------------------------
# Data-Layer Hardening: Caching, Units & Terminology Tests
# ---------------------------------------------------------------------------

def test_cache_hit_avoids_second_http_request():
    """Verify in-memory cache hit prevents a second outbound HTTP call."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_WEATHER_API_RESPONSE

    with patch.object(httpx.Client, "get", return_value=mock_resp) as mock_get:
        # First call: cache miss, triggers HTTP call
        res1 = OpenMeteoWeatherAdapter.fetch_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")
        assert mock_get.call_count == 1
        assert res1["is_mock"] is False

        # Second call with identical params: cache hit, no HTTP call
        res2 = OpenMeteoWeatherAdapter.fetch_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")
        assert mock_get.call_count == 1  # Still 1!
        assert res2["wind_speed_kmh"] == res1["wind_speed_kmh"]
        assert res2["retrieved_at"] == res1["retrieved_at"]


def test_cache_expiration_causes_fresh_request():
    """Verify expired cache entries trigger a fresh outbound HTTP request."""
    import time
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_WEATHER_API_RESPONSE

    # Temporarily set TTL to 0.05s
    original_ttl = marine_cache.ttl_seconds
    marine_cache.ttl_seconds = 0.05
    try:
        with patch.object(httpx.Client, "get", return_value=mock_resp) as mock_get:
            res1 = OpenMeteoWeatherAdapter.fetch_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")
            assert mock_get.call_count == 1

            # Sleep longer than TTL to expire the cache
            time.sleep(0.06)

            # Fresh request must be triggered
            res2 = OpenMeteoWeatherAdapter.fetch_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")
            assert mock_get.call_count == 2
    finally:
        marine_cache.ttl_seconds = original_ttl


def test_fallback_data_does_not_overwrite_live_cached_data():
    """Verify fallback or mock payloads never overwrite live cache entries."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_WEATHER_API_RESPONSE

    # Populate cache with live response
    with patch.object(httpx.Client, "get", return_value=mock_resp):
        live_res = OpenMeteoWeatherAdapter.fetch_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")

    cached_before = marine_cache.get("weather", 9.9312, 76.2673, "tomorrow_morning")
    assert cached_before is not None
    assert cached_before["is_mock"] is False

    # Attempt to write mock fallback data
    fallback_payload = MockWeatherDataAdapter.get_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")
    fallback_payload["is_fallback"] = True
    marine_cache.set("weather", 9.9312, 76.2673, "tomorrow_morning", fallback_payload)

    # Verify cache still holds the live data, not the fallback
    cached_after = marine_cache.get("weather", 9.9312, 76.2673, "tomorrow_morning")
    assert cached_after["is_mock"] is False
    assert cached_after["wind_speed_kmh"] == live_res["wind_speed_kmh"]


def test_retrieved_at_is_none_for_mock_and_fallback():
    """Verify retrieved_at is explicitly None for mock datasets and failure fallbacks."""
    # Direct mock weather
    mock_w = MockWeatherDataAdapter.get_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")
    assert mock_w["retrieved_at"] is None
    assert mock_w["is_mock"] is True

    # Direct mock ocean
    mock_o = MockOceanDataAdapter.get_ocean_conditions("Kochi Offshore", 9.9312, 76.2673, "tomorrow_morning")
    assert mock_o["retrieved_at"] is None
    assert mock_o["is_mock"] is True

    # Failure fallback through WeatherDataAdapter
    with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("Offline")):
        fallback_w = WeatherDataAdapter.get_forecast("Kochi", 9.9312, 76.2673, "tomorrow_morning")
    assert fallback_w["retrieved_at"] is None
    assert fallback_w["is_mock"] is True
    assert fallback_w["is_fallback"] is True


def test_pfz_prohibited_terminology_cleanup():
    """Verify prohibited terms (active PFZ, best PFZ, current PFZ) are not used in generated responses."""
    from app.services.llm_service import llm_service

    # When no PFZ targets are present
    response = llm_service.synthesize_response(
        intent="pfz_search",
        location={"name": "Kochi"},
        time_range="tomorrow_morning",
        geospatial={},
        selected_pfz=None
    )

    assert "No PFZ targets detected in the local demonstration database." in response
    assert "No active PFZ points detected" not in response
    assert "active pfz" not in response.lower()
    assert "best pfz" not in response.lower()
    assert "current pfz" not in response.lower()
    assert "high-probability pfz" not in response.lower()


def test_weather_and_ocean_units_schema_validation():
    """Verify WeatherData and OceanData schemas parse and expose structured unit metadata."""
    w = WeatherData(
        source="OPEN_METEO_WEATHER",
        location="Kochi",
        forecast_time="tomorrow_morning",
        forecast_timestamp="2026-09-24T08:00",
        retrieved_at="2026-09-23T16:00:00Z",
        wind_speed_kmh=18.5,
        rain_probability=20.0,
        units={
            "wind_speed": {"value": 18.5, "unit": "km/h"},
            "rain_probability": {"value": 20.0, "unit": "%"}
        }
    )
    assert w.units["wind_speed"]["value"] == 18.5
    assert w.units["wind_speed"]["unit"] == "km/h"
    assert w.retrieved_at == "2026-09-23T16:00:00Z"
    assert w.forecast_timestamp == "2026-09-24T08:00"

    o = OceanData(
        source="OPEN_METEO_MARINE",
        location="Kochi Offshore",
        sst_c=29.1,
        wave_height_m=1.2,
        sea_state="slight",
        tide="rising",
        retrieved_at="2026-09-23T16:00:00Z",
        forecast_timestamp="2026-09-24T08:00",
        units={
            "wave_height": {"value": 1.2, "unit": "m"},
            "sea_surface_temperature": {"value": 29.1, "unit": "°C"}
        }
    )
    assert o.units["wave_height"]["value"] == 1.2
    assert o.units["wave_height"]["unit"] == "m"
    assert o.retrieved_at == "2026-09-23T16:00:00Z"
    assert o.forecast_timestamp == "2026-09-24T08:00"

