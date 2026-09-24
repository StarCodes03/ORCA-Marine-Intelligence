"""ORCA Marine Intelligence - Weather Agent

Retrieves and validates coastal meteorological conditions via the weather data adapter.
Structured input/output with transparent source provenance.
"""

import logging
from typing import Dict, Any, Optional
from app.models.schemas import WeatherData, LocationCoords
from app.tools.weather_data import WeatherDataAdapter

logger = logging.getLogger("orca.agents.weather")


class WeatherAgent:
    """Specialized agent for marine atmospheric telemetry."""

    AGENT_NAME = "WeatherAgent"

    def execute(
        self,
        location: LocationCoords,
        time_range: str = "tomorrow_morning"
    ) -> WeatherData:
        """Fetch weather data for target coordinate sector and time window."""
        logger.info(
            f"[{self.AGENT_NAME}] Querying weather telemetry for {location.name} "
            f"({location.latitude}, {location.longitude}) at {time_range}"
        )

        raw_data = WeatherDataAdapter.get_forecast(
            location_name=location.name,
            latitude=location.latitude,
            longitude=location.longitude,
            time_range=time_range
        )

        weather_obj = WeatherData(
            source=raw_data["source"],
            location=raw_data["location"],
            forecast_time=raw_data["forecast_time"],
            forecast_timestamp=raw_data.get("forecast_timestamp"),
            retrieved_at=raw_data.get("retrieved_at"),
            wind_speed_kmh=raw_data["wind_speed_kmh"],
            wind_direction_deg=raw_data.get("wind_direction_deg", 270.0),
            rain_probability=raw_data["rain_probability"],
            lightning_risk=raw_data.get("lightning_risk", "unsupported"),
            weather_alert=raw_data.get("weather_alert"),
            weather_condition=raw_data.get("weather_condition"),
            temperature_c=raw_data.get("temperature_c", 28.5),
            visibility_km=raw_data.get("visibility_km"),
            is_mock=raw_data.get("is_mock", True),
            is_fallback=raw_data.get("is_fallback", False),
            units=raw_data.get("units"),
            raw_metadata=raw_data.get("raw_metadata")
        )

        logger.info(
            f"[{self.AGENT_NAME}] Retrieved: wind={weather_obj.wind_speed_kmh}km/h, "
            f"rain={weather_obj.rain_probability}%, lightning={weather_obj.lightning_risk}"
        )
        return weather_obj
