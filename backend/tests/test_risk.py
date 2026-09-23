"""Unit tests for transparent rule-based risk calculation."""

import pytest
from app.models.schemas import (
    WeatherData,
    OceanData,
    GeospatialData,
    LocationCoords,
    RestrictedZoneCheck
)
from app.agents.risk import RiskAssessmentAgent


@pytest.fixture
def risk_agent():
    return RiskAssessmentAgent()


def test_safe_conditions(risk_agent):
    weather = WeatherData(
        source="MOCK_WEATHER_DATA",
        location="Kochi",
        forecast_time="tomorrow_morning",
        wind_speed_kmh=15.0,  # Below 25
        rain_probability=20.0,
        lightning_risk="low"
    )
    ocean = OceanData(
        source="MOCK_OCEAN_DATA",
        location="Kochi Offshore",
        sst_c=28.0,
        wave_height_m=1.1,  # Below 1.5
        sea_state="slight",
        tide="slack",
        chlorophyll_mg_m3=0.8
    )
    geo = GeospatialData(
        source="DEMO_GIS_DATA",
        user_location=LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673),
        restricted_zone_check=RestrictedZoneCheck(
            restricted_zone_nearby=False,
            inside_restricted_zone=False
        )
    )

    assessment = risk_agent.assess(weather=weather, ocean=ocean, geospatial=geo)
    assert assessment.risk_level == "LOW"
    assert assessment.risk_score <= 2.0


def test_elevated_conditions_kochi_demo(risk_agent):
    """Matches the exact demo acceptance criteria:
    wind_speed_kmh: 32, wave_height_m: 1.8, lightning_risk: 'moderate', rain: 65%
    Should evaluate to HIGH risk.
    """
    weather = WeatherData(
        source="MOCK_WEATHER_DATA",
        location="Kochi",
        forecast_time="tomorrow_morning",
        wind_speed_kmh=32.0,
        rain_probability=65.0,
        lightning_risk="moderate"
    )
    ocean = OceanData(
        source="MOCK_OCEAN_DATA",
        location="Kochi Offshore",
        sst_c=28.4,
        wave_height_m=1.8,
        sea_state="moderate",
        tide="rising",
        chlorophyll_mg_m3=0.72
    )
    geo = GeospatialData(
        source="DEMO_GIS_DATA",
        user_location=LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673),
        restricted_zone_check=RestrictedZoneCheck(
            restricted_zone_nearby=False,
            inside_restricted_zone=False
        )
    )

    assessment = risk_agent.assess(weather=weather, ocean=ocean, geospatial=geo)
    assert assessment.risk_level == "HIGH"
    # Verify reasons capture the factors and exact lightning wording
    reasons_str = " ".join(assessment.reasons).lower()
    assert "wind" in reasons_str
    assert "wave" in reasons_str
    assert "lightning" in reasons_str
    assert "Moderate lightning risk" in assessment.reasons
    assert "Moderate to high lightning risk (Moderate)" not in assessment.reasons

    # Verify score breakdown and numeric contributions
    assert assessment.score_breakdown is not None
    assert assessment.score_breakdown.total_score == assessment.risk_score
    scores = assessment.score_breakdown.factor_scores
    assert scores["wind_speed"] == 2.5
    assert scores["rain_probability"] == 0.5
    assert scores["lightning_risk"] == 2.0
    assert scores["wave_height"] == 2.0
    assert scores["sea_state"] == 0.0
    assert scores["restricted_zone_proximity"] == 0.0

    # Verify each evidence item exposes numeric contribution
    evidence_contribs = {e.metric: e.contribution for e in assessment.evidence}
    assert evidence_contribs["wind_speed_kmh"] == 2.5
    assert evidence_contribs["rain_probability"] == 0.5
    assert evidence_contribs["lightning_risk"] == 2.0
    assert evidence_contribs["wave_height_m"] == 2.0


def test_restricted_zone_violation(risk_agent):
    """Inside restricted zone triggers CRITICAL or HIGH penalty."""
    geo = GeospatialData(
        source="DEMO_GIS_DATA",
        user_location=LocationCoords(name="Kochi Naval Enclave", latitude=9.96, longitude=76.23),
        restricted_zone_check=RestrictedZoneCheck(
            restricted_zone_nearby=True,
            inside_restricted_zone=True,
            zone_name="Cochin Naval Base & Port Channel Security Enclave"
        )
    )
    assessment = risk_agent.assess(weather=None, ocean=None, geospatial=geo)
    assert assessment.risk_level in ["HIGH", "CRITICAL"]
    assert any("VIOLATION" in r for r in assessment.reasons)


def test_kochi_demo_query_exact_score_breakdown(risk_agent):
    """Test exact score breakdown for Kochi demo query with live GIS adapter output.
    Wind: 32 km/h (+2.5)
    Rain: 65% (+0.5)
    Lightning: moderate (+2.0)
    Waves: 1.8 m (+2.0)
    Sea state: moderate (+0.0)
    Restricted zone proximity (2.13 km <= 3.0 km buffer): (+1.5)
    Total score: 8.5 -> HIGH risk
    """
    from app.tools.weather_data import MockWeatherDataAdapter
    from app.tools.ocean_data import MockOceanDataAdapter
    from app.tools.gis_data import gis_adapter

    loc = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    w_raw = MockWeatherDataAdapter.get_forecast(loc.name, loc.latitude, loc.longitude, "tomorrow_morning")
    o_raw = MockOceanDataAdapter.get_ocean_conditions(loc.name, loc.latitude, loc.longitude, "tomorrow_morning")
    rz_raw = gis_adapter.check_restricted_zones(loc.latitude, loc.longitude)

    weather = WeatherData(**w_raw)
    ocean = OceanData(**o_raw)
    geo = GeospatialData(
        source="DEMO_GIS_DATA",
        user_location=loc,
        restricted_zone_check=RestrictedZoneCheck(
            restricted_zone_nearby=rz_raw["restricted_zone_nearby"],
            inside_restricted_zone=rz_raw["inside_restricted_zone"],
            zone_name=rz_raw.get("zone_name"),
            zone_id=rz_raw.get("zone_id"),
            distance_to_nearest_zone_km=rz_raw.get("distance_to_nearest_zone_km")
        )
    )

    assessment = risk_agent.assess(weather=weather, ocean=ocean, geospatial=geo)
    assert assessment.risk_level == "HIGH"
    assert assessment.risk_score == 8.5
    assert "Moderate lightning risk" in assessment.reasons

    assert assessment.score_breakdown is not None
    assert assessment.score_breakdown.total_score == 8.5

    scores = assessment.score_breakdown.factor_scores
    assert scores["wind_speed"] == 2.5
    assert scores["rain_probability"] == 0.5
    assert scores["lightning_risk"] == 2.0
    assert scores["wave_height"] == 2.0
    assert scores["sea_state"] == 0.0
    assert scores["restricted_zone_proximity"] == 1.5

    # Check that sum of contributions equals total_score exactly
    contrib_sum = sum(f.contribution for f in assessment.score_breakdown.factors)
    assert contrib_sum == 8.5
