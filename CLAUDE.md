# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Dutch postcode (postal code) geocoding API service that provides fast lookups from postcodes to GPS coordinates and city names. The system uses data from the Dutch BAG (Basisregistratie Adressen en Gebouwen) national address registry.

**Core Components:**
- FastAPI web service (`main.py`) - Production API running on port 7777
- SQLite database (`geodata/bag.sqlite`) - 11GB database with ~30M addresses
- BAG update checker (`bag-update-checker.py`) - Automated data update system
- bagconv tooling (`bagconv-source/`) - External C++ tools for BAG XML processing

## Development Commands

### Running the API Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Option 1: Run with default settings (production database)
uvicorn main:app --host 0.0.0.0 --port 7777 --reload

# Option 2: Use environment variable
DB_PATH=/opt/postcode/geodata/bag-sample.sqlite uvicorn main:app --reload

# Option 3: Use .env file (recommended)
cp .env.sample .env          # For sample database
# OR
cp .env.production .env      # For production database
./run-with-env.sh            # Run with .env configuration

# Option 4: Interactive database switcher
./switch-database.sh         # Choose sample or production
./run-with-env.sh            # Run API
```

### Docker Operations
```bash
# Build and run with Docker Compose
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down

# Manual Docker build
docker build -t postcode-app .
docker run -p 7777:7777 -v /opt/postcode/geodata/bag.sqlite:/opt/postcode/geodata/bag.sqlite:ro postcode-app
```

### Testing the API
```bash
# Health check
curl http://localhost:7777/health

# Lookup postcode
curl http://localhost:7777/postcode/1012AB

# Expected response:
# {"postcode":"1012AB","lat":52.374,...,"lon":4.891...,"woonplaats":"Amsterdam"}
```

### Sample Database for Development

For local development without the full 11GB database, a sample database can be generated:

```bash
# Generate sample database with 1000 postcodes (~16MB)
python3 create-sample-database.py

# Output: geodata/bag-sample.sqlite
```

**Sample Database Contents:**
- **Size**: ~16 MB (vs 11 GB production database)
- **Postcodes**: 1,000 postcodes
  - ~250 from major cities (Amsterdam, Rotterdam, Utrecht, Den Haag, Eindhoven, Groningen)
  - ~750 random postcodes across Netherlands
- **Addresses**: ~22,000 addresses
- **Cities**: ~417 cities represented
- **Creation time**: ~30 seconds

**Using the Sample Database:**
```bash
# Modify main.py to use sample database (temporarily)
# Change: DB_PATH = "/opt/postcode/geodata/bag-sample.sqlite"

# Or use environment variable approach
DB_PATH = os.getenv("DB_PATH", "/opt/postcode/geodata/bag.sqlite")

# Then run:
DB_PATH=/opt/postcode/geodata/bag-sample.sqlite uvicorn main:app --reload
```

**Test Scripts:**
```bash
# Validate sample database structure
python3 test-sample-db.py

# Test API simulation queries
python3 test-api-with-sample.py
```

**CSV Export:**
```bash
# Export postcodes to CSV files
python3 export-postcodes-to-csv.py

# Generates three files:
# - postcodes-sample-summary.csv (56 KB) - One row per postcode
# - postcodes-sample-detailed.csv (2.9 MB) - All addresses
# - cities-sample.csv (13 KB) - City statistics
```

**Note:** Sample database includes all tables/views (nums, vbos, oprs, pnds, unilabel) but excludes:
- `inactnums` (historical addresses)
- `geoindex*` tables (spatial indices for coordinate-based lookups)

## Architecture

### API Service (main.py)
- **Framework**: FastAPI with async SQLite (aiosqlite)
- **Middleware**: Custom pure ASGI LoggingMiddleware (NOT BaseHTTPMiddleware - important for performance)
- **Logging**: Structured JSON logs via python-json-logger
- **Database**: Read-only SQLite connection to `bag.sqlite`
- **Health checks**: `/health` endpoint with database connectivity test

**Key Query Pattern:**
```sql
SELECT postcode, lat, lon, woonplaats
FROM unilabel
WHERE postcode = ?
LIMIT 1
```

The `unilabel` view is a denormalized view created by bagconv that joins multiple BAG tables for fast lookups.

### Database Schema
The SQLite database contains several tables and views from the bagconv tool:
- `nums` - Nummeraanduidingen (addresses with postcodes)
- `vbos` - Verblijfsobjecten (dwelling units with coordinates)
- `oprs` - Openbare ruimtes (public spaces/streets)
- `pnds` - Panden (buildings with 2D shapes)
- `unilabel` - Denormalized view joining all entities for single-query lookups
- `postcode_geo` - Custom view providing one lat/lon per postcode

**Coordinate Systems:**
- Database stores both Dutch RD (Rijksdriehoeksco�rdinaten) x/y coordinates
- API returns WGS84 lat/lon coordinates

### BAG Update System

**Update Workflow** (see `update-strategy.json`):

1. **Version Check** - Compare PDOK ATOM feed timestamp against `download-bag-version.json`
2. **Prepare bagconv** - Update/clone bagconv repository from GitHub
3. **Download** - Fetch new BAG ZIP (~3.5GB) if version changed

**Key Files:**
- `current-bag-version.json` - Version of currently deployed database
- `download-bag-version.json` - Version of last successful download
- `bagconv-source/lvbag-extract-nl.zip` - Downloaded BAG data

**Running Updates:**
```bash
python3 bag-update-checker.py
```

The update checker:
- Fetches https://service.pdok.nl/lv/bag/atom/bag.xml
- Compares version_date timestamps
- Downloads ZIP with resume support (handles ~3.5GB files)
- Requires ~7GB free disk space
- Logs to `/var/log/bag-update.log` or local directory

### bagconv Processing Pipeline

**Note:** This repository uses pre-built `bag.sqlite` database. The bagconv source is included for future updates.

To rebuild database from BAG XML (requires ~120GB disk space):
```bash
cd bagconv-source
cmake . && make
unzip lvbag-extract-nl.zip
./bagconv 9999{WPL,OPR,NUM,VBO,LIG,STA,PND}*.xml > processing.log
sqlite3 bag.sqlite < mkindx
sqlite3 bag.sqlite < geo-queries
```

**Order matters:** WPL,OPR,NUM,VBO,LIG,STA,PND sequence is required for bagconv to work correctly.

## Data Flow

```
PDOK (Dutch Govt)
  � BAG XML files (75GB)
  � bagconv tool processes to SQLite
  � bag.sqlite (11GB, ~30M addresses)
  � FastAPI service
  � JSON responses with lat/lon
```

## Postcode Format

Dutch postcodes are 6 characters: `1234AB`
- 4 digits (area code)
- 2 letters (sub-area)
- API normalizes input (removes spaces, uppercases)
- Validation: `postcode[:4].isdigit() and postcode[4:].isalpha()`

## Production Deployment

The service is designed to run in Docker with:
- Read-only bind mount for `bag.sqlite` (prevents accidental database modification)
- JSON log driver with rotation (10MB max, 3 files)
- Port 7777 exposed on all interfaces
- Health check via Docker: `curl -f --max-time 1 http://localhost:7777/postcode/1012AB`

**Important:** The database file is ~11GB. Ensure sufficient disk space and memory for SQLite to cache indices efficiently.
