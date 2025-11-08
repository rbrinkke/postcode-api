"""
Debug endpoints for development and troubleshooting.

These endpoints provide runtime diagnostics, cache statistics, and system info.
IMPORTANT: Only available when debug_mode=True or production_mode=False.
"""

import logging
import sys
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException
from src.core.config import settings
from src.db.repository import repository
from src.db.connection import DatabasePool

logger = logging.getLogger(__name__)

# Create debug router (conditionally enabled)
debug_router = APIRouter(
    prefix="/debug",
    tags=["Debug & Diagnostics"],
    include_in_schema=not settings.production_mode  # Hide in production docs
)

# Track application start time
_start_time = time.time()


@debug_router.get("/cache-stats")
async def cache_statistics():
    """
    Get cache performance statistics.

    Returns:
        Cache metrics including hit rate, size, and configuration

    Example Response:
        {
          "cache": {
            "enabled": true,
            "hits": 1234,
            "misses": 56,
            "hit_rate": 0.957,
            "size": 456,
            "max_size": 10000,
            "ttl_seconds": 86400
          },
          "timestamp": "2025-11-08T17:30:00.123456"
        }
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")

    stats = repository.get_cache_stats()

    return {
        "cache": stats,
        "timestamp": datetime.utcnow().isoformat(),
        "cache_enabled": settings.enable_response_cache
    }


@debug_router.get("/metrics")
async def performance_metrics():
    """
    Get API performance metrics and system information.

    Returns:
        Performance metrics and system status

    Example Response:
        {
          "uptime_seconds": 3600.5,
          "cache": {
            "hit_rate": 0.957,
            "size": 456
          },
          "database": {
            "connected": true,
            "path": "/path/to/db.sqlite"
          },
          "config": {
            "log_level": "DEBUG",
            "cache_enabled": true
          }
        }
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")

    cache_stats = repository.get_cache_stats()
    db_healthy = await DatabasePool.health_check()
    uptime = time.time() - _start_time

    return {
        "uptime_seconds": round(uptime, 2),
        "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        "cache": {
            "enabled": cache_stats.get("enabled", False),
            "hit_rate": cache_stats.get("hit_rate", 0.0),
            "size": cache_stats.get("size", 0),
            "max_size": cache_stats.get("max_size", 0)
        },
        "database": {
            "connected": db_healthy,
            "path": settings.db_path
        },
        "config": {
            "log_level": settings.log_level,
            "cache_enabled": settings.enable_response_cache,
            "debug_mode": settings.debug_mode,
            "production_mode": settings.production_mode
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@debug_router.get("/health/detailed")
async def health_detailed():
    """
    Detailed health check with comprehensive system information.

    Returns:
        Comprehensive health status including config, cache, database, and system info

    Example Response:
        {
          "status": "healthy",
          "database": {
            "connected": true,
            "path": "/path/to/db.sqlite"
          },
          "cache": {
            "enabled": true,
            "hit_rate": 0.957
          },
          "system": {
            "python_version": "3.11.4",
            "platform": "Linux"
          }
        }
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")

    cache_stats = repository.get_cache_stats()
    db_healthy = await DatabasePool.health_check()
    uptime = time.time() - _start_time

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": {
            "connected": db_healthy,
            "pool_initialized": DatabasePool.is_initialized(),
            "path": settings.get_db_path_for_env()
        },
        "cache": {
            "enabled": settings.enable_response_cache,
            "hit_rate": cache_stats.get("hit_rate", 0.0),
            "size": cache_stats.get("size", 0),
            "max_size": settings.cache_max_size,
            "ttl_seconds": settings.cache_ttl_seconds,
            "total_hits": cache_stats.get("hits", 0),
            "total_misses": cache_stats.get("misses", 0)
        },
        "config": {
            "api_version": settings.api_version,
            "log_level": settings.log_level,
            "log_json": settings.log_json,
            "debug_mode": settings.debug_mode,
            "production_mode": settings.production_mode,
            "cors_enabled": settings.cors_enabled
        },
        "system": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "uptime_seconds": round(uptime, 2),
            "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@debug_router.post("/cache/clear")
async def clear_cache():
    """
    Clear all cached postcodes.

    Use this to force fresh database queries for all subsequent requests.
    Useful for testing or when cache becomes stale.

    Returns:
        Confirmation of cache clear operation
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")

    repository.clear_cache()
    logger.info("Cache cleared via debug endpoint")

    return {
        "status": "success",
        "message": "Cache cleared successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@debug_router.post("/cache/invalidate/{postcode}")
async def invalidate_postcode(postcode: str):
    """
    Invalidate a specific postcode in the cache.

    Args:
        postcode: Dutch postcode to invalidate (e.g., "3511AB")

    Returns:
        Confirmation of invalidation
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")

    postcode = postcode.upper().strip().replace(" ", "")
    repository.invalidate_postcode(postcode)
    logger.info(f"Invalidated cache for postcode: {postcode}")

    return {
        "status": "success",
        "postcode": postcode,
        "message": f"Cache entry for {postcode} invalidated",
        "timestamp": datetime.utcnow().isoformat()
    }
