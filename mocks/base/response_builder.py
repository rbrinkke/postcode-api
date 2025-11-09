"""
Response Builder

Utilities for constructing mock API responses.
Ensures consistency with production response formats.
"""

import asyncio
import random
from typing import Optional, Dict, Any
from datetime import datetime


class ResponseBuilder:
    """
    Build mock API responses matching production format.

    Handles response construction, delay simulation, and field generation.
    """

    def __init__(
        self, enable_delay: bool = False, min_delay_ms: int = 0, max_delay_ms: int = 100
    ):
        """
        Initialize response builder.

        Args:
            enable_delay: Whether to add artificial delays
            min_delay_ms: Minimum delay in milliseconds
            max_delay_ms: Maximum delay in milliseconds
        """
        self.enable_delay = enable_delay
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms

    async def maybe_add_delay(self, override_ms: Optional[int] = None) -> None:
        """
        Add artificial response delay if enabled.

        Args:
            override_ms: Optional specific delay in milliseconds
        """
        if override_ms is not None:
            delay_seconds = override_ms / 1000.0
        elif self.enable_delay:
            delay_ms = random.uniform(self.min_delay_ms, self.max_delay_ms)
            delay_seconds = delay_ms / 1000.0
        else:
            return

        await asyncio.sleep(delay_seconds)

    def build_postcode_response(
        self,
        postcode: str,
        lat: float,
        lon: float,
        woonplaats: str,
        **extra_fields,
    ) -> Dict[str, Any]:
        """
        Build postcode lookup response.

        Args:
            postcode: Dutch postcode (6 characters)
            lat: Latitude (WGS84)
            lon: Longitude (WGS84)
            woonplaats: City/town name
            **extra_fields: Additional fields to include

        Returns:
            Response dictionary matching production format
        """
        response = {
            "postcode": postcode,
            "lat": lat,
            "lon": lon,
            "woonplaats": woonplaats,
        }

        # Add any extra fields
        response.update(extra_fields)

        return response

    def build_health_response(
        self, status: str = "healthy", database: str = "connected", **extra_fields
    ) -> Dict[str, Any]:
        """
        Build health check response.

        Args:
            status: Overall health status
            database: Database connection status
            **extra_fields: Additional fields to include

        Returns:
            Health response dictionary
        """
        response = {"status": status, "database": database}

        response.update(extra_fields)

        return response

    def build_error_response(self, detail: str, **extra_fields) -> Dict[str, Any]:
        """
        Build error response.

        Args:
            detail: Error detail message
            **extra_fields: Additional error fields

        Returns:
            Error response dictionary
        """
        response = {"detail": detail}

        response.update(extra_fields)

        return response

    def build_stats_response(
        self,
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
        uptime_seconds: float,
        **extra_stats,
    ) -> Dict[str, Any]:
        """
        Build statistics response.

        Args:
            total_requests: Total number of requests
            successful_requests: Number of successful requests
            failed_requests: Number of failed requests
            uptime_seconds: Server uptime in seconds
            **extra_stats: Additional statistics

        Returns:
            Statistics response dictionary
        """
        response = {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (
                successful_requests / total_requests if total_requests > 0 else 0.0
            ),
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        response.update(extra_stats)

        return response

    def set_delay_config(
        self, enable: bool, min_ms: int = 0, max_ms: int = 100
    ) -> None:
        """
        Update delay configuration.

        Args:
            enable: Whether to enable delays
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        self.enable_delay = enable
        self.min_delay_ms = min_ms
        self.max_delay_ms = max_ms


class MockResponseFormatter:
    """Format mock responses with additional metadata"""

    @staticmethod
    def add_mock_metadata(response: Dict[str, Any], mock_id: str = "mock") -> Dict[str, Any]:
        """
        Add mock-specific metadata to response.

        Args:
            response: Original response dictionary
            mock_id: Mock server identifier

        Returns:
            Response with added metadata
        """
        response["_mock"] = {
            "source": mock_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        return response

    @staticmethod
    def add_cache_metadata(
        response: Dict[str, Any], cache_hit: bool, ttl_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add cache metadata to response (for testing cache behavior).

        Args:
            response: Original response dictionary
            cache_hit: Whether this was a cache hit
            ttl_seconds: Optional TTL value

        Returns:
            Response with cache metadata
        """
        cache_info = {"cache_hit": cache_hit}

        if ttl_seconds is not None:
            cache_info["ttl_seconds"] = ttl_seconds

        response["_cache"] = cache_info
        return response

    @staticmethod
    def add_timing_metadata(
        response: Dict[str, Any], processing_time_ms: float
    ) -> Dict[str, Any]:
        """
        Add timing metadata to response.

        Args:
            response: Original response dictionary
            processing_time_ms: Processing time in milliseconds

        Returns:
            Response with timing metadata
        """
        response["_timing"] = {"processing_time_ms": round(processing_time_ms, 2)}
        return response


def normalize_postcode(postcode: str) -> str:
    """
    Normalize Dutch postcode format.

    Args:
        postcode: Raw postcode input

    Returns:
        Normalized postcode (uppercase, no spaces)
    """
    return postcode.replace(" ", "").upper()


def validate_postcode_format(postcode: str) -> bool:
    """
    Validate Dutch postcode format.

    Args:
        postcode: Postcode to validate

    Returns:
        True if valid format (4 digits + 2 letters)
    """
    if len(postcode) != 6:
        return False

    area = postcode[:4]
    letters = postcode[4:]

    return area.isdigit() and letters.isalpha() and letters.isupper()


def is_valid_coordinate(lat: float, lon: float) -> bool:
    """
    Validate WGS84 coordinates.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        True if coordinates are within valid ranges
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180
