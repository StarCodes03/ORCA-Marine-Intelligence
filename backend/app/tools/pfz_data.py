"""ORCA Marine Intelligence - Potential Fishing Zone (PFZ) Data Provider & Adapter

Provides:
- PFZDataProvider: Abstract base interface for PFZ query providers.
- IncoisSnapshotPFZAdapter: Concrete adapter for official INCOIS historical snapshot data.
- Graceful automatic fallback to GisDataAdapter (demo/mock) if the snapshot cannot be loaded.
"""

from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.tools.gis_data import haversine_distance, calculate_bearing, GisDataAdapter, gis_adapter

logger = logging.getLogger("orca.tools.pfz")


class PFZDataProvider(ABC):
    """Abstract interface defining operations for Potential Fishing Zone data sources."""

    @abstractmethod
    def get_all_pfzs_with_distance(
        self, origin_lat: float, origin_lon: float
    ) -> List[Dict[str, Any]]:
        """Return all known PFZ candidates ranked by distance from origin."""
        pass

    @abstractmethod
    def find_nearest_pfz(
        self, origin_lat: float, origin_lon: float
    ) -> Optional[Dict[str, Any]]:
        """Return the closest single PFZ candidate to origin."""
        pass

    @abstractmethod
    def get_provenance(self) -> Dict[str, Any]:
        """Return source provenance metadata dictionary."""
        pass

    @abstractmethod
    def get_geojson_features(self) -> List[Dict[str, Any]]:
        """Return GeoJSON feature representation for map visualization."""
        pass


