"""ORCA Marine Intelligence - Geospatial Agent

Performs deterministic spatial calculations:
- Great Circle geodesic distance to Potential Fishing Zones (PFZs)
- Nearest PFZ identification with bearing and biological/landing-centre properties
- Geofence intersection with restricted naval and hazardous port zones
Structured input/output with clear source provenance (INCOIS OFFICIAL_SNAPSHOT or MOCK_FALLBACK).
"""

import logging
from typing import Dict, Any, Optional
from app.models.schemas import (
    GeospatialData,
    LocationCoords,
    NearestPFZ,
    RestrictedZoneCheck
)
from app.tools.gis_data import gis_adapter
from app.tools.pfz_data import PFZDataProvider, incois_snapshot_adapter

logger = logging.getLogger("orca.agents.geospatial")


class GeospatialAgent:
    """Geospatial agent executing deterministic spatial operations."""

    AGENT_NAME = "GeospatialAgent"

    def __init__(self, pfz_provider: Optional[PFZDataProvider] = None):
        self.pfz_provider = pfz_provider or incois_snapshot_adapter

    def execute(
        self,
        location: LocationCoords
    ) -> GeospatialData:
        """Run GIS calculations for given location."""
        logger.info(
            f"[{self.AGENT_NAME}] Performing spatial analysis for ({location.latitude}, {location.longitude})"
        )

        # 1. Fetch and rank all PFZs by distance from the PFZ provider
        all_pfzs_raw = self.pfz_provider.get_all_pfzs_with_distance(
            location.latitude, location.longitude
        )
        all_pfz_models = [NearestPFZ(**item) for item in all_pfzs_raw]

        nearest_pfz_model = all_pfz_models[0] if all_pfz_models else None

        # 2. Check proximity and point-in-polygon for restricted maritime zones
        rz_check_raw = gis_adapter.check_restricted_zones(
            location.latitude, location.longitude, buffer_km=3.0
        )
        rz_model = RestrictedZoneCheck(
            restricted_zone_nearby=rz_check_raw["restricted_zone_nearby"],
            inside_restricted_zone=rz_check_raw["inside_restricted_zone"],
            zone_name=rz_check_raw.get("zone_name"),
            zone_id=rz_check_raw.get("zone_id"),
            distance_to_nearest_zone_km=rz_check_raw.get("distance_to_nearest_zone_km")
        )

        # 3. Retrieve source provenance metadata from PFZ provider
        prov = self.pfz_provider.get_provenance()

        geo_data = GeospatialData(
            source=prov.get("source", "INCOIS"),
            source_type=prov.get("source_type", "OFFICIAL_SNAPSHOT"),
            advisory_date=prov.get("advisory_date"),
            valid_until=prov.get("valid_until"),
            is_live=prov.get("is_live", False),
            is_mock=prov.get("is_mock", False),
            user_location=location,
            nearest_pfz=nearest_pfz_model,
            all_pfzs=all_pfz_models,
            restricted_zone_check=rz_model
        )

        if nearest_pfz_model:
            logger.info(
                f"[{self.AGENT_NAME}] Nearest PFZ: {nearest_pfz_model.name} at {nearest_pfz_model.distance_km} km "
                f"(bearing {nearest_pfz_model.bearing_deg}°) [source: {geo_data.source_type}]"
            )
        logger.info(
            f"[{self.AGENT_NAME}] Restricted zone check: inside={rz_model.inside_restricted_zone}, "
            f"nearby={rz_model.restricted_zone_nearby}"
        )

        return geo_data

    def plan_route(
        self,
        origin: LocationCoords,
        destination: NearestPFZ,
        vessel_type: Optional[str] = None,
        clearance_buffer_km: Optional[float] = None
    ) -> Any:
        """Compute safe passage route avoiding restricted maritime zones."""
        from app.tools.routing import routing_engine
        return routing_engine.plan_safe_transit_route(
            origin=origin,
            destination=destination,
            vessel_type=vessel_type,
            clearance_buffer_km=clearance_buffer_km
        )

