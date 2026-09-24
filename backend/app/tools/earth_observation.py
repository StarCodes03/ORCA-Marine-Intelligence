"""ORCA Marine Intelligence - Earth Observation & Ocean Color Adapter

Provides satellite ocean color and chlorophyll-a telemetry.
Integrates with Copernicus Marine Service and NOAA CoastWatch ERDDAP endpoints.
When unconfigured, cleanly discloses UNAVAILABLE state without fabricating data.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from app.tools.base_adapter import DataSourceAdapter, SourceProvenanceMetadata

logger = logging.getLogger("orca.tools.earth_observation")


class EarthObservationAdapter(DataSourceAdapter):
    """Adapter for satellite Earth Observation (chlorophyll-a, optical ocean color)."""

    def __init__(self):
        super().__init__(source_id="copernicus_ocean_color", source_name="COPERNICUS_MARINE_SERVICE")
        self.copernicus_key = os.getenv("COPERNICUS_API_KEY", "").strip()
        self.noaa_url = os.getenv("NOAA_COASTWATCH_URL", "").strip()
        self._is_configured = bool(self.copernicus_key or self.noaa_url)

    def is_available(self) -> bool:
        """Return True only when legitimate Earth Observation API credentials are configured."""
        return self._is_configured

    def get_provenance(self) -> SourceProvenanceMetadata:
        """Standardized provenance disclosure."""
        if not self._is_configured:
            return SourceProvenanceMetadata(
                source_id=self.source_id,
                source_name=self.source_name,
                source_type="UNAVAILABLE",
                coverage="Global Ocean (Copernicus Sentinel-3 OLCI / MODIS)",
                update_frequency="Daily 300m / 1km raster",
                fetched_at=None,
                is_live=False,
                is_mock=False,
                is_fallback=False,
                limitations=[
                    "Satellite chlorophyll-a / ocean color telemetry requires Copernicus Marine Service or NOAA CoastWatch credentials.",
                    "No API key detected in environment. Metric reported as UNAVAILABLE (not fabricated)."
                ]
            )
        return SourceProvenanceMetadata(
            source_id=self.source_id,
            source_name=self.source_name,
            source_type="LIVE_API",
            coverage="Arabian Sea / Kerala Coast",
            update_frequency="Daily Sentinel-3 OLCI Level-3",
            fetched_at=datetime.now(timezone.utc),
            is_live=True,
            is_mock=False,
            is_fallback=False,
            limitations=[
                "Cloud cover may obstruct optical surface sensors in monsoon conditions."
            ]
        )

    def fetch(self, latitude: float, longitude: float, time_window: str = "current", **kwargs) -> Dict[str, Any]:
        """Fetch ocean color payload or return structured unavailable descriptor."""
        if not self._is_configured:
            logger.info("[EarthObservationAdapter] No credentials configured. Returning UNAVAILABLE state.")
            return {
                "status": "UNAVAILABLE",
                "chlorophyll_mg_m3": None,
                "optical_water_type": None,
                "observation_time": None
            }

        # When credentials are provided, attempt live ERDDAP/Copernicus query
        try:
            target_url = self.noaa_url or "https://coastwatch.pfeg.noaa.gov/erddap/griddap/erdVH3chla1day.json"
            headers = {"Authorization": f"Bearer {self.copernicus_key}"} if self.copernicus_key else {}
            params = {
                "chla[(last)][(0.0)][(" + str(latitude) + ")][(" + str(longitude) + ")]": ""
            }
            with httpx.Client(timeout=4.0) as client:
                res = client.get(target_url, params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    # Parse ERDDAP grid JSON
                    rows = data.get("table", {}).get("rows", [])
                    if rows and len(rows[0]) > 4:
                        val = float(rows[0][4])
                        return {
                            "status": "SUCCESS",
                            "chlorophyll_mg_m3": round(val, 2),
                            "optical_water_type": "Case-1 Oceanic",
                            "observation_time": datetime.now(timezone.utc).isoformat()
                        }
        except Exception as e:
            logger.warning(f"[EarthObservationAdapter] Live query failed: {e}. Returning UNAVAILABLE.")

        return {
            "status": "UNAVAILABLE",
            "chlorophyll_mg_m3": None,
            "optical_water_type": None,
            "observation_time": None
        }

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw observation payload."""
        return {
            "chlorophyll_mg_m3": raw_data.get("chlorophyll_mg_m3"),
            "optical_water_type": raw_data.get("optical_water_type"),
            "status": raw_data.get("status", "UNAVAILABLE"),
            "is_available": self._is_configured and raw_data.get("status") == "SUCCESS"
        }

    def validate(self, normalized_data: Dict[str, Any]) -> bool:
        """Validate ranges (chlorophyll typically 0.01 - 50.0 mg/m3)."""
        chla = normalized_data.get("chlorophyll_mg_m3")
        if chla is not None:
            return 0.0 <= chla <= 100.0
        return True


# Singleton instance
earth_observation_adapter = EarthObservationAdapter()
