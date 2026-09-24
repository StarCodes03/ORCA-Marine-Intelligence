"""ORCA Marine Intelligence - Geospatial Data Adapter & Spatial Engine

Performs deterministic coordinate distance calculations (Haversine),
bearing calculation, and point-in-polygon geofencing for restricted zones.
Loads GeoJSON features for maritime boundaries and spatial reference.
"""

import math
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger("orca.tools.gis")

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance between two points on Earth in kilometers.
    
    Deterministic mathematical implementation.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(EARTH_RADIUS_KM * c, 2)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial compass bearing (0-360 degrees) from point 1 to point 2."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return round(bearing, 1)


def point_in_polygon(lat: float, lon: float, polygon_coords: List[List[float]]) -> bool:
    """Ray-casting algorithm to test if a point (lat, lon) is inside a polygon.
    
    polygon_coords format in GeoJSON: [[lon, lat], [lon, lat], ...]
    """
    inside = False
    n = len(polygon_coords)
    if n < 3:
        return False

    j = n - 1
    for i in range(n):
        # GeoJSON is [longitude, latitude]
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]

        intersect = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i

    return inside


class GisDataAdapter:
    """Geospatial adapter for loading marine spatial layers and spatial calculations."""

    SOURCE_NAME = "DEMO_GIS_DATA"

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            # Locate data/demo relative to backend
            # backend/app/tools/gis_data.py -> up 3 levels to repo root
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.data_dir = repo_root / "data" / "demo"
        else:
            self.data_dir = Path(data_dir)

        self._pfz_features: List[Dict[str, Any]] = []
        self._restricted_features: List[Dict[str, Any]] = []
        self.load_layers()

    def load_layers(self) -> None:
        """Load GeoJSON layers from disk."""
        pfz_path = self.data_dir / "pfz.geojson"
        if pfz_path.exists():
            try:
                with open(pfz_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._pfz_features = data.get("features", [])
                    logger.info(f"Loaded {len(self._pfz_features)} PFZ zones from {pfz_path}")
            except Exception as e:
                logger.error(f"Error loading PFZ GeoJSON: {e}")
        else:
            logger.warning(f"PFZ GeoJSON not found at {pfz_path}")

        restricted_path = self.data_dir / "restricted_zones.geojson"
        if restricted_path.exists():
            try:
                with open(restricted_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._restricted_features = data.get("features", [])
                    logger.info(f"Loaded {len(self._restricted_features)} restricted zones from {restricted_path}")
            except Exception as e:
                logger.error(f"Error loading restricted zones GeoJSON: {e}")
        else:
            logger.warning(f"Restricted zones GeoJSON not found at {restricted_path}")

    def get_all_pfzs_with_distance(
        self, origin_lat: float, origin_lon: float
    ) -> List[Dict[str, Any]]:
        """Calculate distances from origin to all known PFZ clusters."""
        results = []
        for feat in self._pfz_features:
            props = feat.get("properties", {}).copy()
            coords = feat.get("geometry", {}).get("coordinates", [0, 0])
            # GeoJSON coords: [lon, lat]
            pfz_lon, pfz_lat = coords[0], coords[1]

            dist = haversine_distance(origin_lat, origin_lon, pfz_lat, pfz_lon)
            bearing = calculate_bearing(origin_lat, origin_lon, pfz_lat, pfz_lon)

            item = {
                "pfz_id": props.get("pfz_id", "PFZ-UNKNOWN"),
                "name": props.get("name", "Unnamed PFZ"),
                "latitude": pfz_lat,
                "longitude": pfz_lon,
                "distance_km": dist,
                "bearing_deg": bearing,
                "depth_m": props.get("depth_m"),
                "sst_c": props.get("sst_c"),
                "chlorophyll_mg_m3": props.get("chlorophyll_mg_m3"),
                "target_species": props.get("target_species"),
                "confidence_score": props.get("confidence_score", 0.85),
                "source": self.SOURCE_NAME,
            }
            results.append(item)

        results.sort(key=lambda x: x["distance_km"])
        return results

    def find_nearest_pfz(
        self, origin_lat: float, origin_lon: float
    ) -> Optional[Dict[str, Any]]:
        """Return nearest PFZ point."""
        all_pfzs = self.get_all_pfzs_with_distance(origin_lat, origin_lon)
        return all_pfzs[0] if all_pfzs else None

    def check_restricted_zones(
        self, lat: float, lon: float, buffer_km: float = 3.0
    ) -> Dict[str, Any]:
        """Check if coordinates fall inside or within proximity buffer of restricted zones."""
        inside = False
        nearby = False
        nearest_distance = float("inf")
        matched_zone_name = None
        matched_zone_id = None

        for feat in self._restricted_features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])

            # Handle Polygon ring
            if geom.get("type") == "Polygon" and coords:
                ring = coords[0]  # exterior ring: [[lon, lat], ...]
                # Check point in polygon
                if point_in_polygon(lat, lon, ring):
                    inside = True
                    matched_zone_name = props.get("name")
                    matched_zone_id = props.get("zone_id")
                    nearest_distance = 0.0
                    break

                # Check proximity to polygon boundary vertices
                for pt in ring:
                    pt_lon, pt_lat = pt[0], pt[1]
                    d = haversine_distance(lat, lon, pt_lat, pt_lon)
                    if d < nearest_distance:
                        nearest_distance = d
                        matched_zone_name = props.get("name")
                        matched_zone_id = props.get("zone_id")

        if not inside and nearest_distance <= buffer_km:
            nearby = True

        return {
            "inside_restricted_zone": inside,
            "restricted_zone_nearby": nearby or inside,
            "distance_to_nearest_zone_km": round(nearest_distance, 2) if nearest_distance != float("inf") else None,
            "zone_name": matched_zone_name,
            "zone_id": matched_zone_id,
            "source": self.SOURCE_NAME
        }

    @property
    def restricted_zones(self) -> Dict[str, Any]:
        """Return restricted zones FeatureCollection."""
        return {
            "type": "FeatureCollection",
            "features": self._restricted_features
        }

    def get_raw_geojson_layers(self) -> Dict[str, Any]:
        """Return full GeoJSON objects for frontend map rendering."""
        return {
            "pfz": {
                "type": "FeatureCollection",
                "features": self._pfz_features
            },
            "restricted_zones": self.restricted_zones,
            "reference_station": {
                "name": "Kochi Harbor Coastal Reference Station",
                "latitude": 9.9312,
                "longitude": 76.2673
            }
        }


# Singleton instance
gis_adapter = GisDataAdapter()
