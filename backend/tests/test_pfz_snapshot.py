"""Unit and integration tests for official INCOIS historical PFZ snapshot adapter and agent integration.

Covers:
- Static snapshot JSON file validation (21 official Ernakulam landing center records).
- IncoisSnapshotPFZAdapter distance calculation, bearing, and sorting.
- Provenance metadata assertions (source, source_type, advisory_date, valid_until, is_live=False, is_mock=False).
- Automatic fallback behavior when the snapshot is missing or corrupted.
- GeospatialAgent integration returning OFFICIAL_SNAPSHOT.
- GeospatialAgent integration under fallback mode returning MOCK_FALLBACK.
- EvidenceAgent synthesis of the official snapshot disclaimer claim.
"""

import json
from pathlib import Path
import pytest

from app.models.schemas import LocationCoords, GeospatialData, NearestPFZ, PlannerOutput
from app.tools.pfz_data import IncoisSnapshotPFZAdapter, incois_snapshot_adapter
from app.agents.geospatial import GeospatialAgent
from app.agents.evidence import EvidenceAgent


def test_snapshot_json_structure():
    """Verify that incois_kerala_snapshot.json exists, parses, and has authentic INCOIS metadata."""
    snapshot_path = (
        Path(__file__).resolve().parent.parent / "app" / "data" / "pfz" / "incois_kerala_snapshot.json"
    )
    assert snapshot_path.exists(), f"Snapshot file not found at {snapshot_path}"

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["source"] == "INCOIS"
    assert data["source_type"] == "OFFICIAL_SNAPSHOT"
    assert data["advisory_date"] == "2024-04-27T18:30:00Z"
    assert data["valid_until"] == "2024-04-28T18:30:00Z"
    assert data["sector"] == "SEC005"
    assert data["state"] == "KERALA"
    assert data["district"] == "Ernakulam"
    assert "layer" in data
    assert len(data["records"]) == 21

    # Verify each record has required fields and no fabricated attributes
    for r in data["records"]:
        assert r["pfz_id"].startswith("INCOIS-")
        assert len(r["landing_centre"]) > 0
        assert 9.0 <= r["target_latitude"] <= 11.0
        assert 75.0 <= r["target_longitude"] <= 77.0
        assert 0.0 <= r["bearing_deg"] <= 360.0
        assert r["distance_from_km"] > 0
        assert r["distance_to_km"] >= r["distance_from_km"]
        assert r["depth_from_m"] > 0
        assert r["depth_to_m"] >= r["depth_from_m"]
        assert r["forecast_date"] == "2024-04-27T18:30:00Z"
        assert r["validity_date"] == "2024-04-28T18:30:00Z"
        assert r["status"] == "YES"


def test_snapshot_adapter_distance_and_ranking():
    """Verify that IncoisSnapshotPFZAdapter ranks all 21 records by distance from Kochi."""
    adapter = IncoisSnapshotPFZAdapter()
    assert adapter.is_fallback is False

    # Query from Kochi Harbor Coastal Reference Station (9.9312, 76.2673)
    results = adapter.get_all_pfzs_with_distance(9.9312, 76.2673)
    assert len(results) == 21

    # Ascending distance order
    for i in range(len(results) - 1):
        assert results[i]["distance_km"] <= results[i + 1]["distance_km"]

    # Nearest target check
    nearest = results[0]
    assert "PFZ target associated with" in nearest["name"]
    assert 10.0 < nearest["distance_km"] < 60.0  # Offshore Kerala shelf
    assert nearest["source"] == "INCOIS"
    assert nearest["source_type"] == "OFFICIAL_SNAPSHOT"

    # Strict check: attributes not present in official landing center feed must NOT be fabricated
    assert nearest["sst_c"] is None
    assert nearest["chlorophyll_mg_m3"] is None
    assert nearest["target_species"] is None
    assert nearest["confidence_score"] is None


def test_snapshot_provenance_metadata():
    """Verify that provenance metadata strictly identifies OFFICIAL_SNAPSHOT and is_live=False."""
    adapter = IncoisSnapshotPFZAdapter()
    prov = adapter.get_provenance()

    assert prov["source"] == "INCOIS"
    assert prov["source_type"] == "OFFICIAL_SNAPSHOT"
    assert prov["advisory_date"] == "2024-04-27T18:30:00Z"
    assert prov["valid_until"] == "2024-04-28T18:30:00Z"
    assert prov["is_live"] is False
    assert prov["is_mock"] is False


def test_snapshot_find_nearest_pfz():
    """Verify that find_nearest_pfz returns the top-ranked candidate."""
    adapter = IncoisSnapshotPFZAdapter()
    nearest = adapter.find_nearest_pfz(9.9312, 76.2673)
    all_pfzs = adapter.get_all_pfzs_with_distance(9.9312, 76.2673)

    assert nearest is not None
    assert nearest["pfz_id"] == all_pfzs[0]["pfz_id"]
    assert nearest["distance_km"] == all_pfzs[0]["distance_km"]


