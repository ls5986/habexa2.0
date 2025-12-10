# Debugging UPC→ASIN Lookup Failure

## Step 1: Check Product Records in Database

Run the debug script:
```bash
python debug_asin_lookup.py
```

Or query directly in Supabase SQL Editor:
```sql
-- Get recent products with UPCs
SELECT 
    id,
    asin,
    upc,
    title,
    lookup_status,
    asin_status,
    status,
    lookup_attempts,
    created_at
FROM products
WHERE upc IS NOT NULL 
  AND upc != ''
ORDER BY created_at DESC
LIMIT 10;
```

**What to look for:**
- Is `asin` NULL or `PENDING_XXXXXXXX`?
- Is `lookup_status` stuck on `'pending'`?
- Is `lookup_attempts` > 0? (means task tried but failed)

---

## Step 2: Get Celery Worker Logs from Render

### Option A: Render Dashboard
1. Go to https://dashboard.render.com
2. Click on your **Celery Worker** service
3. Click **Logs** tab
4. Filter by: `asin_lookup` or `lookup_product_asins`
5. Copy the last 50 lines

### Option B: Render CLI
```bash
# Install Render CLI
npm install -g render-cli

# Login
render login

# Get logs
render logs --service <your-celery-worker-service-name> --tail 50
```

### Option C: SSH into Render
```bash
# SSH into your Celery worker
render ssh <your-celery-worker-service-name>

# View logs
tail -n 50 /var/log/celery/worker.log
# OR
journalctl -u celery -n 50
```

**What to look for in logs:**
- `✅ Queued Celery ASIN lookup task` - Task was queued
- `📦 Found X products with UPCs` - Task is executing
- `❌ Error in lookup_product_asins` - Task failed
- `SP-API` errors - API call failed
- `No access token available` - Credentials issue

---

## Step 3: Check Upload Endpoint Response

After uploading a CSV, check the response in browser DevTools:

**Expected response for >100 items:**
```json
{
  "success": true,
  "total": 5000,
  "created": 5000,
  "failed": 0,
  "asin_lookup": {
    "converted": 0,
    "failed": 0,
    "multiple_found": 0,
    "not_found": 0,
    "products_ready_for_analysis": []
  },
  "message": "5000 products created"
}
```

**Expected response for <=100 items:**
```json
{
  "success": true,
  "total": 50,
  "created": 50,
  "failed": 0,
  "asin_lookup": {
    "converted": 45,
    "failed": 2,
    "multiple_found": 1,
    "not_found": 2,
    "products_ready_for_analysis": [...]
  },
  "message": "50 products created. 45 UPC→ASIN conversions completed immediately. 45 products queued for immediate analysis"
}
```

**Check if job_id is created:**
```sql
-- Check for recent ASIN lookup jobs
SELECT 
    id,
    type,
    status,
    total_items,
    processed_items,
    progress,
    created_at,
    metadata
FROM jobs
WHERE type = 'asin_lookup'
ORDER BY created_at DESC
LIMIT 5;
```

---

## Step 4: Verify Celery is Running

### Check if Celery worker is active:
```bash
# On Render, check service status
# Should show "Live" status
```

### Check if tasks are being queued:
```sql
-- Check Redis/Celery task queue (if you have access)
-- Or check job records
SELECT COUNT(*) as pending_jobs
FROM jobs
WHERE type = 'asin_lookup'
  AND status IN ('pending', 'processing');
```

---

## Common Issues & Fixes

### Issue 1: Task not queued
**Symptoms:** No job_id in response, no job record in database
**Fix:** Check if Celery is configured correctly, Redis connection

### Issue 2: Task queued but not executing
**Symptoms:** Job status stuck on 'pending', no Celery logs
**Fix:** Check if Celery worker is running, check Redis connection

### Issue 3: Task executing but SP-API failing
**Symptoms:** Job status 'processing' but no ASINs found, SP-API errors in logs
**Fix:** Check SP-API credentials, rate limits, API errors

### Issue 4: SP-API works but ASIN not saved
**Symptoms:** Logs show ASIN found but database still has PENDING_
**Fix:** Check database update code, permissions, transaction issues

---

## Quick Test

Test the lookup manually:
```python
from app.tasks.asin_lookup import lookup_product_asins

# Get a product ID with UPC
product_id = "your-product-id-here"

# Run lookup
result = lookup_product_asins([product_id])
print(result)
```

