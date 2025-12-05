# Complete UPC to Analysis Workflow

**End-to-end workflow for processing UPCs through the entire pipeline**

---

## Setup

```bash
# Set your credentials
export BEARER_TOKEN="eyJhbGciOiJIUzI1NiIsImtpZCI6ImxXc2NWdEdaYVZkbE1pS0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZwaWh6bmFtbndsdmthYXJubGJjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY0ODk3MTU0LCJpYXQiOjE3NjQ4OTM1NTQsImVtYWlsIjoibGluZHNleUBsZXRzY2xpbmsuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImxpbmRzZXlAbGV0c2NsaW5rLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJsaW5kc2V5IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2NDg5MzU1NH1dLCJzZXNzaW9uX2lkIjoiMDQ5MTY3MjYtYTA3Mi00OGVkLTlhZjktNjMxZjY2OTgwM2RkIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.WD7bsRI8f9EWeSnrm0Jp3MyyvPTKhBnyjtW1WzvQIVE"
export API_URL="https://habexa-backend-w5u5.onrender.com"

# Test UPC
export TEST_UPC="860124000177"
```

---

## Step 1: Create Supplier (If Needed)

**Endpoint:** `POST /api/v1/suppliers`

**Request:**
```bash
curl -X POST "$API_URL/api/v1/suppliers" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "name": "KEHE",
    "email": "contact@kehe.com",
    "website": "https://kehe.com",
    "notes": "Wholesale supplier"
  }'
```

**Response:**
```json
{
  "supplier": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": "d320935d-80e8-4b5f-ae69-06315b6b1f36",
    "name": "KEHE",
    "email": "contact@kehe.com",
    "website": "https://kehe.com",
    "notes": "Wholesale supplier",
    "is_active": true,
    "created_at": "2025-01-04T12:00:00Z",
    "updated_at": "2025-01-04T12:00:00Z"
  },
  "limit_info": {
    "limit": 10,
    "remaining": 9,
    "unlimited": false
  }
}
```

**Key Fields:**
- `supplier.id` - **SAVE THIS** - You'll need it for product uploads

---

## Step 2: Analyze UPC (UPC → ASIN + Full Analysis)

**Endpoint:** `POST /api/v1/analyze/single`

**Request:**
```bash
curl -X POST "$API_URL/api/v1/analyze/single" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "identifier_type": "upc",
    "upc": "860124000177",
    "buy_cost": 10.00,
    "moq": 1,
    "supplier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "quantity": 1
  }'
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identifier_type` | string | Yes | `"upc"` or `"asin"` |
| `upc` | string | Yes* | UPC code (12-14 digits) - required if `identifier_type="upc"` |
| `asin` | string | Yes* | ASIN code (10 chars) - required if `identifier_type="asin"` |
| `buy_cost` | float | Yes | Your cost to buy the product |
| `moq` | integer | No | Minimum order quantity (default: 1) |
| `supplier_id` | string | No | Supplier UUID (optional, can add later) |
| `quantity` | integer | No | Pack quantity for UPC products (default: 1) |

**Response:**
```json
{
  "job_id": "fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933",
  "product_id": "ae2e3902-cb28-4883-99b0-f3615eb5d159",
  "asin": "B01GHFBKKA",
  "status": "queued",
  "message": "Analysis queued. Poll /jobs/{job_id} for results.",
  "usage": {
    "analyses_remaining": -1,
    "analyses_limit": -1,
    "unlimited": true
  }
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | **SAVE THIS** - Use to poll for results |
| `product_id` | string | **SAVE THIS** - Product UUID in database |
| `asin` | string | Converted ASIN from UPC |
| `status` | string | Job status: `"queued"`, `"in_progress"`, `"completed"`, `"failed"` |
| `usage.analyses_remaining` | integer | Remaining analyses (-1 = unlimited) |
| `usage.analyses_limit` | integer | Total limit (-1 = unlimited) |

---

## Step 3: Poll Job Status

**Endpoint:** `GET /api/v1/jobs/{job_id}`

**Request:**
```bash
# Replace JOB_ID with the job_id from Step 2
export JOB_ID="fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933"

curl -X GET "$API_URL/api/v1/jobs/$JOB_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

