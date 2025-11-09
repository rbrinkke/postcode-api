"""
Mock Postcode Repository

Drop-in replacement for PostcodeRepository for unit testing.
Provides in-memory mock data without requiring SQLite database.
"""

from typing import Dict, Optional
import json
from pathlib import Path

# Import production models for compatibility
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mocks.base.mock_data_generator import DutchPostcodeGenerator, PostcodeData
from mocks.base.response_builder import normalize_postcode, validate_postcode_format


class MockPostcodeRepository:
    """
    Mock implementation of PostcodeRepository for testing.

    Provides same interface as production repository but uses
    in-memory data instead of SQLite database.

    Usage:
        >>> repo = MockPostcodeRepository()
        >>> repo.add_mock_postcode("1012AB", 52.374, 4.891, "Amsterdam")
        >>> result = await repo.get_postcode("1012AB")
        >>> print(result)  # {'postcode': '1012AB', 'lat': 52.374, ...}
    """

    def __init__(self, mock_data: Optional[Dict[str, PostcodeData]] = None):
        """
        Initialize mock repository.

        Args:
            mock_data: Optional pre-populated mock data dict
        """
        self.data: Dict[str, PostcodeData] = mock_data or {}
        self.call_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_enabled = True
        self.should_raise_error = False
        self.error_message = "Mock repository error"

    def add_mock_postcode(
        self, postcode: str, lat: float, lon: float, woonplaats: str
    ) -> None:
        """
        Add mock postcode data.

        Args:
            postcode: Dutch postcode (e.g., "1012AB")
            lat: Latitude (WGS84)
            lon: Longitude (WGS84)
            woonplaats: City name
        """
        normalized = normalize_postcode(postcode)
        self.data[normalized] = PostcodeData(
            postcode=normalized, lat=lat, lon=lon, woonplaats=woonplaats
        )

    def load_fixtures(self, fixtures_path: str = "mocks/fixtures") -> int:
        """
        Load mock data from fixture files.

        Args:
            fixtures_path: Path to fixtures directory

        Returns:
            Number of postcodes loaded
        """
        fixtures_dir = Path(fixtures_path)
        loaded_count = 0

        if not fixtures_dir.exists():
            return 0

        for json_file in fixtures_dir.glob("postcodes_*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                for item in data:
                    self.add_mock_postcode(
                        item["postcode"],
                        item["lat"],
                        item["lon"],
                        item["woonplaats"],
                    )
                    loaded_count += 1

            except Exception:
                continue

        return loaded_count

    def generate_mock_data(self, count: int = 100) -> None:
        """
        Generate random mock postcode data.

        Args:
            count: Number of postcodes to generate
        """
        generator = DutchPostcodeGenerator()
        data_list = generator.generate_batch(count)

        for data in data_list:
            self.data[data.postcode] = data

    async def get_postcode(self, postcode: str) -> Optional[Dict]:
        """
        Mock postcode lookup.

        Args:
            postcode: Postcode to look up (will be normalized)

        Returns:
            Dictionary with postcode data or None if not found
        """
        self.call_count += 1

        # Simulate error if configured
        if self.should_raise_error:
            raise Exception(self.error_message)

        # Normalize postcode (match production behavior)
        normalized = normalize_postcode(postcode)

        # Validation (match production behavior)
        if not validate_postcode_format(normalized):
            return None

        # Look up in mock data
        data = self.data.get(normalized)

        if data:
            self.cache_hits += 1
            return {
                "postcode": data.postcode,
                "lat": data.lat,
                "lon": data.lon,
                "woonplaats": data.woonplaats,
            }
        else:
            self.cache_misses += 1
            return None

    async def get_cache_stats(self) -> Dict:
        """
        Mock cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.cache_hits + self.cache_misses

        return {
            "enabled": self.cache_enabled,
            "hit_rate": (
                self.cache_hits / total_requests if total_requests > 0 else 0.0
            ),
            "size": len(self.data),
            "max_size": 10000,
            "ttl_seconds": 86400,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
        }

    def clear_mock_data(self) -> None:
        """Clear all mock data"""
        self.data.clear()

    def reset_stats(self) -> None:
        """Reset call statistics"""
        self.call_count = 0
        self.cache_hits = 0
        self.cache_misses = 0

    def set_error_mode(self, should_error: bool, message: str = "Mock error") -> None:
        """
        Configure repository to raise errors.

        Args:
            should_error: Whether to raise errors on queries
            message: Error message to use
        """
        self.should_raise_error = should_error
        self.error_message = message

    def get_stats(self) -> Dict:
        """
        Get repository statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "call_count": self.call_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_postcodes": len(self.data),
        }


def create_mock_repository_with_fixtures() -> MockPostcodeRepository:
    """
    Create mock repository pre-loaded with fixture data.

    Returns:
        MockPostcodeRepository with fixture data loaded
    """
    repo = MockPostcodeRepository()
    repo.load_fixtures()
    return repo


def create_mock_repository_with_generated_data(
    count: int = 100,
) -> MockPostcodeRepository:
    """
    Create mock repository with generated data.

    Args:
        count: Number of postcodes to generate

    Returns:
        MockPostcodeRepository with generated data
    """
    repo = MockPostcodeRepository()
    repo.generate_mock_data(count)
    return repo
