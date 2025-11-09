"""
Postcode API Mock Server

Production-grade mock server for Dutch postcode geocoding API.
Provides exact endpoint parity with the production API for testing.

Usage:
    python mocks/postcode_mock.py
    # or
    uvicorn mocks.postcode_mock:app --reload --port 8888

Features:
    - Exact endpoint matching with production API
    - Realistic Dutch postcode data
    - Configurable error simulation
    - Response delay simulation
    - Request statistics tracking
    - Debug endpoints for testing
    - OpenAPI/Swagger documentation
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import JSONResponse

# Import production models to ensure exact compatibility
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.responses import PostcodeResponse, HealthResponse, ErrorResponse

# Import mock infrastructure
from mocks.base.mock_data_generator import DutchPostcodeGenerator, PostcodeData
from mocks.base.error_simulator import ErrorSimulator
from mocks.base.response_builder import (
    ResponseBuilder,
    normalize_postcode,
    validate_postcode_format,
)
from mocks.base.middleware import (
    MockLoggingMiddleware,
    MockStatisticsMiddleware,
    MockPerformanceMiddleware,
)
from mocks.base.mock_app import (
    create_mock_app,
    add_liveness_endpoint,
    add_readiness_endpoint,
    add_root_endpoint,
)
from mocks.config.mock_settings import get_mock_settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Mock Database
# ============================================================================


class MockPostcodeDatabase:
    """In-memory database for mock postcode data"""

    def __init__(self):
        self.postcodes: Dict[str, PostcodeData] = {}
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors_triggered = 0
        self.start_time = datetime.utcnow()

    def add(self, data: PostcodeData) -> None:
        """Add postcode to database"""
        self.postcodes[data.postcode] = data

    def add_batch(self, data_list: List[PostcodeData]) -> None:
        """Add multiple postcodes to database"""
        for data in data_list:
            self.add(data)

    async def lookup(self, postcode: str) -> Optional[PostcodeData]:
        """
        Look up postcode in database.

        Args:
            postcode: Normalized postcode (6 chars, uppercase)

        Returns:
            PostcodeData if found, None otherwise
        """
        self.request_count += 1

        result = self.postcodes.get(postcode)

        if result:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        return result

    def load_from_fixtures(self, fixtures_path: str) -> int:
        """
        Load postcode data from JSON fixture files.

        Args:
            fixtures_path: Path to fixtures directory

        Returns:
            Number of postcodes loaded
        """
        fixtures_dir = Path(fixtures_path)
        if not fixtures_dir.exists():
            logger.warning(f"Fixtures directory not found: {fixtures_path}")
            return 0

        loaded_count = 0

        for json_file in fixtures_dir.glob("postcodes_*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                for item in data:
                    postcode_data = PostcodeData(
                        postcode=item["postcode"],
                        lat=item["lat"],
                        lon=item["lon"],
                        woonplaats=item["woonplaats"],
                    )
                    self.add(postcode_data)
                    loaded_count += 1

                logger.info(f"Loaded {len(data)} postcodes from {json_file.name}")

            except Exception as e:
                logger.error(f"Error loading fixture {json_file}: {e}")

        return loaded_count

    def generate_mock_data(self, count: int) -> int:
        """
        Generate random mock postcode data.

        Args:
            count: Number of postcodes to generate

        Returns:
            Number of postcodes generated
        """
        generator = DutchPostcodeGenerator()
        data_list = generator.generate_batch(count)
        self.add_batch(data_list)

        logger.info(f"Generated {count} mock postcodes")
        return count

    def get_stats(self) -> Dict:
        """Get database statistics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "postcodes_count": len(self.postcodes),
            "total_requests": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / self.request_count if self.request_count > 0 else 0.0
            ),
            "uptime_seconds": uptime,
        }

    def clear(self) -> None:
        """Clear all postcodes from database"""
        self.postcodes.clear()

    def get_all_postcodes(self) -> List[str]:
        """Get list of all postcode keys"""
        return list(self.postcodes.keys())


# ============================================================================
# Statistics Tracker
# ============================================================================


