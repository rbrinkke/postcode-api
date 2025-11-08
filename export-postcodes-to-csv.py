#!/usr/bin/env python3
"""
Export Postcodes to CSV - Creates CSV files from the database
"""

import sqlite3
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime

# Configuration
SAMPLE_DB = Path("/opt/postcode/geodata/bag-sample.sqlite")
PRODUCTION_DB = Path("/opt/postcode/geodata/bag.sqlite")
OUTPUT_DIR = Path("/opt/postcode")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def export_postcodes_to_csv(db_path, output_file, detailed=False):
    """
    Export postcodes from database to CSV

    Args:
        db_path: Path to SQLite database
        output_file: Output CSV filename
        detailed: If True, export one row per address. If False, one row per postcode.
    """
    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)

    output_path = OUTPUT_DIR / output_file

    if detailed:
        # One row per address (can be large)
        logger.info("Exporting detailed address data (one row per address)...")

        query = """
            SELECT
                postcode,
                woonplaats,
                straat,
                huisnummer,
                huisletter,
                huistoevoeging,
                lat,
                lon,
                oppervlakte,
                gebruiksdoelen,
                num_status,
                vbo_status
            FROM unilabel
            ORDER BY postcode, huisnummer, huisletter, huistoevoeging
        """

        fieldnames = [
            'postcode', 'woonplaats', 'straat', 'huisnummer',
            'huisletter', 'huistoevoeging', 'lat', 'lon',
            'oppervlakte', 'gebruiksdoelen', 'num_status', 'vbo_status'
        ]
    else:
        # One row per postcode (summary)
        logger.info("Exporting postcode summary (one row per postcode)...")

        query = """
            SELECT
                postcode,
                woonplaats,
                lat,
                lon,
                COUNT(*) as address_count
            FROM unilabel
            GROUP BY postcode
            ORDER BY postcode
        """

        fieldnames = ['postcode', 'woonplaats', 'lat', 'lon', 'address_count']

    cursor = conn.execute(query)

    # Write CSV
    logger.info(f"Writing to: {output_path}")
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow(fieldnames)

        # Write data
        row_count = 0
        for row in cursor:
            writer.writerow(row)
            row_count += 1

            if row_count % 1000 == 0:
                logger.info(f"  Exported {row_count:,} rows...")

    conn.close()

    # Get file size
    size_mb = output_path.stat().st_size / (1024 * 1024)

    logger.info(f"✓ Export complete!")
    logger.info(f"  Rows: {row_count:,}")
    logger.info(f"  Size: {size_mb:.2f} MB")
    logger.info(f"  File: {output_path}")

    return row_count, size_mb


def export_unique_cities(db_path, output_file):
    """Export list of unique cities with postcode count"""
    logger.info(f"Exporting unique cities from: {db_path}")
    conn = sqlite3.connect(db_path)

    output_path = OUTPUT_DIR / output_file

    query = """
        SELECT
            woonplaats,
            COUNT(DISTINCT postcode) as postcode_count,
            COUNT(*) as address_count,
            MIN(postcode) as first_postcode,
            MAX(postcode) as last_postcode
        FROM unilabel
        GROUP BY woonplaats
        ORDER BY postcode_count DESC, woonplaats
    """

    cursor = conn.execute(query)

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['city', 'postcode_count', 'address_count', 'first_postcode', 'last_postcode'])

        row_count = 0
        for row in cursor:
            writer.writerow(row)
            row_count += 1

    conn.close()

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"✓ Cities exported: {row_count:,} cities")
    logger.info(f"  File: {output_path} ({size_kb:.1f} KB)")

    return row_count


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Postcode CSV Exporter")
    logger.info("=" * 60)

    # Check which databases exist
    has_sample = SAMPLE_DB.exists()
    has_production = PRODUCTION_DB.exists()

    if not has_sample and not has_production:
        logger.error("No databases found!")
        sys.exit(1)

    try:
        # Sample database exports
        if has_sample:
            logger.info("\n[1] Sample Database Exports")
            logger.info("-" * 60)

            # Summary (one per postcode)
            export_postcodes_to_csv(
                SAMPLE_DB,
                'postcodes-sample-summary.csv',
                detailed=False
            )

            # Detailed (all addresses)
            logger.info("")
            export_postcodes_to_csv(
                SAMPLE_DB,
                'postcodes-sample-detailed.csv',
                detailed=True
            )

            # Cities
            logger.info("")
            export_unique_cities(
                SAMPLE_DB,
                'cities-sample.csv'
            )

        # Production database (summary only - detailed would be huge)
        if has_production and input("\n\nExport production database? This may take a while (y/N): ").lower() == 'y':
            logger.info("\n[2] Production Database Exports")
            logger.info("-" * 60)
            logger.info("⚠ Note: Only exporting summary (detailed would be ~500MB+)")

            export_postcodes_to_csv(
                PRODUCTION_DB,
                'postcodes-production-summary.csv',
                detailed=False
            )

            logger.info("")
            export_unique_cities(
                PRODUCTION_DB,
                'cities-production.csv'
            )

        logger.info("\n" + "=" * 60)
        logger.info("✓ All exports complete!")
        logger.info(f"Output directory: {OUTPUT_DIR}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
