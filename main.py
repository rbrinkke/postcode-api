import os
import sys
import time
import uuid
import aiosqlite
import psutil
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, List
from statistics import mean, median

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from starlette.types import ASGIApp, Receive, Scope, Send, Message
import structlog

# Import logging configuration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.core.logging_config import setup_logging, get_logger
from src.core.config import settings

# Initialize logging system
setup_logging(debug=settings.is_debug_mode, json_logs=settings.use_json_logs)
logger = get_logger(__name__)

# Metrics Collector - tracks all system and application metrics
class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.status_codes = {}
        self.response_times = deque(maxlen=1000)  # Last 1000 requests
        self.recent_requests = deque(maxlen=50)    # Last 50 requests for display
        self.recent_errors = deque(maxlen=20)      # Last 20 errors
        self.slow_queries = deque(maxlen=20)       # Slowest queries
        self.postcode_requests = {}                # Count per postcode
        self.endpoint_stats = {}                   # Stats per endpoint

    def record_request(self, method: str, path: str, status_code: int,
                      response_time: float, error: Optional[str] = None,
                      postcode: Optional[str] = None):
        """Record a request with all its metrics"""
        self.request_count += 1

        # Track status codes
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

        # Track errors
        if status_code >= 400:
            self.error_count += 1
            self.recent_errors.append({
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'path': path,
                'status': status_code,
                'error': error,
                'response_time': response_time
            })

        # Track response times
        self.response_times.append(response_time)

        # Track slow queries (> 100ms)
        if response_time > 100:
            self.slow_queries.append({
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'path': path,
                'response_time': response_time,
                'postcode': postcode
            })

        # Track recent requests
        self.recent_requests.append({
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'path': path,
            'status': status_code,
            'response_time': response_time
        })

        # Track postcode popularity
        if postcode:
            self.postcode_requests[postcode] = self.postcode_requests.get(postcode, 0) + 1

        # Track per-endpoint stats
        endpoint_key = f"{method} {path}"
        if endpoint_key not in self.endpoint_stats:
            self.endpoint_stats[endpoint_key] = {
                'count': 0,
                'errors': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }

        stats = self.endpoint_stats[endpoint_key]
        stats['count'] += 1
        stats['total_time'] += response_time
        stats['min_time'] = min(stats['min_time'], response_time)
        stats['max_time'] = max(stats['max_time'], response_time)
        if status_code >= 400:
            stats['errors'] += 1

    def get_metrics(self) -> Dict:
        """Get all collected metrics"""
        uptime = time.time() - self.start_time
        response_times_list = list(self.response_times)

        # Calculate percentiles
        percentiles = {}
        if response_times_list:
            sorted_times = sorted(response_times_list)
            percentiles = {
                'p50': sorted_times[int(len(sorted_times) * 0.5)] if sorted_times else 0,
                'p95': sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0,
                'p99': sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0,
            }

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Get database size if exists
        db_size = 0
        try:
            if os.path.exists(DB_PATH):
                db_size = os.path.getsize(DB_PATH)
        except:
            pass

        return {
            'system': {
                'uptime_seconds': round(uptime, 2),
                'uptime_formatted': self._format_uptime(uptime),
                'cpu_percent': round(cpu_percent, 2),
                'memory_used_mb': round(memory.used / 1024 / 1024, 2),
                'memory_total_mb': round(memory.total / 1024 / 1024, 2),
                'memory_percent': round(memory.percent, 2),
                'disk_used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                'disk_percent': round(disk.percent, 2),
                'db_size_mb': round(db_size / 1024 / 1024, 2),
                'db_path': DB_PATH
            },
            'requests': {
                'total': self.request_count,
                'errors': self.error_count,
                'success_rate': round((1 - self.error_count / max(self.request_count, 1)) * 100, 2),
                'requests_per_minute': round(self.request_count / (uptime / 60), 2) if uptime > 0 else 0,
                'status_codes': dict(sorted(self.status_codes.items()))
            },
            'performance': {
                'avg_response_time': round(mean(response_times_list), 2) if response_times_list else 0,
                'median_response_time': round(median(response_times_list), 2) if response_times_list else 0,
                'min_response_time': round(min(response_times_list), 2) if response_times_list else 0,
                'max_response_time': round(max(response_times_list), 2) if response_times_list else 0,
                **percentiles
            },
            'recent_requests': list(self.recent_requests),
            'recent_errors': list(self.recent_errors),
            'slow_queries': sorted(list(self.slow_queries), key=lambda x: x['response_time'], reverse=True),
            'top_postcodes': sorted(
                [{'postcode': k, 'count': v} for k, v in self.postcode_requests.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10],
            'endpoints': [
                {
                    'endpoint': k,
                    'count': v['count'],
                    'errors': v['errors'],
                    'avg_time': round(v['total_time'] / v['count'], 2),
                    'min_time': round(v['min_time'], 2),
                    'max_time': round(v['max_time'], 2)
                }
                for k, v in self.endpoint_stats.items()
            ]
        }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m {secs}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

# Global metrics collector
metrics = MetricsCollector()

# Response model
class PostcodeResponse(BaseModel):
    postcode: str = Field(..., description="Dutch postcode (e.g., 1012AB)")
    lat: float = Field(..., description="Latitude in WGS84")
    lon: float = Field(..., description="Longitude in WGS84") 
    woonplaats: str = Field(..., description="City/town name")

# Database configuration (use settings from config)
DB_PATH = settings.get_db_path_for_env()

# Pure ASGI middleware for logging with correlation IDs (NOT BaseHTTPMiddleware!)
class LoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = get_logger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        path = scope.get("path", "")
        method = scope.get("method", "")
        status_code = 0

        # Generate or extract correlation ID
        headers = dict(scope.get("headers", []))
        correlation_id = headers.get(b"x-correlation-id", b"").decode() or str(uuid.uuid4())

        # Bind correlation ID to context for all logs in this request
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_method=method,
            request_path=path
        )

        # Skip logging for health checks and dashboard auto-refresh
        should_log = path not in ["/health", "/api/metrics"]

        if should_log:
            self.logger.info("request_started", method=method, path=path)

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                process_time = time.time() - start_time
                process_time_ms = round(process_time * 1000, 2)

                # Add correlation ID to response headers
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-correlation-id", correlation_id.encode()))
                message["headers"] = headers_list

                if should_log:
                    self.logger.info(
                        "request_completed",
                        method=method,
                        path=path,
                        status_code=status_code,
                        process_time_ms=process_time_ms
                    )

                # Record metrics for all requests (including health/metrics)
                # Extract postcode from path if present
                postcode = None
                if path.startswith("/postcode/"):
                    postcode = path.split("/")[-1].upper().replace(" ", "")

                metrics.record_request(
                    method=method,
                    path=path,
                    status_code=status_code,
                    response_time=process_time_ms,
                    postcode=postcode
                )

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Clear context after request
            structlog.contextvars.clear_contextvars()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("application_startup", db_path=DB_PATH)

    # Test database connection
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM nums") as cursor:
                count = await cursor.fetchone()
                logger.info("database_connected", address_count=count[0], db_path=DB_PATH)
    except Exception as e:
        logger.error("database_connection_failed", error=str(e), db_path=DB_PATH)
        raise

    yield

    logger.info("application_shutdown")

