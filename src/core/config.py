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
    log_level: str = "INFO"
    log_json: bool = True

    # Health Check
    health_check_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

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
