#!/usr/bin/env python3
"""Test API with sample database"""

import sqlite3
import sys

# Test database paths
SAMPLE_DB = "/opt/postcode/geodata/bag-sample.sqlite"

def test_api_queries():
    """Simulate API queries against sample database"""
    print("=" * 60)
    print("API Test with Sample Database")
    print("=" * 60)

    # Test postcodes that should exist in our sample
    test_cases = [
        ('3511AB', 'Utrecht'),      # Should exist (from major cities)
        ('9901EG', 'Appingedam'),   # Should exist (random sample)
        ('1000AA', None),            # Should NOT exist
        ('INVALID', None),           # Invalid format
    ]

    conn = sqlite3.connect(SAMPLE_DB)
    print("\n✓ Database connected")

    for postcode, expected_city in test_cases:
        # Normalize postcode (same as API)
        normalized = postcode.upper().strip().replace(" ", "")

        # Validate format (same as API)
        if len(normalized) != 6 or not (normalized[:4].isdigit() and normalized[4:].isalpha()):
            print(f"\n  {postcode}: ❌ Invalid format")
            continue

        # Query (same as API)
        cursor = conn.execute(
            "SELECT postcode, lat, lon, woonplaats FROM unilabel WHERE postcode = ? LIMIT 1",
            (normalized,)
        )
        row = cursor.fetchone()

        if row:
            print(f"\n  {postcode}: ✓ Found")
            print(f"    - City: {row[3]}")
            print(f"    - Coordinates: {row[1]:.6f}, {row[2]:.6f}")

            if expected_city and row[3] != expected_city:
                print(f"    ⚠ Expected {expected_city}, got {row[3]}")
        else:
            print(f"\n  {postcode}: ❌ Not found")
            if expected_city:
                print(f"    ⚠ Expected to find {expected_city}")

    # Count test
    cursor = conn.execute("SELECT COUNT(*) FROM unilabel")
    count = cursor.fetchone()
    print(f"\n✓ Total addresses in unilabel: {count[0]:,}")

    # Health check simulation
    cursor = conn.execute("SELECT 1")
    cursor.fetchone()
    print("✓ Health check: OK")

    conn.close()

    print("\n" + "=" * 60)
    print("✓ API simulation tests complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_api_queries()