class IncoisSnapshotPFZAdapter(PFZDataProvider):
    """Official INCOIS Historical PFZ Snapshot Adapter.

    Loads verified historical fishing advisory landing-center records (Sector SEC005, Ernakulam/Kochi)
    from local static snapshot.
    Performs geodesic distance and bearing calculations from user/vessel position to target PFZs.
    Falls back gracefully to demo GIS data if the snapshot file is missing or corrupted.
    """

    DEFAULT_SNAPSHOT_PATH = (
        Path(__file__).resolve().parent.parent / "data" / "pfz" / "incois_kerala_snapshot.json"
    )

    def __init__(
        self,
        snapshot_path: Optional[Path] = None,
        fallback_adapter: Optional[GisDataAdapter] = None
    ):
        self.snapshot_path = Path(snapshot_path) if snapshot_path else self.DEFAULT_SNAPSHOT_PATH
        self.fallback_adapter = fallback_adapter or gis_adapter
        self.is_fallback: bool = False
        self.metadata: Dict[str, Any] = {}
        self.records: List[Dict[str, Any]] = []

        self.load_snapshot()

    def load_snapshot(self) -> None:
        """Load and parse the verified INCOIS PFZ snapshot JSON from disk."""
        if not self.snapshot_path.exists():
            logger.warning(
                f"[IncoisSnapshotPFZAdapter] Snapshot file not found at {self.snapshot_path}. "
                f"Activating mock fallback mode."
            )
            self.is_fallback = True
            return

        try:
            with open(self.snapshot_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or "records" not in data or not isinstance(data["records"], list):
                raise ValueError("Invalid snapshot structure: missing 'records' list.")

            self.metadata = {
                "source": data.get("source", "INCOIS"),
                "source_type": data.get("source_type", "OFFICIAL_SNAPSHOT"),
                "advisory_date": data.get("advisory_date", "2024-04-27T18:30:00Z"),
                "valid_until": data.get("valid_until", "2024-04-28T18:30:00Z"),
                "sector": data.get("sector", "SEC005"),
                "state": data.get("state", "KERALA"),
                "district": data.get("district", "Ernakulam"),
                "description": data.get(
                    "description",
                    "Historical INCOIS PFZ snapshot for Kerala (Sector SEC005), Ernakulam landing centres"
                ),
            }
            self.records = data["records"]
            self.is_fallback = False
            logger.info(
                f"[IncoisSnapshotPFZAdapter] Loaded {len(self.records)} official INCOIS PFZ records "
                f"from {self.snapshot_path} (advisory: {self.metadata['advisory_date']})"
            )

        except Exception as e:
            logger.error(
                f"[IncoisSnapshotPFZAdapter] Error loading snapshot from {self.snapshot_path}: {e}. "
                f"Activating mock fallback mode."
            )
            self.is_fallback = True
            self.records = []
            self.metadata = {}

    def get_all_pfzs_with_distance(
        self, origin_lat: float, origin_lon: float
    ) -> List[Dict[str, Any]]:
        """Calculate distances to all official PFZ targets or return fallback data."""
        if self.is_fallback:
            fallback_items = self.fallback_adapter.get_all_pfzs_with_distance(origin_lat, origin_lon)
            for item in fallback_items:
                item["source_type"] = "MOCK_FALLBACK"
                item["is_mock"] = True
            return fallback_items

        results = []
        for rec in self.records:
            target_lat = rec.get("target_latitude")
            target_lon = rec.get("target_longitude")
            if target_lat is None or target_lon is None:
                continue

            dist = haversine_distance(origin_lat, origin_lon, target_lat, target_lon)
            bearing = calculate_bearing(origin_lat, origin_lon, target_lat, target_lon)

            # Midpoint depth calculation if bounds available
            depth_m = None
            if "depth_from_m" in rec and "depth_to_m" in rec:
                depth_m = round((float(rec["depth_from_m"]) + float(rec["depth_to_m"])) / 2.0, 1)

            landing_centre = rec.get("landing_centre", "Coastal")
            direction = rec.get("direction", "SW")
            dist_f = int(rec.get("distance_from_km", 0))
            dist_t = int(rec.get("distance_to_km", 0))

            item = {
                "pfz_id": rec.get("pfz_id", f"INCOIS-{rec.get('unique_id', 'UNKNOWN')}"),
                "name": f"PFZ target associated with {landing_centre} ({direction} {dist_f}-{dist_t} km)",
                "latitude": target_lat,
                "longitude": target_lon,
                "distance_km": dist,
                "bearing_deg": bearing,
                "depth_m": depth_m,
                "sst_c": None,  # Not provided in landing centres layer; never fabricated
                "chlorophyll_mg_m3": None,  # Not provided in landing centres layer; never fabricated
                "target_species": None,  # Not provided in landing centres layer; never fabricated
                "confidence_score": None,  # Not provided in landing centres layer; never fabricated
                "landing_centre": landing_centre,
                "source": self.metadata.get("source", "INCOIS"),
                "source_type": self.metadata.get("source_type", "OFFICIAL_SNAPSHOT"),
            }
            results.append(item)

        results.sort(key=lambda x: x["distance_km"])
        return results

    def find_nearest_pfz(
        self, origin_lat: float, origin_lon: float
    ) -> Optional[Dict[str, Any]]:
        """Return the nearest PFZ candidate to origin."""
        all_pfzs = self.get_all_pfzs_with_distance(origin_lat, origin_lon)
        return all_pfzs[0] if all_pfzs else None

    def get_provenance(self) -> Dict[str, Any]:
        """Return provenance details for GeospatialData model construction."""
        if self.is_fallback:
            return {
                "source": "DEMO_GIS_DATA",
                "source_type": "MOCK_FALLBACK",
                "advisory_date": None,
                "valid_until": None,
                "is_live": False,
                "is_mock": True,
            }

        return {
            "source": self.metadata.get("source", "INCOIS"),
            "source_type": self.metadata.get("source_type", "OFFICIAL_SNAPSHOT"),
            "advisory_date": self.metadata.get("advisory_date", "2024-04-27T18:30:00Z"),
            "valid_until": self.metadata.get("valid_until", "2024-04-28T18:30:00Z"),
            "is_live": False,
            "is_mock": False,
        }

    def get_geojson_features(self) -> List[Dict[str, Any]]:
        """Return GeoJSON features for map rendering."""
        if self.is_fallback:
            return self.fallback_adapter._pfz_features

        features = []
        for rec in self.records:
            t_lon = rec.get("target_longitude")
            t_lat = rec.get("target_latitude")
            if t_lon is None or t_lat is None:
                continue

            lc = rec.get("landing_centre", "Coastal")
            dist_f = int(rec.get("distance_from_km", 0))
            dist_t = int(rec.get("distance_to_km", 0))
            depth_f = int(rec.get("depth_from_m", 0))
            depth_t = int(rec.get("depth_to_m", 0))

            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [t_lon, t_lat]
                },
                "properties": {
                    "pfz_id": rec.get("pfz_id"),
                    "name": f"PFZ target associated with {lc} ({rec.get('direction', 'SW')} {dist_f}-{dist_t} km)",
                    "landing_centre": lc,
                    "lc_coordinates": [rec.get("lc_longitude"), rec.get("lc_latitude")],
                    "bearing_deg": rec.get("bearing_deg"),
                    "direction": rec.get("direction"),
                    "distance_km": f"{dist_f}-{dist_t} km",
                    "depth_m": f"{depth_f}-{depth_t} m",
                    "target_dms": rec.get("target_dms"),
                    "forecast_date": rec.get("forecast_date"),
                    "validity_date": rec.get("validity_date"),
                    "source": "INCOIS",
                    "source_type": "OFFICIAL_SNAPSHOT",
                    "sst_c": None,
                    "chlorophyll_mg_m3": None,
                    "target_species": None,
                    "confidence_score": None,
                }
            }
            features.append(feat)

        return features


# Singleton instance
incois_snapshot_adapter = IncoisSnapshotPFZAdapter()
