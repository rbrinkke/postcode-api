"""
Debug endpoints for development and troubleshooting.

These endpoints provide runtime diagnostics, cache statistics, and system info.
IMPORTANT: Only available when debug_mode=True or production_mode=False.
"""

import sys
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException
from src.core.config import settings
from src.db.repository import repository
from src.db.connection import DatabasePool
from src.core.logging_config import get_logger

logger = get_logger(__name__)

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
    logger.info("cache_cleared_via_debug_endpoint")

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
    logger.info("cache_invalidated_via_debug", postcode=postcode)

    return {
        "status": "success",
        "postcode": postcode,
        "message": f"Cache entry for {postcode} invalidated",
        "timestamp": datetime.utcnow().isoformat()
    }


@debug_router.get("/config")
async def get_configuration():
    """
    Get current runtime configuration.
    
    Returns all settings with their current values.
    Useful for verifying configuration in different environments.
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")
    
    return {
        "database": {
            "path": settings.db_path,
            "cache_statements": settings.db_cache_statements
        },
        "cache": {
            "enabled": settings.enable_response_cache,
            "max_size": settings.cache_max_size,
            "ttl_seconds": settings.cache_ttl_seconds
        },
        "api": {
            "title": settings.api_title,
            "version": settings.api_version,
            "host": settings.api_host,
            "port": settings.api_port
        },
        "cors": {
            "enabled": settings.cors_enabled,
            "origins": settings.cors_origins,
            "allow_credentials": settings.cors_allow_credentials,
            "allow_methods": settings.cors_allow_methods
        },
        "logging": {
            "level": settings.log_level,
            "json": settings.log_json,
            "config_file": settings.log_config_file
        },
        "debug": {
            "debug_mode": settings.debug_mode,
            "production_mode": settings.production_mode
        },
        "health": {
            "enabled": settings.health_check_enabled
        }
    }


@debug_router.post("/log-level")
async def set_log_level(level: str):
    """
    Dynamically change log level without restart.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Example:
        POST /debug/log-level?level=DEBUG
    
    Returns:
        Confirmation of log level change
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")

    import logging

    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    level_upper = level.upper()

    if level_upper not in valid_levels:
        raise HTTPException(400, f"Invalid log level. Must be one of: {', '.join(valid_levels)}")

    # Set log level for our application loggers
    logging.getLogger("src").setLevel(getattr(logging, level_upper))

    # Update root logger as well
    logging.getLogger().setLevel(getattr(logging, level_upper))

    logger.info("log_level_changed_via_api", new_level=level_upper)

    return {
        "status": "success",
        "log_level": level_upper,
        "message": f"Log level changed to {level_upper}",
        "note": "Change is runtime only - restart will reset to config value",
        "timestamp": datetime.utcnow().isoformat()
    }


@debug_router.get("/log-level")
async def get_log_level():
    """
    Get current log level.
    
    Returns:
        Current log level for main loggers
    """
    if settings.production_mode:
        raise HTTPException(404, "Not found")
    
    import logging
    
    return {
        "root_logger": logging.getLevelName(logging.getLogger().level),
        "app_logger": logging.getLevelName(logging.getLogger("src").level),
        "config_default": settings.log_level,
        "timestamp": datetime.utcnow().isoformat()
    }
