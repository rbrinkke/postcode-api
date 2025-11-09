"""
Mock Server Configuration

Provides configuration management for the mock server infrastructure.
All settings can be overridden via environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class MockSettings(BaseSettings):
    """Configuration for mock server behavior and features"""

    # Server settings
    mock_port: int = 8888
    mock_host: str = "0.0.0.0"
    mock_title: str = "Postcode API Mock Server"
    mock_description: str = "Production-grade mock server for Dutch postcode geocoding API"
    mock_version: str = "1.0.0"

    # Behavior settings
    enable_response_delay: bool = False
    min_delay_ms: int = 10
    max_delay_ms: int = 100

    # Error simulation
    error_simulation_enabled: bool = False
    error_rate: float = 0.05  # 5% error rate for random errors

    # Data settings
    mock_data_size: int = 500
    use_fixtures: bool = True
    fixtures_path: str = "mocks/fixtures"

    # Features
    enable_stateful_mode: bool = True
    enable_debug_endpoints: bool = True
    enable_statistics: bool = True

    # CORS settings
    cors_enabled: bool = True
    cors_origins: list[str] = ["*"]

    # Logging
    log_level: str = "INFO"
    log_requests: bool = True
    log_responses: bool = False

    # Cache settings (for mock cache simulation)
    enable_mock_cache: bool = True
    mock_cache_hit_rate: float = 0.75  # Simulated cache hit rate

    class Config:
        env_file = "mocks/config/.env.mock"
        env_prefix = "MOCK_"
        case_sensitive = False


# Global settings instance
_settings: Optional[MockSettings] = None


def get_mock_settings() -> MockSettings:
    """Get or create global mock settings instance"""
    global _settings
    if _settings is None:
        _settings = MockSettings()
    return _settings


def reload_mock_settings() -> MockSettings:
    """Reload settings from environment"""
    global _settings
    _settings = MockSettings()
    return _settings
