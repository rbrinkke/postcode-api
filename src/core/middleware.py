"""
Custom ASGI middleware for logging and performance tracking.

Pure ASGI implementation (NOT BaseHTTPMiddleware) for optimal performance.
"""

import time
import uuid
from contextvars import ContextVar
from starlette.types import ASGIApp, Receive, Scope, Send, Message
from src.core.logging_config import get_logger
import structlog

# Context variable for performance timing
perf_context: ContextVar[dict] = ContextVar('perf_context', default=None)


class LoggingMiddleware:
    """
    Pure ASGI middleware for request/response logging with timing.

    This is implemented as pure ASGI middleware instead of BaseHTTPMiddleware
    to avoid performance overhead and streaming issues.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = get_logger(__name__)

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
            client_ip = scope.get("client", ["unknown"])[0] if scope.get("client") else "unknown"
            self.logger.info("request_started", method=method, path=path, client=client_ip)

        async def send_wrapper(message: Message) -> None:
            """Wrap send to capture response status and timing"""
            if message["type"] == "http.response.start":
                process_time = time.time() - start_time
                status_code = message.get("status", 0)

                if not is_health_check:
                    self.logger.info(
                        "request_completed",
                        method=method,
                        path=path,
                        status_code=status_code,
                        process_time_ms=round(process_time * 1000, 2)
                    )

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
    The trace ID is stored in structlog context and added to all logs.
    The response includes the X-Trace-ID header for external debugging.

    This enables:
    - Request tracing across the entire stack
    - Easy log filtering by trace ID
    - Distributed tracing support
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = get_logger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI request with trace ID"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract or generate trace ID
        trace_id = None
        headers = dict(scope.get("headers", []))

        # Check for existing X-Trace-ID header (or X-Correlation-ID)
        if b"x-trace-id" in headers:
            trace_id = headers[b"x-trace-id"].decode("utf-8")
        elif b"x-correlation-id" in headers:
            trace_id = headers[b"x-correlation-id"].decode("utf-8")

        # Generate new trace ID if not provided
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # Set trace ID in structlog context (for logging)
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            correlation_id=trace_id
        )

        async def send_wrapper(message: Message) -> None:
            """Add X-Trace-ID header to response"""
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-trace-id", trace_id.encode("utf-8")))
                headers_list.append((b"x-correlation-id", trace_id.encode("utf-8")))
                message["headers"] = headers_list

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Clear context after request
            structlog.contextvars.clear_contextvars()


class PerformanceMiddleware:
    """
    Middleware for detailed performance breakdown tracking.

    Tracks time spent in different components:
    - Middleware overhead
    - Route handler execution
    - Database queries (via repository)

    Performance data is stored in context variable and logged with request completion.
    Only enabled when debug_mode=True for minimal production overhead.
    """

    def __init__(self, app: ASGIApp, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled
        self.logger = get_logger(__name__)
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Track request performance"""
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return
        
        # Initialize performance context
        perf_data = {
            "request_start": time.perf_counter(),
            "middleware_time": 0.0,
            "handler_time": 0.0,
            "timings": []
        }
        perf_context.set(perf_data)
        
        middleware_start = time.perf_counter()
        
        async def send_wrapper(message: Message) -> None:
            """Capture final timing on response"""
            if message["type"] == "http.response.start":
                total_time = time.perf_counter() - perf_data["request_start"]
                
                # Log performance breakdown if path is not health check
                path = scope.get("path", "")
                if path not in ["/health", "/health/live", "/health/ready"]:
                    self.logger.debug(
                        "performance_breakdown",
                        path=path,
                        total_ms=round(total_time * 1000, 2),
                        timings=perf_data.get("timings", [])
                    )
            
            await send(message)
        
        # Track middleware overhead
        await self.app(scope, receive, send_wrapper)
        
        middleware_end = time.perf_counter()
        perf_data["middleware_time"] = middleware_end - middleware_start


def track_performance(component: str):
    """
    Context manager for tracking performance of specific components.
    
    Usage:
        with track_performance("database_query"):
            result = await db.query()
    
    Or as decorator:
        @track_performance("route_handler")
        async def my_route():
            ...
    """
    class PerformanceTracker:
        def __init__(self, name: str):
            self.name = name
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = time.perf_counter() - self.start_time
            perf_data = perf_context.get()
            if perf_data is not None:
                perf_data["timings"].append({
                    "component": self.name,
                    "duration_ms": round(elapsed * 1000, 2)
                })
        
        async def __aenter__(self):
            self.start_time = time.perf_counter()
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            elapsed = time.perf_counter() - self.start_time
            perf_data = perf_context.get()
            if perf_data is not None:
                perf_data["timings"].append({
                    "component": self.name,
                    "duration_ms": round(elapsed * 1000, 2)
                })
    
    return PerformanceTracker(component)
