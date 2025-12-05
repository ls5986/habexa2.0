# How to Poll Job Results

Your analysis request was queued successfully! Here's how to get the results.

## Your Job Details

- **Job ID:** `fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933`
- **Product ID:** `ae2e3902-cb28-4883-99b0-f3615eb5d159`
- **ASIN:** `B01GHFBKKA` (converted from UPC `860124000177`)
- **Status:** `queued`

---

## Method 1: Poll with Script (Easiest)

I've created a polling script for you:

```bash
# Set your bearer token
export BEARER_TOKEN="your_token_here"

# Poll the job (uses your job_id by default)
./poll_job_results.sh

# Or specify a different job_id
./poll_job_results.sh fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933
```

The script will:
- Poll every 5 seconds
- Show progress updates
- Display final results when complete
- Timeout after 60 seconds (12 attempts)

---

## Method 2: Manual Curl Polling

```bash
# Set your token
export BEARER_TOKEN="your_token_here"

# Poll once
curl -X GET "https://habexa-backend-w5u5.onrender.com/api/v1/jobs/fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933" \
  -H "Authorization: Bearer $BEARER_TOKEN" | jq '.'
```

**Job Status Values:**
- `queued` - Waiting to start
- `in_progress` - Currently processing
- `completed` - Finished successfully
- `failed` - Error occurred

---

## Method 3: Watch Mode (Continuous Polling)

```bash
# Poll every 3 seconds until complete
watch -n 3 'curl -s -X GET "https://habexa-backend-w5u5.onrender.com/api/v1/jobs/fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933" \
  -H "Authorization: Bearer $BEARER_TOKEN" | jq "{status, progress, result}"'
```

---

## Expected Response Format

### While Processing:
```json
{
  "id": "fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933",
  "user_id": "...",
  "type": "analyze_single",
  "status": "in_progress",
  "progress": 50,
  "total_items": 1,
  "completed_items": 0,
  "success_count": 0,
  "error_count": 0,
  "created_at": "2025-01-04T...",
  "updated_at": "2025-01-04T..."
}
```

### When Completed:
```json
{
  "id": "fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933",
  "user_id": "...",
  "type": "analyze_single",
  "status": "completed",
  "progress": 100,
  "total_items": 1,
  "completed_items": 1,
  "success_count": 1,
  "error_count": 0,
  "result": {
    "analysis_id": "uuid-here",
    "product_id": "ae2e3902-cb28-4883-99b0-f3615eb5d159",
    "asin": "B01GHFBKKA"
  },
  "created_at": "2025-01-04T...",
  "completed_at": "2025-01-04T..."
}
```

---

## Quick Test Command

```bash
# One-liner to check status
curl -s -X GET "https://habexa-backend-w5u5.onrender.com/api/v1/jobs/fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933" \
  -H "Authorization: Bearer $BEARER_TOKEN" | jq '{status, progress, result}'
```

---

## Get Product Details After Analysis

Once the job is `completed`, you can get the full product details:

```bash
# Get product with analysis
curl -X GET "https://habexa-backend-w5u5.onrender.com/api/v1/products?asin=B01GHFBKKA" \
  -H "Authorization: Bearer $BEARER_TOKEN" | jq '.'
```

This will return the product with all analysis data (pricing, fees, profitability, etc.).

---

## Troubleshooting

**Job stuck in "queued" status:**
- Check if Celery workers are running on Render
- Check backend logs for errors

**Job status is "failed":**
- Check the `errors` field in the response
- Check backend logs for details

**Token expired (401 Unauthorized):**
- Get a fresh token from browser DevTools
- Or re-run `get_bearer_token.py`

---

## Typical Processing Time

- **Single product analysis:** 10-30 seconds
- **UPC to ASIN conversion:** Included in the time above
- **Full analysis (pricing + fees):** 15-45 seconds total

Your job should complete within 30-60 seconds.

