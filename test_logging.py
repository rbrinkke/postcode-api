#!/usr/bin/env python3
"""
Test script to verify structlog configuration works correctly.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test 1: Import and setup logging
print("=" * 60)
print("TEST 1: Import and setup logging")
print("=" * 60)

try:
    from src.core.logging_config import setup_logging, get_logger
    print("✓ Successfully imported logging_config")
except Exception as e:
    print(f"✗ Failed to import logging_config: {e}")
    sys.exit(1)

# Test 2: Initialize logging in debug mode
print("\n" + "=" * 60)
print("TEST 2: Initialize logging in DEBUG mode (pretty console)")
print("=" * 60)

try:
    setup_logging(debug=True, json_logs=False)
    logger = get_logger(__name__)
    print("✓ Successfully initialized logging in debug mode")
except Exception as e:
    print(f"✗ Failed to initialize logging: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test structured logging
print("\n" + "=" * 60)
print("TEST 3: Test structured logging (should be colorful)")
print("=" * 60)

try:
    logger.info("test_event", test_key="test_value", number=42, boolean=True)
    logger.warning("test_warning", reason="testing warnings")
    logger.debug("test_debug", extra_data={"nested": "value"})
    print("✓ Successfully logged test messages")
except Exception as e:
    print(f"✗ Failed to log messages: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test context variables
print("\n" + "=" * 60)
print("TEST 4: Test correlation ID context")
print("=" * 60)

try:
    import structlog
    structlog.contextvars.bind_contextvars(correlation_id="test-123-456")
    logger.info("test_with_correlation", action="testing correlation IDs")
    structlog.contextvars.clear_contextvars()
    print("✓ Successfully tested correlation ID context")
except Exception as e:
    print(f"✗ Failed correlation ID test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Re-initialize in production mode (JSON)
print("\n" + "=" * 60)
print("TEST 5: Initialize logging in PRODUCTION mode (JSON)")
print("=" * 60)

try:
    setup_logging(debug=False, json_logs=True)
    logger = get_logger("production_test")
    logger.info("production_test_event", environment="production", json_output=True)
    print("✓ Successfully initialized logging in production mode")
except Exception as e:
    print(f"✗ Failed to initialize production logging: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
