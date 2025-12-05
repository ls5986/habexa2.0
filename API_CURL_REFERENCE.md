# Complete API Curl Reference

**Base URL:** `https://habexa-backend-w5u5.onrender.com`  
**Bearer Token:** `eyJhbGciOiJIUzI1NiIsImtpZCI6ImxXc2NWdEdaYVZkbE1pS0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZwaWh6bmFtbndsdmthYXJubGJjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY0ODk3MTU0LCJpYXQiOjE3NjQ4OTM1NTQsImVtYWlsIjoibGluZHNleUBsZXRzY2xpbmsuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImxpbmRzZXlAbGV0c2NsaW5rLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJsaW5kc2V5IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2NDg5MzU1NH1dLCJzZXNzaW9uX2lkIjoiMDQ5MTY3MjYtYTA3Mi00OGVkLTlhZjktNjMxZjY2OTgwM2RkIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.WD7bsRI8f9EWeSnrm0Jp3MyyvPTKhBnyjtW1WzvQIVE`

**Note:** Token expires after ~1 hour. Get a fresh one from browser DevTools if you get 401 errors.

---

## Setup (Copy this first)

```bash
# Set your bearer token
export BEARER_TOKEN="eyJhbGciOiJIUzI1NiIsImtpZCI6ImxXc2NWdEdaYVZkbE1pS0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZwaWh6bmFtbndsdmthYXJubGJjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY0ODk3MTU0LCJpYXQiOjE3NjQ4OTM1NTQsImVtYWlsIjoibGluZHNleUBsZXRzY2xpbmsuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImxpbmRzZXlAbGV0c2NsaW5rLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJsaW5kc2V5IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2NDg5MzU1NH1dLCJzZXNzaW9uX2lkIjoiMDQ5MTY3MjYtYTA3Mi00OGVkLTlhZjktNjMxZjY2OTgwM2RkIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.WD7bsRI8f9EWeSnrm0Jp3MyyvPTKhBnyjtW1WzvQIVE"

# Base URL
export API_URL="https://habexa-backend-w5u5.onrender.com"
```

---

## 1. Health & Info

### Health Check
```bash
curl -X GET "$API_URL/health"
```

### API Info
```bash
curl -X GET "$API_URL/"
```

### Get Current User
```bash
curl -X GET "$API_URL/api/v1/auth/me" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 2. Products & Deals

### Get All Products/Deals
```bash
# Get all deals
curl -X GET "$API_URL/api/v1/products?limit=50" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by stage
curl -X GET "$API_URL/api/v1/products?stage=reviewed&limit=50" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by supplier
curl -X GET "$API_URL/api/v1/products?supplier_id=SUPPLIER_ID&limit=50" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Search by ASIN
curl -X GET "$API_URL/api/v1/products?search=B01GHFBKKA&limit=50" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by ROI
curl -X GET "$API_URL/api/v1/products?min_roi=30&limit=50" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Product Stats
```bash
curl -X GET "$API_URL/api/v1/products/stats" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Deals by ASIN
```bash
curl -X GET "$API_URL/api/v1/products/by-asin/B01GHFBKKA" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Add Product/Deal
```bash
curl -X POST "$API_URL/api/v1/products" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "asin": "B01GHFBKKA",
    "buy_cost": 10.00,
    "moq": 1,
    "supplier_id": "SUPPLIER_ID",
    "source": "manual"
  }'
```

### Update Deal
```bash
curl -X PATCH "$API_URL/api/v1/products/deal/DEAL_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "buy_cost": 12.00,
    "stage": "reviewed",
    "notes": "Updated price"
  }'
```

### Delete Deal
```bash
curl -X DELETE "$API_URL/api/v1/products/deal/DEAL_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Bulk Update Stage
```bash
curl -X POST "$API_URL/api/v1/products/bulk-stage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "deal_ids": ["DEAL_ID_1", "DEAL_ID_2"],
    "stage": "buy_list"
  }'
```

### Get Product Variations
```bash
curl -X GET "$API_URL/api/v1/products/B01GHFBKKA/variations" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 3. Analysis

### Analyze Single Product (ASIN)
```bash
curl -X POST "$API_URL/api/v1/analyze/single" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "identifier_type": "asin",
    "asin": "B01GHFBKKA",
    "buy_cost": 10.00,
    "moq": 1
  }'
```

### Analyze Single Product (UPC)
```bash
curl -X POST "$API_URL/api/v1/analyze/single" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "identifier_type": "upc",
    "upc": "860124000177",
    "buy_cost": 10.00,
    "moq": 1
  }'
```

