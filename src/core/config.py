"""
Configuration management using Pydantic Settings.

All configuration is centralized here with type validation and environment variable support.
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with validation.

    Environment variables override defaults.
    Example: DB_PATH=/custom/path uvicorn ...
    """

    # Database Configuration
    db_path: str = "/opt/postcode/geodata/bag.sqlite"
    db_cache_statements: int = 100

    # Performance & Caching
    enable_response_cache: bool = True
    cache_max_size: int = 10000
    cache_ttl_seconds: int = 86400  # 24 hours

    # API Configuration
    api_title: str = "Dutch Postcode Geocoding API"
    api_description: str = "Fast postcode to GPS coordinate lookup for Dutch postcodes"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 7777

    # CORS Configuration
    cors_enabled: bool = True
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = False
    cors_allow_methods: List[str] = ["GET", "HEAD", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]

    # Logging Configuration
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_json: bool = True    # JSON logs (prod) vs pretty console (dev)
    debug: bool = False      # Enable debug mode features

    # Debug & Development
    debug_mode: bool = False  # Enable debug endpoints and features
    production_mode: bool = False  # Production optimizations (disables debug endpoints)

    # Health Check
    health_check_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def is_debug_mode(self) -> bool:
        """
        Check if debug mode is enabled.

        Debug mode is enabled when either debug=True or log_level=DEBUG.
        """
        return self.debug or self.log_level.upper() == "DEBUG"

    @property
    def use_json_logs(self) -> bool:
        """
        Determine whether to use JSON logs.

        In debug mode: respects log_json setting (allows override)
        In production: always uses JSON logs
        """
        if self.debug:
            return self.log_json  # Allow override in dev
        return True  # Always JSON in production

    def get_db_path_for_env(self) -> str:
        """
        Get database path, checking if file exists.
        Falls back to sample database for development.
        """
        if os.path.exists(self.db_path):
            return self.db_path

        # Check for sample database in local development
        sample_db = "/home/user/postcode-api/geodata/bag-sample.sqlite"
        if os.path.exists(sample_db):
            return sample_db

        # Return original path (will fail with clear error if not found)
        return self.db_path


# Global settings instance
settings = Settings()
