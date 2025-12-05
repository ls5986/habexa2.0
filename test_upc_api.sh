#!/bin/bash
# Test UPC to ASIN via backend API
# Note: Requires authentication token

BACKEND_URL="https://habexa-backend-w5u5.onrender.com"
UPC="860124000177"

echo "Testing UPC to ASIN conversion via API..."
echo "UPC: $UPC"
echo ""

# Note: This requires a valid auth token
# Replace YOUR_TOKEN with actual JWT token from login
curl -X POST "$BACKEND_URL/api/v1/analyze/single" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "{
    \"identifier_type\": \"upc\",
    \"upc\": \"$UPC\",
    \"buy_cost\": 10.00,
    \"moq\": 1
  }" | jq '.'