### Batch Analyze
```bash
curl -X POST "$API_URL/api/v1/analyze/batch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "items": [
      {
        "asin": "B01GHFBKKA",
        "buy_cost": 10.00,
        "moq": 1
      },
      {
        "upc": "860124000177",
        "identifier_type": "upc",
        "buy_cost": 15.00,
        "moq": 2
      }
    ]
  }'
```

### Bulk Analyze Products
```bash
curl -X POST "$API_URL/api/v1/products/bulk-analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "deal_ids": ["DEAL_ID_1", "DEAL_ID_2"]
  }'
```

---

## 4. Jobs

### Get Job Status
```bash
curl -X GET "$API_URL/api/v1/jobs/JOB_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### List All Jobs
```bash
# All jobs
curl -X GET "$API_URL/api/v1/jobs?limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by type
curl -X GET "$API_URL/api/v1/jobs?type=batch_analyze&limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by status
curl -X GET "$API_URL/api/v1/jobs?status=completed&limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Cancel Job
```bash
curl -X POST "$API_URL/api/v1/jobs/JOB_ID/cancel" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Start Batch Analysis Job
```bash
curl -X POST "$API_URL/api/v1/jobs/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "product_ids": ["PRODUCT_ID_1", "PRODUCT_ID_2"]
  }'
```

---

## 5. Suppliers

### List Suppliers
```bash
curl -X GET "$API_URL/api/v1/suppliers" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Create Supplier
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

### Update Supplier
```bash
curl -X PUT "$API_URL/api/v1/suppliers/SUPPLIER_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "name": "KEHE Updated",
    "rating": 4.5
  }'
```

### Delete Supplier
```bash
curl -X DELETE "$API_URL/api/v1/suppliers/SUPPLIER_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 6. File Upload

### Upload CSV/Excel File
```bash
curl -X POST "$API_URL/api/v1/products/upload" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -F "file=@/path/to/file.csv" \
  -F "supplier_id=SUPPLIER_ID"
```

---

## 7. Buy List

### Get Buy List
```bash
curl -X GET "$API_URL/api/v1/buy-list" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Add to Buy List
```bash
curl -X POST "$API_URL/api/v1/buy-list" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "product_id": "DEAL_ID",
    "quantity": 5
  }'
```

### Update Buy List Item
```bash
curl -X PATCH "$API_URL/api/v1/buy-list/ITEM_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "quantity": 10
  }'
```

### Remove from Buy List
```bash
curl -X DELETE "$API_URL/api/v1/buy-list/ITEM_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Clear Buy List
```bash
curl -X DELETE "$API_URL/api/v1/buy-list" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Create Order from Buy List
```bash
curl -X POST "$API_URL/api/v1/buy-list/create-order" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 8. Orders

### List Orders
```bash
# All orders
curl -X GET "$API_URL/api/v1/orders?limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by status
curl -X GET "$API_URL/api/v1/orders?status=pending&limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Filter by supplier
curl -X GET "$API_URL/api/v1/orders?supplier_id=SUPPLIER_ID&limit=20" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Single Order
```bash
curl -X GET "$API_URL/api/v1/orders/ORDER_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Create Order
```bash
curl -X POST "$API_URL/api/v1/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "asin": "B01GHFBKKA",
    "quantity": 5,
    "unit_cost": 10.00,
    "supplier_id": "SUPPLIER_ID",
    "notes": "First order"
  }'
```

### Update Order
```bash
curl -X PUT "$API_URL/api/v1/orders/ORDER_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "status": "confirmed",
    "expected_delivery": "2025-01-15",
    "notes": "Updated notes"
  }'
```

### Update Order Status
```bash
curl -X PUT "$API_URL/api/v1/orders/ORDER_ID/status?status=shipped" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 9. Billing & Subscription

### Get Subscription
```bash
curl -X GET "$API_URL/api/v1/billing/subscription" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Available Plans
```bash
curl -X GET "$API_URL/api/v1/billing/plans" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Usage Stats
```bash
curl -X GET "$API_URL/api/v1/billing/usage" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get User Limits
```bash
curl -X GET "$API_URL/api/v1/billing/user/limits" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get All Feature Limits
```bash
curl -X GET "$API_URL/api/v1/billing/limits" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Check Specific Feature Limit
```bash
curl -X GET "$API_URL/api/v1/billing/limits/analyses_per_month" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Create Checkout Session
```bash
curl -X POST "$API_URL/api/v1/billing/checkout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "price_key": "starter_monthly",
    "include_trial": true
  }'
```

