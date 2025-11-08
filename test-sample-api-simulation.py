#!/usr/bin/env python3
"""
Simulate API behavior with sample database
Tests all endpoints as if they were running through FastAPI
"""

import sqlite3
import os
import sys

DB_PATH = '/opt/postcode/geodata/bag-sample.sqlite'

class PostcodeAPI:
    """Simulates the FastAPI service"""

    def __init__(self, db_path):
        self.db_path = db_path

    def health_check(self):
        """Simulate /health endpoint"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("SELECT 1")
            conn.close()
            return {"status": "healthy", "database": "connected"}, 200
        except Exception as e:
            return {"status": "unhealthy", "database": "disconnected", "error": str(e)}, 503

    def get_postcode(self, postcode):
        """Simulate /postcode/{postcode} endpoint"""
        # Normalize postcode (same as API)
        postcode = postcode.upper().strip().replace(" ", "")

        # Validate format
        if len(postcode) != 6 or not (postcode[:4].isdigit() and postcode[4:].isalpha()):
            return {
                "detail": f"Invalid postcode format: {postcode}. Expected format: 1234AB"
            }, 400

        # Query database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT postcode, lat, lon, woonplaats FROM unilabel WHERE postcode = ? LIMIT 1",
                (postcode,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return {
                    "detail": f"Postcode {postcode} not found in database"
                }, 404

            return {
                "postcode": row[0],
                "lat": row[1],
                "lon": row[2],
                "woonplaats": row[3]
            }, 200

        except Exception as e:
            return {"detail": "Database error occurred"}, 500


def main():
    """Test the API simulation"""
    print("=" * 70)
    print("Sample Database API Simulation Test")
    print("=" * 70)
    print()

    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Sample database not found: {DB_PATH}")
        print("   Run: python3 create-sample-database.py")
        sys.exit(1)

    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"✓ Database: {DB_PATH} ({db_size:.1f} MB)")
    print()

    # Initialize API
    api = PostcodeAPI(DB_PATH)

    # Define test cases
    test_cases = [
        {
            'name': 'Health Check',
            'method': 'health_check',
            'args': [],
            'expected_status': 200,
            'expected_keys': ['status', 'database']
        },
        {
            'name': 'Valid Postcode: Utrecht (3511AB)',
            'method': 'get_postcode',
            'args': ['3511AB'],
            'expected_status': 200,
            'expected_data': {'postcode': '3511AB', 'woonplaats': 'Utrecht'}
        },
        {
            'name': 'Valid Postcode: Appingedam (9901EG)',
            'method': 'get_postcode',
            'args': ['9901EG'],
            'expected_status': 200,
            'expected_data': {'postcode': '9901EG', 'woonplaats': 'Appingedam'}
        },
        {
            'name': 'Valid Postcode: Amsterdam (1011LN)',
            'method': 'get_postcode',
            'args': ['1011LN'],
            'expected_status': 200,
            'expected_data': {'woonplaats': 'Amsterdam'}
        },
        {
            'name': 'Postcode with spaces (should normalize)',
            'method': 'get_postcode',
            'args': ['3511 AB'],
            'expected_status': 200,
            'expected_data': {'postcode': '3511AB'}
        },
        {
            'name': 'Lowercase postcode (should normalize)',
            'method': 'get_postcode',
            'args': ['3511ab'],
            'expected_status': 200,
            'expected_data': {'postcode': '3511AB'}
        },
        {
            'name': 'Postcode not in sample (1000AA)',
            'method': 'get_postcode',
            'args': ['1000AA'],
            'expected_status': 404
        },
        {
            'name': 'Invalid format (too short)',
            'method': 'get_postcode',
            'args': ['123AB'],
            'expected_status': 400
        },
        {
            'name': 'Invalid format (wrong pattern)',
            'method': 'get_postcode',
            'args': ['INVALID'],
            'expected_status': 400
        }
    ]

    # Run tests
    passed = 0
    failed = 0

    for test in test_cases:
        print(f"{test['name']}")
        print("-" * 70)

        # Execute method
        method = getattr(api, test['method'])
        response, status = method(*test['args'])

        # Check status code
        if status != test['expected_status']:
            print(f"  ❌ Status: {status} (expected {test['expected_status']})")
            print(f"     Response: {response}")
            failed += 1
        else:
            print(f"  ✓ Status: {status}")

            # Check keys
            if 'expected_keys' in test:
                missing = set(test['expected_keys']) - set(response.keys())
                if missing:
                    print(f"  ❌ Missing keys: {missing}")
                    failed += 1
                else:
                    print(f"  ✓ Keys present: {test['expected_keys']}")

            # Check expected data
            if 'expected_data' in test and status == 200:
                for key, expected_value in test['expected_data'].items():
                    actual_value = response.get(key)
                    if actual_value != expected_value:
                        print(f"  ❌ {key}: '{actual_value}' (expected '{expected_value}')")
                        failed += 1
                    else:
                        print(f"  ✓ {key}: {actual_value}")

            # Show response
            if status == 200:
                print(f"  Response: {response}")
            else:
                print(f"  Message: {response.get('detail', response)}")

            passed += 1

        print()

    # Summary
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    print()

    if failed == 0:
        print("✓ ALL TESTS PASSED! Sample database API simulation works perfectly!")
        print()
        print("The sample database is ready for use with:")
        print("  DB_PATH=/opt/postcode/geodata/bag-sample.sqlite uvicorn main:app --reload")
        return 0
    else:
        print("✗ Some tests failed. Check output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
