"""
Logging configuration for structured JSON logging.

This module sets up centralized logging with JSON formatting for Docker/production.
"""

import logging
import sys
from pythonjsonlogger import jsonlogger
from src.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Configure structured JSON logging for the application.

    Returns:
        Logger instance for the application
    """
    # Create JSON formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (stdout for Docker)
    console_handler = logging.StreamHandler(sys.stdout)

    if settings.log_json:
        console_handler.setFormatter(formatter)
    else:
        # Simple format for local development
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(simple_formatter)

    root_logger.addHandler(console_handler)

    # Suppress uvicorn access logs (we use custom middleware)
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.access").propagate = False

    return logging.getLogger(__name__)


# Initialize logger on module import
logger = setup_logging()
