"""
Prometheus metrics definitions for postcode-api.

This module defines all Prometheus metrics for monitoring the postcode API service.
Metrics include HTTP request tracking, postcode lookup results, cache performance,
and database query performance.
"""

from prometheus_client import Counter, Histogram, Gauge, Info


# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests by method, endpoint and status code',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds by method and endpoint',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)


# ============================================================================
# Postcode Lookup Metrics
# ============================================================================

postcode_lookups_total = Counter(
    'postcode_lookups_total',
    'Total postcode lookup requests by result',
    ['result']  # Values: 'found', 'not_found', 'invalid_format'
)

postcode_lookup_duration_seconds = Histogram(
    'postcode_lookup_duration_seconds',
    'Postcode lookup duration in seconds including cache and database time',
    ['result'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)


# ============================================================================
# Cache Metrics
# ============================================================================

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations by result',
    ['operation']  # Values: 'hit', 'miss'
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio (hits / total requests)'
)

cache_size_current = Gauge(
    'cache_size_current',
    'Current number of entries in cache'
)

cache_size_max = Gauge(
    'cache_size_max',
    'Maximum cache size configured'
)


# ============================================================================
# Database Metrics
# ============================================================================

database_queries_total = Counter(
    'database_queries_total',
    'Total database queries by operation and status',
    ['operation', 'status']  # operation: 'postcode_lookup', status: 'success', 'error'
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds by operation',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)


# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    'postcode_api_info',
    'Postcode API application information'
)


# ============================================================================
# Helper Functions
# ============================================================================

def normalize_endpoint(path: str) -> str:
    """
    Normalize endpoint path to prevent label cardinality explosion.

    Converts dynamic paths like /postcode/1012AB to /postcode/{postcode}
    to avoid creating unlimited unique metric labels.

    Args:
        path: The request path

    Returns:
        Normalized path with parameters replaced
    """
    if path.startswith('/postcode/'):
        return '/postcode/{postcode}'
    return path


def set_app_info(version: str, environment: str = "production"):
    """
    Set application information metrics.

    Args:
        version: API version string
        environment: Environment name (production, development, etc.)
    """
    app_info.info({
        'version': version,
        'environment': environment,
        'service': 'postcode-api'
    })


def initialize_static_metrics(cache_max_size: int):
    """
    Initialize static gauge metrics that don't change during runtime.

    Args:
        cache_max_size: Maximum cache size configured
    """
    cache_size_max.set(cache_max_size)