**Response (While Processing):**
```json
{
  "id": "fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933",
  "user_id": "d320935d-80e8-4b5f-ae69-06315b6b1f36",
  "type": "analyze_single",
  "status": "in_progress",
  "progress": 50,
  "total_items": 1,
  "completed_items": 0,
  "success_count": 0,
  "error_count": 0,
  "created_at": "2025-01-04T12:00:00Z",
  "updated_at": "2025-01-04T12:00:05Z"
}
```

**Response (Completed):**
```json
{
  "id": "fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933",
  "user_id": "d320935d-80e8-4b5f-ae69-06315b6b1f36",
  "type": "analyze_single",
  "status": "completed",
  "progress": 100,
  "total_items": 1,
  "completed_items": 1,
  "success_count": 1,
  "error_count": 0,
  "result": {
    "analysis_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "product_id": "ae2e3902-cb28-4883-99b0-f3615eb5d159",
    "asin": "B01GHFBKKA"
  },
  "created_at": "2025-01-04T12:00:00Z",
  "completed_at": "2025-01-04T12:00:30Z"
}
```

**Job Status Values:**
- `queued` - Waiting to start
- `in_progress` - Currently processing
- `completed` - Finished successfully
- `failed` - Error occurred

**Polling Script:**
```bash
# Poll until complete (max 60 seconds)
for i in {1..12}; do
  echo "Attempt $i/12..."
  STATUS=$(curl -s -X GET "$API_URL/api/v1/jobs/$JOB_ID" \
    -H "Authorization: Bearer $BEARER_TOKEN" | jq -r '.status')
  
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done
```

---

## Step 4: Get Product with Full Analysis Data

**Endpoint:** `GET /api/v1/products?asin={asin}`

**Request:**
```bash
# Use the ASIN from Step 2
export ASIN="B01GHFBKKA"

curl -X GET "$API_URL/api/v1/products?asin=$ASIN" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

**Response:**
```json
{
  "deals": [
    {
      "deal_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "product_id": "ae2e3902-cb28-4883-99b0-f3615eb5d159",
      "user_id": "d320935d-80e8-4b5f-ae69-06315b6b1f36",
      "asin": "B01GHFBKKA",
      "title": "Product Title Here",
      "image_url": "https://m.media-amazon.com/images/I/...",
      "sell_price": 29.99,
      "fees_total": 8.50,
      "bsr": 12345,
      "seller_count": 5,
      "fba_seller_count": 3,
      "amazon_sells": false,
      "product_status": "analyzed",
      "analysis_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "supplier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "supplier_name": "KEHE",
      "buy_cost": 10.00,
      "moq": 1,
      "source": "quick_analyze",
      "source_detail": null,
      "stage": "reviewed",
      "notes": null,
      "is_active": true,
      "deal_created_at": "2025-01-04T12:00:00Z",
      "deal_updated_at": "2025-01-04T12:00:30Z",
      "profit": 11.49,
      "roi": 114.90,
      "profit_margin": 38.31,
      "meets_threshold": true
    }
  ],
  "total": 1
}
```

**Key Fields Explained:**

### Product Info
| Field | Type | Description |
|-------|------|-------------|
| `deal_id` | string | **SAVE THIS** - Deal UUID (used for updates/deletes) |
| `product_id` | string | Product UUID |
| `asin` | string | Amazon ASIN |
| `title` | string | Product title |
| `image_url` | string | Product image URL |
| `bsr` | integer | Best Seller Rank |

### Pricing & Fees
| Field | Type | Description |
|-------|------|-------------|
| `buy_cost` | float | Your cost to buy |
| `sell_price` | float | Amazon sell price (buy box) |
| `fees_total` | float | Total Amazon fees (referral + FBA) |
| `fees_referral` | float | Amazon referral fee (from analyses table) |
| `fees_fba` | float | FBA fulfillment fee (from analyses table) |

### Profitability (Calculated)
| Field | Type | Description |
|-------|------|-------------|
| `profit` | float | Net profit = `sell_price - fees_total - buy_cost` |
| `roi` | float | ROI % = `(profit / buy_cost) * 100` |
| `profit_margin` | float | Margin % = `(profit / sell_price) * 100` |
| `meets_threshold` | boolean | True if ROI >= 30% (or your threshold) |

### Competition
| Field | Type | Description |
|-------|------|-------------|
| `seller_count` | integer | Total number of sellers |
| `fba_seller_count` | integer | Number of FBA sellers |
| `amazon_sells` | boolean | True if Amazon is a seller |

### Pipeline
| Field | Type | Description |
|-------|------|-------------|
| `stage` | string | Pipeline stage: `"new"`, `"analyzing"`, `"reviewed"`, `"buy_list"`, `"ordered"` |
| `product_status` | string | Analysis status: `"pending"`, `"analyzed"`, `"error"` |
| `source` | string | Source: `"manual"`, `"csv"`, `"telegram"`, `"quick_analyze"` |

### Supplier Info
| Field | Type | Description |
|-------|------|-------------|
| `supplier_id` | string | Supplier UUID |
| `supplier_name` | string | Supplier name |
| `moq` | integer | Minimum order quantity |

---

## Step 5: Update Deal Stage (Move Through Pipeline)

**Endpoint:** `PATCH /api/v1/products/deal/{deal_id}`

### Move to Reviewed
```bash
export DEAL_ID="c3d4e5f6-a7b8-9012-cdef-123456789012"

