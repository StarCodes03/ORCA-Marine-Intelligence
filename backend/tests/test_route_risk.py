"""ORCA Marine Intelligence - Isolated Unit Tests for Prototype Route Risk Index Engine (M5)

Verifies:
1. 4-factor deterministic composite calculation (env, vessel, distance, geofence).
2. Differences between craft categories driven strictly by configured prototype limits (not objective claims).
3. Distance exposure penalty scaling with nautical miles.
4. Route geofence interaction penalty when corridor avoidance is applied.
5. Factor breakdown dictionary, limiting factor identification, and prototype disclaimer.
"""

import pytest

from app.models.schemas import (
    LocationCoords,
    NearestPFZ,
    TransitRoute,
    WeatherData,
    OceanData,
    RiskAssessment
)
from app.tools.route_risk import route_risk_calculator, RouteRiskCalculator
from app.config.risk_thresholds import PROTOTYPE_ROUTE_RISK_CONFIG


@pytest.fixture
def origin_point():
    return LocationCoords(name="Kochi Port", latitude=9.9600, longitude=76.2400)


@pytest.fixture
def target_pfz():
    return NearestPFZ(
        pfz_id="PFZ-TEST-M5",
        name="Offshore Bank Target",
        latitude=10.1500,
        longitude=75.9500,
        distance_km=38.5,
        bearing_deg=310.0
    )


def test_route_risk_composite_formula(origin_point, target_pfz):
    """Verify deterministic 4-factor composite calculation and factor breakdown structure."""
    route = TransitRoute(
        origin=origin_point,
        destination=target_pfz,
        waypoints=[],
        total_distance_km=37.04,
        total_distance_nm=20.0,  # Moderate distance (10-25 nm)
        estimated_duration_hours=2.5,
        geofence_avoidance_applied=False,
        clearance_buffer_km=1.5
    )
    weather = WeatherData(
        temperature_c=28.0,
        wind_speed_kmh=15.0,
        wind_direction_deg=270.0,
        rain_probability=10.0,
        lightning_risk="none",
        source="MOCK"
    )
    ocean = OceanData(
        sst_c=28.0,
        wave_height_m=1.0,
        sea_state="slight",
        tide="high_tide",
        source="MOCK"
    )
    risk_assessment = RiskAssessment(
        risk_level="LOW",
        risk_score=2.0
    )

    assessment = route_risk_calculator.assess_route_risk(
        origin=origin_point,
        transit_route=route,
        weather=weather,
        ocean=ocean,
        risk_assessment=risk_assessment,
        vessel_type="motorized_frp_obm"
    )

    assert 0.0 <= assessment.prototype_route_risk_index <= 10.0
    assert assessment.evaluation_point.name == "Kochi Port"
    assert "Prototype Route Risk Index" in assessment.disclaimer
    assert "NOT an official maritime safety rating" in assessment.disclaimer

    fb = assessment.factor_breakdown
    assert "environmental_factor" in fb
    assert "vessel_stress_factor" in fb
    assert "distance_exposure_factor" in fb
    assert "geofence_interaction_factor" in fb

    # Check sum of factors matches prototype_route_risk_index within rounding tolerance
    expected_sum = round(
        fb["environmental_factor"] +
        fb["vessel_stress_factor"] +
        fb["distance_exposure_factor"] +
        fb["geofence_interaction_factor"],
        1
    )
    assert assessment.prototype_route_risk_index == expected_sum


