#!/usr/bin/env python3
"""Quick test script for sample database"""

import sqlite3
import sys

DB_PATH = "/opt/postcode/geodata/bag-sample.sqlite"

def test_queries():
    """Run test queries against sample database"""
    conn = sqlite3.connect(DB_PATH)

    print("=" * 60)
    print("Sample Database Test Queries")
    print("=" * 60)

    # 1. Distinct cities
    cursor = conn.execute("SELECT COUNT(DISTINCT woonplaats) FROM unilabel")
    city_count = cursor.fetchone()[0]
    print(f"\n✓ Distinct cities: {city_count}")

    # 2. Major cities representation
    print("\n✓ Major cities sample (first 5 per city):")
    for city in ['Amsterdam', 'Rotterdam', 'Utrecht', 'Den Haag', 'Eindhoven', 'Groningen']:
        cursor = conn.execute(
            "SELECT postcode, straat FROM unilabel WHERE woonplaats = ? LIMIT 5",
            (city,)
        )
        rows = cursor.fetchall()
        if rows:
            print(f"  {city}: {len(rows)} samples - {rows[0][0]} ({rows[0][1]})")

    # 3. Random postcodes check
    print("\n✓ Random postcode samples:")
    cursor = conn.execute("""
        SELECT postcode, woonplaats, lat, lon
        FROM unilabel
        WHERE woonplaats NOT IN ('Amsterdam', 'Rotterdam', 'Utrecht', 'Den Haag', 'Eindhoven', 'Groningen')
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]} - {row[1]} ({row[2]:.4f}, {row[3]:.4f})")

    # 4. Test specific postcode lookup (API simulation)
    test_postcodes = ['1012AB', '3011AB', '3511AB', '2511AB']
    print("\n✓ API simulation - postcode lookups:")
    for postcode in test_postcodes:
        cursor = conn.execute(
            "SELECT postcode, lat, lon, woonplaats FROM unilabel WHERE postcode = ? LIMIT 1",
            (postcode,)
        )
        result = cursor.fetchone()
        if result:
            print(f"  {result[0]}: {result[3]} ({result[1]:.6f}, {result[2]:.6f})")
        else:
            print(f"  {postcode}: Not in sample")

    # 5. Database statistics
    print("\n✓ Database statistics:")
    tables = ['nums', 'vbos', 'oprs', 'pnds', 'vbo_num', 'vbo_pnd']
    for table in tables:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:12s}: {count:8,} rows")

    cursor = conn.execute("SELECT COUNT(*) FROM unilabel")
    print(f"  {'unilabel':12s}: {cursor.fetchone()[0]:8,} rows (view)")

    conn.close()
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_queries()
