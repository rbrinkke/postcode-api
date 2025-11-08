# Sample Database for Development

## Overview

The sample database is a lightweight subset of the full 11GB BAG database, designed for local development and testing.

## Quick Start

```bash
# Generate sample database (takes ~30 seconds)
python3 create-sample-database.py

# Output: geodata/bag-sample.sqlite (~16 MB)
```

## What's Included

| Metric | Production DB | Sample DB |
|--------|--------------|-----------|
| **File Size** | 11 GB | 16 MB |
| **Postcodes** | ~470,000 | 1,000 |
| **Addresses** | ~10.5M | ~22,000 |
| **Cities** | 2,621 | ~417 |
| **Creation Time** | Hours | 30 seconds |

### Postcode Selection Strategy

- **~250 postcodes** from major cities:
  - Amsterdam (10xx)
  - Rotterdam (30xx)
  - Den Haag (25xx)
  - Utrecht (35xx)
  - Eindhoven (56xx)
  - Groningen (97xx)

- **~750 postcodes** randomly selected across Netherlands for diverse geographic coverage

## Database Contents

### Included Tables
- ✅ `nums` - Address numbers with postcodes
- ✅ `vbos` - Dwelling units with coordinates
- ✅ `oprs` - Streets and public spaces
- ✅ `pnds` - Buildings with shapes
- ✅ `wpls` - All cities (full table, only 2,621 rows)
- ✅ `vbo_num` - Junction table (vbo ↔ num)
- ✅ `vbo_pnd` - Junction table (vbo ↔ pnd)
- ✅ **Views**: `unilabel`, `alllabel`, `postcode_geo`
- ✅ **Indices**: All performance indices recreated

### Excluded Tables
- ❌ `inactnums` - Historical/inactive addresses (not needed for development)
- ❌ `geoindex*` - Spatial indices for coordinate-based lookups

## Usage

### With Environment Variable (Recommended)

```bash
# Run API with sample database
DB_PATH=/opt/postcode/geodata/bag-sample.sqlite uvicorn main:app --reload

# Or export for session
export DB_PATH=/opt/postcode/geodata/bag-sample.sqlite
uvicorn main:app --reload
```

### Testing

```bash
# Validate database structure
python3 test-sample-db.py

# Test API queries
python3 test-api-with-sample.py
```

### Sample Queries

```bash
# These postcodes exist in the sample:
curl http://localhost:7777/postcode/3511AB  # Utrecht
curl http://localhost:7777/postcode/9901EG  # Appingedam

# This won't be found (not in sample):
curl http://localhost:7777/postcode/1000AA  # Not found
```

### CSV Export

Export postcodes to CSV for analysis, spreadsheets, or other tools:

```bash
# Run export script
python3 export-postcodes-to-csv.py
```

**Generated Files:**

1. **postcodes-sample-summary.csv** (56 KB)
   - One row per postcode
   - Columns: `postcode, woonplaats, lat, lon, address_count`
   - Perfect for: Quick lookups, mapping, data analysis

2. **postcodes-sample-detailed.csv** (2.9 MB)
   - One row per address (~20,500 addresses)
   - Columns: Full address details including street, house number, coordinates
   - Perfect for: Complete address lists, geocoding

3. **cities-sample.csv** (13 KB)
   - One row per city (417 cities)
   - Columns: `city, postcode_count, address_count, first_postcode, last_postcode`
   - Perfect for: Geographic statistics, city coverage

**Example Usage:**
```python
import pandas as pd

# Load summary
df = pd.read_csv('postcodes-sample-summary.csv')
print(df[df['woonplaats'] == 'Amsterdam'].head())

# Load cities
cities = pd.read_csv('cities-sample.csv')
print(cities.sort_values('postcode_count', ascending=False).head(10))
```

## Use Cases

1. **Local Development**: Fast iteration without loading 11GB database
2. **Testing**: Predictable test data with known cities
3. **Demos**: Recognizable addresses from major cities
4. **CI/CD**: Lightweight database for automated testing

## Regenerating

The sample database can be regenerated at any time:

```bash
# This will recreate geodata/bag-sample.sqlite
python3 create-sample-database.py

# Logs saved to: sample-db-creation.log
```

## Technical Details

### Creation Process

1. Select 1,000 postcodes (mix of major cities + random)
2. Find all related addresses (~22k addresses)
3. Extract all related entities:
   - Dwelling units (vbos)
   - Streets (oprs)
   - Buildings (pnds)
4. Copy filtered data to new database
5. Recreate all indices and views
6. Validate structure

### Performance

The sample database provides the same query performance characteristics as the full database:

- Indexed lookups on postcode
- Fast joins via materialized `unilabel` view
- Same schema and API compatibility

### Limitations

- Only 1,000 out of 470,000+ postcodes
- Not suitable for production use
- No spatial coordinate-based lookups (geoindex excluded)
- Random selection changes each regeneration

## File Locations

```
/opt/postcode/
├── create-sample-database.py      # Generator script
├── test-sample-db.py              # Validation script
├── test-api-with-sample.py        # API simulation tests
├── sample-db-creation.log         # Creation logs
└── geodata/
    ├── bag.sqlite                 # Production (11GB)
    └── bag-sample.sqlite          # Sample (16MB)
```

## Questions?

See `CLAUDE.md` for full project documentation.
