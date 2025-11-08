#!/bin/bash
# Quick test to run API with sample database

echo "Starting API with sample database on port 8888..."
DB_PATH=/opt/postcode/geodata/bag-sample.sqlite uvicorn main:app --host 127.0.0.1 --port 8888 --log-level warning &
API_PID=$!

echo "Waiting for API to start..."
sleep 3

echo ""
echo "Testing endpoints..."
echo ""

# Test health
echo "1. Health check:"
curl -s http://127.0.0.1:8888/health | python3 -m json.tool
echo ""

# Test valid postcode from sample
echo "2. Valid postcode (Utrecht 3511AB):"
curl -s http://127.0.0.1:8888/postcode/3511AB | python3 -m json.tool
echo ""

# Test not found
echo "3. Postcode not in sample (1000AA):"
curl -s http://127.0.0.1:8888/postcode/1000AA
echo ""
echo ""

# Cleanup
echo "Stopping test API..."
kill $API_PID 2>/dev/null
wait $API_PID 2>/dev/null

echo "✓ Test complete!"
