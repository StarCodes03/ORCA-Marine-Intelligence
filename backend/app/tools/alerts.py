"""ORCA Marine Intelligence - Deterministic Local Alert Engine

Evaluates real-time navigational and environmental safety conditions against:
1. Proximity to restricted maritime zones (distance <= 2.0 km or inside zone).
2. Vessel seaworthiness threshold limits (wave height, wind speed vs vessel profile).
3. Route deviation / cross-track error (vessel position deviates > 1.0 km from active corridor).

All evaluations are deterministic and reproducible.
"""

import math
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from app.tools.gis_data import haversine_distance, gis_adapter
from app.config.risk_thresholds import VESSEL_PROFILES, get_vessel_profile
from app.services.storage import storage_repo

logger = logging.getLogger("orca.tools.alerts")

# Deterministic safety alert thresholds
RESTRICTED_ZONE_BUFFER_KM = 2.0
ROUTE_DEVIATION_MAX_KM = 1.0


def point_to_segment_distance_km(
    lat_p: float, lon_p: float,
    lat_a: float, lon_a: float,
    lat_b: float, lon_b: float
) -> float:
    """Calculate perpendicular/minimum distance from point P to line segment AB in km."""
    mid_lat_rad = math.radians((lat_a + lat_b) / 2.0)
    cos_lat = math.cos(mid_lat_rad)

    # Coordinates in km relative to A
    ax, ay = 0.0, 0.0
    bx = (lon_b - lon_a) * 111.320 * cos_lat
    by = (lat_b - lat_a) * 110.574
    px = (lon_p - lon_a) * 111.320 * cos_lat
    py = (lat_p - lat_a) * 110.574

    dx = bx - ax
    dy = by - ay
    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq < 1e-9:
        return haversine_distance(lat_p, lon_p, lat_a, lon_a)

    t = (px * dx + py * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))

    qx = ax + t * dx
    qy = ay + t * dy

    dist = math.sqrt((px - qx) ** 2 + (py - qy) ** 2)
    return round(dist, 3)


def point_to_polyline_distance_km(
    lat: float, lon: float, waypoints: List[Tuple[float, float]]
) -> float:
    """Calculate minimum distance in km from point to polyline coordinates [(lat, lon), ...]."""
    if not waypoints:
        return 0.0
    if len(waypoints) == 1:
        return haversine_distance(lat, lon, waypoints[0][0], waypoints[0][1])

    min_dist = float("inf")
    for i in range(len(waypoints) - 1):
        a_lat, a_lon = waypoints[i]
        b_lat, b_lon = waypoints[i + 1]
        d = point_to_segment_distance_km(lat, lon, a_lat, a_lon, b_lat, b_lon)
        if d < min_dist:
            min_dist = d

    return round(min_dist, 3)


