#!/usr/bin/env python3
"""
Sample Database Creator - Creates a smaller development database
Creates a ~250MB sample with 1000 postcodes from the 11GB production database
"""

import sqlite3
import logging
import sys
from pathlib import Path
from datetime import datetime
import random

# Configuration
SOURCE_DB = Path("/opt/postcode/geodata/bag.sqlite")
TARGET_DB = Path("/opt/postcode/geodata/bag-sample.sqlite")
TOTAL_POSTCODES = 1000
MAJOR_CITY_POSTCODES = 250  # Rest will be random

# Major Dutch cities by postcode prefix
MAJOR_CITIES = {
    'Amsterdam': '10',      # 1000-1109
    'Rotterdam': '30',      # 3000-3099
    'Den Haag': '25',       # 2500-2599
    'Utrecht': '35',        # 3500-3599
    'Eindhoven': '56',      # 5600-5699
    'Groningen': '97',      # 9700-9799
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sample-db-creation.log')
    ]
)
logger = logging.getLogger(__name__)


def get_major_city_postcodes(conn, num_per_city=None):
    """Get postcodes from major cities"""
    if num_per_city is None:
        num_per_city = MAJOR_CITY_POSTCODES // len(MAJOR_CITIES)

    logger.info(f"Selecting ~{num_per_city} postcodes per major city...")

    all_postcodes = []
    for city, prefix in MAJOR_CITIES.items():
        cursor = conn.execute(
            """
            SELECT DISTINCT postcode
            FROM nums
            WHERE postcode LIKE ? || '%'
              AND postcode != ''
              AND status != 'Naamgeving ingetrokken'
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (prefix, num_per_city)
        )
        postcodes = [row[0] for row in cursor.fetchall()]
        all_postcodes.extend(postcodes)
        logger.info(f"  {city}: {len(postcodes)} postcodes")

    return all_postcodes


def get_random_postcodes(conn, count, exclude_postcodes):
    """Get random postcodes from across Netherlands"""
    logger.info(f"Selecting {count} random postcodes...")

    placeholders = ','.join('?' * len(exclude_postcodes))
    cursor = conn.execute(
        f"""
        SELECT DISTINCT postcode
        FROM nums
        WHERE postcode != ''
          AND status != 'Naamgeving ingetrokken'
          AND postcode NOT IN ({placeholders})
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (*exclude_postcodes, count)
    )

    postcodes = [row[0] for row in cursor.fetchall()]
    logger.info(f"  Selected {len(postcodes)} random postcodes")
    return postcodes


def get_related_ids(conn, postcodes):
    """Get all related IDs for selected postcodes"""
    logger.info("Gathering all related IDs...")

    placeholders = ','.join('?' * len(postcodes))

    # Get num IDs
    cursor = conn.execute(
        f"SELECT DISTINCT id FROM nums WHERE postcode IN ({placeholders})",
        postcodes
    )
    num_ids = [row[0] for row in cursor.fetchall()]
    logger.info(f"  nums: {len(num_ids):,} addresses")

    # Get vbo IDs via vbo_num
    num_placeholders = ','.join('?' * len(num_ids))
    cursor = conn.execute(
        f"SELECT DISTINCT vbo FROM vbo_num WHERE num IN ({num_placeholders})",
        num_ids
    )
    vbo_ids = [row[0] for row in cursor.fetchall()]
    logger.info(f"  vbos: {len(vbo_ids):,} dwelling units")

    # Get opr IDs (streets)
    cursor = conn.execute(
        f"SELECT DISTINCT ligtAanRef FROM nums WHERE id IN ({num_placeholders})",
        num_ids
    )
    opr_ids = [row[0] for row in cursor.fetchall()]
    logger.info(f"  oprs: {len(opr_ids):,} streets/public spaces")

    # Get pnd IDs via vbo_pnd
    vbo_placeholders = ','.join('?' * len(vbo_ids))
    cursor = conn.execute(
        f"SELECT DISTINCT pnd FROM vbo_pnd WHERE vbo IN ({vbo_placeholders})",
        vbo_ids
    )
    pnd_ids = [row[0] for row in cursor.fetchall()]
    logger.info(f"  pnds: {len(pnd_ids):,} buildings")

    return {
        'num_ids': num_ids,
        'vbo_ids': vbo_ids,
        'opr_ids': opr_ids,
        'pnd_ids': pnd_ids,
        'postcodes': postcodes
    }