def test_snapshot_geojson_features():
    """Verify that GeoJSON features are generated with correct properties for map popups."""
    adapter = IncoisSnapshotPFZAdapter()
    features = adapter.get_geojson_features()

    assert len(features) == 21
    first_feat = features[0]
    assert first_feat["type"] == "Feature"
    assert first_feat["geometry"]["type"] == "Point"
    assert len(first_feat["geometry"]["coordinates"]) == 2  # [lon, lat]

    props = first_feat["properties"]
    assert props["source"] == "INCOIS"
    assert props["source_type"] == "OFFICIAL_SNAPSHOT"
    assert "landing_centre" in props
    assert "distance_km" in props
    assert "depth_m" in props


def test_missing_file_automatic_fallback(tmp_path):
    """Verify graceful fallback to mock GIS data when snapshot file is missing."""
    missing_path = tmp_path / "nonexistent_snapshot.json"
    adapter = IncoisSnapshotPFZAdapter(snapshot_path=missing_path)

    assert adapter.is_fallback is True

    prov = adapter.get_provenance()
    assert prov["source"] == "DEMO_GIS_DATA"
    assert prov["source_type"] == "MOCK_FALLBACK"
    assert prov["is_live"] is False
    assert prov["is_mock"] is True

    results = adapter.get_all_pfzs_with_distance(9.9312, 76.2673)
    assert len(results) >= 3
    assert results[0]["source_type"] == "MOCK_FALLBACK"
    assert results[0]["is_mock"] is True


def test_corrupt_file_automatic_fallback(tmp_path):
    """Verify graceful fallback when snapshot file contains invalid JSON."""
    corrupt_file = tmp_path / "corrupt_snapshot.json"
    corrupt_file.write_text("{ this is invalid json syntax ::: ", encoding="utf-8")

    adapter = IncoisSnapshotPFZAdapter(snapshot_path=corrupt_file)
    assert adapter.is_fallback is True

    prov = adapter.get_provenance()
    assert prov["source_type"] == "MOCK_FALLBACK"
    assert prov["is_mock"] is True


def test_geospatial_agent_official_snapshot_integration():
    """Verify GeospatialAgent returns OFFICIAL_SNAPSHOT GeospatialData using official records."""
    agent = GeospatialAgent()
    loc = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

    geo_data: GeospatialData = agent.execute(location=loc)

    assert geo_data.source == "INCOIS"
    assert geo_data.source_type == "OFFICIAL_SNAPSHOT"
    assert geo_data.advisory_date == "2024-04-27T18:30:00Z"
    assert geo_data.valid_until == "2024-04-28T18:30:00Z"
    assert geo_data.is_live is False
    assert geo_data.is_mock is False

    assert geo_data.nearest_pfz is not None
    assert geo_data.nearest_pfz.source == "INCOIS"
    assert geo_data.nearest_pfz.source_type == "OFFICIAL_SNAPSHOT"
    assert len(geo_data.all_pfzs) == 21

    # Restricted zones check preserved
    assert geo_data.restricted_zone_check is not None


def test_geospatial_agent_fallback_integration(tmp_path):
    """Verify GeospatialAgent produces MOCK_FALLBACK GeospatialData when fallback adapter is active."""
    fallback_adapter = IncoisSnapshotPFZAdapter(snapshot_path=tmp_path / "missing.json")
    agent = GeospatialAgent(pfz_provider=fallback_adapter)
    loc = LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)

    geo_data: GeospatialData = agent.execute(location=loc)

    assert geo_data.source_type == "MOCK_FALLBACK"
    assert geo_data.is_mock is True
    assert geo_data.is_live is False
    assert geo_data.advisory_date is None


def test_evidence_agent_snapshot_provenance_and_disclaimer():
    """Verify EvidenceAgent includes the required snapshot disclaimer in evidence claims."""
    evidence_agent = EvidenceAgent()

    plan = PlannerOutput(
        intent="pfz_search",
        location=LocationCoords(name="Kochi", latitude=9.9312, longitude=76.2673)
    )

    nearest_pfz = NearestPFZ(
        pfz_id="INCOIS-KL0619b",
        name="PFZ off Kochi (SW 27-32 km)",
        latitude=9.8361,
        longitude=75.9986,
        distance_km=31.2,
        bearing_deg=243.0,
        landing_centre="Kochi",
        source="INCOIS",
        source_type="OFFICIAL_SNAPSHOT"
    )

    geo_data = GeospatialData(
        source="INCOIS",
        source_type="OFFICIAL_SNAPSHOT",
        advisory_date="2024-04-27T18:30:00Z",
        valid_until="2024-04-28T18:30:00Z",
        is_live=False,
        is_mock=False,
        user_location=plan.location,
        nearest_pfz=nearest_pfz,
        all_pfzs=[nearest_pfz]
    )

    result = evidence_agent.synthesize(planner_plan=plan, geospatial=geo_data)

    evidence_items = result["evidence"]
    snapshot_claims = [
        item for item in evidence_items
        if item.category == "source_metadata" and "not a live fishing advisory" in item.claim
    ]

    assert len(snapshot_claims) == 1
    claim = snapshot_claims[0]
    assert "official INCOIS historical snapshot" in claim.claim
    assert "2024-04-27" in claim.claim
    assert claim.source == "INCOIS"
