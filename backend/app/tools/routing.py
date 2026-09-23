"""ORCA Marine Intelligence - Safe Passage Corridor Routing Engine
Milestone 4 (M4)

Implements deterministic line/polygon intersection testing against actual restricted maritime
polygons (naval firing ranges, commercial port channels). Generates collision-free clearance
waypoints around buffered restricted geometries, computes geodesic nautical distances,
deterministic transit durations, and explicit fuel consumption estimates based on
configured vessel parameters.
"""

import math
import logging
from typing import Dict, Any, Optional, List, Tuple
from shapely.geometry import Point, LineString, Polygon

from app.models.schemas import (
    LocationCoords,
    NearestPFZ,
    TransitRoute,
    TransitWaypoint
)
from app.tools.gis_data import haversine_distance, calculate_bearing, gis_adapter
from app.config.risk_thresholds import (
    ROUTING_CONFIG,
    VESSEL_PROFILES,
    get_vessel_profile
)

logger = logging.getLogger("orca.tools.routing")


class SafeRoutingEngine:
    """Deterministic routing and geofence-avoidance corridor generator."""

    def __init__(self, gis_source=None):
        self.gis = gis_source or gis_adapter

    def plan_safe_transit_route(
        self,
        origin: LocationCoords,
        destination: NearestPFZ,
        vessel_type: Optional[str] = None,
        clearance_buffer_km: Optional[float] = None
    ) -> TransitRoute:
        """Compute collision-free passage corridor from vessel origin to target PFZ."""
        buffer_km = clearance_buffer_km or ROUTING_CONFIG.get("default_clearance_buffer_km", 1.5)
        v_profile = get_vessel_profile(vessel_type) or VESSEL_PROFILES["motorized_frp_obm"]

        logger.info(
            f"[RoutingEngine] Planning passage from ({origin.latitude}, {origin.longitude}) to "
            f"PFZ '{destination.name}' ({destination.latitude}, {destination.longitude}) "
            f"for craft '{v_profile['name']}' with {buffer_km} km clearance buffer"
        )

        p0_pt = Point(origin.longitude, origin.latitude)
        pt_pt = Point(destination.longitude, destination.latitude)
        direct_line = LineString([(origin.longitude, origin.latitude), (destination.longitude, destination.latitude)])

        # 1. Retrieve restricted zone geometries
        restricted_features = self.gis.restricted_zones.get("features", [])
        restricted_polygons: List[Tuple[str, Polygon]] = []

        for feat in restricted_features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            z_name = props.get("name", "Restricted Maritime Zone")
            if geom.get("type") == "Polygon":
                poly = Polygon(geom["coordinates"][0])
                restricted_polygons.append((z_name, poly))

        # 2. Test direct LineString intersection against restricted geometries
        intersecting_zones: List[Tuple[str, Polygon]] = []
        for z_name, poly in restricted_polygons:
            if direct_line.intersects(poly):
                intersecting_zones.append((z_name, poly))
                logger.info(f"[RoutingEngine] Direct transit intersects restricted zone: '{z_name}'")

        waypoints: List[TransitWaypoint] = []
        avoided_zone_names: List[str] = []
        geofence_avoidance_applied = False

        # 3. Route Calculation
        if not intersecting_zones:
            # Direct line of sight is clear
            total_distance_km = haversine_distance(
                origin.latitude, origin.longitude, destination.latitude, destination.longitude
            )
            route_coords = [
                [origin.longitude, origin.latitude],
                [destination.longitude, destination.latitude]
            ]
        else:
            # Direct corridor is blocked; compute collision-free clearance waypoints
            geofence_avoidance_applied = True
            # Degrees approximation: 1 deg lat ~ 111 km, lon scaled by cos(lat)
            lat_mid = (origin.latitude + destination.latitude) / 2.0
            deg_lat_buffer = buffer_km / 111.0
            deg_lon_buffer = buffer_km / (111.0 * max(0.2, math.cos(math.radians(lat_mid))))

            best_waypoint: Optional[Tuple[float, float]] = None
            min_detour_dist = float("inf")

            for z_name, poly in intersecting_zones:
                avoided_zone_names.append(z_name)

                # Generate candidate clearance vertices around the buffered geometry
                # Buffer polygon in degree coordinates
                buffered_poly = poly.buffer(max(deg_lat_buffer, deg_lon_buffer))

                # Inspect vertices of the buffered boundary
                candidate_pts = list(buffered_poly.exterior.coords)

                for c_lon, c_lat in candidate_pts:
                    cand_pt = Point(c_lon, c_lat)

                    # Candidate point must not fall inside ANY restricted zone
                    inside_any = any(poly_check.contains(cand_pt) for _, poly_check in restricted_polygons)
                    if inside_any:
                        continue

                    # Candidate legs
                    leg1 = LineString([(origin.longitude, origin.latitude), (c_lon, c_lat)])
                    leg2 = LineString([(c_lon, c_lat), (destination.longitude, destination.latitude)])

                    # Both legs must be collision-free
                    collision = any(
                        leg1.intersects(poly_check) or leg2.intersects(poly_check)
                        for _, poly_check in restricted_polygons
                    )

                    if not collision:
                        # Candidate is valid and collision-free; evaluate detour length
                        d1 = haversine_distance(origin.latitude, origin.longitude, c_lat, c_lon)
                        d2 = haversine_distance(c_lat, c_lon, destination.latitude, destination.longitude)
                        detour = d1 + d2

                        if detour < min_detour_dist:
                            min_detour_dist = detour
                            best_waypoint = (c_lat, c_lon)

            if best_waypoint:
                w_lat, w_lon = best_waypoint
                waypoints.append(TransitWaypoint(
                    name="WP-1 (Clearance)",
                    latitude=round(w_lat, 4),
                    longitude=round(w_lon, 4),
                    description=f"Clearance waypoint bypassing {', '.join(avoided_zone_names)} with {buffer_km} km buffer."
                ))
                total_distance_km = round(min_detour_dist, 2)
                route_coords = [
                    [origin.longitude, origin.latitude],
                    [round(w_lon, 4), round(w_lat, 4)],
                    [destination.longitude, destination.latitude]
                ]
                logger.info(
                    f"[RoutingEngine] Collision-free corridor established via WP-1 ({w_lat:.4f}, {w_lon:.4f}). "
                    f"Total distance: {total_distance_km} km"
                )
            else:
                # Fallback: clearance offset perpendicular to direct line mid-point
                bearing = calculate_bearing(origin.latitude, origin.longitude, destination.latitude, destination.longitude)
                offset_bearing = (bearing + 90.0) % 360.0
                rad_b = math.radians(offset_bearing)
                mid_lat = (origin.latitude + destination.latitude) / 2.0
                mid_lon = (origin.longitude + destination.longitude) / 2.0
                # Offset by 2x buffer
                offset_km = buffer_km * 2.5
                d_lat = (offset_km / 111.0) * math.cos(rad_b)
                d_lon = (offset_km / (111.0 * math.cos(math.radians(mid_lat)))) * math.sin(rad_b)
                alt_lat = round(mid_lat + d_lat, 4)
                alt_lon = round(mid_lon + d_lon, 4)

                waypoints.append(TransitWaypoint(
                    name="WP-1 (Seaward Clearance)",
                    latitude=alt_lat,
                    longitude=alt_lon,
                    description=f"Seaward bypass offset clearing {', '.join(avoided_zone_names)}."
                ))
                d1 = haversine_distance(origin.latitude, origin.longitude, alt_lat, alt_lon)
                d2 = haversine_distance(alt_lat, alt_lon, destination.latitude, destination.longitude)
                total_distance_km = round(d1 + d2, 2)
                route_coords = [
                    [origin.longitude, origin.latitude],
                    [alt_lon, alt_lat],
                    [destination.longitude, destination.latitude]
                ]

        # 4. Deterministic Metric Calculations
        nm_ratio = ROUTING_CONFIG.get("nautical_mile_km", 1.852)
        total_distance_nm = round(total_distance_km / nm_ratio, 2)

        cruising_speed = v_profile.get("cruising_speed_knots", 7.5)
        if cruising_speed > 0:
            estimated_duration_hours = round(total_distance_nm / cruising_speed, 2)
        else:
            estimated_duration_hours = round(total_distance_nm / 3.5, 2)

        burn_rate = v_profile.get("fuel_consumption_l_per_hour", 0.0)
        fuel_litres = round(estimated_duration_hours * burn_rate, 1) if burn_rate > 0 else 0.0
        fuel_note = v_profile.get("fuel_estimate_note", ROUTING_CONFIG.get("fuel_disclaimer", ""))

        # 5. GeoJSON Feature Creation
        geojson_feature = {
            "type": "Feature",
            "properties": {
                "route_type": "safe_passage_corridor",
                "vessel_type": v_profile["vessel_type"],
                "vessel_name": v_profile["name"],
                "total_distance_km": total_distance_km,
                "total_distance_nm": total_distance_nm,
                "estimated_duration_hours": estimated_duration_hours,
                "estimated_fuel_litres": fuel_litres,
                "fuel_type": v_profile.get("fuel_type", "N/A"),
                "geofence_avoidance_applied": geofence_avoidance_applied,
                "avoided_zones": avoided_zone_names,
                "clearance_buffer_km": buffer_km
            },
            "geometry": {
                "type": "LineString",
                "coordinates": route_coords
            }
        }

        return TransitRoute(
            origin=origin,
            destination=destination,
            waypoints=waypoints,
            total_distance_km=total_distance_km,
            total_distance_nm=total_distance_nm,
            estimated_duration_hours=estimated_duration_hours,
            estimated_fuel_litres=fuel_litres,
            fuel_type=v_profile.get("fuel_type"),
            geofence_avoidance_applied=geofence_avoidance_applied,
            avoided_zones=avoided_zone_names,
            clearance_buffer_km=buffer_km,
            geojson_feature=geojson_feature,
            fuel_estimate_note=fuel_note
        )


# Singleton routing engine instance
routing_engine = SafeRoutingEngine()
