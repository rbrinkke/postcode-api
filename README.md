# Dutch Postcode Geocoding API

A fast, lightweight FastAPI service for converting Dutch postcodes to GPS coordinates using data from the BAG (Basisregistratie Adressen en Gebouwen) national address registry.

## Features

- 🚀 **Fast**: SQLite with optimized indices for sub-millisecond lookups
- 📦 **Lightweight**: Sample database (16 MB) included for development
- 🐳 **Docker**: Production-ready container with health checks
- 🔄 **Flexible**: Easy switching between sample and production databases
- 📊 **Export**: CSV export functionality for external tools
- 🧪 **Tested**: Comprehensive test suite included

## Quick Start

### Local Development (with sample database)

```bash
# Install dependencies
pip install -r requirements.txt

# Use sample database (included in repo)
cp .env.sample .env

# Run API
uvicorn main:app --host 0.0.0.0 --port 7777 --reload
```

### Docker

```bash
# Build and run
docker-compose up -d

# Test
curl http://localhost:7777/health
curl http://localhost:7777/postcode/3511AB
```

## API Usage

### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Postcode Lookup
```bash
GET /postcode/{postcode}
```

Example:
```bash
curl http://localhost:7777/postcode/3511AB
```

Response:
```json
{
  "postcode": "3511AB",
  "lat": 52.0960645,
  "lon": 5.1159257,
  "woonplaats": "Utrecht"
}
```

## Database Options

### Sample Database (Included)
- **Size**: 16 MB
- **Postcodes**: 1,000 (major cities + random sample)
- **Addresses**: ~22,000
- **Use for**: Development, testing, demos

### Production Database (Not Included)
- **Size**: 11 GB
- **Postcodes**: 470,000+ (complete Netherlands)
- **Addresses**: ~10.5M
- **Use for**: Production deployment

See [README-sample-database.md](README-sample-database.md) for details on generating and using databases.

## Configuration

### Environment Variables

Configure via `.env` file or environment variables:

```bash
DB_PATH=/opt/postcode/geodata/bag-sample.sqlite  # Database path
HOST=0.0.0.0                                      # Server host
PORT=7777                                         # Server port
LOG_LEVEL=INFO                                    # Logging level
```

### Quick Database Switching

```bash
# Interactive switcher
./switch-database.sh

# Or manually
cp .env.sample .env        # For sample database
cp .env.production .env    # For production database (when available)
```

See [README-environment.md](README-environment.md) for complete configuration guide.

## CSV Export

Export postcodes to CSV for analysis or external tools:

```bash
python3 export-postcodes-to-csv.py
```

Generates:
- `postcodes-sample-summary.csv` - One row per postcode
- `postcodes-sample-detailed.csv` - All addresses
- `cities-sample.csv` - City statistics

## Project Structure

```
/opt/postcode/
├── main.py                      # FastAPI application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker container
├── docker-compose.yml           # Docker Compose config
│
├── geodata/
│   ├── bag-sample.sqlite       # Sample database (16 MB) ✓ included
│   └── bag.sqlite              # Production database (11 GB) ✗ not included
│
├── .env.example                # Environment template
├── .env.sample                 # Sample DB preset
├── .env.production             # Production DB preset
│
├── create-sample-database.py   # Generate sample database
├── export-postcodes-to-csv.py  # Export to CSV
├── bag-update-checker.py       # Update BAG data
│
├── test-sample-db.py           # Database tests
├── test-api-with-sample.py     # API tests
├── switch-database.sh          # Database switcher
├── run-with-env.sh             # Run with .env
│
└── bagconv-source/             # BAG processing tools
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Complete project documentation
- [README-sample-database.md](README-sample-database.md) - Sample database guide
- [README-environment.md](README-environment.md) - Environment configuration

## Development

### Running Tests

```bash
# Validate sample database
python3 test-sample-db.py

# Test API queries
python3 test-api-with-sample.py
```

### Generating Sample Database

```bash
# Requires production database (bag.sqlite)
python3 create-sample-database.py
```

## Production Deployment

### Getting Production Database

The production database is not included in this repository (11 GB). To obtain it:

1. Download BAG data: `python3 bag-update-checker.py`
2. Process with bagconv (see [CLAUDE.md](CLAUDE.md))
3. Or use pre-built database (if available separately)

### Docker Deployment

```bash
# With production database
docker-compose up -d

# Or with custom database path
docker run -d \
  -e DB_PATH=/opt/postcode/geodata/bag.sqlite \
  -v /path/to/bag.sqlite:/opt/postcode/geodata/bag.sqlite:ro \
  -p 7777:7777 \
  postcode-app
```

## Data Source

Data from [PDOK BAG](https://service.pdok.nl/lv/bag/atom/bag.xml) - Dutch national address registry.

## Technical Details

- **Framework**: FastAPI with async SQLite (aiosqlite)
- **Database**: SQLite with optimized indices
- **Logging**: Structured JSON logs
- **Performance**: ~1ms query time, pure ASGI middleware
- **Coordinates**: WGS84 (lat/lon) output, Dutch RD in database

## License

See LICENSE file for details.

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines and architecture details.
