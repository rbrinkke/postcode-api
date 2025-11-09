"""
Mock App Factory

Factory function for creating FastAPI mock server applications
with consistent configuration and middleware setup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging

from mocks.config.mock_settings import MockSettings


def create_mock_app(
    title: str,
    description: str,
    version: str = "1.0.0",
    settings: Optional[MockSettings] = None,
    cors_enabled: bool = True,
    cors_origins: Optional[List[str]] = None,
) -> FastAPI:
    """
    Create a FastAPI mock server application with standard configuration.

    Args:
        title: API title
        description: API description
        version: API version
        settings: Optional MockSettings instance
        cors_enabled: Whether to enable CORS
        cors_origins: List of allowed CORS origins

    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware if enabled
    if cors_enabled:
        origins = cors_origins or ["*"]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Configure logging
    log_level = settings.log_level if settings else "INFO"
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    return app


def add_health_endpoint(app: FastAPI, custom_health_check=None):
    """
    Add standard health check endpoint to app.

    Args:
        app: FastAPI application
        custom_health_check: Optional custom health check function
    """

    @app.get("/health", tags=["Health"])
    async def health():
        """Standard health check endpoint"""
        if custom_health_check:
            return await custom_health_check()

        return {"status": "healthy", "database": "connected"}


def add_liveness_endpoint(app: FastAPI):
    """
    Add Kubernetes liveness probe endpoint.

    Args:
        app: FastAPI application
    """

    @app.get("/health/live", tags=["Health"])
    async def liveness():
        """Kubernetes liveness probe"""
        return {"status": "alive"}


def add_readiness_endpoint(app: FastAPI, ready_check=None):
    """
    Add Kubernetes readiness probe endpoint.

    Args:
        app: FastAPI application
        ready_check: Optional custom readiness check function
    """

    @app.get("/health/ready", tags=["Health"])
    async def readiness():
        """Kubernetes readiness probe"""
        if ready_check:
            is_ready = await ready_check()
            if not is_ready:
                from fastapi import status, HTTPException

                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service not ready",
                )

        return {"status": "ready", "database": "connected"}


def add_root_endpoint(app: FastAPI, api_info: Optional[dict] = None):
    """
    Add root endpoint with API information.

    Args:
        app: FastAPI application
        api_info: Optional custom API info dictionary
    """

    @app.get("/", tags=["Info"])
    async def root():
        """API information endpoint"""
        if api_info:
            return api_info

        return {
            "name": app.title,
            "version": app.version,
            "description": app.description,
            "docs": "/docs",
            "redoc": "/redoc",
        }