def test_route_risk_configured_craft_parameters(origin_point, target_pfz):
    """Verify that route risk index variations between craft categories stem strictly

    from configured prototype parameters (e.g. wave safe limits of 1.0m vs 2.5m under identical
    1.8m input conditions) without claiming objective real-world superiority.
    """
    route = TransitRoute(
        origin=origin_point,
        destination=target_pfz,
        waypoints=[],
        total_distance_km=25.0,
        total_distance_nm=13.5,
        estimated_duration_hours=2.0,
        geofence_avoidance_applied=False,
        clearance_buffer_km=1.5
    )
    weather = WeatherData(
        temperature_c=28.0,
        wind_speed_kmh=18.0,
        wind_direction_deg=270.0,
        rain_probability=10.0,
        lightning_risk="none",
        source="MOCK"
    )
    # 1.8m wave height:
    # - For traditional_craft (configured prototype limit 1.0m): ratio = 1.80 > 1.0 -> penalty 10.0
    # - For mechanized_trawler (configured prototype limit 2.5m): ratio = 0.72 < 1.0 -> penalty 1.4
    ocean = OceanData(
        sst_c=28.0,
        wave_height_m=1.8,
        sea_state="moderate",
        tide="high_tide",
        source="MOCK"
    )
    risk_assessment = RiskAssessment(
        risk_level="MODERATE",
        risk_score=4.0
    )

    res_trad = route_risk_calculator.assess_route_risk(
        origin=origin_point,
        transit_route=route,
        weather=weather,
        ocean=ocean,
        risk_assessment=risk_assessment,
        vessel_type="traditional_craft"
    )

    res_trawler = route_risk_calculator.assess_route_risk(
        origin=origin_point,
        transit_route=route,
        weather=weather,
        ocean=ocean,
        risk_assessment=risk_assessment,
        vessel_type="mechanized_trawler"
    )

    assert res_trad.wave_stress_ratio == 1.8
    assert res_trawler.wave_stress_ratio == 0.72
    assert res_trad.prototype_route_risk_index > res_trawler.prototype_route_risk_index
    assert res_trad.factor_breakdown["vessel_stress_factor"] > res_trawler.factor_breakdown["vessel_stress_factor"]
    assert any("configured prototype" in r.lower() for r in res_trad.reasons)


def test_route_risk_distance_exposure_penalty(origin_point, target_pfz):
    """Verify that route distance exposure penalty scales from short coastal to extended offshore transit."""
    calc = RouteRiskCalculator()

    # Short transit: <= 10 nm
    short_penalty = calc.calculate_distance_exposure_penalty(distance_nm=6.5)
    assert short_penalty["penalty_score"] == 1.0
    assert "minimal offshore exposure" in short_penalty["reason"].lower()

    # Moderate transit: 18.0 nm
    mod_penalty = calc.calculate_distance_exposure_penalty(distance_nm=18.0)
    assert 1.0 < mod_penalty["penalty_score"] < 5.0
    assert "moderate offshore exposure" in mod_penalty["reason"].lower()

    # Extended offshore transit: 35.0 nm
    long_penalty = calc.calculate_distance_exposure_penalty(distance_nm=35.0)
    assert long_penalty["penalty_score"] >= 5.0
    assert "elevated exposure" in long_penalty["reason"].lower()


def test_route_risk_geofence_interaction_penalty(origin_point, target_pfz):
    """Verify route geofence interaction penalty increases when restricted-zone avoidance is active."""
    calc = RouteRiskCalculator()

    # Route A: Direct clear passage
    route_clear = TransitRoute(
        origin=origin_point,
        destination=target_pfz,
        waypoints=[],
        total_distance_km=20.0,
        total_distance_nm=10.8,
        estimated_duration_hours=1.5,
        geofence_avoidance_applied=False,
        clearance_buffer_km=1.5
    )
    pen_clear = calc.calculate_geofence_interaction_penalty(route_clear)
    assert pen_clear["penalty_score"] == 0.0

    # Route B: Active geofence avoidance with buffer < 2.0 km (tightness addition active)
    route_avoidance = TransitRoute(
        origin=origin_point,
        destination=target_pfz,
        waypoints=[],
        total_distance_km=25.0,
        total_distance_nm=13.5,
        estimated_duration_hours=1.8,
        geofence_avoidance_applied=True,
        avoided_zones=["Kochi Naval Base Security Perimeter"],
        clearance_buffer_km=1.5
    )
    pen_avoidance = calc.calculate_geofence_interaction_penalty(route_avoidance)
    assert pen_avoidance["penalty_score"] == 6.0  # 4.0 base + 2.0 tightness
    assert "restricted-zone intersection active" in pen_avoidance["reason"].lower()
