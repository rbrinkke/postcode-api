#!/usr/bin/env python3
"""
Test the actual FastAPI service with sample database
"""

import os
import sys
import time
import requests
import subprocess
import signal

# Configuration
os.environ['DB_PATH'] = '/opt/postcode/geodata/bag-sample.sqlite'
API_URL = 'http://127.0.0.1:8888'

def start_api():
    """Start the API server"""
    print("🚀 Starting API with sample database...")
    print(f"   DB_PATH={os.environ['DB_PATH']}")

    process = subprocess.Popen(
        ['uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8888'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ
    )

    # Wait for server to start
    print("   Waiting for server to start...", end='', flush=True)
    for i in range(30):
        try:
            response = requests.get(f'{API_URL}/health', timeout=1)
            if response.status_code == 200:
                print(" ✓")
                return process
        except:
            pass
        time.sleep(0.5)
        print(".", end='', flush=True)

    print(" ✗")
    print("❌ Server failed to start")
    process.kill()
    return None

def test_endpoints(process):
    """Test API endpoints"""
    print("\n📊 Testing API endpoints...")
    print("=" * 60)

    tests = [
        {
            'name': 'Health Check',
            'url': f'{API_URL}/health',
            'expected_status': 200,
            'expected_keys': ['status', 'database']
        },
        {
            'name': 'Valid Postcode (Utrecht 3511AB)',
            'url': f'{API_URL}/postcode/3511AB',
            'expected_status': 200,
            'expected_keys': ['postcode', 'lat', 'lon', 'woonplaats'],
            'expected_values': {'postcode': '3511AB', 'woonplaats': 'Utrecht'}
        },
        {
            'name': 'Valid Postcode (Appingedam 9901EG)',
            'url': f'{API_URL}/postcode/9901EG',
            'expected_status': 200,
            'expected_keys': ['postcode', 'lat', 'lon', 'woonplaats'],
            'expected_values': {'postcode': '9901EG', 'woonplaats': 'Appingedam'}
        },
        {
            'name': 'Postcode not in sample (1000AA)',
            'url': f'{API_URL}/postcode/1000AA',
            'expected_status': 404
        },
        {
            'name': 'Invalid postcode format',
            'url': f'{API_URL}/postcode/INVALID',
            'expected_status': 400
        },
        {
            'name': 'Postcode with spaces (should normalize)',
            'url': f'{API_URL}/postcode/3511 AB',
            'expected_status': 200,
            'expected_values': {'postcode': '3511AB'}
        }
    ]

    passed = 0
    failed = 0

    for test in tests:
        print(f"\n{test['name']}")
        print("-" * 60)

        try:
            response = requests.get(test['url'], timeout=5)

            # Check status code
            if response.status_code != test['expected_status']:
                print(f"  ❌ Status code: {response.status_code} (expected {test['expected_status']})")
                failed += 1
                continue
            else:
                print(f"  ✓ Status code: {response.status_code}")

            # Check response for successful requests
            if response.status_code == 200:
                data = response.json()

                # Check keys
                if 'expected_keys' in test:
                    missing_keys = set(test['expected_keys']) - set(data.keys())
                    if missing_keys:
                        print(f"  ❌ Missing keys: {missing_keys}")
                        failed += 1
                        continue
                    else:
                        print(f"  ✓ All expected keys present")

                # Check values
                if 'expected_values' in test:
                    for key, expected in test['expected_values'].items():
                        if data.get(key) != expected:
                            print(f"  ❌ {key}: {data.get(key)} (expected {expected})")
                            failed += 1
                            continue
                        else:
                            print(f"  ✓ {key}: {data.get(key)}")

                # Show full response
                print(f"  Response: {data}")

            passed += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0

def main():
    """Main test execution"""
    print("=" * 60)
    print("FastAPI Service Test with Sample Database")
    print("=" * 60)
    print()

    # Verify sample database exists
    db_path = os.environ['DB_PATH']
    if not os.path.exists(db_path):
        print(f"❌ Sample database not found: {db_path}")
        print("   Run: python3 create-sample-database.py")
        sys.exit(1)

    db_size = os.path.getsize(db_path) / (1024 * 1024)
    print(f"✓ Database found: {db_path} ({db_size:.1f} MB)")
    print()

    # Start API
    process = start_api()
    if not process:
        sys.exit(1)

    try:
        # Run tests
        success = test_endpoints(process)

        print()
        if success:
            print("✓ All tests passed! Sample database is working perfectly.")
            sys.exit(0)
        else:
            print("✗ Some tests failed. Check output above.")
            sys.exit(1)

    finally:
        # Cleanup
        print("\n🛑 Stopping API server...")
        process.send_signal(signal.SIGTERM)
        time.sleep(1)
        if process.poll() is None:
            process.kill()
        print("   Done!")

if __name__ == "__main__":
    main()
