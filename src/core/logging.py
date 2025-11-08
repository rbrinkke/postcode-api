"""
Logging configuration for structured JSON logging.

This module sets up centralized logging with JSON formatting for Docker/production.
Includes TraceIDFilter for request correlation.
"""

import logging
import sys
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger
from src.core.config import settings

# Context variable for trace ID (thread-safe, async-safe)
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='no-trace')


class TraceIDFilter(logging.Filter):
    """
    Logging filter that adds trace_id to every log record.

    The trace_id is retrieved from the context variable set by TraceIDMiddleware.
    This enables request correlation across the entire application stack.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace_id to the log record"""
        record.trace_id = trace_id_var.get()
        return True


def setup_logging() -> logging.Logger:
    """
    Configure structured JSON logging for the application.

    Returns:
        Logger instance for the application
    """
    # Create TraceID filter
    trace_filter = TraceIDFilter()

    # Create formatters
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(trace_id)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - [%(trace_id)s] - %(levelname)-8s - %(name)s - %(message)s',
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
    console_handler.addFilter(trace_filter)

    if settings.log_json:
        console_handler.setFormatter(json_formatter)
    else:
        # Simple format for local development
        console_handler.setFormatter(simple_formatter)

    root_logger.addHandler(console_handler)

    # Suppress uvicorn access logs (we use custom middleware)
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.access").propagate = False

    return logging.getLogger(__name__)


# Initialize logger on module import
logger = setup_logging()