class StatisticsTracker:
    """Track request statistics"""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times: List[float] = []
        self.endpoint_counts: Dict[str, int] = defaultdict(int)
        self.status_codes: Dict[int, int] = defaultdict(int)

    def record_request(
        self,
        endpoint: str,
        duration_ms: float,
        success: bool,
        status_code: int,
    ) -> None:
        """Record request metrics"""
        self.total_requests += 1
        self.endpoint_counts[endpoint] += 1
        self.status_codes[status_code] += 1
        self.response_times.append(duration_ms)

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        # Calculate percentiles
        sorted_times = sorted(self.response_times)
        count = len(sorted_times)

        def percentile(p: int) -> float:
            if count == 0:
                return 0.0
            index = int((p / 100) * count)
            return sorted_times[min(index, count - 1)]

        return {
            "uptime_seconds": uptime,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / max(self.total_requests, 1)
            ),
            "average_response_time_ms": (
                sum(self.response_times) / count if count > 0 else 0.0
            ),
            "p50_response_time_ms": percentile(50),
            "p95_response_time_ms": percentile(95),
            "p99_response_time_ms": percentile(99),
            "endpoint_breakdown": dict(self.endpoint_counts),
            "status_code_breakdown": dict(self.status_codes),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


# ============================================================================
# Application Setup
# ============================================================================

# Load settings
settings = get_mock_settings()

# Create FastAPI app
app = create_mock_app(
    title=settings.mock_title,
    description=settings.mock_description,
    version=settings.mock_version,
    settings=settings,
    cors_enabled=settings.cors_enabled,
    cors_origins=settings.cors_origins,
)

# Initialize components
mock_db = MockPostcodeDatabase()
error_simulator = ErrorSimulator(
    enabled=settings.error_simulation_enabled,
    error_rate=settings.error_rate,
)
response_builder = ResponseBuilder(
    enable_delay=settings.enable_response_delay,
    min_delay_ms=settings.min_delay_ms,
    max_delay_ms=settings.max_delay_ms,
)
stats_tracker = StatisticsTracker()

# Add middleware
app.add_middleware(MockPerformanceMiddleware)
if settings.enable_statistics:
    app.add_middleware(MockStatisticsMiddleware, stats_tracker=stats_tracker)
# Note: MockLoggingMiddleware is a pure ASGI middleware - could be added via app wrapping if needed


# ============================================================================
# Startup Event
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize mock database on startup"""
    logger.info("🎭 Starting Postcode API Mock Server")
    logger.info(f"Settings: {settings.model_dump()}")

    # Load fixtures if enabled
    if settings.use_fixtures:
        loaded = mock_db.load_from_fixtures(settings.fixtures_path)
        if loaded > 0:
            logger.info(f"✅ Loaded {loaded} postcodes from fixtures")

    # Generate additional mock data if needed
    current_count = len(mock_db.postcodes)
    if current_count < settings.mock_data_size:
        to_generate = settings.mock_data_size - current_count
        mock_db.generate_mock_data(to_generate)
        logger.info(f"✅ Generated {to_generate} additional mock postcodes")

    total_postcodes = len(mock_db.postcodes)
    logger.info(f"🎯 Mock database initialized with {total_postcodes} postcodes")
    logger.info(f"🚀 Server ready on http://{settings.mock_host}:{settings.mock_port}")


# ============================================================================
# Production API Endpoints (Exact Parity)
# ============================================================================


@app.get(
    "/postcode/{postcode}",
    response_model=PostcodeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Postcode not found"},
        422: {"model": ErrorResponse, "description": "Invalid postcode format"},
    },
    tags=["Postcode Lookup"],
)
async def lookup_postcode(
    postcode: str,
    simulate_error: Optional[str] = Query(None, description="Simulate error (404, 500, 503)"),
    delay_ms: Optional[int] = Query(None, description="Add response delay in milliseconds"),
) -> PostcodeResponse:
    """
    Look up Dutch postcode and return GPS coordinates and city name.

    This endpoint exactly matches the production API behavior.

    Query Parameters:
        - simulate_error: Force specific error (e.g., "404", "500")
        - delay_ms: Add artificial delay in milliseconds
    """
    # Apply delay if requested
    if delay_ms or settings.enable_response_delay:
        await response_builder.maybe_add_delay(delay_ms)

    # Check for error simulation
    try:
        await error_simulator.maybe_raise_error(key=postcode, error_type=simulate_error)
    except HTTPException:
        # Re-raise as-is for error simulation
        raise

    # Normalize postcode
    normalized = normalize_postcode(postcode)

    # Validate format
    if not validate_postcode_format(normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid postcode format. Expected: 1234AB (4 digits + 2 letters)",
        )

    # Look up in mock database
    result = await mock_db.lookup(normalized)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Postcode not found",
        )

    # Return response matching production format
    return PostcodeResponse(
        postcode=result.postcode,
        lat=result.lat,
        lon=result.lon,
        woonplaats=result.woonplaats,
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Matches production API health check.
    """
    return HealthResponse(
        status="healthy",
        database="connected",
    )


