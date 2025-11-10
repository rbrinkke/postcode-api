"""
Dutch Postcode Geocoding API - Main Application Entry Point

Professional FastAPI application for Dutch postcode to GPS coordinate lookups.

Features:
- Connection pooling for optimal database performance
- Response caching (90%+ faster for cached postcodes)
- Structured JSON logging
- Security headers
- Health checks (liveness & readiness)
- OpenAPI documentation

Architecture:
- Layered design: API → Repository → Database
- Dependency injection
- Separation of concerns
- Fully typed with Pydantic
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configuration first
from src.core.config import settings
from src.core.logging_config import setup_logging, get_logger
from src.core.middleware import (
    LoggingMiddleware,
    SecurityHeadersMiddleware,
    TraceIDMiddleware,
    PerformanceMiddleware
)
from src.db.connection import DatabasePool
from src.api.routes import router
from src.api.debug import debug_router

# Initialize logging system
setup_logging(debug=settings.is_debug_mode, json_logs=settings.use_json_logs)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.

    Startup:
    - Initialize database connection pool
    - Log configuration
    - Verify database connectivity

    Shutdown:
    - Close database connections
    - Log shutdown event
    """
    # Startup
    logger.info("=" * 60)
    logger.info(
        "application_starting",
        version=settings.api_version,
        cache_enabled=settings.enable_response_cache,
        cache_size=settings.cache_max_size,
        db_path=settings.get_db_path_for_env()
    )

    try:
        # Initialize database pool
        db_path = settings.get_db_path_for_env()
        await DatabasePool.initialize(
            db_path=db_path,
            cache_size=settings.db_cache_statements
        )

        logger.info("application_startup_complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("application_startup_failed", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("application_shutting_down")

    try:
        await DatabasePool.close()
        logger.info("application_shutdown_complete")

    except Exception as e:
        logger.error("application_shutdown_error", error=str(e))

    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware (if enabled)
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    logger.info("cors_enabled", origins=settings.cors_origins)

# Add performance tracking middleware (only in debug mode)
if settings.debug_mode:
    app.add_middleware(PerformanceMiddleware, enabled=True)
    logger.info("performance_tracking_enabled")

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add trace ID middleware (for request correlation)
app.add_middleware(TraceIDMiddleware)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include API routes
app.include_router(router)

# Include debug routes (only in development)
if not settings.production_mode:
    app.include_router(debug_router)
    logger.info(
        "debug_endpoints_enabled",
        debug_mode=settings.debug_mode,
        production_mode=settings.production_mode
    )

# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API information"
)
async def root():
    """
    Root endpoint with API information.

    Returns:
        API metadata and usage information
    """
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "documentation": "/docs",
        "health_check": "/health",
        "example_usage": "/postcode/3511AB"
    }


# Application info on startup
if __name__ == "__main__":
    import uvicorn

    logger.info("development_server_starting", host=settings.api_host, port=settings.api_port)

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