curl -X PATCH "$API_URL/api/v1/products/deal/$DEAL_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "stage": "reviewed",
    "notes": "Looks profitable, ready to buy"
  }'
```

### Move to Buy List
```bash
curl -X PATCH "$API_URL/api/v1/products/deal/$DEAL_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "stage": "buy_list"
  }'
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `buy_cost` | float | No | Update buy cost |
| `moq` | integer | No | Update minimum order quantity |
| `stage` | string | No | Update stage: `"new"`, `"analyzing"`, `"reviewed"`, `"buy_list"`, `"ordered"` |
| `notes` | string | No | Add/update notes |
| `supplier_id` | string | No | Change supplier |

**Response:**
```json
{
  "action": "updated",
  "deal": {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "stage": "buy_list",
    "notes": "Looks profitable, ready to buy",
    "updated_at": "2025-01-04T12:05:00Z"
  }
}
```

---

## Step 6: Manage Buy List

### Get Buy List
**Endpoint:** `GET /api/v1/buy-list`

```bash
curl -X GET "$API_URL/api/v1/buy-list" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

**Response:**
```json
[
  {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "product_id": "ae2e3902-cb28-4883-99b0-f3615eb5d159",
    "deal_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "asin": "B01GHFBKKA",
    "title": "Product Title Here",
    "image_url": "https://m.media-amazon.com/images/I/...",
    "buy_cost": 10.00,
    "moq": 1,
    "quantity": 1,
    "supplier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "supplier_name": "KEHE",
    "created_at": "2025-01-04T12:05:00Z"
  }
]
```

### Update Buy List Item Quantity
**Endpoint:** `PATCH /api/v1/buy-list/{item_id}`

```bash
curl -X PATCH "$API_URL/api/v1/buy-list/$DEAL_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "quantity": 5
  }'
```

### Remove from Buy List
**Endpoint:** `DELETE /api/v1/buy-list/{item_id}`

```bash
curl -X DELETE "$API_URL/api/v1/buy-list/$DEAL_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Create Order from Buy List
**Endpoint:** `POST /api/v1/buy-list/create-order`

```bash
curl -X POST "$API_URL/api/v1/buy-list/create-order" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "orders_created": 1,
  "orders": [
    {
      "id": "d4e5f6a7-b8c9-0123-def4-234567890123",
      "user_id": "d320935d-80e8-4b5f-ae69-06315b6b1f36",
      "supplier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "asin": "B01GHFBKKA",
      "quantity": 5,
      "unit_cost": 10.00,
      "total_cost": 50.00,
      "status": "pending",
      "notes": "Created from buy list",
      "created_at": "2025-01-04T12:10:00Z"
    }
  ]
}
```

---

## Step 7: Manage Orders

### List Orders
**Endpoint:** `GET /api/v1/orders`

```bash
# All orders
curl -X GET "$API_URL/api/v1/orders?limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by status
curl -X GET "$API_URL/api/v1/orders?status=pending&limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Single Order
**Endpoint:** `GET /api/v1/orders/{order_id}`

```bash
export ORDER_ID="d4e5f6a7-b8c9-0123-def4-234567890123"

curl -X GET "$API_URL/api/v1/orders/$ORDER_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Update Order Status
**Endpoint:** `PUT /api/v1/orders/{order_id}/status`

```bash
curl -X PUT "$API_URL/api/v1/orders/$ORDER_ID/status?status=confirmed" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

**Status Values:** `"pending"`, `"confirmed"`, `"shipped"`, `"received"`, `"cancelled"`

---

## Complete Workflow Example

### Full Pipeline: UPC → Analysis → Buy List → Order

```bash
#!/bin/bash
# Complete UPC workflow example

