"""
Mock Server Middleware

Custom middleware for mock server functionality including
request logging, statistics tracking, and performance monitoring.
"""

import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger(__name__)


class MockLoggingMiddleware:
    """
    Pure ASGI middleware for request/response logging in mock server.

    Logs all requests with timing information and highlights that
    these are mock requests for easier debugging.
    """

    def __init__(self, app, log_requests: bool = True):
        self.app = app
        self.log_requests = log_requests

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.log_requests:
            return await self.app(scope, receive, send)

        start_time = time.time()
        request_path = scope.get("path", "")
        request_method = scope.get("method", "")

        # Log incoming request
        logger.info(
            f"🎭 MOCK REQUEST: {request_method} {request_path}",
            extra={"mock": True, "method": request_method, "path": request_path},
        )

        # Track response status
        response_status = None

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # Log response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"🎭 MOCK RESPONSE: {request_method} {request_path} - "
            f"Status: {response_status} - Duration: {duration_ms:.2f}ms",
            extra={
                "mock": True,
                "method": request_method,
                "path": request_path,
                "status": response_status,
                "duration_ms": duration_ms,
            },
        )


class MockStatisticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking request statistics.

    Tracks:
    - Total requests
    - Successful vs failed requests
    - Response times
    - Endpoint usage
    """

    def __init__(self, app, stats_tracker):
        super().__init__(app)
        self.stats_tracker = stats_tracker

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Track successful request
            self.stats_tracker.record_request(
                endpoint=request.url.path,
                duration_ms=duration_ms,
                success=response.status_code < 400,
                status_code=response.status_code,
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Track failed request
            self.stats_tracker.record_request(
                endpoint=request.url.path,
                duration_ms=duration_ms,
                success=False,
                status_code=500,
            )

            raise e


class MockPerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding performance headers to responses.

    Adds X-Processing-Time header with request duration.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Processing-Time"] = f"{duration_ms:.2f}ms"
        response.headers["X-Mock-Server"] = "true"

        return response


class MockDelayMiddleware(BaseHTTPMiddleware):
    """
    Middleware for simulating network delays.

    Adds artificial delays to responses for testing timeout handling.
    """

    def __init__(self, app, delay_simulator):
        super().__init__(app)
        self.delay_simulator = delay_simulator

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for override delay in query params
        delay_ms = request.query_params.get("delay_ms")
        override_delay = int(delay_ms) if delay_ms else None

        # Apply delay before processing request
        await self.delay_simulator.apply_delay(override_delay)

        response = await call_next(request)

        return response
