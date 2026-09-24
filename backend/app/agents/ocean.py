"""ORCA Marine Intelligence - Ocean Agent

Retrieves and formats physical and biological oceanographic parameters
(SST, wave dynamics, tides, sea state, chlorophyll).
Structured input/output with explicit source provenance.
"""

import logging
from typing import Dict, Any, Optional
from app.models.schemas import OceanData, LocationCoords
from app.tools.ocean_data import OceanDataAdapter

logger = logging.getLogger("orca.agents.ocean")


class OceanAgent:
    """Specialized agent for oceanographic and hydrodynamic telemetry."""

    AGENT_NAME = "OceanAgent"

    def execute(
        self,
        location: LocationCoords,
        time_range: str = "tomorrow_morning"
    ) -> OceanData:
        """Fetch ocean state for target coordinate sector and time window."""
        logger.info(
            f"[{self.AGENT_NAME}] Querying oceanographic telemetry for {location.name} "
            f"({location.latitude}, {location.longitude}) at {time_range}"
        )

        raw_data = OceanDataAdapter.get_ocean_conditions(
            location_name=f"{location.name} Offshore",
            latitude=location.latitude,
            longitude=location.longitude,
            time_range=time_range
        )

        ocean_obj = OceanData(
            source=raw_data["source"],
            location=raw_data["location"],
            forecast_time=raw_data.get("forecast_time"),
            forecast_timestamp=raw_data.get("forecast_timestamp"),
            retrieved_at=raw_data.get("retrieved_at"),
            sst_c=raw_data["sst_c"],
            wave_height_m=raw_data["wave_height_m"],
            sea_state=raw_data["sea_state"],
            tide=raw_data["tide"],
            chlorophyll_mg_m3=raw_data.get("chlorophyll_mg_m3"),
            salinity_psu=raw_data.get("salinity_psu", 34.6),
            current_speed_knots=raw_data.get("current_speed_knots", 1.4),
            current_direction_deg=raw_data.get("current_direction_deg"),
            wave_period_s=raw_data.get("wave_period_s"),
            wave_direction_deg=raw_data.get("wave_direction_deg"),
            sea_level_height_m=raw_data.get("sea_level_height_m"),
            tide_note=raw_data.get("tide_note"),
            is_mock=raw_data.get("is_mock", True),
            is_fallback=raw_data.get("is_fallback", False),
            units=raw_data.get("units"),
            raw_metadata=raw_data.get("raw_metadata")
        )

        chloro_display = f"{ocean_obj.chlorophyll_mg_m3}mg/m³" if ocean_obj.chlorophyll_mg_m3 is not None else "N/A (unsupported)"
        logger.info(
            f"[{self.AGENT_NAME}] Retrieved: wave={ocean_obj.wave_height_m}m, "
            f"sea_state='{ocean_obj.sea_state}', SST={ocean_obj.sst_c}°C, chlorophyll={chloro_display}"
        )
        return ocean_obj
