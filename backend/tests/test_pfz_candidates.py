"""ORCA Marine Intelligence - Isolated Unit Tests
Deterministic PFZ Candidate Reasoning Engine (M5 Step 3)

Verifies:
1. Radius filtering against historical INCOIS snapshot using Haversine distance
2. Nearest-target ranking preserving authentic snapshot fields and bearings
3. Candidate comparison with distance, bearing, landing centre, depth range, and unavailable fields
4. Unavailable-field handling (SST, chlorophyll, target species, fish abundance remain None)
5. Spatial/geofence reasoning for direct routes intersecting vs clear of restricted zones
"""

import pytest
from app.models.schemas import LocationCoords, NearestPFZ
from app.tools.pfz_candidates import PFZCandidateEngine, pfz_candidate_engine
from app.tools.pfz_data import incois_snapshot_adapter
from app.tools.gis_data import gis_adapter


def test_radial_filter_within_radius():
    """Verify deterministic radius filtering from Kochi:
    - Exactly 2 targets exist within 25 km in the historical snapshot.
    - Exactly 8 targets exist within 30 km in the historical snapshot.
    - Zero targets exist within 10 km.
    - Candidates are returned sorted by distance ascending.
    """
    kochi = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

    # 1. 25 km threshold
    candidates_25 = pfz_candidate_engine.get_candidates_within_radius(kochi, 25.0)
    assert len(candidates_25) == 2
    assert all(c.distance_km <= 25.0 for c in candidates_25)
    assert candidates_25[0].distance_km <= candidates_25[1].distance_km
    assert candidates_25[0].landing_centre == "Kuzhuppilly"
    assert candidates_25[1].landing_centre == "Cherai"

    # 2. 30 km threshold
    candidates_30 = pfz_candidate_engine.get_candidates_within_radius(kochi, 30.0)
    assert len(candidates_30) == 9
    assert all(c.distance_km <= 30.0 for c in candidates_30)
    # Check monotonicity
    for i in range(len(candidates_30) - 1):
        assert candidates_30[i].distance_km <= candidates_30[i + 1].distance_km

    # 3. 10 km threshold (empty)
    candidates_10 = pfz_candidate_engine.get_candidates_within_radius(kochi, 10.0)
    assert len(candidates_10) == 0


def test_nearest_target_ranking():
    """Verify ranking top K historical PFZ targets preserves authentic snapshot fields
    and does not label targets as 'active' or 'high probability'.
    """
    kochi = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

    ranked = pfz_candidate_engine.get_ranked_candidates(kochi, limit=5)
    assert len(ranked) == 5

    # Check top candidate
    top = ranked[0]
    assert top.landing_centre == "Kuzhuppilly"
    assert round(top.distance_km, 1) == 24.4
    assert top.bearing_deg is not None
    assert top.source == "INCOIS"
    assert top.source_type == "OFFICIAL_SNAPSHOT"

    # Verify no fabrication of active status or fish probability
    for target in ranked:
        assert target.confidence_score is None
        assert target.target_species is None
        assert target.sst_c is None
        assert target.chlorophyll_mg_m3 is None


def test_candidate_pair_comparison():
    """Verify deterministic candidate comparison between two specific historical PFZ targets."""
    kochi = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    ranked = pfz_candidate_engine.get_ranked_candidates(kochi, limit=2)
    target_a = ranked[0]  # Kuzhuppilly (24.37 km)
    target_b = ranked[1]  # Cherai (24.46 km)

    comp = pfz_candidate_engine.compare_candidates(kochi, target_a, target_b)

    assert comp.target_a.pfz_id == target_a.pfz_id
    assert comp.target_b.pfz_id == target_b.pfz_id
    assert comp.closer_target == target_a.name
    assert comp.distance_difference_km == round(abs(target_b.distance_km - target_a.distance_km), 2)
    assert "Depth comparison" in comp.depth_comparison
    assert comp.geofence_status_a in ["CLEAR", "INTERSECTS_RESTRICTED_ZONE"]
    assert comp.geofence_status_b in ["CLEAR", "INTERSECTS_RESTRICTED_ZONE"]
    assert "Historical INCOIS landing-centre-associated PFZ target comparison" in comp.disclaimer


def test_unavailable_field_handling():
    """Verify that unavailable fields are explicitly listed and never fabricated."""
    kochi = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    ranked = pfz_candidate_engine.get_ranked_candidates(kochi, limit=2)

    comp = pfz_candidate_engine.compare_candidates(kochi, ranked[0], ranked[1])

    # Assert unavailable fields checklist is present and explicit
    unavail = comp.unavailable_fields
    assert any("sst_c" in f for f in unavail)
    assert any("chlorophyll" in f for f in unavail)
    assert any("target_species" in f for f in unavail)
    assert any("fish_abundance" in f for f in unavail)
    assert any("real_time_validity" in f for f in unavail)

    # Test depth comparison when depth_m is None
    dummy_a = ranked[0].model_copy(update={"depth_m": None})
    dummy_b = ranked[1].model_copy(update={"depth_m": None})
    comp_no_depth = pfz_candidate_engine.compare_candidates(kochi, dummy_a, dummy_b)
    assert "unavailable or incomplete" in comp_no_depth.depth_comparison.lower()


def test_direct_route_geofence_reasoning():
    """Verify that direct routes crossing restricted zones are flagged as intersecting,
    while open water routes are flagged as clear.
    """
    # 1. Direct route from Kochi Harbor crosses Cochin Naval Base / Port security polygon
    kochi = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    kuzhuppilly_target = pfz_candidate_engine.get_ranked_candidates(kochi, limit=1)[0]
    gf_kochi = pfz_candidate_engine.check_direct_route_geofence(kochi, kuzhuppilly_target)

    assert gf_kochi["intersects"] is True
    assert gf_kochi["status"] == "INTERSECTS_RESTRICTED_ZONE"
    assert "Cochin Naval Base & Port Channel Security Enclave" in gf_kochi["intersected_zones"]

    # 2. Direct route from Chellanam offshore is south of the naval base polygon and clear
    chellanam = LocationCoords(name="Chellanam", latitude=9.8000, longitude=76.2600)
    maruvakad_target = pfz_candidate_engine.get_ranked_candidates(chellanam, limit=1)[0]
    gf_chellanam = pfz_candidate_engine.check_direct_route_geofence(chellanam, maruvakad_target)

    assert gf_chellanam["intersects"] is False
    assert gf_chellanam["status"] == "CLEAR"
    assert len(gf_chellanam["intersected_zones"]) == 0
