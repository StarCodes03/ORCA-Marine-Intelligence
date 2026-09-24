"""ORCA Marine Intelligence - Unified Data Source Adapter Base Class

Defines the abstract interface and provenance contract for all external,
historical, and derived data providers in ORCA.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SourceProvenanceMetadata(BaseModel):
    """Structured provenance metadata contract for all ORCA telemetry."""
    source_id: str
    source_name: str
    source_type: Literal["LIVE_API", "OFFICIAL_SNAPSHOT", "DERIVED_CALCULATION", "MOCK_FALLBACK", "UNAVAILABLE"]
    coverage: str
    update_frequency: str
    fetched_at: Optional[datetime] = None
    is_live: bool = False
    is_mock: bool = False
    is_fallback: bool = False
    limitations: List[str] = Field(default_factory=list)


class DataSourceAdapter(ABC):
    """Unified base adapter for ORCA data sources."""

    def __init__(self, source_id: str, source_name: str):
        self.source_id = source_id
        self.source_name = source_name

    @abstractmethod
    def fetch(self, latitude: float, longitude: float, time_window: str = "current", **kwargs) -> Dict[str, Any]:
        """Fetch raw payload from underlying API, file snapshot, or mock generator."""
        pass

    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform provider payload into ORCA normalized dictionary schema."""
        pass

    @abstractmethod
    def validate(self, normalized_data: Dict[str, Any]) -> bool:
        """Validate normalized data against expected physical ranges and schema contracts."""
        pass

    @abstractmethod
    def get_provenance(self) -> SourceProvenanceMetadata:
        """Return standardized provenance metadata including live/mock status and limitations."""
        pass

    def is_available(self) -> bool:
        """Indicate whether the upstream data source is configured and accessible."""
        return True

    def cached_fetch(self, latitude: float, longitude: float, time_window: str = "current", **kwargs) -> Dict[str, Any]:
        """Template method: fetch -> normalize -> validate with provenance."""
        raw = self.fetch(latitude, longitude, time_window, **kwargs)
        normalized = self.normalize(raw)
        self.validate(normalized)
        normalized["_provenance"] = self.get_provenance().model_dump()
        return normalized
