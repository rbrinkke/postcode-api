#!/bin/bash
# Helper script to run API with different .env configurations

set -e

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo ""
    echo "Usage: $0 [env-file]"
    echo ""
    echo "Available presets:"
    echo "  $0 .env.sample      - Run with sample database"
    echo "  $0 .env.production  - Run with production database"
    echo ""
    echo "Or create your own .env file:"
    echo "  cp .env.example .env"
    echo "  # Edit .env"
    echo "  $0 .env"
    exit 1
fi

echo "🚀 Starting API with configuration: $ENV_FILE"
echo ""

# Load environment variables and show config
export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "Configuration:"
echo "  DB_PATH:   ${DB_PATH:-/opt/postcode/geodata/bag.sqlite}"
echo "  HOST:      ${HOST:-0.0.0.0}"
echo "  PORT:      ${PORT:-7777}"
echo "  LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "⚠️  Warning: Database file not found: $DB_PATH"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check database size
DB_SIZE=$(du -h "$DB_PATH" 2>/dev/null | cut -f1 || echo "unknown")
echo "Database: $DB_PATH ($DB_SIZE)"
echo ""

# Run uvicorn
echo "Starting uvicorn..."
uvicorn main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-7777}" \
    --reload \
    --log-level "${LOG_LEVEL:-info}"
