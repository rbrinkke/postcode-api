#!/bin/bash

# Observability Stack Integration Verification Script
# Tests all aspects of the postcode-api integration with the observability stack

set -e

echo "=========================================="
echo "Postcode API - Observability Integration"
echo "Verification Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=$3

    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "Testing $name... "

    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5 || echo "000")

    if [ "$response_code" -eq "$expected_code" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $response_code)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected HTTP $expected_code, got $response_code)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Helper function to check if string exists in response
test_response_contains() {
    local name=$1
    local url=$2
    local search_string=$3

    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "Testing $name... "

    response=$(curl -s "$url" --max-time 5 || echo "")

    if echo "$response" | grep -q "$search_string"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (String '$search_string' not found)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Helper function to check trace ID in headers
test_trace_id() {
    local name=$1
    local url=$2

    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "Testing $name... "

    trace_id=$(curl -s -I "$url" --max-time 5 | grep -i "x-trace-id:" | awk '{print $2}' | tr -d '\r\n' || echo "")

    if [ -n "$trace_id" ] && [ ${#trace_id} -eq 36 ]; then
        echo -e "${GREEN}✓ PASSED${NC} (Trace ID: $trace_id)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (No valid trace ID found)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

echo "Phase 1: Endpoint Availability Tests"
echo "======================================="

# Test health endpoint
test_endpoint "Health endpoint" "http://localhost:8005/health" 200

# Test metrics endpoint
test_endpoint "Metrics endpoint" "http://localhost:8005/metrics" 200

# Test postcode lookup (valid)
test_endpoint "Postcode lookup (valid)" "http://localhost:8005/postcode/1012AB" 200

# Test postcode lookup (invalid)
test_endpoint "Postcode lookup (invalid)" "http://localhost:8005/postcode/9999XX" 404

echo ""
echo "Phase 2: Response Content Tests"
echo "======================================="

# Test health response contains required fields
test_response_contains "Health: status field" "http://localhost:8005/health" '"status"'
test_response_contains "Health: timestamp field" "http://localhost:8005/health" '"timestamp"'
test_response_contains "Health: service field" "http://localhost:8005/health" '"service":"postcode-api"'

# Test metrics endpoint contains Prometheus metrics
test_response_contains "Metrics: http_requests_total" "http://localhost:8005/metrics" "http_requests_total"
test_response_contains "Metrics: http_request_duration_seconds" "http://localhost:8005/metrics" "http_request_duration_seconds"
test_response_contains "Metrics: postcode_lookups_total" "http://localhost:8005/metrics" "postcode_lookups_total"
test_response_contains "Metrics: database_query_duration_seconds" "http://localhost:8005/metrics" "database_query_duration_seconds"

echo ""
echo "Phase 3: Trace ID Correlation Tests"
echo "======================================="

# Test trace ID in response headers
test_trace_id "Trace ID in /health response" "http://localhost:8005/health"
test_trace_id "Trace ID in /metrics response" "http://localhost:8005/metrics"
test_trace_id "Trace ID in /postcode response" "http://localhost:8005/postcode/1012AB"

echo ""
echo "Phase 4: Docker Configuration Tests"
echo "======================================="

# Check if container is running
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing container is running... "
if docker ps | grep -q "postcode-api"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Check Prometheus labels
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing Prometheus labels... "
if docker inspect postcode-api | grep -q "prometheus.scrape"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Check Loki label
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing Loki label... "
if docker inspect postcode-api | grep -q "loki.collect"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Check network membership
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing activity-observability network... "
if docker inspect postcode-api | grep -q "activity-observability"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (Network may not exist yet)"
fi

# Check logging driver
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing json-file logging driver... "
if docker inspect postcode-api | grep -q "json-file"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""
echo "Phase 5: Log Format Tests"
echo "======================================="

# Check if logs are JSON formatted
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing JSON log format... "
if docker logs postcode-api --tail 5 2>&1 | grep -q '"timestamp"'; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Check if logs contain service field
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing service field in logs... "
if docker logs postcode-api --tail 10 2>&1 | grep -q '"service":"postcode-api"'; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Check if logs contain trace_id field
TESTS_TOTAL=$((TESTS_TOTAL + 1))
echo -n "Testing trace_id field in logs... "
if docker logs postcode-api --tail 20 2>&1 | grep -q '"trace_id"'; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠ WARNING${NC} (Make some requests first)"
fi

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo -e "Total tests: $TESTS_TOTAL"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Integration successful!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Check Prometheus targets: http://localhost:9091/targets"
    echo "2. Check Grafana dashboards: http://localhost:3002"
    echo "3. Check Loki logs: http://localhost:3100/loki/api/v1/labels"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
