"""
Custom ASGI middleware for logging and performance tracking.

Pure ASGI implementation (NOT BaseHTTPMiddleware) for optimal performance.
"""

import logging
import time
import uuid
from starlette.types import ASGIApp, Receive, Scope, Send, Message
from src.core.logging import trace_id_var


class LoggingMiddleware:
    """
    Pure ASGI middleware for request/response logging with timing.

    This is implemented as pure ASGI middleware instead of BaseHTTPMiddleware
    to avoid performance overhead and streaming issues.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI request"""
        # Only handle HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        path = scope.get("path", "")
        method = scope.get("method", "")

        # Skip verbose logging for health checks
        is_health_check = path in ["/health", "/health/live", "/health/ready"]

        if not is_health_check:
            self.logger.info("Request started", extra={
                "method": method,
                "path": path,
                "client": scope.get("client", ["unknown"])[0] if scope.get("client") else "unknown"
            })

        async def send_wrapper(message: Message) -> None:
            """Wrap send to capture response status and timing"""
            if message["type"] == "http.response.start":
                process_time = time.time() - start_time
                status_code = message.get("status", 0)

                if not is_health_check:
                    self.logger.info("Request completed", extra={
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "process_time_ms": round(process_time * 1000, 2)
                    })

            await send(message)

        await self.app(scope, receive, send_wrapper)


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses.

    Headers include:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Add security headers to responses"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Add security headers
                headers.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                ])

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)


class TraceIDMiddleware:
    """
    Middleware for request correlation via Trace IDs.

    Generates a unique trace ID for each request (or uses existing X-Trace-ID header).
    The trace ID is stored in a context variable and added to all logs.
    The response includes the X-Trace-ID header for external debugging.

    This enables:
    - Request tracing across the entire stack
    - Easy log filtering by trace ID
    - Distributed tracing support
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI request with trace ID"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract or generate trace ID
        trace_id = None
        headers = dict(scope.get("headers", []))

        # Check for existing X-Trace-ID header
        if b"x-trace-id" in headers:
            trace_id = headers[b"x-trace-id"].decode("utf-8")

        # Generate new trace ID if not provided
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # Set trace ID in context variable (for logging)
        trace_id_var.set(trace_id)

        async def send_wrapper(message: Message) -> None:
            """Add X-Trace-ID header to response"""
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-trace-id", trace_id.encode("utf-8")))
                message["headers"] = headers_list

            await send(message)

        await self.app(scope, receive, send_wrapper)
