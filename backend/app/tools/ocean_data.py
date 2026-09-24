"""ORCA Marine Intelligence - Ocean Data Adapter

Provides oceanographic and hydrodynamic telemetry (SST, waves, tides, sea state).
Integrates live Open-Meteo Marine API with automated fallback to high-fidelity
mock data upon network failure, timeout, or invalid response.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os
import logging
import httpx
from app.tools.marine_cache import marine_cache

logger = logging.getLogger("orca.tools.ocean")

OPEN_METEO_TIMEOUT_SECONDS = float(os.getenv("OPEN_METEO_TIMEOUT", "4.0"))


class MockOceanDataAdapter:
    """Mock ocean data adapter for Kochi offshore waters."""

    SOURCE_NAME = "MOCK_OCEAN_DATA"

    DEFAULT_OCEAN_STATE = {
        "sst_c": 28.4,
        "wave_height_m": 1.8,
        "sea_state": "moderate",
        "tide": "rising",
        "chlorophyll_mg_m3": 0.72,
        "salinity_psu": 34.6,
        "current_speed_knots": 1.4,
        "wave_period_s": 7.2,
        "primary_swell_direction_deg": 245.0,
    }

    @classmethod
    def get_ocean_conditions(
        cls,
        location_name: str = "Kochi Offshore",
        latitude: float = 9.9312,
        longitude: float = 76.2673,
        time_range: str = "tomorrow_morning"
    ) -> Dict[str, Any]:
        """Fetch simulated ocean physical & biological parameters."""
        logger.info(
            f"MockOceanDataAdapter: providing fallback ocean state for {location_name} "
            f"({latitude}, {longitude}) at {time_range}"
        )

        state = cls.DEFAULT_OCEAN_STATE.copy()

        units = {
            "wave_height": {"value": state["wave_height_m"], "unit": "m"},
            "wave_direction": {"value": state.get("primary_swell_direction_deg"), "unit": "deg"},
            "wave_period": {"value": state.get("wave_period_s"), "unit": "s"},
            "sea_surface_temperature": {"value": state["sst_c"], "unit": "°C"},
            "current_speed": {"value": state["current_speed_knots"], "unit": "knots"},
            "sea_level_height": {"value": None, "unit": "m"},
        }

        return {
            "source": cls.SOURCE_NAME,
            "location": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "forecast_time": time_range,
            "forecast_timestamp": None,
            "retrieved_at": None,
            "sst_c": state["sst_c"],
            "wave_height_m": state["wave_height_m"],
            "sea_state": state["sea_state"],
            "tide": state["tide"],
            "chlorophyll_mg_m3": state["chlorophyll_mg_m3"],
            "salinity_psu": state["salinity_psu"],
            "current_speed_knots": state["current_speed_knots"],
            "wave_period_s": state["wave_period_s"],
            "wave_direction_deg": state["primary_swell_direction_deg"],
            "is_mock": True,
            "units": units,
            "notice": "DEMONSTRATION OCEANOGRAPHIC DATA ONLY."
        }


from app.tools.base_adapter import SourceProvenanceMetadata


class OpenMeteoMarineAdapter:
    """Live marine adapter querying official Open-Meteo Marine Forecast API."""

    SOURCE_NAME = "OPEN_METEO_MARINE"
    BASE_URL = "https://marine-api.open-meteo.com/v1/marine"

    @classmethod
    def get_provenance(cls, is_live: bool = True, is_fallback: bool = False) -> SourceProvenanceMetadata:
        """Return standardized provenance metadata."""
        return SourceProvenanceMetadata(
            source_id="open_meteo_marine",
            source_name=cls.SOURCE_NAME if not is_fallback else "MOCK_OCEAN_DATA",
            source_type="LIVE_API" if (is_live and not is_fallback) else "MOCK_FALLBACK",
            coverage="Global Ocean Gridded Hydrodynamic Models (Copernicus / ECMWF WAM)",
            update_frequency="Hourly",
            fetched_at=datetime.now(timezone.utc) if (is_live and not is_fallback) else None,
            is_live=is_live and not is_fallback,
            is_mock=is_fallback,
            is_fallback=is_fallback,
            limitations=[
                "Chlorophyll-a requires specialized optical ocean color satellite credentials (Copernicus / NASA).",
                "Tidal sea-level trends represent astronomical/hydrodynamic models rather than acoustic gauge readings."
            ]
        )

    @staticmethod
    def _calculate_sea_state(wave_height_m: float) -> str:
        """Map significant wave height to Douglas Sea Scale."""
        if wave_height_m < 0.1:
            return "calm"
        elif wave_height_m < 0.5:
            return "smooth"
        elif wave_height_m < 1.25:
            return "slight"
        elif wave_height_m < 2.5:
            return "moderate"
        elif wave_height_m < 4.0:
            return "rough"
        elif wave_height_m < 6.0:
            return "very_rough"
        else:
            return "high"

    @classmethod
    def _find_forecast_index(cls, times: List[str], time_range: str) -> int:
        """Find the matching hourly forecast index based on requested time range."""
        if not times:
            return 0

        time_key = time_range.lower().replace(" ", "_")

        if time_key in ["current", "now"]:
            return 0

        # Day 1 (Today)
        if time_key in ["today", "today_morning"]:
            for target_hour in ["T08:00", "T06:00", "T07:00", "T09:00"]:
                for idx, t in enumerate(times[:24]):
                    if target_hour in t:
                        return idx
            return min(len(times) - 1, 8)

        if time_key == "today_afternoon":
            for target_hour in ["T14:00", "T12:00", "T13:00", "T15:00"]:
                for idx, t in enumerate(times[:24]):
                    if target_hour in t:
                        return idx
            return min(len(times) - 1, 14)

        if time_key == "today_evening":
            for target_hour in ["T18:00", "T17:00", "T19:00", "T20:00"]:
                for idx, t in enumerate(times[:24]):
                    if target_hour in t:
                        return idx
            return min(len(times) - 1, 18)

        if time_key == "today_night":
            for target_hour in ["T22:00", "T21:00", "T23:00"]:
                for idx, t in enumerate(times[:24]):
                    if target_hour in t:
                        return idx
            return min(len(times) - 1, 22)

        # Day 2 (Tomorrow)
        if time_key in ["tomorrow_morning", "tomorrow"]:
            for target_hour in ["T08:00", "T06:00", "T07:00", "T09:00"]:
                for idx, t in enumerate(times[20:]):
                    if target_hour in t:
                        return idx + 20
            return min(len(times) - 1, 24 + 8)

        if time_key == "tomorrow_afternoon":
            for target_hour in ["T14:00", "T12:00", "T13:00", "T15:00"]:
                for idx, t in enumerate(times[20:]):
                    if target_hour in t:
                        return idx + 20
            return min(len(times) - 1, 24 + 14)

        if time_key == "tomorrow_evening":
            for target_hour in ["T18:00", "T17:00", "T19:00", "T20:00"]:
                for idx, t in enumerate(times[20:]):
                    if target_hour in t:
                        return idx + 20
            return min(len(times) - 1, 24 + 18)

        if time_key == "tomorrow_night":
            for target_hour in ["T22:00", "T21:00", "T23:00"]:
                for idx, t in enumerate(times[20:]):
                    if target_hour in t:
                        return idx + 20
            return min(len(times) - 1, 24 + 22)

        if "afternoon" in time_key:
            return min(len(times) - 1, 14)
        if "evening" in time_key:
            return min(len(times) - 1, 18)
        if "morning" in time_key:
            return min(len(times) - 1, 8)

        return 0

    @classmethod
    def fetch_conditions(
        cls,
        location_name: str = "Kochi Offshore",
        latitude: float = 9.9312,
        longitude: float = 76.2673,
        time_range: str = "tomorrow_morning"
    ) -> Dict[str, Any]:
        """Fetch live oceanographic telemetry from Open-Meteo Marine API."""
        # Check in-memory cache before performing HTTP call
        cached = marine_cache.get("ocean", latitude, longitude, time_range)
        if cached:
            return cached

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "wave_height,wave_direction,wave_period,ocean_current_velocity,ocean_current_direction,sea_surface_temperature,sea_level_height_msl",
            "timezone": "auto",
            "forecast_days": 2,
        }

        logger.info(
            f"OpenMeteoMarineAdapter: Querying live marine telemetry for {location_name} "
            f"({latitude}, {longitude}) at {time_range} [Timeout: {OPEN_METEO_TIMEOUT_SECONDS}s]"
        )

        with httpx.Client(timeout=OPEN_METEO_TIMEOUT_SECONDS) as client:
            response = client.get(cls.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        # Capture actual machine time when live HTTP response successfully returned
        retrieved_at = datetime.now(timezone.utc).isoformat()

        if "hourly" not in data or "time" not in data["hourly"]:
            raise ValueError("Open-Meteo marine response missing 'hourly.time' series.")

        hourly = data["hourly"]
        times = hourly.get("time", [])
        if not times:
            raise ValueError("Open-Meteo marine response contained empty time series.")

        idx = cls._find_forecast_index(times, time_range)
        forecast_timestamp = times[idx]

        wave_height = float(hourly["wave_height"][idx]) if hourly.get("wave_height") and hourly["wave_height"][idx] is not None else 1.0
        wave_direction = float(hourly["wave_direction"][idx]) if hourly.get("wave_direction") and hourly["wave_direction"][idx] is not None else None
        wave_period = float(hourly["wave_period"][idx]) if hourly.get("wave_period") and hourly["wave_period"][idx] is not None else None
        sst_c = float(hourly["sea_surface_temperature"][idx]) if hourly.get("sea_surface_temperature") and hourly["sea_surface_temperature"][idx] is not None else 28.0

        current_velocity_kmh = float(hourly["ocean_current_velocity"][idx]) if hourly.get("ocean_current_velocity") and hourly["ocean_current_velocity"][idx] is not None else 0.0
        current_speed_knots = round(current_velocity_kmh / 1.852, 2)
        current_direction = float(hourly["ocean_current_direction"][idx]) if hourly.get("ocean_current_direction") and hourly["ocean_current_direction"][idx] is not None else None

        sea_state = cls._calculate_sea_state(wave_height)

        # Sea level height and forecast trend calculation (Requirement 2):
        sea_levels = hourly.get("sea_level_height_msl", [])
        sea_level_m: Optional[float] = None
        tide_trend_label = "forecast sea-level trend: steady"

        if sea_levels and idx < len(sea_levels) and sea_levels[idx] is not None:
            sea_level_m = round(float(sea_levels[idx]), 2)
            # Compare with adjacent hourly values
            if idx > 0 and sea_levels[idx - 1] is not None:
                delta = float(sea_levels[idx]) - float(sea_levels[idx - 1])
            elif idx + 1 < len(sea_levels) and sea_levels[idx + 1] is not None:
                delta = float(sea_levels[idx + 1]) - float(sea_levels[idx])
            else:
                delta = 0.0

            if delta > 0.02:
                tide_trend_label = "rising (forecast sea-level trend)"
            elif delta < -0.02:
                tide_trend_label = "falling (forecast sea-level trend)"
            else:
                tide_trend_label = "steady (forecast sea-level trend)"
        else:
            tide_trend_label = "unavailable (forecast sea-level trend)"

        # Chlorophyll is NOT provided by Open-Meteo. Do NOT fabricate (Requirement 8).
        chlorophyll_mg_m3: Optional[float] = None

        units = {
            "wave_height": {"value": wave_height, "unit": "m"},
            "wave_direction": {"value": wave_direction, "unit": "deg"},
            "wave_period": {"value": wave_period, "unit": "s"},
            "sea_surface_temperature": {"value": sst_c, "unit": "°C"},
            "current_speed": {"value": current_speed_knots, "unit": "knots"},
            "current_direction": {"value": current_direction, "unit": "deg"},
            "sea_level_height": {"value": sea_level_m, "unit": "m"},
        }

        result = {
            "source": cls.SOURCE_NAME,
            "location": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "forecast_time": time_range,
            "forecast_timestamp": forecast_timestamp,
            "retrieved_at": retrieved_at,
            "sst_c": sst_c,
            "wave_height_m": wave_height,
            "wave_direction_deg": wave_direction,
            "wave_period_s": wave_period,
            "sea_state": sea_state,
            "tide": tide_trend_label,
            "sea_level_height_m": sea_level_m,
            "tide_note": "Local sea-level trend determined by comparing adjacent Open-Meteo forecast values. Not authoritative coastal navigation tide information.",
            "chlorophyll_mg_m3": chlorophyll_mg_m3,
            "salinity_psu": None,
            "current_speed_knots": current_speed_knots,
            "current_direction_deg": current_direction,
            "is_mock": False,
            "units": units,
            "raw_metadata": {
                "provider": "Open-Meteo Marine",
                "api_endpoint": cls.BASE_URL,
                "queried_coordinates": [latitude, longitude],
                "resolved_forecast_timestamp": forecast_timestamp,
                "retrieved_at": retrieved_at,
                "sea_level_height_msl": sea_level_m,
                "chlorophyll_notice": "Chlorophyll data is not provided by Open-Meteo Marine API and is marked as unsupported."
            }
        }

        # Cache successful live payload
        marine_cache.set("ocean", latitude, longitude, time_range, result)

        return result


class OceanDataAdapter:
    """Primary Ocean Data Adapter with transparent live query and automated mock fallback."""

    SOURCE_NAME = "OPEN_METEO_MARINE"

    @classmethod
    def get_ocean_conditions(
        cls,
        location_name: str = "Kochi Offshore",
        latitude: float = 9.9312,
        longitude: float = 76.2673,
        time_range: str = "tomorrow_morning"
    ) -> Dict[str, Any]:
        """Fetch ocean telemetry, attempting live Open-Meteo Marine with automated mock fallback."""
        enable_live = os.getenv("ORCA_ENABLE_LIVE_OCEAN", "true").lower() == "true"

        if enable_live:
            try:
                return OpenMeteoMarineAdapter.fetch_conditions(
                    location_name=location_name,
                    latitude=latitude,
                    longitude=longitude,
                    time_range=time_range
                )
            except Exception as e:
                logger.warning(
                    f"OpenMeteoMarineAdapter failed for {location_name} ({latitude}, {longitude}): "
                    f"{type(e).__name__} - {e}. Executing automatic fallback to MockOceanDataAdapter."
                )
                fallback_data = MockOceanDataAdapter.get_ocean_conditions(
                    location_name=location_name,
                    latitude=latitude,
                    longitude=longitude,
                    time_range=time_range
                )
                fallback_data["is_fallback"] = True
                fallback_data["raw_metadata"] = {
                    "provider": "Mock (Fallback from Open-Meteo Marine)",
                    "live_attempted": True,
                    "is_fallback": True,
                    "fallback_reason": f"{type(e).__name__}: {str(e)}"
                }
                return fallback_data

        return MockOceanDataAdapter.get_ocean_conditions(
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            time_range=time_range
        )