# Create FastAPI app
app = FastAPI(
    title="Postcode API",
    description="Fast postcode to GPS coordinate lookup for Dutch postcodes",
    version="1.0.0",
    lifespan=lifespan
)

# Add our custom middleware
app.add_middleware(LoggingMiddleware)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("health_check_failed", error=str(e), db_path=DB_PATH)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )

@app.get("/postcode/{postcode}", response_model=PostcodeResponse)
async def get_postcode(postcode: str):
    """
    Get GPS coordinates and city for a Dutch postcode

    - **postcode**: Dutch postcode without spaces (e.g., 1012AB)
    """
    # Normalize postcode: uppercase, no spaces
    postcode = postcode.upper().strip().replace(" ", "")

    # Basic validation
    if len(postcode) != 6 or not (postcode[:4].isdigit() and postcode[4:].isalpha()):
        logger.warning("invalid_postcode_format", postcode=postcode)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid postcode format: {postcode}. Expected format: 1234AB"
        )

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT postcode, lat, lon, woonplaats FROM unilabel WHERE postcode = ? LIMIT 1",
                (postcode,)
            ) as cursor:
                row = await cursor.fetchone()

                if not row:
                    logger.info("postcode_not_found", postcode=postcode)
                    raise HTTPException(
                        status_code=404,
                        detail=f"Postcode {postcode} not found in database"
                    )

                logger.info(
                    "postcode_lookup_success",
                    postcode=postcode,
                    lat=row[1],
                    lon=row[2],
                    woonplaats=row[3]
                )

                return PostcodeResponse(
                    postcode=row[0],
                    lat=row[1],
                    lon=row[2],
                    woonplaats=row[3]
                )

    except aiosqlite.Error as e:
        logger.error("database_query_error", error=str(e), postcode=postcode)
        raise HTTPException(
            status_code=500,
            detail="Database error occurred"
        )

