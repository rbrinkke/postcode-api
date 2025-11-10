"""
Prometheus metrics endpoint for postcode-api.

This module provides the /metrics endpoint that Prometheus scrapes
to collect application metrics.
"""

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, REGISTRY

from src.core.logging_config import get_logger

logger = get_logger(__name__)

# Create router for metrics endpoints
metrics_router = APIRouter()


@metrics_router.get(
    "/metrics",
    tags=["Observability"],
    summary="Prometheus metrics endpoint",
    response_class=Response
)
async def metrics():
    """
    Prometheus metrics endpoint for scraping.

    This endpoint returns metrics in Prometheus text exposition format.
    Prometheus scrapes this endpoint periodically (default: every 15 seconds)
    to collect application metrics.

    Returns:
        Response with Prometheus metrics in text format

    Example metrics exposed:
        - http_requests_total{method="GET",endpoint="/postcode/{postcode}",status="200"} 42
        - http_request_duration_seconds_bucket{method="GET",endpoint="/postcode/{postcode}",le="0.1"} 40
        - postcode_lookups_total{result="found"} 38
        - cache_hit_ratio 0.85
        - database_query_duration_seconds_sum{operation="postcode_lookup"} 1.234
    """
    # Generate metrics in Prometheus format
    metrics_output = generate_latest(REGISTRY)

    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST
    )
