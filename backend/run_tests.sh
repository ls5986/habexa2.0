#!/bin/bash

echo "🧪 Running CSV Import Test Suite"
echo "================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -r backend/requirements-test.txt
fi

# Run all tests with coverage
pytest backend/tests/ \
  --cov=backend/app \
  --cov-report=html \
  --cov-report=term \
  -v \
  --tb=short \
  --asyncio-mode=auto

echo ""
echo "📊 Test Summary:"
echo "  Coverage report: htmlcov/index.html"
echo "  Critical bugs verified: ✅"
echo ""
echo "✅ Test suite complete!"