@app.get("/api/metrics")
async def get_metrics():
    """Get real-time metrics (JSON endpoint for dashboard)"""
    return metrics.get_metrics()

@app.get("/api/db-stats")
async def get_db_stats():
    """Get detailed database statistics"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            stats = {}

            # Count records in each table
            tables = ['nums', 'vbos', 'oprs', 'pnds', 'unilabel']
            for table in tables:
                try:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = await cursor.fetchone()
                        stats[f'{table}_count'] = count[0]
                except:
                    stats[f'{table}_count'] = 0

            # Get unique postcodes count
            try:
                async with db.execute("SELECT COUNT(DISTINCT postcode) FROM unilabel") as cursor:
                    count = await cursor.fetchone()
                    stats['unique_postcodes'] = count[0]
            except:
                stats['unique_postcodes'] = 0

            # Get unique cities count
            try:
                async with db.execute("SELECT COUNT(DISTINCT woonplaats) FROM unilabel") as cursor:
                    count = await cursor.fetchone()
                    stats['unique_cities'] = count[0]
            except:
                stats['unique_cities'] = 0

            return stats
    except Exception as e:
        logger.error("database_stats_error", error=str(e), db_path=DB_PATH)
        return {"error": str(e)}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Technical monitoring dashboard"""
    html_content = """
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Postcode API - Technical Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff00;
            padding: 20px;
            font-size: 13px;
            line-height: 1.4;
        }

        .container {
            max-width: 1800px;
            margin: 0 auto;
        }

        .header {
            background: #1a1a1a;
            border: 2px solid #00ff00;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #00ff00;
            font-size: 24px;
            text-shadow: 0 0 10px #00ff00;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00ff00;
            box-shadow: 0 0 10px #00ff00;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .panel {
            background: #1a1a1a;
            border: 2px solid #333;
            padding: 15px;
        }

        .panel-header {
            color: #00ff00;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #333;
            text-transform: uppercase;
        }

        .metric {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #222;
        }

        .metric-label {
            color: #888;
        }

        .metric-value {
            color: #00ff00;
            font-weight: bold;
        }

        .metric-value.warning {
            color: #ffaa00;
        }

        .metric-value.error {
            color: #ff0000;
        }

        .table-container {
            overflow-x: auto;
            margin-top: 10px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }

        th {
            background: #222;
            color: #00ff00;
            padding: 8px;
            text-align: left;
            border: 1px solid #333;
            font-weight: bold;
        }

        td {
            padding: 6px 8px;
            border: 1px solid #222;
            color: #aaa;
        }

        tr:hover {
            background: #1a1a1a;
        }

        .status-200 { color: #00ff00; }
        .status-400 { color: #ffaa00; }
        .status-404 { color: #ff8800; }
        .status-500 { color: #ff0000; }

        .full-width {
            grid-column: 1 / -1;
        }

        .progress-bar {
            width: 100%;
            height: 20px;
            background: #222;
            border: 1px solid #333;
            margin-top: 5px;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff00, #00aa00);
            transition: width 0.3s;
        }

        .progress-fill.warning {
            background: linear-gradient(90deg, #ffaa00, #ff8800);
        }

        .progress-fill.error {
            background: linear-gradient(90deg, #ff0000, #cc0000);
        }

        .timestamp {
            color: #666;
            font-size: 11px;
        }

        .refresh-info {
            color: #666;
            font-size: 11px;
        }

        .no-data {
            color: #666;
            font-style: italic;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ POSTCODE API - TECHNICAL DASHBOARD</h1>
            <div class="status-indicator">
                <span class="refresh-info" id="last-update">Last update: --:--:--</span>
                <span class="status-dot"></span>
                <span>ONLINE</span>
            </div>
        </div>

        <div class="grid">
            <!-- System Health -->
            <div class="panel">
                <div class="panel-header">⚙️ System Health</div>
                <div class="metric">
                    <span class="metric-label">Uptime</span>
                    <span class="metric-value" id="uptime">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">CPU Usage</span>
                    <span class="metric-value" id="cpu">--</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" style="width: 0%"></div>
                </div>
                <div class="metric">
                    <span class="metric-label">Memory Usage</span>
                    <span class="metric-value" id="memory">--</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar" style="width: 0%"></div>
                </div>
                <div class="metric">
                    <span class="metric-label">Disk Usage</span>
                    <span class="metric-value" id="disk">--</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="disk-bar" style="width: 0%"></div>
                </div>
            </div>

            <!-- Database Info -->
            <div class="panel">
                <div class="panel-header">💾 Database</div>
                <div class="metric">
                    <span class="metric-label">Database Size</span>
                    <span class="metric-value" id="db-size">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Database Path</span>
                    <span class="metric-value" id="db-path" style="font-size: 10px;">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Postcodes</span>
                    <span class="metric-value" id="total-postcodes">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Addresses</span>
                    <span class="metric-value" id="total-addresses">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Unique Cities</span>
                    <span class="metric-value" id="total-cities">--</span>
                </div>
            </div>

            <!-- Request Stats -->
            <div class="panel">
                <div class="panel-header">📊 Request Statistics</div>
                <div class="metric">
                    <span class="metric-label">Total Requests</span>
                    <span class="metric-value" id="total-requests">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Requests/Minute</span>
                    <span class="metric-value" id="requests-per-min">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Success Rate</span>
                    <span class="metric-value" id="success-rate">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Error Count</span>
                    <span class="metric-value" id="error-count">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status Codes</span>
                    <span class="metric-value" id="status-codes">--</span>
                </div>
            </div>

            <!-- Performance Metrics -->
            <div class="panel">
                <div class="panel-header">⚡ Performance</div>
                <div class="metric">
                    <span class="metric-label">Avg Response Time</span>
                    <span class="metric-value" id="avg-response">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Median Response Time</span>
                    <span class="metric-value" id="median-response">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Min / Max</span>
                    <span class="metric-value" id="min-max-response">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">P95 Response Time</span>
                    <span class="metric-value" id="p95-response">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">P99 Response Time</span>
                    <span class="metric-value" id="p99-response">--</span>
                </div>
            </div>
        </div>

        <!-- Top Requested Postcodes -->
        <div class="panel full-width">
            <div class="panel-header">🔥 Top Requested Postcodes</div>
            <div class="table-container">
                <table id="top-postcodes-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Postcode</th>
                            <th>Requests</th>
                        </tr>
                    </thead>
                    <tbody id="top-postcodes">
                        <tr><td colspan="3" class="no-data">No data yet...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Recent Requests -->
        <div class="panel full-width">
            <div class="panel-header">📝 Recent Requests (Last 20)</div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Method</th>
                            <th>Path</th>
                            <th>Status</th>
                            <th>Response Time (ms)</th>
                        </tr>
                    </thead>
                    <tbody id="recent-requests">
                        <tr><td colspan="5" class="no-data">No requests yet...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Recent Errors -->
        <div class="panel full-width">
            <div class="panel-header">❌ Recent Errors</div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Method</th>
                            <th>Path</th>
                            <th>Status</th>
                            <th>Response Time (ms)</th>
                        </tr>
                    </thead>
                    <tbody id="recent-errors">
                        <tr><td colspan="5" class="no-data">No errors yet! 🎉</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Slow Queries -->
        <div class="panel full-width">
            <div class="panel-header">🐌 Slow Queries (> 100ms)</div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Method</th>
                            <th>Path</th>
                            <th>Postcode</th>
                            <th>Response Time (ms)</th>
                        </tr>
                    </thead>
                    <tbody id="slow-queries">
                        <tr><td colspan="5" class="no-data">No slow queries yet! 🚀</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let dbStats = null;

        async function fetchDbStats() {
            try {
                const response = await fetch('/api/db-stats');
                dbStats = await response.json();
            } catch (error) {
                console.error('Failed to fetch DB stats:', error);
            }
        }

        async function updateMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                // Update timestamp
                const now = new Date();
                document.getElementById('last-update').textContent =
                    `Last update: ${now.toLocaleTimeString()}`;

                // System metrics
                document.getElementById('uptime').textContent = data.system.uptime_formatted;
                document.getElementById('cpu').textContent = `${data.system.cpu_percent}%`;
                document.getElementById('memory').textContent =
                    `${data.system.memory_used_mb} / ${data.system.memory_total_mb} MB (${data.system.memory_percent}%)`;
                document.getElementById('disk').textContent =
                    `${data.system.disk_used_gb} / ${data.system.disk_total_gb} GB (${data.system.disk_percent}%)`;

                // Update progress bars
                updateProgressBar('cpu-bar', data.system.cpu_percent);
                updateProgressBar('memory-bar', data.system.memory_percent);
                updateProgressBar('disk-bar', data.system.disk_percent);

                // Database info
                document.getElementById('db-size').textContent = `${data.system.db_size_mb} MB`;
                document.getElementById('db-path').textContent = data.system.db_path;

                if (dbStats) {
                    document.getElementById('total-postcodes').textContent =
                        dbStats.unique_postcodes?.toLocaleString() || '--';
                    document.getElementById('total-addresses').textContent =
                        dbStats.unilabel_count?.toLocaleString() || '--';
                    document.getElementById('total-cities').textContent =
                        dbStats.unique_cities?.toLocaleString() || '--';
                }

                // Request stats
                document.getElementById('total-requests').textContent = data.requests.total.toLocaleString();
                document.getElementById('requests-per-min').textContent = data.requests.requests_per_minute.toFixed(2);
                document.getElementById('success-rate').textContent = `${data.requests.success_rate}%`;
                document.getElementById('error-count').textContent = data.requests.errors;

                // Status codes
                const statusCodesText = Object.entries(data.requests.status_codes)
                    .map(([code, count]) => `${code}:${count}`)
                    .join(', ') || 'None';
                document.getElementById('status-codes').textContent = statusCodesText;

                // Performance metrics
                document.getElementById('avg-response').textContent = `${data.performance.avg_response_time} ms`;
                document.getElementById('median-response').textContent = `${data.performance.median_response_time} ms`;
                document.getElementById('min-max-response').textContent =
                    `${data.performance.min_response_time} / ${data.performance.max_response_time} ms`;
                document.getElementById('p95-response').textContent = `${data.performance.p95 || 0} ms`;
                document.getElementById('p99-response').textContent = `${data.performance.p99 || 0} ms`;

                // Color code avg response time
                const avgEl = document.getElementById('avg-response');
                if (data.performance.avg_response_time > 100) {
                    avgEl.className = 'metric-value error';
                } else if (data.performance.avg_response_time > 50) {
                    avgEl.className = 'metric-value warning';
                } else {
                    avgEl.className = 'metric-value';
                }

                // Top postcodes
                updateTopPostcodes(data.top_postcodes);

                // Recent requests
                updateRecentRequests(data.recent_requests);

                // Recent errors
                updateRecentErrors(data.recent_errors);

                // Slow queries
                updateSlowQueries(data.slow_queries);

            } catch (error) {
                console.error('Failed to fetch metrics:', error);
            }
        }

        function updateProgressBar(id, percent) {
            const bar = document.getElementById(id);
            bar.style.width = `${percent}%`;

            if (percent > 90) {
                bar.className = 'progress-fill error';
            } else if (percent > 75) {
                bar.className = 'progress-fill warning';
            } else {
                bar.className = 'progress-fill';
            }
        }

        function updateTopPostcodes(postcodes) {
            const tbody = document.getElementById('top-postcodes');
            if (!postcodes || postcodes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" class="no-data">No data yet...</td></tr>';
                return;
            }

            tbody.innerHTML = postcodes.slice(0, 10).map((item, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${item.postcode}</td>
                    <td>${item.count}</td>
                </tr>
            `).join('');
        }

        function updateRecentRequests(requests) {
            const tbody = document.getElementById('recent-requests');
            if (!requests || requests.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="no-data">No requests yet...</td></tr>';
                return;
            }

            tbody.innerHTML = requests.slice().reverse().slice(0, 20).map(req => `
                <tr>
                    <td class="timestamp">${new Date(req.timestamp).toLocaleTimeString()}</td>
                    <td>${req.method}</td>
                    <td>${req.path}</td>
                    <td class="status-${Math.floor(req.status / 100) * 100}">${req.status}</td>
                    <td>${req.response_time} ms</td>
                </tr>
            `).join('');
        }

        function updateRecentErrors(errors) {
            const tbody = document.getElementById('recent-errors');
            if (!errors || errors.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="no-data">No errors yet! 🎉</td></tr>';
                return;
            }

            tbody.innerHTML = errors.slice().reverse().map(err => `
                <tr>
                    <td class="timestamp">${new Date(err.timestamp).toLocaleTimeString()}</td>
                    <td>${err.method}</td>
                    <td>${err.path}</td>
                    <td class="status-${Math.floor(err.status / 100) * 100}">${err.status}</td>
                    <td>${err.response_time} ms</td>
                </tr>
            `).join('');
        }

        function updateSlowQueries(queries) {
            const tbody = document.getElementById('slow-queries');
            if (!queries || queries.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="no-data">No slow queries yet! 🚀</td></tr>';
                return;
            }

            tbody.innerHTML = queries.slice(0, 20).map(query => `
                <tr>
                    <td class="timestamp">${new Date(query.timestamp).toLocaleTimeString()}</td>
                    <td>${query.method}</td>
                    <td>${query.path}</td>
                    <td>${query.postcode || 'N/A'}</td>
                    <td class="metric-value warning">${query.response_time} ms</td>
                </tr>
            `).join('');
        }

        // Initial load
        fetchDbStats();
        updateMetrics();

        // Auto-refresh every 2 seconds
        setInterval(updateMetrics, 2000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)