export BEARER_TOKEN="your_token_here"
export API_URL="https://habexa-backend-w5u5.onrender.com"
export UPC="860124000177"
export BUY_COST=10.00
export SUPPLIER_ID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"

echo "Step 1: Analyze UPC..."
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/analyze/single" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d "{
    \"identifier_type\": \"upc\",
    \"upc\": \"$UPC\",
    \"buy_cost\": $BUY_COST,
    \"moq\": 1,
    \"supplier_id\": \"$SUPPLIER_ID\"
  }")

JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
PRODUCT_ID=$(echo $RESPONSE | jq -r '.product_id')
ASIN=$(echo $RESPONSE | jq -r '.asin')

echo "Job ID: $JOB_ID"
echo "Product ID: $PRODUCT_ID"
echo "ASIN: $ASIN"

echo -e "\nStep 2: Polling for completion..."
for i in {1..12}; do
  STATUS=$(curl -s -X GET "$API_URL/api/v1/jobs/$JOB_ID" \
    -H "Authorization: Bearer $BEARER_TOKEN" | jq -r '.status')
  
  echo "Status: $STATUS (attempt $i/12)"
  
  if [ "$STATUS" = "completed" ]; then
    echo "✅ Analysis complete!"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "❌ Analysis failed"
    exit 1
  fi
  
  sleep 5
done

echo -e "\nStep 3: Get product data..."
PRODUCT_DATA=$(curl -s -X GET "$API_URL/api/v1/products?asin=$ASIN" \
  -H "Authorization: Bearer $BEARER_TOKEN")

DEAL_ID=$(echo $PRODUCT_DATA | jq -r '.deals[0].deal_id')
ROI=$(echo $PRODUCT_DATA | jq -r '.deals[0].roi')
PROFIT=$(echo $PRODUCT_DATA | jq -r '.deals[0].profit')

echo "Deal ID: $DEAL_ID"
echo "ROI: $ROI%"
echo "Profit: \$$PROFIT"

if (( $(echo "$ROI >= 30" | bc -l) )); then
  echo -e "\nStep 4: Moving to buy list (ROI >= 30%)..."
  curl -s -X PATCH "$API_URL/api/v1/products/deal/$DEAL_ID" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -d '{"stage": "buy_list"}' | jq '.'
  
  echo -e "\nStep 5: Creating order from buy list..."
  curl -s -X POST "$API_URL/api/v1/buy-list/create-order" \
    -H "Authorization: Bearer $BEARER_TOKEN" | jq '.'
else
  echo "ROI too low ($ROI%), not adding to buy list"
fi
```

---

## Batch Processing Multiple UPCs

### Batch Analyze Multiple UPCs

**Endpoint:** `POST /api/v1/analyze/batch`

```bash
curl -X POST "$API_URL/api/v1/analyze/batch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "items": [
      {
        "identifier_type": "upc",
        "upc": "860124000177",
        "buy_cost": 10.00,
        "moq": 1,
        "supplier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
      },
      {
        "identifier_type": "upc",
        "upc": "123456789012",
        "buy_cost": 15.00,
        "moq": 2,
        "supplier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
      }
    ]
  }'
