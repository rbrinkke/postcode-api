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

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configuration first
from src.core.config import settings
from src.core.logging import setup_logging
from src.core.middleware import LoggingMiddleware, SecurityHeadersMiddleware
from src.db.connection import DatabasePool
from src.api.routes import router

# Initialize logging
logger = setup_logging()


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
    logger.info("Starting Dutch Postcode API", extra={
        "version": settings.api_version,
        "cache_enabled": settings.enable_response_cache,
        "cache_size": settings.cache_max_size,
        "db_path": settings.get_db_path_for_env()
    })

    try:
        # Initialize database pool
        db_path = settings.get_db_path_for_env()
        await DatabasePool.initialize(
            db_path=db_path,
            cache_size=settings.db_cache_statements
        )

        logger.info("Application startup complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("Failed to start application", extra={"error": str(e)})
        raise

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("Shutting down Dutch Postcode API")

    try:
        await DatabasePool.close()
        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error("Error during shutdown", extra={"error": str(e)})

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
    logger.info("CORS enabled", extra={"origins": settings.cors_origins})

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include API routes
app.include_router(router)

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

    logger.info("Starting development server")

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
