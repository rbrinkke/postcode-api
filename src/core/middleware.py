"""
Custom ASGI middleware for logging and performance tracking.

Pure ASGI implementation (NOT BaseHTTPMiddleware) for optimal performance.
"""

import logging
import time
from starlette.types import ASGIApp, Receive, Scope, Send, Message


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
