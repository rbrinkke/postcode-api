# Environment Configuration Guide

## Overview

The API supports flexible database configuration through environment variables and `.env` files.

## Quick Start

### Method 1: Interactive Switcher (Easiest)

```bash
# Run the interactive database switcher
./switch-database.sh

# Select:
# 1) Sample database (16 MB - for development)
# 2) Production database (11 GB - full data)

# Then run API
./run-with-env.sh
```

### Method 2: Manual .env File

```bash
# Copy a preset configuration
cp .env.sample .env          # For sample database
# OR
cp .env.production .env      # For production database

# Run API with configuration
./run-with-env.sh
```

### Method 3: Direct Environment Variable

```bash
# Run with sample database
DB_PATH=/opt/postcode/geodata/bag-sample.sqlite uvicorn main:app --reload

# Run with production database
DB_PATH=/opt/postcode/geodata/bag.sqlite uvicorn main:app --reload
```

## Available Configurations

### .env.sample (Development)
```bash
DB_PATH=/opt/postcode/geodata/bag-sample.sqlite
HOST=0.0.0.0
PORT=7777
LOG_LEVEL=INFO
```
- **Use for**: Local development, testing, demos
- **Database size**: 16 MB
- **Postcodes**: 1,000 postcodes

### .env.production (Production)
```bash
DB_PATH=/opt/postcode/geodata/bag.sqlite
HOST=0.0.0.0
PORT=7777
LOG_LEVEL=INFO
```
- **Use for**: Production deployment, full dataset
- **Database size**: 11 GB
- **Postcodes**: 470,000 postcodes

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `/opt/postcode/geodata/bag.sqlite` | Path to SQLite database |
| `HOST` | `0.0.0.0` | Server host binding |
| `PORT` | `7777` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## File Structure

```
/opt/postcode/
├── .env                    # Your active configuration (gitignored)
├── .env.example            # Template with documentation
├── .env.sample             # Preset: sample database
├── .env.production         # Preset: production database
├── switch-database.sh      # Interactive switcher
└── run-with-env.sh         # Run API with .env
```

## Usage Examples

### Switch Between Databases

```bash
# Switch to sample database
cp .env.sample .env
./run-with-env.sh

# Switch to production database
cp .env.production .env
./run-with-env.sh
```

### Custom Configuration

```bash
# Create custom .env
cat > .env << EOF
DB_PATH=/custom/path/to/database.sqlite
HOST=127.0.0.1
PORT=8888
LOG_LEVEL=DEBUG
EOF

# Run with custom config
./run-with-env.sh
```

### Check Current Configuration

```bash
# Show current .env
cat .env

# Or use the switcher
./switch-database.sh
# Select option 3 to view current config
```

## Docker Usage

When using Docker, mount your database and pass environment variables:

```bash
# With docker-compose (edit docker-compose.yml)
environment:
  - DB_PATH=/opt/postcode/geodata/bag-sample.sqlite

# With docker run
docker run -e DB_PATH=/opt/postcode/geodata/bag-sample.sqlite \
  -v /opt/postcode/geodata:/opt/postcode/geodata:ro \
  postcode-app
```

## Best Practices

1. **Never commit `.env`** - It's in `.gitignore`
2. **Use `.env.sample` for development** - Fast startup, small footprint
3. **Use `.env.production` for production** - Full dataset
4. **Keep `.env.example` updated** - Document all variables
5. **Use `./switch-database.sh`** - Safest way to switch

## Troubleshooting

### Database not found
```bash
# Check DB_PATH in .env
grep DB_PATH .env

# Verify file exists
ls -lh $(grep DB_PATH .env | cut -d'=' -f2)
```

### Port already in use
```bash
# Change port in .env
echo "PORT=8888" >> .env

# Or use environment variable
PORT=8888 ./run-with-env.sh
```

### Permission errors
```bash
# Ensure database is readable
chmod 644 /opt/postcode/geodata/*.sqlite

# Ensure scripts are executable
chmod +x *.sh
```

## See Also

- `CLAUDE.md` - Complete project documentation
- `README-sample-database.md` - Sample database guide
- `.env.example` - All available environment variables
