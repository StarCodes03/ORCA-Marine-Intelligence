"""ORCA Marine Intelligence - Deterministic PFZ Candidate Reasoning Engine (M5)

Performs mathematical spatial filtering, candidate ranking, candidate pair comparison,
and direct-route restricted-zone intersection on the historical INCOIS Kerala PFZ snapshot.

Strict Constraints:
- Historical INCOIS landing-centre-associated PFZ Target snapshot — not a live fishing advisory.
- Never call targets "active", "current", or "high-probability".
- Do not infer present-day validity or biological suitability from proximity.
- Zero fabrication of SST, chlorophyll, target species, confidence score, or fish abundance.
- Attribution of conditions to evaluation point / origin.
"""

import logging
from typing import Dict, Any, List, Optional
from shapely.geometry import LineString, Polygon

from app.models.schemas import (
    LocationCoords,
    NearestPFZ,
    PFZComparisonResult
)
from app.tools.gis_data import haversine_distance, calculate_bearing, gis_adapter
from app.tools.pfz_data import incois_snapshot_adapter, PFZDataProvider

logger = logging.getLogger("orca.tools.pfz_candidates")


class PFZCandidateEngine:
    """Deterministic candidate evaluation engine for historical INCOIS PFZ targets."""

    def __init__(self, pfz_provider: Optional[PFZDataProvider] = None, gis_source=None):
        self.pfz_provider = pfz_provider or incois_snapshot_adapter
        self.gis = gis_source or gis_adapter

    def get_candidates_within_radius(
        self, origin: LocationCoords, radius_km: float
    ) -> List[NearestPFZ]:
        """Filter historical PFZ targets where Haversine(origin, target) <= radius_km.
        
        Deterministic mathematical evaluation. Returns candidates sorted by distance ascending.
        Never fabricates biological suitability, fish abundance, or missing telemetry.
        """
        all_raw = self.pfz_provider.get_all_pfzs_with_distance(origin.latitude, origin.longitude)
        filtered = [
            NearestPFZ(**item)
            for item in all_raw
            if float(item["distance_km"]) <= float(radius_km)
        ]
        filtered.sort(key=lambda t: t.distance_km)
        logger.info(
            f"[PFZCandidateEngine] Found {len(filtered)} historical PFZ targets within {radius_km} km of {origin.name}"
        )
        return filtered

    def get_ranked_candidates(
        self, origin: LocationCoords, limit: Optional[int] = None
    ) -> List[NearestPFZ]:
        """Rank historical PFZ targets by deterministic distance from origin.
        
        Preserves authentic snapshot fields and bearing calculations.
        Does not label results as 'active' or 'high probability'.
        """
        all_raw = self.pfz_provider.get_all_pfzs_with_distance(origin.latitude, origin.longitude)
        ranked = [NearestPFZ(**item) for item in all_raw]
        ranked.sort(key=lambda t: t.distance_km)
        if limit is not None and limit > 0:
            return ranked[:limit]
        return ranked

    def check_direct_route_geofence(
        self, origin: LocationCoords, target: NearestPFZ
    ) -> Dict[str, Any]:
        """Determine whether a direct straight-line route from origin to target intersects
        any restricted maritime zone using Shapely geometry.
        
        Does not fabricate route-wide ocean/weather conditions.
        """
        direct_line = LineString([
            (origin.longitude, origin.latitude),
            (target.longitude, target.latitude)
        ])

        restricted_features = self.gis.restricted_zones.get("features", [])
        intersecting_zones: List[str] = []

        for feat in restricted_features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            z_name = props.get("name", "Restricted Maritime Zone")
            if geom.get("type") == "Polygon" and geom.get("coordinates"):
                poly = Polygon(geom["coordinates"][0])
                if direct_line.intersects(poly):
                    intersecting_zones.append(z_name)

        intersects = len(intersecting_zones) > 0
        status = "INTERSECTS_RESTRICTED_ZONE" if intersects else "CLEAR"

        return {
            "intersects": intersects,
            "status": status,
            "intersected_zones": intersecting_zones,
            "target_name": target.name,
            "target_id": target.pfz_id
        }

    def compare_candidates(
        self, origin: LocationCoords, target_a: NearestPFZ, target_b: NearestPFZ
    ) -> PFZComparisonResult:
        """Deterministically compare two historical PFZ targets using available snapshot fields.
        
        Clearly identifies unavailable fields and avoids claiming either is 'better' for fishing.
        """
        dist_a = round(float(target_a.distance_km), 2)
        dist_b = round(float(target_b.distance_km), 2)
        diff_km = round(abs(dist_b - dist_a), 2)

        if dist_a < dist_b:
            closer_target = target_a.name
        elif dist_b < dist_a:
            closer_target = target_b.name
        else:
            closer_target = "EQUAL_DISTANCE"

        bearing_diff = None
        if target_a.bearing_deg is not None and target_b.bearing_deg is not None:
            bearing_diff = round(abs(float(target_b.bearing_deg) - float(target_a.bearing_deg)), 1)

        # Depth comparison
        if target_a.depth_m is not None and target_b.depth_m is not None:
            depth_delta = round(abs(float(target_b.depth_m) - float(target_a.depth_m)), 1)
            depth_comparison = (
                f"Depth comparison: {target_a.landing_centre or target_a.name} is ~{target_a.depth_m}m vs "
                f"{target_b.landing_centre or target_b.name} is ~{target_b.depth_m}m (difference: {depth_delta}m)."
            )
        else:
            depth_comparison = (
                f"Depth data is unavailable or incomplete in historical snapshot "
                f"({target_a.depth_m if target_a.depth_m is not None else 'Unavailable'} vs "
                f"{target_b.depth_m if target_b.depth_m is not None else 'Unavailable'})."
            )

        # Geofence checks
        gf_a = self.check_direct_route_geofence(origin, target_a)
        gf_b = self.check_direct_route_geofence(origin, target_b)

        return PFZComparisonResult(
            target_a=target_a,
            target_b=target_b,
            closer_target=closer_target,
            distance_difference_km=diff_km,
            bearing_difference_deg=bearing_diff,
            depth_comparison=depth_comparison,
            geofence_status_a=gf_a["status"],
            geofence_status_b=gf_b["status"],
            intersected_zones_a=gf_a["intersected_zones"],
            intersected_zones_b=gf_b["intersected_zones"],
            direct_route_intersects_a=gf_a["intersects"],
            direct_route_intersects_b=gf_b["intersects"],
            unavailable_fields=[
                "sst_c (not in snapshot)",
                "chlorophyll_mg_m3 (not in snapshot)",
                "target_species (not in snapshot)",
                "confidence_score (not in snapshot)",
                "fish_abundance (not in snapshot)",
                "real_time_validity (historical snapshot)"
            ],
            disclaimer=(
                "Historical INCOIS landing-centre-associated PFZ target comparison — not a live fishing advisory. "
                "Proximity does not imply biological suitability or present-day fishing potential."
            )
        )


# Singleton instance
pfz_candidate_engine = PFZCandidateEngine()
