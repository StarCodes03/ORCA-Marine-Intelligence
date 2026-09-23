"""Unit tests for deterministic geospatial calculations and adapters."""

import pytest
from app.tools.gis_data import (
    haversine_distance,
    calculate_bearing,
    point_in_polygon,
    gis_adapter
)


def test_haversine_known_coordinates():
    # Distance from Kochi (9.9312, 76.2673) to Chellanam PFZ (9.8000, 76.1000)
    dist = haversine_distance(9.9312, 76.2673, 9.8000, 76.1000)
    assert 20.0 < dist < 26.0  # Approx 23 km
    # Distance from same point to itself should be 0
    assert haversine_distance(9.9312, 76.2673, 9.9312, 76.2673) == 0.0


def test_calculate_bearing():
    bearing = calculate_bearing(9.9312, 76.2673, 9.8000, 76.1000)
    assert 0.0 <= bearing <= 360.0
    # Chellanam is South-West of Kochi (bearing roughly ~220-230 degrees)
    assert 200.0 < bearing < 250.0


def test_point_in_polygon():
    # Simple rectangular polygon in [lon, lat] format
    square = [
        [76.20, 9.94],
        [76.25, 9.94],
        [76.25, 9.98],
        [76.20, 9.98],
        [76.20, 9.94]
    ]

    # Point clearly inside
    inside_pt = (9.96, 76.22)
    assert point_in_polygon(inside_pt[0], inside_pt[1], square) is True

    # Point clearly outside
    outside_pt = (9.90, 76.15)
    assert point_in_polygon(outside_pt[0], outside_pt[1], square) is False


def test_gis_adapter_pfz_search():
    # Search from Kochi harbor
    all_pfzs = gis_adapter.get_all_pfzs_with_distance(9.9312, 76.2673)
    assert len(all_pfzs) >= 3
    # Nearest should be first
    assert all_pfzs[0]["distance_km"] <= all_pfzs[1]["distance_km"]

    nearest = gis_adapter.find_nearest_pfz(9.9312, 76.2673)
    assert nearest is not None
    assert nearest["pfz_id"] == "PFZ-KL-001"
    assert "Chellanam" in nearest["name"]
    assert nearest["source"] == "DEMO_GIS_DATA"


def test_gis_adapter_restricted_zone():
    # Point inside the Cochin naval / port enclave (lat ~9.96, lon ~76.23)
    result_inside = gis_adapter.check_restricted_zones(9.96, 76.23)
    assert result_inside["inside_restricted_zone"] is True
    assert result_inside["restricted_zone_nearby"] is True

    # Point far offshore (lat 9.80, lon 75.80)
    result_outside = gis_adapter.check_restricted_zones(9.80, 75.80)
    assert result_outside["inside_restricted_zone"] is False
