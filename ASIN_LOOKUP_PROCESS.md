# UPC→ASIN→SP-API/Keepa Process Flow

## Current Process (FIXED)

### 1. CSV Upload with UPCs (no ASINs)

**Endpoint:** `POST /api/v1/products/upload/confirm`

**What happens:**
1. Products created with `asin = "PENDING_{UPC}"` and `lookup_status = 'pending'`
2. Job record created in `jobs` table with `type = 'asin_lookup'`
3. **Decision point:**
   - **>100 products:** Queues to Celery background task `lookup_product_asins.delay(product_ids)`
   - **≤100 products:** Processes immediately with parallel batches

### 2. UPC→ASIN Conversion

**Celery Task:** `app.tasks.asin_lookup.lookup_product_asins`

**What it does:**
1. Gets products with UPCs from database
2. Extracts unique UPCs
3. Checks `upc_asin_cache` table for cached results
4. **FIXED:** Processes uncached UPCs in **batches of 20** (SP-API limit)
   - Before: Only processed first 20 UPCs ❌
   - After: Processes ALL UPCs in batches ✅
5. Calls SP-API `search_catalog_items` with up to 20 UPCs per request
6. Updates products:
   - `asin` = found ASIN
   - `lookup_status` = 'found'
   - `asin_status` = 'found'
   - `status` = 'pending' (ready for analysis)
7. Caches results in `upc_asin_cache` table
8. Queues products with ASINs for analysis

### 3. ASIN→SP-API + Keepa Analysis

**Celery Task:** `app.tasks.analysis.batch_analyze_products`

**What it does:**
1. Gets products with ASINs (status = 'pending')
2. For each product:
   - Calls SP-API for pricing, fees, eligibility
   - Calls Keepa API for sales rank, price history
   - Calculates profit, ROI, deal score
3. Updates product with analysis results
4. Updates `product_sources` (deals) with profitability data

---

## What Was Broken (FIXED)

### Bug #1: Only First 20 UPCs Processed ❌
**Problem:** `lookup_product_asins` called `upcs_to_asins_batch(uncached_upcs)` with ALL UPCs, but the method only processes first 20.

**Fix:** Now processes UPCs in batches of 20, calling the method multiple times.

**Code:**
```python
# BEFORE (BROKEN):
batch_results = run_async(upc_converter.upcs_to_asins_batch(uncached_upcs))  # Only first 20!

# AFTER (FIXED):
for batch_idx in range(0, len(uncached_upcs), 20):
    batch_upcs = uncached_upcs[batch_idx:batch_idx + 20]
    batch_results = run_async(upc_converter.upcs_to_asins_batch(batch_upcs))
    lookups.update(batch_results)
```

### Bug #2: Large Uploads Blocking HTTP Request ❌
**Problem:** Uploads >100 items tried to process immediately, causing timeouts.

**Fix:** Large uploads now queue to Celery immediately.

### Bug #3: No Job Tracking ❌
**Problem:** ASIN lookup jobs weren't visible in Upload Jobs UI.

**Fix:** Jobs are now created and tracked in `jobs` table.

---

## Expected Flow for 5000 UPC Upload

1. **Upload:** Creates 5000 products with `PENDING_` ASINs
2. **Job Created:** `jobs` table gets record with `type='asin_lookup'`, `status='pending'`
3. **Celery Task Queued:** `lookup_product_asins.delay(product_ids)` 
4. **Worker Processes:**
   - Extracts 5000 UPCs
   - Checks cache (maybe 1000 cached)
   - Processes 4000 uncached UPCs in batches of 20 = **200 API calls**
   - Each batch takes ~2-3 seconds = **~10 minutes total**
5. **Products Updated:** ASINs saved to database
6. **Analysis Queued:** Products with ASINs queued for SP-API + Keepa analysis
7. **Analysis Processes:** Background analysis runs

---

## Verification

### Check if UPC→ASIN is working:
```sql
-- Products with UPCs that got ASINs
SELECT COUNT(*) 
FROM products 
WHERE upc IS NOT NULL 
  AND asin IS NOT NULL 
  AND asin NOT LIKE 'PENDING_%'
  AND lookup_status = 'found';
```

### Check if stuck:
```sql
-- Products stuck in pending
SELECT COUNT(*) 
FROM products 
WHERE lookup_status = 'pending' 
  AND upc IS NOT NULL 
  AND upc != '';
```

### Check Celery task execution:
```sql
-- Recent ASIN lookup jobs
SELECT id, status, total_items, processed_items, progress, created_at
FROM jobs
WHERE type = 'asin_lookup'
ORDER BY created_at DESC
LIMIT 5;
```

---

## Debugging

If ASINs aren't being found:

1. **Check Celery logs** - Look for:
   - `✅ Queued Celery ASIN lookup task` - Task queued
   - `📦 Found X products with UPCs` - Task executing
   - `🚀 Calling SP-API for X UPCs` - API calls happening
   - `✅ SP-API lookup complete: X/Y found` - Results
   - `❌ Error` - Something failed

2. **Check SP-API credentials** - Look for:
   - `No access token available` - Credentials issue
   - `SP-API error: 401` - Auth failed
   - `SP-API error: 429` - Rate limited

3. **Check database**:
   - Are products created with `PENDING_` ASINs?
   - Is `lookup_status` = 'pending'?
   - Are jobs being created?

4. **Check Redis/Celery**:
   - Is Celery worker running?
   - Are tasks being queued?
   - Check Redis for queued tasks