class AlertEngine:
    """Deterministic local maritime alert generation engine."""

    def __init__(self, storage=None):
        self.storage = storage or storage_repo

    def evaluate_proximity_alerts(
        self,
        lat: float,
        lon: float,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Check proximity or inside status for restricted zones (buffer: 2.0 km)."""
        alerts = []
        zone_check = gis_adapter.check_restricted_zones(lat, lon, buffer_km=RESTRICTED_ZONE_BUFFER_KM)

        if zone_check.get("inside_restricted_zone"):
            zone_name = zone_check.get("zone_name", "Restricted Area")
            zone_id = zone_check.get("zone_id", "RZ-UNKNOWN")
            alerts.append({
                "id": f"alert-prox-inside-{uuid.uuid4().hex[:8]}",
                "conversation_id": conversation_id,
                "severity": "CRITICAL",
                "title": "Restricted Maritime Zone Violation",
                "message": f"Vessel is INSIDE restricted zone '{zone_name}' ({zone_id}). Immediate exit required.",
                "zone_id": zone_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            })
        elif zone_check.get("restricted_zone_nearby"):
            dist = zone_check.get("distance_to_nearest_zone_km", RESTRICTED_ZONE_BUFFER_KM)
            zone_name = zone_check.get("zone_name", "Restricted Area")
            zone_id = zone_check.get("zone_id", "RZ-UNKNOWN")
            alerts.append({
                "id": f"alert-prox-near-{uuid.uuid4().hex[:8]}",
                "conversation_id": conversation_id,
                "severity": "WARNING",
                "title": "Restricted Maritime Zone Proximity Alert",
                "message": (
                    f"Vessel is {dist:.2f} km from restricted boundary '{zone_name}' ({zone_id}). "
                    f"Maintain minimum safety clearance of {RESTRICTED_ZONE_BUFFER_KM} km."
                ),
                "zone_id": zone_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            })

        return alerts

    def evaluate_threshold_alerts(
        self,
        vessel_type: Optional[str],
        wave_height_m: Optional[float] = None,
        wind_speed_kmh: Optional[float] = None,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate environmental wave and wind parameters against vessel limits."""
        alerts = []
        if not vessel_type:
            return alerts

        # Try storage repository profile first, then fallback to built-in dict
        profile = self.storage.get_vessel_profile(vessel_type) if self.storage else None
        if not profile:
            profile = get_vessel_profile(vessel_type)
        if not profile:
            return alerts

        name = profile.get("name", vessel_type)
        wave_safe = profile.get("wave_max_safe", 1.5)
        wave_mod = profile.get("wave_max_moderate", 2.2)
        wind_safe = profile.get("wind_max_safe", 25.0)
        wind_mod = profile.get("wind_max_moderate", 35.0)

        # Wave height check
        if wave_height_m is not None:
            if wave_height_m > wave_mod:
                alerts.append({
                    "id": f"alert-thresh-wave-crit-{uuid.uuid4().hex[:8]}",
                    "conversation_id": conversation_id,
                    "severity": "CRITICAL",
                    "title": "Severe Wave Limit Exceeded",
                    "message": (
                        f"Significant wave height of {wave_height_m:.1f} m exceeds moderate/maximum operating limit "
                        f"({wave_mod:.1f} m) for {name}."
                    ),
                    "zone_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                })
            elif wave_height_m > wave_safe:
                alerts.append({
                    "id": f"alert-thresh-wave-warn-{uuid.uuid4().hex[:8]}",
                    "conversation_id": conversation_id,
                    "severity": "WARNING",
                    "title": "Moderate Wave Advisory",
                    "message": (
                        f"Significant wave height of {wave_height_m:.1f} m exceeds safe baseline limit "
                        f"({wave_safe:.1f} m) for {name}. Caution advised."
                    ),
                    "zone_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                })

        # Wind speed check
        if wind_speed_kmh is not None:
            if wind_speed_kmh > wind_mod:
                alerts.append({
                    "id": f"alert-thresh-wind-crit-{uuid.uuid4().hex[:8]}",
                    "conversation_id": conversation_id,
                    "severity": "CRITICAL",
                    "title": "Severe Wind Limit Exceeded",
                    "message": (
                        f"Wind speed of {wind_speed_kmh:.1f} km/h exceeds moderate/maximum operating limit "
                        f"({wind_mod:.1f} km/h) for {name}."
                    ),
                    "zone_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                })
            elif wind_speed_kmh > wind_safe:
                alerts.append({
                    "id": f"alert-thresh-wind-warn-{uuid.uuid4().hex[:8]}",
                    "conversation_id": conversation_id,
                    "severity": "WARNING",
                    "title": "Elevated Wind Advisory",
                    "message": (
                        f"Wind speed of {wind_speed_kmh:.1f} km/h exceeds safe craft limit "
                        f"({wind_safe:.1f} km/h) for {name}."
                    ),
                    "zone_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                })

        return alerts

    def evaluate_route_deviation_alerts(
        self,
        vessel_lat: float,
        vessel_lon: float,
        route_waypoints: List[Tuple[float, float]],
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate cross-track error against active route corridor (max: 1.0 km)."""
        alerts = []
        if not route_waypoints or len(route_waypoints) < 2:
            return alerts

        deviation_km = point_to_polyline_distance_km(vessel_lat, vessel_lon, route_waypoints)
        if deviation_km > ROUTE_DEVIATION_MAX_KM:
            alerts.append({
                "id": f"alert-route-dev-{uuid.uuid4().hex[:8]}",
                "conversation_id": conversation_id,
                "severity": "WARNING",
                "title": "Route Corridor Deviation Detected",
                "message": (
                    f"Vessel position ({vessel_lat:.4f}, {vessel_lon:.4f}) deviates {deviation_km:.2f} km "
                    f"from the planned safe transit corridor (cross-track limit: {ROUTE_DEVIATION_MAX_KM} km)."
                ),
                "zone_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            })

        return alerts

    def evaluate_all(
        self,
        vessel_lat: float,
        vessel_lon: float,
        vessel_type: Optional[str] = None,
        wave_height_m: Optional[float] = None,
        wind_speed_kmh: Optional[float] = None,
        route_waypoints: Optional[List[Tuple[float, float]]] = None,
        conversation_id: Optional[str] = None,
        persist: bool = True
    ) -> List[Dict[str, Any]]:
        """Evaluate all alert categories and optionally persist to storage."""
        alerts = []
        alerts.extend(self.evaluate_proximity_alerts(vessel_lat, vessel_lon, conversation_id))
        alerts.extend(self.evaluate_threshold_alerts(vessel_type, wave_height_m, wind_speed_kmh, conversation_id))
        if route_waypoints:
            alerts.extend(self.evaluate_route_deviation_alerts(vessel_lat, vessel_lon, route_waypoints, conversation_id))

        if persist and self.storage:
            for alert in alerts:
                self.storage.save_alert(alert)

        return alerts


# Singleton instance
alert_engine = AlertEngine()
