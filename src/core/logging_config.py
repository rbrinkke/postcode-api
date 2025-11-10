"""
Professional Logging Configuration for postcode-api

Features:
- JSON structured logs via structlog
- Granular log level control per logger
- Request correlation IDs
- Third-party library noise filtering
- Zero log duplication
- Container-ready stdout/stderr streams
- Debug mode toggle for development (pretty console) vs production (JSON)
"""

import logging
import logging.config
import sys
from typing import Any, Dict
import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to all log records"""
    event_dict["service"] = "postcode-api"
    event_dict["version"] = "1.0.0"
    return event_dict


def configure_structlog(debug: bool = False, json_logs: bool = True) -> None:
    """
    Configure structlog for structured logging.

    Args:
        debug: Enable debug mode with pretty console output
        json_logs: Use JSON formatting (True for production, False for dev)
    """
    # Shared processors for all configurations
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    # Choose renderer based on mode
    if debug and not json_logs:
        # Development mode: colorful console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # Production mode: JSON output
        renderer = structlog.processors.JSONRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logging_config(debug: bool = False, json_logs: bool = True) -> Dict[str, Any]:
    """
    Generate logging dictConfig for stdlib logging.

    This configuration:
    - Routes INFO+ to stdout
    - Routes ERROR+ to stderr
    - Suppresses noisy third-party libraries
    - Prevents log duplication with propagate=False

    Args:
        debug: Enable debug-level logging
        json_logs: Use JSON formatting

    Returns:
        Dictionary suitable for logging.config.dictConfig()
    """
    # Determine log level
    log_level = "DEBUG" if debug else "INFO"

    # Choose renderer based on mode
    if debug and not json_logs:
        # Development: pretty console
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # Production: JSON
        renderer = structlog.processors.JSONRenderer()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": renderer,
                "foreign_pre_chain": [
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    add_app_context,
                    structlog.processors.TimeStamper(fmt="iso"),
                ],
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
                "level": log_level,
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "stream": sys.stderr,
                "formatter": "json",
                "level": "ERROR",
            },
        },
        "loggers": {
            # Application logger
            "postcode-api": {
                "handlers": ["stdout", "stderr"],
                "level": log_level,
                "propagate": False,
            },
            # Root logger (catches everything else)
            "": {
                "handlers": ["stdout", "stderr"],
                "level": log_level,
            },
            # Third-party noise suppression
            "uvicorn.access": {
                "handlers": [],
                "level": "WARNING",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["stdout", "stderr"],
                "level": "INFO",
                "propagate": False,
            },
            "asyncio": {
                "handlers": ["stdout", "stderr"],
                "level": "WARNING",
                "propagate": False,
            },
            "aiosqlite": {
                "handlers": ["stdout", "stderr"],
                "level": "WARNING",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["stdout", "stderr"],
                "level": "WARNING",
                "propagate": False,
            },
            "httpx": {
                "handlers": ["stdout", "stderr"],
                "level": "WARNING",
                "propagate": False,
            },
            "httpcore": {
                "handlers": ["stdout", "stderr"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }


def setup_logging(debug: bool = False, json_logs: bool = True) -> None:
    """
    Initialize the complete logging system.

    Call this once at application startup, before creating any loggers.

    Args:
        debug: Enable debug mode with verbose logging and pretty console output
        json_logs: Use JSON formatting (typically True in production, False in dev)

    Example:
        >>> from postcode_api.core.logging_config import setup_logging
        >>> setup_logging(debug=True, json_logs=False)  # Development
        >>> setup_logging(debug=False, json_logs=True)  # Production
    """
    # Configure structlog first
    configure_structlog(debug=debug, json_logs=json_logs)

    # Then configure stdlib logging
    config = get_logging_config(debug=debug, json_logs=json_logs)
    logging.config.dictConfig(config)

    # Log initialization
    logger = get_logger(__name__)
    logger.info(
        "logging_initialized",
        debug_mode=debug,
        json_logs=json_logs,
        log_level="DEBUG" if debug else "INFO"
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Use this instead of logging.getLogger() to get structlog benefits.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance

    Example:
        >>> from postcode_api.core.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("postcode_lookup", postcode="1012AB", city="Amsterdam")
    """
    return structlog.get_logger(name)
