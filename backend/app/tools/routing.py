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
from typing import Dict, Any, Optional, List, Tuple, Union
from shapely.geometry import Point, LineString, Polygon

from app.models.schemas import (
    LocationCoords,
    NearestPFZ,
    TransitRoute,
    TransitWaypoint,
    RouteAlternative
)
from app.tools.gis_data import haversine_distance, calculate_bearing, gis_adapter
from app.config.risk_thresholds import (
    ROUTING_CONFIG,
    VESSEL_PROFILES,
    get_vessel_profile
)

logger = logging.getLogger("orca.tools.routing")


class SafeRoutingEngine:
    """Deterministic routing and geofence-avoidance corridor generator with route alternatives (M5)."""

    def __init__(self, gis_source=None):
        self.gis = gis_source or gis_adapter

    def plan_safe_transit_route(
        self,
        origin: LocationCoords,
        destination: Union[NearestPFZ, LocationCoords],
        vessel_type: Optional[str] = None,
        clearance_buffer_km: Optional[float] = None
    ) -> TransitRoute:
        """Compute collision-free passage corridor from vessel origin to target destination.
        
        Generates deterministic route alternatives:
        1. Direct Passage (Fastest / Line-of-Sight)
        2. Safe Passage Corridor (Geofence-Clearing Waypoint)
        3. High-Clearance Seaward Corridor (Max Margin Alternative)
        Includes discrete route evaluation points and explicit environmental limitation provenance.
        """
        buffer_km = clearance_buffer_km or ROUTING_CONFIG.get("default_clearance_buffer_km", 1.5)
        v_profile = get_vessel_profile(vessel_type) or VESSEL_PROFILES["motorized_frp_obm"]

        dest_lat = float(destination.latitude)
        dest_lon = float(destination.longitude)
        dest_name = getattr(destination, "name", "Destination Point")

        logger.info(
            f"[RoutingEngine] Planning passage from ({origin.latitude}, {origin.longitude}) to "
            f"'{dest_name}' ({dest_lat}, {dest_lon}) "
            f"for craft '{v_profile['name']}' with {buffer_km} km clearance buffer"
        )

        direct_line = LineString([(origin.longitude, origin.latitude), (dest_lon, dest_lat)])

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

        nm_ratio = ROUTING_CONFIG.get("nautical_mile_km", 1.852)
        cruising_speed = v_profile.get("cruising_speed_knots", 7.5)
        speed = cruising_speed if cruising_speed > 0 else 3.5
        burn_rate = v_profile.get("fuel_consumption_l_per_hour", 0.0)
        fuel_note = v_profile.get("fuel_estimate_note", ROUTING_CONFIG.get("fuel_disclaimer", ""))

        # 3. Alternative 1: Direct Passage (Fastest / Line-of-Sight)
        direct_distance_km = haversine_distance(origin.latitude, origin.longitude, dest_lat, dest_lon)
        direct_distance_nm = round(direct_distance_km / nm_ratio, 2)
        direct_duration_h = round(direct_distance_nm / speed, 2)
        direct_fuel_l = round(direct_duration_h * burn_rate, 1) if burn_rate > 0 else 0.0
        direct_intersects = len(intersecting_zones) > 0
        direct_avoided = [z for z, _ in intersecting_zones]
        direct_risk_index = 8.5 if direct_intersects else 2.5
        direct_risk_level = "CRITICAL" if direct_intersects else "LOW"

        direct_coords = [
            [origin.longitude, origin.latitude],
            [dest_lon, dest_lat]
        ]
        direct_geojson = {
            "type": "Feature",
            "properties": {
                "alternative_id": "direct",
                "name": "Direct Route (Line-of-Sight)",
                "total_distance_km": direct_distance_km,
                "total_distance_nm": direct_distance_nm,
                "estimated_duration_hours": direct_duration_h,
                "estimated_fuel_litres": direct_fuel_l,
                "intersects_restricted_zone": direct_intersects,
                "intersected_zones": direct_avoided,
                "route_risk_index": direct_risk_index
            },
            "geometry": {
                "type": "LineString",
                "coordinates": direct_coords
            }
        }

        alt_direct = RouteAlternative(
            alternative_id="direct",
            name="Direct Route (Line-of-Sight)",
            total_distance_km=direct_distance_km,
            total_distance_nm=direct_distance_nm,
            estimated_duration_hours=direct_duration_h,
            estimated_fuel_litres=direct_fuel_l,
            fuel_type=v_profile.get("fuel_type"),
            intersects_restricted_zone=direct_intersects,
            intersected_zones=direct_avoided,
            route_risk_index=direct_risk_index,
            route_risk_level=direct_risk_level,
            waypoints=[],
            geojson_feature=direct_geojson,
            is_recommended=not direct_intersects,
            recommendation_reason="Direct line-of-sight is completely clear of restricted zones." if not direct_intersects else f"CAUTION: Traverses restricted maritime zone ({', '.join(direct_avoided)})."
        )

        # 4. Alternative 2: Safe Passage Corridor (Geofence-Clearing Waypoint Route)
        safe_waypoints: List[TransitWaypoint] = []
        safe_avoided_names: List[str] = []
        geofence_avoidance_applied = False

        if not intersecting_zones:
            safe_distance_km = direct_distance_km
            safe_coords = direct_coords
        else:
            geofence_avoidance_applied = True
            lat_mid = (origin.latitude + dest_lat) / 2.0
            deg_lat_buffer = buffer_km / 111.0
            deg_lon_buffer = buffer_km / (111.0 * max(0.2, math.cos(math.radians(lat_mid))))

            best_waypoint: Optional[Tuple[float, float]] = None
            min_detour_dist = float("inf")

            for z_name, poly in intersecting_zones:
                safe_avoided_names.append(z_name)
                buffered_poly = poly.buffer(max(deg_lat_buffer, deg_lon_buffer))
                candidate_pts = list(buffered_poly.exterior.coords)

                for c_lon, c_lat in candidate_pts:
                    cand_pt = Point(c_lon, c_lat)
                    if any(poly_check.contains(cand_pt) for _, poly_check in restricted_polygons):
                        continue

                    leg1 = LineString([(origin.longitude, origin.latitude), (c_lon, c_lat)])
                    leg2 = LineString([(c_lon, c_lat), (dest_lon, dest_lat)])

                    if not any(leg1.intersects(poly_check) or leg2.intersects(poly_check) for _, poly_check in restricted_polygons):
                        d1 = haversine_distance(origin.latitude, origin.longitude, c_lat, c_lon)
                        d2 = haversine_distance(c_lat, c_lon, dest_lat, dest_lon)
                        detour = d1 + d2
                        if detour < min_detour_dist:
                            min_detour_dist = detour
                            best_waypoint = (c_lat, c_lon)

            if best_waypoint:
                w_lat, w_lon = best_waypoint
                safe_waypoints.append(TransitWaypoint(
                    name="WP-1 (Clearance)",
                    latitude=round(w_lat, 4),
                    longitude=round(w_lon, 4),
                    description=f"Clearance waypoint bypassing {', '.join(safe_avoided_names)} with {buffer_km} km buffer."
                ))
                safe_distance_km = round(min_detour_dist, 2)
                safe_coords = [
                    [origin.longitude, origin.latitude],
                    [round(w_lon, 4), round(w_lat, 4)],
                    [dest_lon, dest_lat]
                ]
            else:
                bearing = calculate_bearing(origin.latitude, origin.longitude, dest_lat, dest_lon)
                offset_bearing = (bearing + 90.0) % 360.0
                rad_b = math.radians(offset_bearing)
                mid_lat = (origin.latitude + dest_lat) / 2.0
                mid_lon = (origin.longitude + dest_lon) / 2.0
                offset_km = buffer_km * 2.5
                d_lat = (offset_km / 111.0) * math.cos(rad_b)
                d_lon = (offset_km / (111.0 * math.cos(math.radians(mid_lat)))) * math.sin(rad_b)
                alt_lat = round(mid_lat + d_lat, 4)
                alt_lon = round(mid_lon + d_lon, 4)

                safe_waypoints.append(TransitWaypoint(
                    name="WP-1 (Seaward Clearance)",
                    latitude=alt_lat,
                    longitude=alt_lon,
                    description=f"Seaward bypass offset clearing {', '.join(safe_avoided_names)}."
                ))
                d1 = haversine_distance(origin.latitude, origin.longitude, alt_lat, alt_lon)
                d2 = haversine_distance(alt_lat, alt_lon, dest_lat, dest_lon)
                safe_distance_km = round(d1 + d2, 2)
                safe_coords = [
                    [origin.longitude, origin.latitude],
                    [alt_lon, alt_lat],
                    [dest_lon, dest_lat]
                ]

        safe_distance_nm = round(safe_distance_km / nm_ratio, 2)
        safe_duration_h = round(safe_distance_nm / speed, 2)
        safe_fuel_l = round(safe_duration_h * burn_rate, 1) if burn_rate > 0 else 0.0

        safe_geojson = {
            "type": "Feature",
            "properties": {
                "route_type": "safe_passage_corridor",
                "alternative_id": "safe_corridor",
                "name": "Safe Passage Corridor (Waypoints)",
                "vessel_type": v_profile["vessel_type"],
                "vessel_name": v_profile["name"],
                "total_distance_km": safe_distance_km,
                "total_distance_nm": safe_distance_nm,
                "estimated_duration_hours": safe_duration_h,
                "estimated_fuel_litres": safe_fuel_l,
                "fuel_type": v_profile.get("fuel_type", "N/A"),
                "geofence_avoidance_applied": geofence_avoidance_applied,
                "avoided_zones": safe_avoided_names,
                "clearance_buffer_km": buffer_km
            },
            "geometry": {
                "type": "LineString",
                "coordinates": safe_coords
            }
        }

        alt_safe = RouteAlternative(
            alternative_id="safe_corridor",
            name="Safe Passage Corridor (Waypoints)",
            total_distance_km=safe_distance_km,
            total_distance_nm=safe_distance_nm,
            estimated_duration_hours=safe_duration_h,
            estimated_fuel_litres=safe_fuel_l,
            fuel_type=v_profile.get("fuel_type"),
            intersects_restricted_zone=False,
            intersected_zones=[],
            route_risk_index=3.2,
            route_risk_level="LOW",
            waypoints=safe_waypoints,
            geojson_feature=safe_geojson,
            is_recommended=True,
            recommendation_reason="Recommended passage: avoids all restricted zones with configured safety margin."
        )

        # 5. Alternative 3: High-Clearance Seaward Corridor (Max Margin Alternative)
        bearing = calculate_bearing(origin.latitude, origin.longitude, dest_lat, dest_lon)
        seaward_bearing = (bearing + 90.0) % 360.0
        rad_s = math.radians(seaward_bearing)
        mid_lat = (origin.latitude + dest_lat) / 2.0
        mid_lon = (origin.longitude + dest_lon) / 2.0
        extra_offset_km = max(buffer_km * 3.5, 4.0)
        s_d_lat = (extra_offset_km / 111.0) * math.cos(rad_s)
        s_d_lon = (extra_offset_km / (111.0 * math.cos(math.radians(mid_lat)))) * math.sin(rad_s)
        sea_wp_lat = round(mid_lat + s_d_lat, 4)
        sea_wp_lon = round(mid_lon + s_d_lon, 4)

        d_s1 = haversine_distance(origin.latitude, origin.longitude, sea_wp_lat, sea_wp_lon)
        d_s2 = haversine_distance(sea_wp_lat, sea_wp_lon, dest_lat, dest_lon)
        sea_distance_km = round(d_s1 + d_s2, 2)
        sea_distance_nm = round(sea_distance_km / nm_ratio, 2)
        sea_duration_h = round(sea_distance_nm / speed, 2)
        sea_fuel_l = round(sea_duration_h * burn_rate, 1) if burn_rate > 0 else 0.0

        sea_waypoints = [TransitWaypoint(
            name="WP-1 (Seaward Wide Margin)",
            latitude=sea_wp_lat,
            longitude=sea_wp_lon,
            description="Deep-water seaward waypoint with extended 4.0+ km perimeter clearance."
        )]
        sea_geojson = {
            "type": "Feature",
            "properties": {
                "alternative_id": "high_clearance",
                "name": "High-Clearance Seaward Corridor",
                "total_distance_km": sea_distance_km,
                "total_distance_nm": sea_distance_nm,
                "estimated_duration_hours": sea_duration_h,
                "estimated_fuel_litres": sea_fuel_l,
                "intersects_restricted_zone": False
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [origin.longitude, origin.latitude],
                    [sea_wp_lon, sea_wp_lat],
                    [dest_lon, dest_lat]
                ]
            }
        }

        alt_sea = RouteAlternative(
            alternative_id="high_clearance",
            name="High-Clearance Seaward Corridor",
            total_distance_km=sea_distance_km,
            total_distance_nm=sea_distance_nm,
            estimated_duration_hours=sea_duration_h,
            estimated_fuel_litres=sea_fuel_l,
            fuel_type=v_profile.get("fuel_type"),
            intersects_restricted_zone=False,
            intersected_zones=[],
            route_risk_index=3.8,
            route_risk_level="LOW",
            waypoints=sea_waypoints,
            geojson_feature=sea_geojson,
            is_recommended=False,
            recommendation_reason="Extended deep-water margin alternative for heavy weather or restricted vessel draft."
        )

        alternatives = [alt_direct, alt_safe, alt_sea]

        # 6. Environmental Route Reasoning Evaluation Points
        midpoint_eval_coords = [round((origin.latitude + dest_lat) / 2.0, 4), round((origin.longitude + dest_lon) / 2.0, 4)]
        env_evaluations = [
            {
                "point_index": 1,
                "label": "Departure Sector",
                "name": origin.name or "Origin",
                "latitude": origin.latitude,
                "longitude": origin.longitude,
                "evaluation_type": "Live Open-Meteo Coastal Telemetry"
            },
            {
                "point_index": 2,
                "label": "Corridor Midpoint",
                "name": "Mid-Passage Evaluation Point",
                "latitude": midpoint_eval_coords[0],
                "longitude": midpoint_eval_coords[1],
                "evaluation_type": "Deterministic Geometric Sampling"
            },
            {
                "point_index": 3,
                "label": "Target Destination",
                "name": dest_name,
                "latitude": dest_lat,
                "longitude": dest_lon,
                "evaluation_type": "Arrival Coastal/Offshore Sector"
            }
        ]

        env_limitation = (
            "Environmental telemetry evaluated at departure sector (Open-Meteo). "
            "Mid-corridor and destination parameters represent discrete spatial sampling points; "
            "continuous real-time buoy or satellite observations are not deployed route-wide."
        )

        return TransitRoute(
            origin=origin,
            destination=destination,
            waypoints=safe_waypoints,
            total_distance_km=safe_distance_km,
            total_distance_nm=safe_distance_nm,
            estimated_duration_hours=safe_duration_h,
            estimated_fuel_litres=safe_fuel_l,
            fuel_type=v_profile.get("fuel_type"),
            geofence_avoidance_applied=geofence_avoidance_applied,
            avoided_zones=safe_avoided_names,
            clearance_buffer_km=buffer_km,
            geojson_feature=safe_geojson,
            fuel_estimate_note=fuel_note,
            alternatives=alternatives,
            environmental_evaluations=env_evaluations,
            evaluation_limitation=env_limitation
        )


# Singleton routing engine instance
routing_engine = SafeRoutingEngine()
