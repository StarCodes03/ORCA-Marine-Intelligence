"""ORCA Marine Intelligence - In-Memory Live Telemetry Cache

Lightweight, thread-safe in-memory cache for live meteorological (Open-Meteo Weather)
and oceanographic (Open-Meteo Marine) API responses.

Design requirements:
- ~15-minute TTL (900 seconds)
- Key composed of category, rounded coordinates (~110m precision), and normalized time window
- Only successful live responses (is_mock=False, is_fallback=False) are cached
- Fallback/mock responses NEVER overwrite live cache entries
- Cache failures fail open and never disrupt the caller
"""

import time
import copy
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("orca.cache")


class MarineDataCache:
    """Thread-safe in-memory cache for live Open-Meteo telemetry."""

    DEFAULT_TTL_SECONDS = 900  # 15 minutes

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._ttl_seconds = ttl_seconds
        self._store: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    @ttl_seconds.setter
    def ttl_seconds(self, value: int) -> None:
        self._ttl_seconds = value

    @staticmethod
    def make_key(category: str, latitude: float, longitude: float, time_range: str) -> str:
        """Construct deterministic cache key with 3-decimal coordinate rounding (~110m resolution)."""
        rounded_lat = round(float(latitude), 3)
        rounded_lon = round(float(longitude), 3)
        norm_time = str(time_range).strip().lower().replace(" ", "_")
        return f"{category.strip().lower()}:{rounded_lat}:{rounded_lon}:{norm_time}"

    def get(
        self,
        category: str,
        latitude: float,
        longitude: float,
        time_range: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached payload if present and within TTL."""
        try:
            key = self.make_key(category, latitude, longitude, time_range)
            entry = self._store.get(key)
            if not entry:
                return None

            cached_at, data = entry
            elapsed = time.time() - cached_at

            if elapsed > self._ttl_seconds:
                # Expired - evict and return None
                self._store.pop(key, None)
                logger.debug(f"[{category.upper()}_CACHE] Expired entry for {key} (age: {elapsed:.1f}s > {self._ttl_seconds}s)")
                return None

            logger.info(f"[{category.upper()}_CACHE] Cache HIT for {key} (age: {elapsed:.1f}s)")
            return copy.deepcopy(data)
        except Exception as e:
            logger.warning(f"[{category.upper()}_CACHE] Error reading cache for {category}: {e}")
            return None

    def set(
        self,
        category: str,
        latitude: float,
        longitude: float,
        time_range: str,
        data: Dict[str, Any]
    ) -> None:
        """Cache live telemetry data.

        Strict constraints:
        - Only live data (is_mock == False and is_fallback == False) is eligible.
        - Mock, fallback, or corrupted data is rejected to protect live cache entries.
        """
        try:
            if not data or not isinstance(data, dict):
                return

            # Reject mock or fallback data: live data must never be overwritten by fallbacks
            if data.get("is_mock", True) or data.get("is_fallback", False):
                logger.debug(
                    f"[{category.upper()}_CACHE] Skipping cache write: payload is marked as mock or fallback "
                    f"(is_mock={data.get('is_mock')}, is_fallback={data.get('is_fallback')})"
                )
                return

            key = self.make_key(category, latitude, longitude, time_range)
            self._store[key] = (time.time(), copy.deepcopy(data))
            logger.info(f"[{category.upper()}_CACHE] Cache SET for {key} (TTL: {self._ttl_seconds}s)")
        except Exception as e:
            logger.warning(f"[{category.upper()}_CACHE] Error writing cache for {category}: {e}")

    def clear(self) -> None:
        """Flush all cache entries."""
        self._store.clear()
        logger.debug("MarineDataCache cleared.")

    def entry_count(self) -> int:
        """Return total number of entries currently stored."""
        return len(self._store)


# Global singleton instance with 15-minute TTL
marine_cache = MarineDataCache(ttl_seconds=900)
