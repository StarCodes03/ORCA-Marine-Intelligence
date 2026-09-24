"""ORCA Marine Intelligence - Geospatial Agent

Performs deterministic spatial calculations:
- Great Circle geodesic distance to Potential Fishing Zones (PFZs)
- Nearest PFZ identification with bearing and biological/landing-centre properties
- Geofence intersection with restricted naval and hazardous port zones
Structured input/output with clear source provenance (INCOIS OFFICIAL_SNAPSHOT or MOCK_FALLBACK).
"""

import logging
from typing import Dict, Any, Optional, List
from app.models.schemas import (
    GeospatialData,
    LocationCoords,
    NearestPFZ,
    RestrictedZoneCheck,
    PFZComparisonResult
)
from app.tools.gis_data import gis_adapter
from app.tools.pfz_data import PFZDataProvider, incois_snapshot_adapter
from app.tools.pfz_candidates import PFZCandidateEngine, pfz_candidate_engine

logger = logging.getLogger("orca.agents.geospatial")


class GeospatialAgent:
    """Geospatial agent executing deterministic spatial operations."""

    AGENT_NAME = "GeospatialAgent"

    def __init__(
        self,
        pfz_provider: Optional[PFZDataProvider] = None,
        candidate_engine: Optional[PFZCandidateEngine] = None
    ):
        self.pfz_provider = pfz_provider or incois_snapshot_adapter
        self.candidate_engine = candidate_engine or pfz_candidate_engine

    def execute(
        self,
        location: LocationCoords,
        radius_km: Optional[float] = None,
        intent: Optional[str] = None,
        candidate_context: Optional[List[NearestPFZ]] = None,
        selected_target: Optional[NearestPFZ] = None,
        compare_targets: Optional[List[int]] = None
    ) -> GeospatialData:
        """Run GIS calculations and deterministic PFZ candidate operations for given location."""
        logger.info(
            f"[{self.AGENT_NAME}] Performing spatial analysis for ({location.latitude}, {location.longitude})"
        )

        # 1. Fetch and rank all PFZs by distance from the PFZ provider
        all_pfzs_raw = self.pfz_provider.get_all_pfzs_with_distance(
            location.latitude, location.longitude
        )
        all_pfz_models = [NearestPFZ(**item) for item in all_pfzs_raw]

        nearest_pfz_model = all_pfz_models[0] if all_pfz_models else None

        # 2. Check proximity and point-in-polygon for restricted maritime zones at user position
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

        # 3. Deterministic PFZ Candidate Operations (M5 Step 3)
        candidate_pfzs: List[NearestPFZ] = []
        pfz_comp_result: Optional[PFZComparisonResult] = None
        direct_route_status: Optional[str] = None
        direct_route_zones: List[str] = []

        if intent == "pfz_radius_filter" or radius_km is not None:
            effective_radius = radius_km if radius_km is not None else 30.0
            candidate_pfzs = self.candidate_engine.get_candidates_within_radius(location, effective_radius)
        elif candidate_context:
            candidate_pfzs = list(candidate_context)

        if intent == "pfz_comparison":
            pool = candidate_context if (candidate_context and len(candidate_context) >= 2) else (candidate_pfzs if len(candidate_pfzs) >= 2 else all_pfz_models)
            idx_a = compare_targets[0] if (compare_targets and len(compare_targets) > 0) else 0
            idx_b = compare_targets[1] if (compare_targets and len(compare_targets) > 1) else 1
            if len(pool) > max(idx_a, idx_b):
                target_a = pool[idx_a]
                target_b = pool[idx_b]
                pfz_comp_result = self.candidate_engine.compare_candidates(location, target_a, target_b)
                logger.info(f"[{self.AGENT_NAME}] Compared candidates: {target_a.name} vs {target_b.name}")

        if intent == "pfz_geofence_check":
            target_to_eval = selected_target or (candidate_context[0] if candidate_context else (candidate_pfzs[0] if candidate_pfzs else nearest_pfz_model))
            if target_to_eval:
                gf_res = self.candidate_engine.check_direct_route_geofence(location, target_to_eval)
                direct_route_status = gf_res["status"]
                direct_route_zones = gf_res["intersected_zones"]
                logger.info(f"[{self.AGENT_NAME}] Direct route geofence to {target_to_eval.name}: {direct_route_status}")

        # 4. Retrieve source provenance metadata from PFZ provider
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
            candidate_pfzs=candidate_pfzs,
            pfz_comparison=pfz_comp_result,
            direct_route_geofence_status=direct_route_status,
            direct_route_intersected_zones=direct_route_zones,
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

