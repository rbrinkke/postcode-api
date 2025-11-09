# Postcode API Mock Server

Production-grade mock server infrastructure for the Dutch Postcode Geocoding API. Provides exact endpoint parity with the production API for development, testing, and CI/CD workflows.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r mocks/requirements-mocks.txt

# Run mock server
python mocks/postcode_mock.py

# Server starts on http://localhost:8888
# API documentation: http://localhost:8888/docs
```

## 📋 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Running the Mock Server](#running-the-mock-server)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Error Simulation](#error-simulation)
- [Testing Integration](#testing-integration)
- [Docker Setup](#docker-setup)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

## ✨ Features

### Production Parity
- ✅ **Exact endpoint matching** - All production endpoints implemented
- ✅ **Response format compatibility** - Uses same Pydantic models as production
- ✅ **Validation logic** - Identical postcode validation
- ✅ **Error responses** - Same HTTP status codes and error formats

### Mock Capabilities
- 🎭 **500+ realistic Dutch postcodes** - Major cities + random coverage
- 📊 **Request statistics** - Track requests, response times, cache hits
- ⚠️ **Error simulation** - Configurable error rates and specific errors
- ⏱️ **Delay simulation** - Simulate network latency
- 🔧 **Debug endpoints** - Inspect and control mock behavior
- 📝 **OpenAPI documentation** - Auto-generated Swagger/ReDoc

### Developer Experience
- 🏃 **Fast startup** - Ready in seconds
- 🔄 **Hot reload** - Changes apply immediately with uvicorn --reload
- 🐳 **Docker support** - Run in containers
- 📦 **No database required** - In-memory data storage
- 🧪 **Test utilities** - Mock repository and database for unit tests

## 📦 Installation

```bash
# From project root
cd postcode-api

# Install mock server dependencies
pip install -r mocks/requirements-mocks.txt

# Or install all project dependencies (includes mocks)
pip install -r requirements.txt
```

### Dependencies

- `fastapi==0.109.0` - Web framework
- `uvicorn[standard]==0.27.0` - ASGI server
- `pydantic==2.12.4` - Data validation
- `pydantic-settings==2.11.0` - Configuration management
- `httpx==0.27.0` - HTTP client (for testing)
- `pytest==8.0.0` - Testing framework (optional)

## 🏃 Running the Mock Server

### Method 1: Direct Python Execution

```bash
python mocks/postcode_mock.py
```

### Method 2: Uvicorn (Recommended for Development)

```bash
# With hot reload
uvicorn mocks.postcode_mock:app --reload --port 8888

# Custom host/port
uvicorn mocks.postcode_mock:app --host 0.0.0.0 --port 8000
```

### Method 3: Docker

```bash
docker-compose -f mocks/docker-compose.mock.yml up
```

### Method 4: Background Mode

```bash
# Start in background
nohup python mocks/postcode_mock.py > mock-server.log 2>&1 &

# Check if running
curl http://localhost:8888/health
```

## 🌐 API Endpoints

### Production Endpoints (Exact Parity)

#### `GET /postcode/{postcode}`
Look up Dutch postcode and return GPS coordinates + city name.

**Request:**
```bash
curl http://localhost:8888/postcode/1012AB
```

**Response:**
```json
{
  "postcode": "1012AB",
  "lat": 52.374,
  "lon": 4.891,
  "woonplaats": "Amsterdam"
}
```

**Query Parameters:**
- `simulate_error` - Force specific error (404, 500, 503)
- `delay_ms` - Add artificial delay in milliseconds

**Examples:**
```bash
# Trigger 404 error
curl http://localhost:8888/postcode/1012AB?simulate_error=404

# Add 500ms delay
curl http://localhost:8888/postcode/1012AB?delay_ms=500