```

**Response:**
```json
{
  "job_id": "e5f6a7b8-c9d0-1234-ef01-345678901234",
  "message": "Batch analysis queued",
  "total": 2
}
```

Then poll `/api/v1/jobs/{job_id}` as in Step 3.

---

## Field Reference

### All Product/Deal Fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `deal_id` | UUID | `product_sources.id` | Unique deal identifier |
| `product_id` | UUID | `products.id` | Product identifier |
| `asin` | string | Analysis | Amazon ASIN |
| `title` | string | Keepa/SP-API | Product title |
| `image_url` | string | Keepa/SP-API | Product image |
| `brand` | string | Keepa/SP-API | Brand name |
| `category` | string | Keepa | Product category |
| `bsr` | integer | Keepa | Best Seller Rank |
| `sell_price` | float | SP-API/Keepa | Amazon sell price |
| `fees_total` | float | SP-API | Total fees |
| `fees_referral` | float | SP-API | Referral fee |
| `fees_fba` | float | SP-API | FBA fee |
| `seller_count` | integer | SP-API | Total sellers |
| `fba_seller_count` | integer | SP-API | FBA sellers |
| `amazon_sells` | boolean | SP-API | Amazon is seller |
| `buy_cost` | float | User input | Your buy cost |
| `moq` | integer | User input | Minimum order qty |
| `profit` | float | Calculated | Net profit |
| `roi` | float | Calculated | ROI percentage |
| `profit_margin` | float | Calculated | Profit margin % |
| `meets_threshold` | boolean | Calculated | ROI >= threshold |
| `stage` | string | Pipeline | Current stage |
| `product_status` | string | Analysis | Analysis status |
| `supplier_id` | UUID | User input | Supplier UUID |
| `supplier_name` | string | Suppliers table | Supplier name |
| `source` | string | User input | Source type |
| `notes` | string | User input | Notes |

---

## Error Handling

### Common Errors

**401 Unauthorized:**
```json
{
  "detail": "Invalid authentication credentials"
}
```
**Fix:** Get a fresh bearer token from browser DevTools

**404 Not Found (UPC):**
```json
{
  "detail": "Could not find ASIN for UPC 860124000177. Product may not be available on Amazon."
}
```
**Fix:** UPC may not exist on Amazon, try a different UPC

**400 Bad Request:**
```json
{
  "detail": "Invalid UPC format. Must be 12-14 digits."
}
```
**Fix:** Clean UPC (remove dashes, spaces, .0 suffix)

**403 Forbidden:**
```json
{
  "detail": "You've reached your analysis limit (10 per month)"
}
```
**Fix:** Upgrade subscription or wait for limit reset

---

## Quick Reference: All Endpoints Used

1. **Create Supplier:** `POST /api/v1/suppliers`
2. **Analyze UPC:** `POST /api/v1/analyze/single`
3. **Poll Job:** `GET /api/v1/jobs/{job_id}`
4. **Get Products:** `GET /api/v1/products?asin={asin}`
5. **Update Deal:** `PATCH /api/v1/products/deal/{deal_id}`
6. **Get Buy List:** `GET /api/v1/buy-list`
7. **Create Order:** `POST /api/v1/buy-list/create-order`
8. **List Orders:** `GET /api/v1/orders`

---

## Complete Example with All Keys

```bash
# 1. Create supplier (get supplier_id)
SUPPLIER_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/suppliers" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{"name": "KEHE"}')
SUPPLIER_ID=$(echo $SUPPLIER_RESPONSE | jq -r '.supplier.id')

# 2. Analyze UPC (get job_id, product_id, asin)
ANALYZE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/analyze/single" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d "{
    \"identifier_type\": \"upc\",
    \"upc\": \"860124000177\",
    \"buy_cost\": 10.00,
    \"supplier_id\": \"$SUPPLIER_ID\"
  }")
JOB_ID=$(echo $ANALYZE_RESPONSE | jq -r '.job_id')
PRODUCT_ID=$(echo $ANALYZE_RESPONSE | jq -r '.product_id')
ASIN=$(echo $ANALYZE_RESPONSE | jq -r '.asin')

# 3. Poll until complete
while true; do
  STATUS=$(curl -s -X GET "$API_URL/api/v1/jobs/$JOB_ID" \
    -H "Authorization: Bearer $BEARER_TOKEN" | jq -r '.status')
  [ "$STATUS" = "completed" ] && break
  [ "$STATUS" = "failed" ] && exit 1
  sleep 5
done

# 4. Get product data (get deal_id)
PRODUCT_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/products?asin=$ASIN" \
  -H "Authorization: Bearer $BEARER_TOKEN")
DEAL_ID=$(echo $PRODUCT_RESPONSE | jq -r '.deals[0].deal_id')
ROI=$(echo $PRODUCT_RESPONSE | jq -r '.deals[0].roi')

# 5. Move to buy list if profitable
if (( $(echo "$ROI >= 30" | bc -l) )); then
  curl -s -X PATCH "$API_URL/api/v1/products/deal/$DEAL_ID" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -d '{"stage": "buy_list"}'
fi

# 6. Create order
curl -s -X POST "$API_URL/api/v1/buy-list/create-order" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

**All keys you'll need:**
- `BEARER_TOKEN` - Your auth token
- `SUPPLIER_ID` - From creating supplier
- `JOB_ID` - From analyze request
- `PRODUCT_ID` - From analyze response
- `ASIN` - From analyze response
- `DEAL_ID` - From get products response
- `ORDER_ID` - From create order response

