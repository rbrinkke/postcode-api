"""
API route handlers for postcode lookups and health checks.

All endpoints are documented with OpenAPI schemas and include proper
error handling with appropriate HTTP status codes.
"""

import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.models.responses import PostcodeResponse, HealthResponse, ErrorResponse
from src.db.repository import repository
from src.db.connection import DatabasePool
from src.core.logging_config import get_logger

logger = get_logger(__name__)

# Import Prometheus metrics (gracefully handle if not available)
try:
    from src.core.metrics import postcode_lookups_total
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Create API router
router = APIRouter()


@router.get(
    "/postcode/{postcode}",
    response_model=PostcodeResponse,
    responses={
        200: {
            "description": "Postcode found successfully",
            "model": PostcodeResponse
        },
        400: {
            "description": "Invalid postcode format",
            "model": ErrorResponse
        },
        404: {
            "description": "Postcode not found in database",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Lookup Dutch postcode",
    tags=["Postcode Lookup"]
)
async def get_postcode(postcode: str) -> PostcodeResponse:
    """
    Get GPS coordinates and city name for a Dutch postcode.

    Dutch postcodes consist of 6 characters:
    - 4 digits (area code)
    - 2 letters (sub-area)

    Examples: 1012AB, 3511AB, 9901EG

    The endpoint automatically normalizes input:
    - Removes spaces
    - Converts to uppercase
    - Validates format

    Returns:
        PostcodeResponse with coordinates and city name

    Raises:
        HTTPException 400: Invalid postcode format
        HTTPException 404: Postcode not found
        HTTPException 500: Database error
    """
    # Normalize postcode: uppercase, no spaces
    postcode = postcode.upper().strip().replace(" ", "")

    # Validate postcode format
    if len(postcode) != 6 or not (postcode[:4].isdigit() and postcode[4:].isalpha()):
        logger.warning("invalid_postcode_format", postcode=postcode)

        # Record invalid format metric
        if METRICS_AVAILABLE:
            postcode_lookups_total.labels(result="invalid_format").inc()

        raise HTTPException(
            status_code=400,
            detail=f"Invalid postcode format: {postcode}. Expected format: 1234AB (4 digits + 2 letters)"
        )

    # Query database (with caching)
    try:
        result = await repository.get_postcode(postcode)

        if not result:
            logger.info("postcode_not_found", postcode=postcode)
            raise HTTPException(
                status_code=404,
                detail=f"Postcode {postcode} not found in database"
            )

        logger.info(
            "postcode_lookup_successful",
            postcode=postcode,
            woonplaats=result["woonplaats"]
        )

        return PostcodeResponse(**result)

    except HTTPException:
        # Re-raise HTTP exceptions (400, 404)
        raise

    except Exception as e:
        logger.error(
            "database_error_postcode_lookup",
            postcode=postcode,
            error=str(e),
            error_type=type(e).__name__,
            stack_trace=traceback.format_exc()
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"}
    },
    summary="Health check",
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """
    Check if the service is healthy and database is accessible.

    Used by:
    - Docker healthcheck
    - Kubernetes liveness probes
    - Load balancers
    - Monitoring systems

    Returns:
        HealthResponse with status and database connection state

    Returns HTTP 503 if database is not accessible.
    """
    try:
        is_healthy = await DatabasePool.health_check()

        if not is_healthy:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "database": "disconnected"
                }
            )

        return HealthResponse(
            status="healthy",
            database="connected"
        )

    except Exception as e:
        logger.error(
            "health_check_exception",
            error=str(e),
            error_type=type(e).__name__,
            stack_trace=traceback.format_exc()
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "error",
                "detail": str(e)
            }
        )


@router.get(
    "/health/live",
    summary="Liveness probe",
    tags=["Health"]
)
async def liveness_probe() -> dict:
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the container is alive and running.
    Does NOT check database connectivity.

    Use this for:
    - Kubernetes livenessProbe
    - Container restart decisions
    """
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
    tags=["Health"]
)
async def readiness_probe() -> JSONResponse:
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    Checks database connectivity.

    Use this for:
    - Kubernetes readinessProbe
    - Load balancer decisions
    - Traffic routing
    """
    is_ready = await DatabasePool.health_check()

    if not is_ready:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "disconnected"}
        )

    return JSONResponse(
        status_code=200,
        content={"status": "ready", "database": "connected"}
    )