### Create Portal Session
```bash
curl -X POST "$API_URL/api/v1/billing/portal" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Cancel Subscription
```bash
# Cancel at period end
curl -X POST "$API_URL/api/v1/billing/cancel?at_period_end=true" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Cancel immediately
curl -X POST "$API_URL/api/v1/billing/cancel-immediately" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Reactivate Subscription
```bash
curl -X POST "$API_URL/api/v1/billing/reactivate" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Sync Subscription
```bash
curl -X POST "$API_URL/api/v1/billing/sync" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Invoices
```bash
curl -X GET "$API_URL/api/v1/billing/invoices?limit=10" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 10. Keepa API

### Get Keepa Product Data
```bash
curl -X GET "$API_URL/api/v1/keepa/product/B01GHFBKKA?days=90" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Price History
```bash
curl -X GET "$API_URL/api/v1/keepa/history/B01GHFBKKA?days=90" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Batch Get Keepa Data
```bash
curl -X POST "$API_URL/api/v1/keepa/batch?days=90" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '["B01GHFBKKA", "B08XYZ1234"]'
```

---

## 11. SP-API

### Get Product Offers
```bash
curl -X GET "$API_URL/api/v1/sp-api/product/B01GHFBKKA/offers" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Product Fees
```bash
curl -X GET "$API_URL/api/v1/sp-api/product/B01GHFBKKA/fees?price=29.99" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Product Eligibility
```bash
curl -X GET "$API_URL/api/v1/sp-api/product/B01GHFBKKA/eligibility" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get Sales Estimate
```bash
curl -X GET "$API_URL/api/v1/sp-api/product/B01GHFBKKA/sales-estimate" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 12. Settings

### Get Profile
```bash
curl -X GET "$API_URL/api/v1/settings/profile" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Update Profile
```bash
curl -X PUT "$API_URL/api/v1/settings/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "full_name": "Lindsey Stevens"
  }'
```

### Get Alert Settings
```bash
curl -X GET "$API_URL/api/v1/settings/alerts" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Update Alert Settings
```bash
curl -X PUT "$API_URL/api/v1/settings/alerts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "alert_min_roi": 30.00,
    "alert_channels": ["push", "email"]
  }'
```

### Get Cost Settings
```bash
curl -X GET "$API_URL/api/v1/settings/costs" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Update Cost Settings
```bash
curl -X PUT "$API_URL/api/v1/settings/costs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "default_prep_cost": 0.50,
    "default_inbound_shipping": 0.50
  }'
```

### Get Profit Rules
```bash
curl -X GET "$API_URL/api/v1/settings/profit-rules" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Update Profit Rules
```bash
curl -X PUT "$API_URL/api/v1/settings/profit-rules" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "min_roi": 30.00,
    "min_profit": 3.00,
    "max_rank": 100000
  }'
```

---

## 13. Notifications

### List Notifications
```bash
curl -X GET "$API_URL/api/v1/notifications" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Mark Notification as Read
```bash
curl -X POST "$API_URL/api/v1/notifications/NOTIFICATION_ID/read" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Mark All as Read
```bash
curl -X POST "$API_URL/api/v1/notifications/read-all" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 14. Watchlist

### Get Watchlist
```bash
curl -X GET "$API_URL/api/v1/watchlist" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Add to Watchlist
```bash
curl -X POST "$API_URL/api/v1/watchlist" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "asin": "B01GHFBKKA",
    "target_price": 25.00,
    "notify_on_price_drop": true
  }'
```

### Remove from Watchlist
```bash
curl -X DELETE "$API_URL/api/v1/watchlist/ITEM_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## 15. Users

### Get Current User Info
```bash
curl -X GET "$API_URL/api/v1/users/me" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

---

## Quick Test Script

Save this as `test_api.sh`:

```bash
#!/bin/bash
export BEARER_TOKEN="your_token_here"
export API_URL="https://habexa-backend-w5u5.onrender.com"

echo "Testing Health..."
curl -s "$API_URL/health" | jq '.'

echo -e "\nTesting Auth..."
curl -s -X GET "$API_URL/api/v1/auth/me" \
  -H "Authorization: Bearer $BEARER_TOKEN" | jq '.'

echo -e "\nTesting Products..."
curl -s -X GET "$API_URL/api/v1/products?limit=5" \
  -H "Authorization: Bearer $BEARER_TOKEN" | jq '.deals | length'

echo -e "\nTesting Subscription..."
curl -s -X GET "$API_URL/api/v1/billing/subscription" \
  -H "Authorization: Bearer $BEARER_TOKEN" | jq '.tier'
```

Run: `chmod +x test_api.sh && ./test_api.sh`

---

## Notes

- **Token Expiration:** Tokens expire after ~1 hour. Get a fresh one from browser DevTools.
- **Rate Limits:** Be mindful of API rate limits, especially for Keepa and SP-API endpoints.
- **Error Responses:** All errors return JSON with `detail` field.
- **Pagination:** Use `limit` and `offset` query params for paginated endpoints.
- **File Uploads:** Use `-F` flag for multipart/form-data uploads.

---

## Common Response Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid/expired token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

