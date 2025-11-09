"""
Error Simulator

Provides configurable error simulation for testing error handling.
Supports probabilistic errors, forced errors, and various HTTP status codes.
"""

import random
from typing import Optional, Dict
from fastapi import HTTPException, status
from enum import Enum


class ErrorType(str, Enum):
    """Common error types for simulation"""

    NOT_FOUND = "404"
    INTERNAL_ERROR = "500"
    SERVICE_UNAVAILABLE = "503"
    BAD_REQUEST = "400"
    UNPROCESSABLE_ENTITY = "422"
    TIMEOUT = "timeout"
    DATABASE_ERROR = "database"


class ErrorSimulator:
    """
    Simulate various error conditions for testing.

    Supports:
    - Probabilistic errors (random based on error rate)
    - Forced errors (always fail for specific inputs)
    - Configurable error types
    - Statistics tracking
    """

    def __init__(self, enabled: bool = False, error_rate: float = 0.05):
        """
        Initialize error simulator.

        Args:
            enabled: Whether error simulation is enabled
            error_rate: Probability of triggering random errors (0.0-1.0)
        """
        self.enabled = enabled
        self.error_rate = max(0.0, min(1.0, error_rate))
        self.forced_errors: Dict[str, int] = {}
        self.errors_triggered = 0
        self.total_checks = 0

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable error simulation"""
        self.enabled = enabled

    def set_error_rate(self, rate: float) -> None:
        """
        Set error rate for probabilistic errors.

        Args:
            rate: Error rate between 0.0 and 1.0
        """
        self.error_rate = max(0.0, min(1.0, rate))

    def force_error_for_key(self, key: str, status_code: int) -> None:
        """
        Force specific key to always trigger an error.

        Args:
            key: Key to always fail (e.g., postcode)
            status_code: HTTP status code to return
        """
        self.forced_errors[key] = status_code

    def remove_forced_error(self, key: str) -> None:
        """Remove forced error for a key"""
        self.forced_errors.pop(key, None)

    def clear_forced_errors(self) -> None:
        """Clear all forced errors"""
        self.forced_errors.clear()

    def should_trigger_error(self) -> bool:
        """
        Determine if a random error should be triggered.

        Returns:
            True if error should be triggered based on error rate
        """
        self.total_checks += 1

        if not self.enabled:
            return False

        return random.random() < self.error_rate

    def get_random_error_type(self) -> int:
        """
        Get a random HTTP error status code.

        Returns:
            Random status code (404, 500, 503)
        """
        return random.choice([404, 500, 503])

    async def maybe_raise_error(
        self, key: Optional[str] = None, error_type: Optional[str] = None
    ) -> None:
        """
        Maybe raise an error based on configuration.

        Args:
            key: Optional key to check for forced errors
            error_type: Optional specific error type to simulate

        Raises:
            HTTPException: If error conditions are met
        """
        # Check for forced errors first
        if key and key in self.forced_errors:
            status_code = self.forced_errors[key]
            self.errors_triggered += 1
            raise self._create_exception(status_code, f"Forced error for: {key}")

        # Check for explicit error type request
        if error_type:
            self.errors_triggered += 1
            raise self._create_error_from_type(error_type)

        # Check for probabilistic errors
        if self.should_trigger_error():
            status_code = self.get_random_error_type()
            self.errors_triggered += 1
            raise self._create_exception(status_code, "Simulated random error")

    def _create_error_from_type(self, error_type: str) -> HTTPException:
        """
        Create exception from error type string.

        Args:
            error_type: Error type identifier

        Returns:
            HTTPException for the specified error type
        """
        if error_type == ErrorType.NOT_FOUND or error_type == "404":
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postcode not found (simulated error)",
            )
        elif error_type == ErrorType.INTERNAL_ERROR or error_type == "500":
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error (simulated error)",
            )
        elif error_type == ErrorType.SERVICE_UNAVAILABLE or error_type == "503":
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable (simulated error)",
            )
        elif error_type == ErrorType.BAD_REQUEST or error_type == "400":
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad request (simulated error)",
            )
        elif error_type == ErrorType.DATABASE_ERROR or error_type == "database":
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection error (simulated error)",
            )
        else:
            # Default to 500 for unknown error types
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unknown error type: {error_type}",
            )

    def _create_exception(self, status_code: int, detail: str) -> HTTPException:
        """
        Create HTTPException with given status code and detail.

        Args:
            status_code: HTTP status code
            detail: Error detail message

        Returns:
            HTTPException instance
        """
        return HTTPException(status_code=status_code, detail=detail)

    def get_stats(self) -> Dict:
        """
        Get error simulation statistics.

        Returns:
            Dictionary with error statistics
        """
        return {
            "enabled": self.enabled,
            "error_rate": self.error_rate,
            "total_checks": self.total_checks,
            "errors_triggered": self.errors_triggered,
            "trigger_rate": (
                self.errors_triggered / self.total_checks if self.total_checks > 0 else 0.0
            ),
            "forced_errors_count": len(self.forced_errors),
            "forced_errors": dict(self.forced_errors),
        }

    def reset_stats(self) -> None:
        """Reset error statistics"""
        self.errors_triggered = 0
        self.total_checks = 0


# Convenience functions for common error scenarios
def simulate_not_found(postcode: str) -> HTTPException:
    """Create 404 Not Found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Postcode {postcode} not found",
    )


def simulate_internal_error(message: str = "Internal server error") -> HTTPException:
    """Create 500 Internal Server Error exception"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message
    )


def simulate_database_error() -> HTTPException:
    """Create database connection error exception"""
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database connection error",
    )


def simulate_timeout_error() -> HTTPException:
    """Create timeout error exception"""
    return HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        detail="Request timeout",
    )


def simulate_validation_error(field: str, message: str) -> HTTPException:
    """Create validation error exception"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Validation error for {field}: {message}",
    )
