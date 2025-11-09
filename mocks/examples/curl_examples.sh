#!/bin/bash
#
# Postcode API Mock Server - cURL Examples
#
# Usage: ./curl_examples.sh
#
# Prerequisites:
# - Mock server running on http://localhost:8888
# - jq installed (optional, for pretty JSON)

BASE_URL="http://localhost:8888"

echo "=================================="
echo "Postcode API Mock Server Examples"
echo "=================================="
echo ""

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function run_example() {
    echo -e "${BLUE}=== $1 ===${NC}"
    echo -e "${GREEN}Command:${NC} $2"
    echo "Response:"
    eval $2
    echo ""
    echo ""
}

# Basic health check
run_example "Health Check" \
    "curl -s $BASE_URL/health | jq"

# Liveness probe
run_example "Liveness Probe" \
    "curl -s $BASE_URL/health/live | jq"

# API root
run_example "API Info" \
    "curl -s $BASE_URL/ | jq"

# Basic postcode lookup
run_example "Basic Postcode Lookup" \
    "curl -s $BASE_URL/postcode/1012AB | jq"

# Postcode with spaces (should be normalized)
run_example "Postcode with Spaces" \
    "curl -s '$BASE_URL/postcode/1012 AB' | jq"

# Rotterdam postcode
run_example "Rotterdam Postcode" \
    "curl -s $BASE_URL/postcode/3011AA | jq"

# Utrecht postcode
run_example "Utrecht Postcode" \
    "curl -s $BASE_URL/postcode/3511AA | jq"

# Invalid postcode format (should fail)
run_example "Invalid Postcode Format (422)" \
    "curl -s -w '\nHTTP Status: %{http_code}\n' $BASE_URL/postcode/INVALID"

# Non-existent postcode (should 404)
run_example "Non-existent Postcode (404)" \
    "curl -s -w '\nHTTP Status: %{http_code}\n' $BASE_URL/postcode/9876ZZ"

# Simulate 404 error
run_example "Simulate 404 Error" \
    "curl -s -w '\nHTTP Status: %{http_code}\n' '$BASE_URL/postcode/1012AB?simulate_error=404'"

# Simulate 500 error
run_example "Simulate 500 Error" \
    "curl -s -w '\nHTTP Status: %{http_code}\n' '$BASE_URL/postcode/1012AB?simulate_error=500'"

# Simulate 503 error
run_example "Simulate 503 Error" \
    "curl -s -w '\nHTTP Status: %{http_code}\n' '$BASE_URL/postcode/1012AB?simulate_error=503'"

# Add response delay
run_example "Add 500ms Response Delay" \
    "time curl -s '$BASE_URL/postcode/1012AB?delay_ms=500' | jq"

# Combine error and delay
run_example "Combine Error + Delay" \
    "curl -s '$BASE_URL/postcode/1012AB?simulate_error=500&delay_ms=1000'"

# Get mock statistics
run_example "Mock Server Statistics" \
    "curl -s $BASE_URL/mock/stats | jq"

# Get available postcodes (first 10)
run_example "List Available Postcodes (first 10)" \
    "curl -s '$BASE_URL/mock/data?limit=10' | jq"

# Get mock configuration
run_example "Mock Server Configuration" \
    "curl -s $BASE_URL/mock/config | jq '.mock_port, .mock_data_size, .error_simulation_enabled'"

# Enable error simulation (10% error rate)
run_example "Enable Error Simulation (10%)" \
    "curl -s -X POST '$BASE_URL/mock/errors/enable?error_rate=0.1' | jq"

# Make multiple requests to see random errors
echo -e "${BLUE}=== Testing Random Errors (10% rate) ===${NC}"
echo "Making 10 requests - some should fail randomly:"
for i in {1..10}; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/postcode/1012AB")
    if [ "$status" -eq 200 ]; then
        echo -e "  Request $i: ${GREEN}✓ Success (200)${NC}"
    else
        echo -e "  Request $i: ⚠️  Failed ($status)"
    fi
done
echo ""

# Disable error simulation
run_example "Disable Error Simulation" \
    "curl -s -X POST $BASE_URL/mock/errors/disable | jq"

# Enable response delay (50-200ms)
run_example "Enable Response Delay (50-200ms)" \
    "curl -s -X POST '$BASE_URL/mock/delay/set?min_ms=50&max_ms=200' | jq"

# Make timed request
echo -e "${BLUE}=== Testing Response Delay ===${NC}"
echo "Making 5 requests with random delay (50-200ms):"
for i in {1..5}; do
    result=$(time curl -s "$BASE_URL/postcode/1012AB" 2>&1)
    echo "  Request $i completed"
done
echo ""

# Disable response delay
run_example "Disable Response Delay" \
    "curl -s -X POST $BASE_URL/mock/delay/disable | jq"

# Reload mock data
run_example "Reload Mock Data from Fixtures" \
    "curl -s -X POST $BASE_URL/mock/data/reload | jq"

# Generate additional postcodes
run_example "Generate 50 Additional Postcodes" \
    "curl -s -X POST '$BASE_URL/mock/data/generate?count=50' | jq"

# Final statistics
run_example "Final Statistics" \
    "curl -s $BASE_URL/mock/stats | jq '.server | {total_requests, success_rate, average_response_time_ms}'"

echo "=================================="
echo "All examples completed!"
echo "=================================="
echo ""
echo "Explore more at:"
echo "  - OpenAPI Docs: $BASE_URL/docs"
echo "  - ReDoc: $BASE_URL/redoc"
echo ""