@app.get("/health/live", tags=["Health"])
async def liveness():
    """Kubernetes liveness probe (container is alive)"""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """Kubernetes readiness probe (ready to serve traffic)"""
    return {"status": "ready", "database": "connected"}


@app.get("/", tags=["Info"])
async def root():
    """API information endpoint"""
    return {
        "name": app.title,
        "version": app.version,
        "description": app.description,
        "type": "mock",
        "postcodes_available": len(mock_db.postcodes),
        "endpoints": {
            "postcode_lookup": "/postcode/{postcode}",
            "health": "/health",
            "docs": "/docs",
            "stats": "/mock/stats",
        },
    }


# ============================================================================
# Mock-Specific Debug Endpoints
# ============================================================================


@app.get("/mock/stats", tags=["Mock Admin"])
async def get_mock_stats():
    """
    Get comprehensive mock server statistics.

    Returns information about:
    - Request counts and success rates
    - Response time percentiles
    - Database statistics
    - Error simulation stats
    """
    return {
        "server": stats_tracker.get_stats(),
        "database": mock_db.get_stats(),
        "error_simulator": error_simulator.get_stats(),
    }


@app.get("/mock/data", tags=["Mock Admin"])
async def get_mock_data(limit: int = Query(100, description="Max postcodes to return")):
    """
    List available mock postcodes.

    Args:
        limit: Maximum number of postcodes to return
    """
    all_postcodes = mock_db.get_all_postcodes()

    return {
        "total_count": len(all_postcodes),
        "returned_count": min(limit, len(all_postcodes)),
        "postcodes": all_postcodes[:limit],
    }


@app.post("/mock/data/reload", tags=["Mock Admin"])
async def reload_mock_data():
    """Reload mock data from fixtures"""
    mock_db.clear()

    loaded = 0
    if settings.use_fixtures:
        loaded = mock_db.load_from_fixtures(settings.fixtures_path)

    if len(mock_db.postcodes) < settings.mock_data_size:
        to_generate = settings.mock_data_size - len(mock_db.postcodes)
        mock_db.generate_mock_data(to_generate)

    return {
        "status": "reloaded",
        "loaded_from_fixtures": loaded,
        "total_postcodes": len(mock_db.postcodes),
    }


@app.post("/mock/data/generate", tags=["Mock Admin"])
async def generate_mock_data(count: int = Query(100, description="Number to generate")):
    """Generate additional mock postcode data"""
    generated = mock_db.generate_mock_data(count)

    return {
        "status": "generated",
        "count": generated,
        "total_postcodes": len(mock_db.postcodes),
    }


@app.get("/mock/config", tags=["Mock Admin"])
async def get_mock_config():
    """Get current mock server configuration"""
    return settings.model_dump()


@app.post("/mock/errors/enable", tags=["Mock Admin"])
async def enable_error_simulation(error_rate: float = Query(0.05, description="Error rate 0-1")):
    """Enable error simulation with specified rate"""
    error_simulator.set_enabled(True)
    error_simulator.set_error_rate(error_rate)

    return {
        "status": "enabled",
        "error_rate": error_rate,
    }


@app.post("/mock/errors/disable", tags=["Mock Admin"])
async def disable_error_simulation():
    """Disable error simulation"""
    error_simulator.set_enabled(False)

    return {
        "status": "disabled",
    }


@app.post("/mock/delay/set", tags=["Mock Admin"])
async def set_response_delay(
    min_ms: int = Query(10, description="Min delay in ms"),
    max_ms: int = Query(100, description="Max delay in ms"),
):
    """Configure response delay simulation"""
    response_builder.set_delay_config(True, min_ms, max_ms)

    return {
        "status": "configured",
        "min_delay_ms": min_ms,
        "max_delay_ms": max_ms,
    }


@app.post("/mock/delay/disable", tags=["Mock Admin"])
async def disable_response_delay():
    """Disable response delay simulation"""
    response_builder.set_delay_config(False)

    return {
        "status": "disabled",
    }


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.mock_host,
        port=settings.mock_port,
        log_level=settings.log_level.lower(),
    )