# Combine both
curl http://localhost:8888/postcode/1012AB?simulate_error=500&delay_ms=1000
```

#### `GET /health`
Standard health check.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

#### `GET /health/live`
Kubernetes liveness probe.

#### `GET /health/ready`
Kubernetes readiness probe.

#### `GET /`
API information endpoint.

### Mock-Specific Debug Endpoints

#### `GET /mock/stats`
Comprehensive server statistics.

**Response:**
```json
{
  "server": {
    "uptime_seconds": 3600,
    "total_requests": 1234,
    "successful_requests": 1200,
    "failed_requests": 34,
    "success_rate": 0.97,
    "average_response_time_ms": 12.5,
    "p50_response_time_ms": 10,
    "p95_response_time_ms": 25,
    "p99_response_time_ms": 50
  },
  "database": {
    "postcodes_count": 500,
    "total_requests": 1234,
    "cache_hit_rate": 0.75
  },
  "error_simulator": {
    "enabled": false,
    "error_rate": 0.05,
    "errors_triggered": 10
  }
}
```

#### `GET /mock/data`
List available mock postcodes.

**Query Parameters:**
- `limit` - Max postcodes to return (default: 100)

**Response:**
```json
{
  "total_count": 500,
  "returned_count": 100,
  "postcodes": ["1011AA", "1011AB", "1012AB", ...]
}
```

#### `POST /mock/data/reload`
Reload mock data from fixtures.

#### `POST /mock/data/generate?count=100`
Generate additional random postcodes.

#### `GET /mock/config`
View current mock configuration.

#### `POST /mock/errors/enable?error_rate=0.1`
Enable error simulation (10% error rate).

#### `POST /mock/errors/disable`
Disable error simulation.

#### `POST /mock/delay/set?min_ms=10&max_ms=100`
Configure response delay simulation.

#### `POST /mock/delay/disable`
Disable response delays.

## ⚙️ Configuration

Configuration is managed via environment variables or `.env.mock` file.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_PORT` | `8888` | Server port |
| `MOCK_HOST` | `0.0.0.0` | Server host |
| `MOCK_ENABLE_RESPONSE_DELAY` | `false` | Enable random delays |
| `MOCK_MIN_DELAY_MS` | `10` | Minimum delay (ms) |
| `MOCK_MAX_DELAY_MS` | `100` | Maximum delay (ms) |
| `MOCK_ERROR_SIMULATION_ENABLED` | `false` | Enable random errors |
| `MOCK_ERROR_RATE` | `0.05` | Error rate (5%) |
| `MOCK_DATA_SIZE` | `500` | Number of postcodes |
| `MOCK_USE_FIXTURES` | `true` | Load from fixtures |
| `MOCK_FIXTURES_PATH` | `mocks/fixtures` | Fixtures directory |
| `MOCK_ENABLE_DEBUG_ENDPOINTS` | `true` | Enable /mock/* endpoints |
| `MOCK_LOG_LEVEL` | `INFO` | Log level |

### Configuration File

Create `.env.mock` in `mocks/config/`:

```env
MOCK_PORT=8888
MOCK_ERROR_SIMULATION_ENABLED=true
MOCK_ERROR_RATE=0.1
MOCK_ENABLE_RESPONSE_DELAY=true
MOCK_MIN_DELAY_MS=50
MOCK_MAX_DELAY_MS=200
```

Then run:
```bash
python mocks/postcode_mock.py
```

## 💡 Usage Examples

### cURL Examples

See `mocks/examples/curl_examples.sh`:

```bash
# Basic lookup
curl http://localhost:8888/postcode/1012AB

# Pretty print JSON
curl http://localhost:8888/postcode/1012AB | jq

# Health check
curl http://localhost:8888/health

# Statistics
curl http://localhost:8888/mock/stats | jq '.server'

# List all postcodes
curl http://localhost:8888/mock/data?limit=50

# Enable errors (10% rate)
curl -X POST "http://localhost:8888/mock/errors/enable?error_rate=0.1"

# Trigger specific error
curl http://localhost:8888/postcode/1012AB?simulate_error=404

# Add delay
curl http://localhost:8888/postcode/1012AB?delay_ms=1000
```

### Python Client Example

See `mocks/examples/python_client.py`:

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Lookup postcode
        response = await client.get("http://localhost:8888/postcode/1012AB")
        print(response.json())

        # Get statistics
        stats = await client.get("http://localhost:8888/mock/stats")
        print(stats.json())

asyncio.run(main())
```

### JavaScript/Fetch Example

```javascript
// Lookup postcode
fetch('http://localhost:8888/postcode/1012AB')
  .then(response => response.json())
  .then(data => console.log(data));

// With error handling
async function lookupPostcode(postcode) {
  try {
    const response = await fetch(`http://localhost:8888/postcode/${postcode}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Lookup failed:', error);
  }
}
```

## ⚠️ Error Simulation

### Global Error Simulation

Enable random errors for all requests:

```bash
# Enable 5% error rate
curl -X POST "http://localhost:8888/mock/errors/enable?error_rate=0.05"

# Now 5% of requests will fail randomly
curl http://localhost:8888/postcode/1012AB  # might fail!

# Disable errors
curl -X POST "http://localhost:8888/mock/errors/disable"
```

### Per-Request Error Simulation

Force specific errors using query parameters:

```bash
# 404 Not Found
curl http://localhost:8888/postcode/1012AB?simulate_error=404

# 500 Internal Server Error
curl http://localhost:8888/postcode/1012AB?simulate_error=500

# 503 Service Unavailable
curl http://localhost:8888/postcode/1012AB?simulate_error=503
```

### Use Cases

1. **Timeout testing** - Add delays and test timeout handling
2. **Error recovery** - Test retry logic with error simulation
3. **Resilience testing** - Combine errors + delays for chaos testing
4. **UI error states** - Test error message display

## 🧪 Testing Integration

### Using Mock Repository in Unit Tests

```python
# test_mycode.py
import pytest
from mocks.repository_mock import MockPostcodeRepository

@pytest.fixture
def mock_repo():
    repo = MockPostcodeRepository()
    repo.add_mock_postcode("1012AB", 52.374, 4.891, "Amsterdam")
    return repo

async def test_postcode_lookup(mock_repo):
    result = await mock_repo.get_postcode("1012AB")

    assert result is not None
    assert result["woonplaats"] == "Amsterdam"
    assert result["lat"] == 52.374
```

### Using Mock Database

```python
from mocks.database_mock import MockDatabasePool

async def test_database_query():
    db = MockDatabasePool()

    # Configure mock data
    db.add_mock_postcode("1012AB", 52.374, 4.891, "Amsterdam")

    # Execute query
    results = await db.execute_query(
        "SELECT * FROM unilabel WHERE postcode = ?",
        ("1012AB",)
    )

    assert len(results) == 1
    assert results[0]["woonplaats"] == "Amsterdam"
```

### Integration with FastAPI TestClient

```python
from fastapi.testclient import TestClient
from mocks.postcode_mock import app

client = TestClient(app)

def test_postcode_endpoint():
    response = client.get("/postcode/1012AB")

    assert response.status_code == 200
    data = response.json()
    assert "postcode" in data
    assert "lat" in data
```

## 🐳 Docker Setup

### Using Docker Compose

Create `docker-compose.mock.yml`:

```yaml
version: '3.8'

services:
  postcode-mock:
    build:
      context: ..
      dockerfile: mocks/Dockerfile.mock
    ports:
      - "8888:8888"
    environment:
      - MOCK_PORT=8888
      - MOCK_ERROR_SIMULATION_ENABLED=false
      - MOCK_DATA_SIZE=500
    volumes:
      - ./fixtures:/app/mocks/fixtures:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/health"]
      interval: 10s
      timeout: 3s
      retries: 3
```

Run:
```bash
docker-compose -f mocks/docker-compose.mock.yml up
```

### Manual Docker Build

```bash
# Build image
docker build -t postcode-mock -f mocks/Dockerfile.mock .

# Run container
docker run -p 8888:8888 --name postcode-mock postcode-mock

# Run with custom env
docker run -p 8888:8888 \
  -e MOCK_DATA_SIZE=1000 \
  -e MOCK_ERROR_RATE=0.1 \
  postcode-mock
```

## 🏗️ Architecture

### Directory Structure

```
mocks/
├── base/                      # Shared infrastructure
│   ├── mock_app.py           # FastAPI app factory
│   ├── mock_data_generator.py # Data generation utilities
│   ├── error_simulator.py    # Error simulation
│   ├── response_builder.py   # Response construction
│   └── middleware.py         # Custom middleware
│
├── fixtures/                 # Static mock data
│   ├── postcodes_amsterdam.json
│   ├── postcodes_rotterdam.json
│   ├── postcodes_utrecht.json
│   └── edge_cases.json
│
├── config/                   # Configuration
│   ├── mock_settings.py
│   └── .env.mock
│
├── examples/                 # Usage examples
│   ├── curl_examples.sh
│   └── python_client.py
│
├── tests/                    # Mock tests
│   ├── test_mock_api.py
│   └── test_mock_repository.py
│
├── postcode_mock.py          # Main mock server
├── repository_mock.py        # Mock repository
├── database_mock.py          # Mock database
├── requirements-mocks.txt    # Dependencies
└── README.md                 # This file
```

### Component Overview

1. **Mock Server** (`postcode_mock.py`) - Main FastAPI application
2. **Data Generator** - Creates realistic Dutch postcodes
3. **Error Simulator** - Configurable error injection
4. **Response Builder** - Constructs API responses
5. **Statistics Tracker** - Monitors requests/performance
6. **Mock Repository** - For unit testing (no network)
7. **Mock Database** - For integration testing

## 🔧 Troubleshooting

### Server Won't Start

**Problem:** Port already in use

```bash
# Check what's using port 8888
lsof -i :8888

# Kill the process
kill -9 <PID>

# Or use different port
MOCK_PORT=9999 python mocks/postcode_mock.py
```

### No Postcodes Available

**Problem:** Fixtures not loading

```bash
# Check fixtures exist
ls -la mocks/fixtures/

# Reload data via API
curl -X POST http://localhost:8888/mock/data/reload

# Generate data manually
curl -X POST "http://localhost:8888/mock/data/generate?count=100"
```

### Import Errors

**Problem:** Module not found

```bash
# Install dependencies
pip install -r mocks/requirements-mocks.txt

# Or run from project root
cd /path/to/postcode-api
python mocks/postcode_mock.py
```

### Slow Responses

**Problem:** Delay simulation enabled

```bash
# Disable delays
curl -X POST http://localhost:8888/mock/delay/disable

# Or restart without delay config
MOCK_ENABLE_RESPONSE_DELAY=false python mocks/postcode_mock.py
```

### Too Many Errors

**Problem:** Error simulation enabled

```bash
# Disable error simulation
curl -X POST http://localhost:8888/mock/errors/disable

# Check configuration
curl http://localhost:8888/mock/config | jq '.error_simulation_enabled'
```

## 📊 Performance

The mock server is designed for high performance:

- **Response time**: < 10ms (without delay simulation)
- **Throughput**: 1000+ req/s on modern hardware
- **Memory**: ~50MB with 500 postcodes
- **Startup time**: < 2 seconds

## 🎯 Best Practices

1. **Use fixtures for consistent tests** - Load same data every time
2. **Reset mock state between tests** - Clear data/stats
3. **Test both success and error paths** - Use error simulation
4. **Monitor statistics** - Use `/mock/stats` to verify behavior
5. **Version control fixtures** - Keep fixture data in git
6. **Document test data** - Add comments to fixtures
7. **Isolate test environments** - Run mock on different port than production

## 📝 License

Same as parent project.

## 🤝 Contributing

Contributions welcome! See main project CONTRIBUTING.md.

## 📚 Additional Resources

- **OpenAPI Docs**: http://localhost:8888/docs
- **ReDoc**: http://localhost:8888/redoc
- **Production API**: See main README.md
- **Examples**: See `mocks/examples/` directory
