"""ORCA Marine Intelligence - Weather Data Adapter

Provides structured coastal meteorological conditions.
Integrates live Open-Meteo Weather API with automatic fallback to high-fidelity
mock data upon network failure, timeout, or invalid response.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os
import logging
import httpx
from app.tools.marine_cache import marine_cache

logger = logging.getLogger("orca.tools.weather")

OPEN_METEO_TIMEOUT_SECONDS = float(os.getenv("OPEN_METEO_TIMEOUT", "4.0"))

WMO_WEATHER_CODE_DESCRIPTIONS: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm (slight or moderate)",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class MockWeatherDataAdapter:
    """Mock weather adapter for Kochi coastal region."""

    SOURCE_NAME = "MOCK_WEATHER_DATA"

    DEFAULT_FORECAST = {
        "tomorrow_morning": {
            "wind_speed_kmh": 32.0,
            "wind_direction_deg": 280.0,
            "rain_probability": 65.0,
            "lightning_risk": "moderate",
            "weather_alert": None,
            "temperature_c": 28.5,
            "visibility_km": 7.5,
        },
        "current": {
            "wind_speed_kmh": 18.0,
            "wind_direction_deg": 260.0,
            "rain_probability": 20.0,
            "lightning_risk": "low",
            "weather_alert": None,
            "temperature_c": 29.8,
            "visibility_km": 10.0,
        },
        "tomorrow_afternoon": {
            "wind_speed_kmh": 36.0,
            "wind_direction_deg": 290.0,
            "rain_probability": 75.0,
            "lightning_risk": "high",
            "weather_alert": "Squally weather warning: Wind gusts up to 45 km/h expected off Kerala coast.",
            "temperature_c": 27.8,
            "visibility_km": 5.0,
        }
    }

    @classmethod
    def get_forecast(
        cls,
        location_name: str = "Kochi",
        latitude: float = 9.9312,
        longitude: float = 76.2673,
        time_range: str = "tomorrow_morning"
    ) -> Dict[str, Any]:
        """Fetch simulated weather data for location and time window."""
        logger.info(
            f"MockWeatherDataAdapter: providing fallback forecast for {location_name} "
            f"({latitude}, {longitude}) at {time_range}"
        )

        time_key = time_range.lower().replace(" ", "_")
        if time_key not in cls.DEFAULT_FORECAST:
            time_key = "tomorrow_morning"

        profile = cls.DEFAULT_FORECAST[time_key]

        units = {
            "wind_speed": {"value": profile["wind_speed_kmh"], "unit": "km/h"},
            "wind_direction": {"value": profile["wind_direction_deg"], "unit": "deg"},
            "rain_probability": {"value": profile["rain_probability"], "unit": "%"},
            "temperature": {"value": profile["temperature_c"], "unit": "°C"},
            "visibility": {"value": profile.get("visibility_km", 8.0), "unit": "km"},
        }

        return {
            "source": cls.SOURCE_NAME,
            "location": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "forecast_time": time_range,
            "forecast_timestamp": None,
            "retrieved_at": None,
            "wind_speed_kmh": profile["wind_speed_kmh"],
            "wind_direction_deg": profile["wind_direction_deg"],
            "rain_probability": profile["rain_probability"],
            "lightning_risk": profile["lightning_risk"],
            "weather_alert": profile["weather_alert"],
            "weather_condition": "Simulated coastal conditions",
            "temperature_c": profile["temperature_c"],
            "visibility_km": profile.get("visibility_km", 8.0),
            "is_mock": True,
            "units": units,
            "notice": "DEMONSTRATION DATA ONLY. Not for actual maritime navigation."
        }


from app.tools.base_adapter import SourceProvenanceMetadata


class OpenMeteoWeatherAdapter:
    """Live weather adapter querying official Open-Meteo Forecast API."""

    SOURCE_NAME = "OPEN_METEO_WEATHER"
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    @classmethod
    def get_provenance(cls, is_live: bool = True, is_fallback: bool = False) -> SourceProvenanceMetadata:
        """Return standardized provenance metadata."""
        return SourceProvenanceMetadata(
            source_id="open_meteo_weather",
            source_name=cls.SOURCE_NAME if not is_fallback else "MOCK_WEATHER_DATA",
            source_type="LIVE_API" if (is_live and not is_fallback) else "MOCK_FALLBACK",
            coverage="Global Land & Marine Gridded Forecast (11km DWD/ECMWF)",
            update_frequency="Hourly",
            fetched_at=datetime.now(timezone.utc) if (is_live and not is_fallback) else None,
            is_live=is_live and not is_fallback,
            is_mock=is_fallback,
            is_fallback=is_fallback,
            limitations=[
                "Lightning risk metric unsupported by provider; intentionally excluded from numeric scoring.",
                "Hourly discrete forecast steps, not continuous real-time anemometer telemetry."
            ]
        )

    @classmethod
    def _find_forecast_index(cls, times: List[str], time_range: str) -> int:
        """Find the matching hourly forecast index based on requested time range."""
        if not times:
            return 0

        time_key = time_range.lower().replace(" ", "_")

        if time_key in ["current", "now", "today"]:
            return 0

        if time_key in ["tomorrow_morning", "tomorrow"]:
            # Look for index around 08:00 or 06:00 on day 2 (index >= 24)
            for target_hour in ["T08:00", "T06:00", "T07:00", "T09:00"]:
                for idx, t in enumerate(times):
                    if idx >= 20 and target_hour in t:
                        return idx
            # Fallback to ~24 hours ahead
            return min(len(times) - 1, 24 + 8)

        if time_key == "tomorrow_afternoon":
            for target_hour in ["T14:00", "T12:00", "T13:00", "T15:00"]:
                for idx, t in enumerate(times):
                    if idx >= 20 and target_hour in t:
                        return idx
            return min(len(times) - 1, 24 + 14)

        return 0

    @classmethod
    def fetch_forecast(
        cls,
        location_name: str = "Kochi",
        latitude: float = 9.9312,
        longitude: float = 76.2673,
        time_range: str = "tomorrow_morning"
    ) -> Dict[str, Any]:
        """Fetch live weather forecast from Open-Meteo and parse structured output."""
        # Check in-memory cache before performing HTTP call
        cached = marine_cache.get("weather", latitude, longitude, time_range)
        if cached:
            return cached

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "wind_speed_10m,wind_direction_10m,precipitation_probability,weather_code,temperature_2m,visibility",
            "wind_speed_unit": "kmh",
            "timezone": "auto",
            "forecast_days": 2,
        }

        logger.info(
            f"OpenMeteoWeatherAdapter: Querying live forecast for {location_name} "
            f"({latitude}, {longitude}) at {time_range} [Timeout: {OPEN_METEO_TIMEOUT_SECONDS}s]"
        )

        with httpx.Client(timeout=OPEN_METEO_TIMEOUT_SECONDS) as client:
            response = client.get(cls.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        # Capture actual machine time when live HTTP response successfully returned
        retrieved_at = datetime.now(timezone.utc).isoformat()

        if "hourly" not in data or "time" not in data["hourly"]:
            raise ValueError("Open-Meteo response missing 'hourly.time' data array.")

        hourly = data["hourly"]
        times = hourly.get("time", [])
        if not times:
            raise ValueError("Open-Meteo response contained empty hourly time series.")

        idx = cls._find_forecast_index(times, time_range)
        forecast_timestamp = times[idx]

        wind_speed = float(hourly["wind_speed_10m"][idx]) if hourly.get("wind_speed_10m") and hourly["wind_speed_10m"][idx] is not None else 0.0
        wind_dir = float(hourly["wind_direction_10m"][idx]) if hourly.get("wind_direction_10m") and hourly["wind_direction_10m"][idx] is not None else 270.0
        rain_prob = float(hourly["precipitation_probability"][idx]) if hourly.get("precipitation_probability") and hourly["precipitation_probability"][idx] is not None else 0.0
        temp_c = float(hourly["temperature_2m"][idx]) if hourly.get("temperature_2m") and hourly["temperature_2m"][idx] is not None else 28.0

        w_code = int(hourly["weather_code"][idx]) if hourly.get("weather_code") and hourly["weather_code"][idx] is not None else 0
        condition_desc = WMO_WEATHER_CODE_DESCRIPTIONS.get(w_code, f"Weather Code {w_code}")

        visibility_km: Optional[float] = None
        if hourly.get("visibility") and hourly["visibility"][idx] is not None:
            visibility_km = round(float(hourly["visibility"][idx]) / 1000.0, 1)

        weather_alert: Optional[str] = None
        if wind_speed >= 45.0:
            weather_alert = f"Gale warning: High wind speeds of {wind_speed} km/h forecast for sector."
        elif w_code in [95, 96, 99]:
            weather_alert = f"Convective weather advisory: Thunderstorm conditions detected ({condition_desc})."

        # Explicitly enforce Requirement 1:
        # Open-Meteo does not provide marine lightning risk. Do NOT fabricate or infer.
        lightning_risk = "unsupported"

        units = {
            "wind_speed": {"value": wind_speed, "unit": "km/h"},
            "wind_direction": {"value": wind_dir, "unit": "deg"},
            "rain_probability": {"value": rain_prob, "unit": "%"},
            "temperature": {"value": temp_c, "unit": "°C"},
            "visibility": {"value": visibility_km if visibility_km is not None else 8.0, "unit": "km"},
        }

        result = {
            "source": cls.SOURCE_NAME,
            "location": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "forecast_time": time_range,
            "forecast_timestamp": forecast_timestamp,
            "retrieved_at": retrieved_at,
            "wind_speed_kmh": wind_speed,
            "wind_direction_deg": wind_dir,
            "rain_probability": rain_prob,
            "lightning_risk": lightning_risk,
            "weather_condition": condition_desc,
            "weather_alert": weather_alert,
            "temperature_c": temp_c,
            "visibility_km": visibility_km if visibility_km is not None else 8.0,
            "is_mock": False,
            "units": units,
            "raw_metadata": {
                "provider": "Open-Meteo",
                "api_endpoint": cls.BASE_URL,
                "queried_coordinates": [latitude, longitude],
                "resolved_forecast_timestamp": forecast_timestamp,
                "retrieved_at": retrieved_at,
                "wmo_code": w_code,
                "lightning_risk_notice": "Lightning risk was not provided by the selected live source (Open-Meteo) and is marked as unsupported."
            }
        }

        # Cache successful live payload
        marine_cache.set("weather", latitude, longitude, time_range, result)

        return result


class WeatherDataAdapter:
    """Primary Weather Data Adapter with transparent live query and automated mock fallback."""

    SOURCE_NAME = "OPEN_METEO_WEATHER"

    @classmethod
    def get_forecast(
        cls,
        location_name: str = "Kochi",
        latitude: float = 9.9312,
        longitude: float = 76.2673,
        time_range: str = "tomorrow_morning"
    ) -> Dict[str, Any]:
        """Fetch weather data, attempting live Open-Meteo with automatic mock fallback."""
        enable_live = os.getenv("ORCA_ENABLE_LIVE_WEATHER", "true").lower() == "true"

        if enable_live:
            try:
                return OpenMeteoWeatherAdapter.fetch_forecast(
                    location_name=location_name,
                    latitude=latitude,
                    longitude=longitude,
                    time_range=time_range
                )
            except Exception as e:
                logger.warning(
                    f"OpenMeteoWeatherAdapter failed for {location_name} ({latitude}, {longitude}): "
                    f"{type(e).__name__} - {e}. Executing automatic fallback to MockWeatherDataAdapter."
                )
                fallback_data = MockWeatherDataAdapter.get_forecast(
                    location_name=location_name,
                    latitude=latitude,
                    longitude=longitude,
                    time_range=time_range
                )
                fallback_data["is_fallback"] = True
                fallback_data["raw_metadata"] = {
                    "provider": "Mock (Fallback from Open-Meteo)",
                    "live_attempted": True,
                    "is_fallback": True,
                    "fallback_reason": f"{type(e).__name__}: {str(e)}"
                }
                return fallback_data

        return MockWeatherDataAdapter.get_forecast(
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            time_range=time_range
        )
