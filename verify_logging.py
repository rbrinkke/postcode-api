#!/usr/bin/env python3
"""
Comprehensive logging verification script.
Tests all imports and logging functionality after ultrathink audit.
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all critical imports work without errors"""
    print("=" * 60)
    print("TEST 1: Verify all imports (critical for preventing crashes)")
    print("=" * 60)

    tests = [
        ("Core logging config", "from src.core.logging_config import setup_logging, get_logger"),
        ("Main app", "import main"),
        ("Src main app", "from src.main import app"),
        ("API routes", "from src.api.routes import router"),
        ("Debug routes", "from src.api.debug import debug_router"),
        ("DB connection", "from src.db.connection import DatabasePool"),
        ("DB repository", "from src.db.repository import repository"),
        ("Middleware", "from src.core.middleware import LoggingMiddleware, TraceIDMiddleware"),
        ("Config", "from src.core.config import settings"),
    ]

    passed = 0
    failed = 0

    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name}: OK")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: FAILED - {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_logging_initialization():
    """Test that logging can be initialized without errors"""
    print("\n" + "=" * 60)
    print("TEST 2: Initialize logging in both modes")
    print("=" * 60)

    try:
        from src.core.logging_config import setup_logging, get_logger

        # Test debug mode
        print("\nTesting DEBUG mode (console + colors)...")
        setup_logging(debug=True, json_logs=False)
        logger = get_logger("test_debug")
        logger.info("test_debug_mode", test_key="debug_value")
        print("✅ Debug mode: OK")

        # Test production mode
        print("\nTesting PRODUCTION mode (JSON)...")
        setup_logging(debug=False, json_logs=True)
        logger = get_logger("test_production")
        logger.info("test_production_mode", test_key="production_value")
        print("✅ Production mode: OK")

        return True
    except Exception as e:
        print(f"❌ Logging initialization FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_structlog_features():
    """Test structlog-specific features"""
    print("\n" + "=" * 60)
    print("TEST 3: Structlog features (correlation IDs, context)")
    print("=" * 60)

    try:
        from src.core.logging_config import get_logger
        import structlog

        logger = get_logger("test_features")

        # Test context variables
        print("\nTesting correlation ID context...")
        structlog.contextvars.bind_contextvars(
            correlation_id="test-correlation-123",
            user_id="test-user"
        )
        logger.info("test_with_context", action="testing context vars")
        structlog.contextvars.clear_contextvars()
        print("✅ Context variables: OK")

        # Test structured logging
        print("\nTesting structured logging...")
        logger.debug("test_structured", key1="value1", key2=42, key3=True)
        logger.info("test_event", event_type="test", status="success")
        logger.warning("test_warning", reason="just testing")
        print("✅ Structured logging: OK")

        return True
    except Exception as e:
        print(f"❌ Structlog features FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_old_imports():
    """Verify old logging module doesn't exist"""
    print("\n" + "=" * 60)
    print("TEST 4: Verify old logging.py is removed")
    print("=" * 60)

    old_file = "src/core/logging.py"
    if os.path.exists(old_file):
        print(f"❌ CRITICAL: Old {old_file} still exists! This will cause conflicts!")
        return False
    else:
        print(f"✅ Old {old_file} removed: OK")
        return True


def test_trace_id_removal():
    """Verify trace_id_var is not referenced anywhere"""
    print("\n" + "=" * 60)
    print("TEST 5: Verify no trace_id_var references (would cause NameError)")
    print("=" * 60)

    files_to_check = [
        "src/api/routes.py",
        "src/api/debug.py",
        "src/db/repository.py",
    ]

    found_issues = []

    for filepath in files_to_check:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
                if 'trace_id_var' in content:
                    found_issues.append(filepath)

    if found_issues:
        print(f"❌ CRITICAL: Found trace_id_var references in:")
        for f in found_issues:
            print(f"   - {f}")
        return False
    else:
        print("✅ No trace_id_var references: OK")
        return True


def test_all_loggers_use_structlog():
    """Verify all loggers use get_logger, not logging.getLogger"""
    print("\n" + "=" * 60)
    print("TEST 6: Verify all loggers use structlog")
    print("=" * 60)

    files_to_check = [
        "src/api/routes.py",
        "src/api/debug.py",
        "src/db/connection.py",
        "src/db/repository.py",
        "src/core/middleware.py",
        "src/main.py",
        "main.py",
    ]

    issues = []

    for filepath in files_to_check:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    # Check for old-style logging.getLogger
                    if 'logging.getLogger' in line and 'import logging' not in line:
                        issues.append(f"{filepath}:{i} - Uses logging.getLogger")
                    # Check for get_logger import
                    if 'from src.core.logging_config import get_logger' in line:
                        print(f"✅ {filepath}: Uses get_logger")
                        break

    if issues:
        print(f"\n❌ Found old-style logging:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("\n✅ All files use structlog: OK")
        return True


def main():
    """Run all verification tests"""
    print("\n" + "🔍" * 30)
    print(" " * 10 + "LOGGING VERIFICATION SUITE")
    print("🔍" * 30)

    results = {
        "Imports": test_imports(),
        "Logging Init": test_logging_initialization(),
        "Structlog Features": test_structlog_features(),
        "Old File Removed": test_no_old_imports(),
        "No trace_id_var": test_trace_id_removal(),
        "All Use Structlog": test_all_loggers_use_structlog(),
    }

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n" + "🎉" * 30)
        print(" " * 15 + "ALL TESTS PASSED!")
        print(" " * 10 + "Logging system is PRODUCTION-READY")
        print("🎉" * 30)
        sys.exit(0)
    else:
        print("\n" + "⚠️ " * 30)
        print(" " * 15 + "SOME TESTS FAILED!")
        print(" " * 10 + "Review errors above before deploying")
        print("⚠️ " * 30)
        sys.exit(1)


if __name__ == "__main__":
    main()
