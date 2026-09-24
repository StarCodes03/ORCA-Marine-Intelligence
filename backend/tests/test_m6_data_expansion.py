"""ORCA Marine Intelligence - M6 Data & Earth Observation Expansion Regression Suite

Tests cover:
1. Unified DataSourceAdapter contract (fetch, normalize, validate, provenance).
2. EarthObservationAdapter unconfigured graceful UNAVAILABLE state without fabricated metrics.
3. OpenMeteoWeatherAdapter structured provenance disclosure.
4. OpenMeteoMarineAdapter structured provenance disclosure.
"""

import pytest
from app.tools.base_adapter import DataSourceAdapter, SourceProvenanceMetadata
from app.tools.earth_observation import EarthObservationAdapter, earth_observation_adapter
from app.tools.weather_data import OpenMeteoWeatherAdapter
from app.tools.ocean_data import OpenMeteoMarineAdapter


def test_base_adapter_contract():
    """Verify that DataSourceAdapter enforces the interface contract."""
    class DummyAdapter(DataSourceAdapter):
        def fetch(self, lat, lon, time_window="current", **kwargs):
            return {"raw_val": 42.0}

        def normalize(self, raw_data):
            return {"val": raw_data["raw_val"]}

        def validate(self, normalized_data):
            return normalized_data["val"] > 0

        def get_provenance(self):
            return SourceProvenanceMetadata(
                source_id=self.source_id,
                source_name=self.source_name,
                source_type="DERIVED_CALCULATION",
                coverage="Local",
                update_frequency="On-demand",
                is_live=False,
                is_mock=False,
                is_fallback=False
            )

    adapter = DummyAdapter(source_id="dummy", source_name="DUMMY_PROVIDER")
    assert adapter.is_available() is True
    res = adapter.cached_fetch(9.93, 76.26)
    assert res["val"] == 42.0
    assert "_provenance" in res
    assert res["_provenance"]["source_id"] == "dummy"
    assert res["_provenance"]["source_type"] == "DERIVED_CALCULATION"


def test_earth_observation_unconfigured_state():
    """Verify that unconfigured EarthObservationAdapter returns UNAVAILABLE without fabricated data."""
    eo = EarthObservationAdapter()
    eo._is_configured = False

    assert eo.is_available() is False
    prov = eo.get_provenance()
    assert prov.source_type == "UNAVAILABLE"
    assert prov.is_live is False
    assert prov.is_mock is False
    assert len(prov.limitations) >= 1
    assert "Copernicus" in prov.limitations[0]

    raw = eo.fetch(9.9312, 76.2673)
    assert raw["status"] == "UNAVAILABLE"
    assert raw["chlorophyll_mg_m3"] is None

    norm = eo.normalize(raw)
    assert norm["chlorophyll_mg_m3"] is None
    assert norm["is_available"] is False
    assert eo.validate(norm) is True


def test_weather_adapter_provenance():
    """Verify live and fallback provenance metadata from OpenMeteoWeatherAdapter."""
    prov_live = OpenMeteoWeatherAdapter.get_provenance(is_live=True, is_fallback=False)
    assert prov_live.source_id == "open_meteo_weather"
    assert prov_live.source_type == "LIVE_API"
    assert prov_live.is_live is True
    assert prov_live.is_fallback is False
    assert any("Lightning" in lim for lim in prov_live.limitations)

    prov_fallback = OpenMeteoWeatherAdapter.get_provenance(is_live=False, is_fallback=True)
    assert prov_fallback.source_type == "MOCK_FALLBACK"
    assert prov_fallback.is_mock is True
    assert prov_fallback.is_fallback is True


def test_marine_adapter_provenance():
    """Verify live and fallback provenance metadata from OpenMeteoMarineAdapter."""
    prov_live = OpenMeteoMarineAdapter.get_provenance(is_live=True, is_fallback=False)
    assert prov_live.source_id == "open_meteo_marine"
    assert prov_live.source_type == "LIVE_API"
    assert prov_live.is_live is True
    assert any("Chlorophyll" in lim for lim in prov_live.limitations)

    prov_fallback = OpenMeteoMarineAdapter.get_provenance(is_live=False, is_fallback=True)
    assert prov_fallback.source_type == "MOCK_FALLBACK"
    assert prov_fallback.is_fallback is True