def create_schema(target_conn, source_conn):
    """Create tables in target database"""
    logger.info("Creating database schema...")

    # Get all CREATE TABLE statements
    cursor = source_conn.execute(
        """
        SELECT sql FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'geoindex%'
          AND name NOT LIKE 'sqlite_%'
          AND sql IS NOT NULL
        """
    )

    for row in cursor.fetchall():
        sql = row[0]
        target_conn.execute(sql)
        logger.info(f"  Created table from: {sql[:50]}...")

    target_conn.commit()


def copy_table_data(target_conn, source_conn, table, id_field, ids):
    """Copy filtered data for a table"""
    if not ids:
        logger.warning(f"  {table}: No IDs to copy, skipping")
        return 0

    placeholders = ','.join('?' * len(ids))

    # Get column names
    cursor = source_conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    cols_str = ', '.join(columns)

    # Copy data
    cursor = source_conn.execute(
        f"SELECT {cols_str} FROM {table} WHERE {id_field} IN ({placeholders})",
        ids
    )

    rows = cursor.fetchall()
    if rows:
        placeholders_insert = ','.join('?' * len(columns))
        target_conn.executemany(
            f"INSERT INTO {table} VALUES ({placeholders_insert})",
            rows
        )

    logger.info(f"  {table}: {len(rows):,} rows copied")
    return len(rows)


def copy_junction_table(target_conn, source_conn, table, field1, ids1, field2, ids2):
    """Copy junction table data"""
    if not ids1 or not ids2:
        logger.warning(f"  {table}: No IDs to copy, skipping")
        return 0

    placeholders1 = ','.join('?' * len(ids1))
    placeholders2 = ','.join('?' * len(ids2))

    cursor = source_conn.execute(
        f"""
        SELECT * FROM {table}
        WHERE {field1} IN ({placeholders1})
          AND {field2} IN ({placeholders2})
        """,
        (*ids1, *ids2)
    )

    rows = cursor.fetchall()
    if rows:
        # Get column count
        num_cols = len(rows[0])
        placeholders = ','.join('?' * num_cols)
        target_conn.executemany(
            f"INSERT INTO {table} VALUES ({placeholders})",
            rows
        )

    logger.info(f"  {table}: {len(rows):,} rows copied")
    return len(rows)


def copy_full_table(target_conn, source_conn, table):
    """Copy entire small reference table"""
    cursor = source_conn.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()

    if rows:
        num_cols = len(rows[0])
        placeholders = ','.join('?' * num_cols)
        target_conn.executemany(
            f"INSERT INTO {table} VALUES ({placeholders})",
            rows
        )

    logger.info(f"  {table}: {len(rows):,} rows copied (full table)")
    return len(rows)


def create_indices(target_conn, source_conn):
    """Create all indices"""
    logger.info("Creating indices...")

    cursor = source_conn.execute(
        """
        SELECT sql FROM sqlite_master
        WHERE type='index'
          AND sql IS NOT NULL
          AND name NOT LIKE 'geoindex%'
          AND name NOT LIKE 'sqlite_%'
        """
    )

    for row in cursor.fetchall():
        sql = row[0]
        try:
            target_conn.execute(sql)
            logger.info(f"  Created index: {sql[:60]}...")
        except sqlite3.OperationalError as e:
            logger.warning(f"  Skipped index (already exists or error): {e}")

    target_conn.commit()


def create_views(target_conn, source_conn):
    """Create views (unilabel, alllabel, postcode_geo)"""
    logger.info("Creating views...")

    cursor = source_conn.execute(
        """
        SELECT sql FROM sqlite_master
        WHERE type='view'
          AND sql IS NOT NULL
        """
    )

    for row in cursor.fetchall():
        sql = row[0]
        target_conn.execute(sql)
        logger.info(f"  Created view: {sql[:60]}...")

    target_conn.commit()


def validate_sample_database(db_path):
    """Validate the created sample database"""
    logger.info("Validating sample database...")

    conn = sqlite3.connect(db_path)

    # Check row counts
    tables = ['nums', 'vbos', 'oprs', 'pnds', 'wpls', 'vbo_num', 'vbo_pnd']
    for table in tables:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        logger.info(f"  {table}: {count:,} rows")

    # Check views exist
    cursor = conn.execute("SELECT COUNT(*) FROM unilabel")
    unilabel_count = cursor.fetchone()[0]
    logger.info(f"  unilabel view: {unilabel_count:,} rows")

    # Check distinct postcodes
    cursor = conn.execute("SELECT COUNT(DISTINCT postcode) FROM nums")
    postcode_count = cursor.fetchone()[0]
    logger.info(f"  Distinct postcodes: {postcode_count:,}")

    # Test a sample query
    cursor = conn.execute(
        "SELECT postcode, lat, lon, woonplaats FROM unilabel LIMIT 1"
    )
    sample = cursor.fetchone()
    if sample:
        logger.info(f"  Sample query successful: {sample}")

    conn.close()
    logger.info("✓ Validation complete")


def main():
    """Main execution"""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("BAG Sample Database Creator")
    logger.info("=" * 60)

    # Check source database exists
    if not SOURCE_DB.exists():
        logger.error(f"Source database not found: {SOURCE_DB}")
        sys.exit(1)

    logger.info(f"Source: {SOURCE_DB}")
    logger.info(f"Target: {TARGET_DB}")
    logger.info(f"Total postcodes to sample: {TOTAL_POSTCODES}")

    # Remove existing target if exists
    if TARGET_DB.exists():
        logger.info(f"Removing existing target database...")
        TARGET_DB.unlink()

    try:
        # Connect to databases
        logger.info("\n[1/7] Connecting to source database...")
        source_conn = sqlite3.connect(SOURCE_DB)

        # Select postcodes
        logger.info("\n[2/7] Selecting postcodes...")
        major_city_postcodes = get_major_city_postcodes(source_conn)
        random_count = TOTAL_POSTCODES - len(major_city_postcodes)
        random_postcodes = get_random_postcodes(source_conn, random_count, major_city_postcodes)

        all_postcodes = major_city_postcodes + random_postcodes
        logger.info(f"Total selected: {len(all_postcodes)} postcodes")

        # Get all related IDs
        logger.info("\n[3/7] Gathering related data IDs...")
        ids = get_related_ids(source_conn, all_postcodes)

        # Create target database
        logger.info(f"\n[4/7] Creating target database at {TARGET_DB}...")
        target_conn = sqlite3.connect(TARGET_DB)
        create_schema(target_conn, source_conn)

        # Copy data
        logger.info("\n[5/7] Copying filtered data...")
        copy_table_data(target_conn, source_conn, 'nums', 'id', ids['num_ids'])
        copy_table_data(target_conn, source_conn, 'vbos', 'id', ids['vbo_ids'])
        copy_table_data(target_conn, source_conn, 'oprs', 'id', ids['opr_ids'])
        copy_table_data(target_conn, source_conn, 'pnds', 'id', ids['pnd_ids'])
        copy_full_table(target_conn, source_conn, 'wpls')
        copy_junction_table(target_conn, source_conn, 'vbo_num', 'num', ids['num_ids'], 'vbo', ids['vbo_ids'])
        copy_junction_table(target_conn, source_conn, 'vbo_pnd', 'vbo', ids['vbo_ids'], 'pnd', ids['pnd_ids'])
        target_conn.commit()

        # Create indices
        logger.info("\n[6/7] Creating indices...")
        create_indices(target_conn, source_conn)

        # Create views
        logger.info("\n[7/7] Creating views...")
        create_views(target_conn, source_conn)

        # Cleanup
        source_conn.close()
        target_conn.close()

        # Validate
        logger.info("\n" + "=" * 60)
        validate_sample_database(TARGET_DB)

        # Report
        duration = datetime.now() - start_time
        size_mb = TARGET_DB.stat().st_size / (1024 * 1024)

        logger.info("\n" + "=" * 60)
        logger.info("SUCCESS!")
        logger.info(f"Duration: {duration}")
        logger.info(f"Sample database size: {size_mb:.1f} MB")
        logger.info(f"Location: {TARGET_DB}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
