# File Upload Flow - Complete API Call Documentation

## Overview
When you upload a CSV/Excel file, here's exactly what happens:

---

## STEP 1: File Upload Endpoint
**Endpoint:** `POST /api/v1/products/upload`

**What it does:**
1. Receives the file
2. Validates file format (CSV/Excel)
3. Creates a `job` record in database (type: `upload`)
4. Queues `process_file_upload` Celery task
5. Returns `job_id` for tracking

**No API calls made yet** - just file validation and job creation.

---

## STEP 2: File Processing Task
**Task:** `process_file_upload` (Celery background task)

**Location:** `backend/app/tasks/file_processing.py`

### 2.1 Parse File
- Reads CSV/Excel rows
- Maps columns to database fields
- Extracts UPCs, buy costs, MOQ, etc.

**No API calls yet.**

### 2.2 UPC → ASIN Conversion (BATCHED)
**API Calls:** SP-API `GetCatalogItems` (UPC lookup)

**How batching works:**
- Groups UPCs into batches of **20 UPCs per batch**
- Makes **one SP-API call per batch** (not per UPC!)
- Example: 100 UPCs = 5 API calls (20 + 20 + 20 + 20 + 20)

**Code location:** `backend/app/tasks/file_processing.py` lines ~600-800

**API Response Format:**
```json
{
  "upc": "123456789012",
  "asin": "B01ABC1234",
  "title": "Product Name",
  "brand": "Brand Name",
  "image": "https://...",
  ...
}
```

**What gets stored:**
- ✅ `asin` (if found)
- ✅ `potential_asins` (if multiple found)
- ✅ `asin_status` (`found`, `multiple_found`, `not_found`)
- ❌ **RAW SP-API RESPONSE IS NOT STORED HERE** (only during analysis)

**Rate Limiting:**
- 0.5 second delay between batches (2 requests/sec max)
- Uses semaphore for parallel processing (up to 5 concurrent batches)

---

## STEP 3: Product Creation
**What happens:**
- Products are inserted into `products` table
- `product_sources` (deals) are created/upserted
- Products without ASINs get `asin = NULL` (not `PENDING_`)

**No API calls yet.**

---

## STEP 4: API Data Fetching (NEW PRODUCTS WITH ASINs)
**Location:** `backend/app/tasks/file_processing.py` lines ~905-925

**API Calls Made:**
1. **SP-API:** `get_catalog_item(asin)` - Full product details
2. **Keepa:** `get_products_batch([asin])` - Historical data

**How it works:**
```python
for product in created_products:
    if product.asin and product.asin != "PENDING_":
        # Fetch BOTH APIs in parallel
        result = fetch_and_store_all_api_data(
            asin=product.asin,
            user_id=product.user_id,
            force_refresh=False
        )
```

**Batching:**
- **SP-API:** One call per ASIN (no batching currently)
- **Keepa:** One call per ASIN (no batching currently)
- **Problem:** If you upload 100 products, that's 200 API calls! (100 SP-API + 100 Keepa)

**What gets stored:**
- ✅ `sp_api_raw_response` (complete JSON)
- ✅ `keepa_raw_response` (complete JSON)
- ✅ `sp_api_last_fetched` (timestamp)
- ✅ `keepa_last_fetched` (timestamp)
- ✅ **All structured fields** extracted from responses (see `api_data_extractor.py`)

**Storage location:** `backend/app/services/api_storage_service.py`

---

## STEP 5: Auto-Analysis (OPTIONAL)
**Location:** `backend/app/tasks/file_processing.py` lines ~1140-1200

**What happens:**
- If products have real ASINs (not NULL, not PENDING_)
- Queues `batch_analyze_products` Celery task
- Processes in chunks of 50 products

**API Calls in Analysis:**
- SP-API: Catalog, Pricing, Fees, Eligibility
- Keepa: Historical data, sales rank, offers

**But wait:** Analysis should use **cached data** from Step 4!

---

## CURRENT PROBLEMS

### ❌ Problem 1: API Data Not Being Stored
**Issue:** Even though `fetch_and_store_all_api_data` is called, data might not be saved.

**Why:**
1. Missing `user_id` in storage calls (FIXED in recent commit)
2. Using `.upsert()` instead of `.update()` with proper filters (FIXED)
3. Products might not exist yet when API data is fetched

**Check:**
```sql
SELECT 
  id, asin, 
  sp_api_raw_response IS NOT NULL as has_sp_api,
  keepa_raw_response IS NOT NULL as has_keepa,
  sp_api_last_fetched,
  keepa_last_fetched
FROM products
WHERE user_id = 'your-user-id'
ORDER BY created_at DESC
LIMIT 10;
```

### ❌ Problem 2: No Batching for API Data Fetch
**Issue:** Each product triggers 2 separate API calls (SP-API + Keepa)

**Current:**
- 100 products = 200 API calls
- No batching
- Sequential processing

**Should be:**
- Batch SP-API calls (up to 20 ASINs per call)
- Batch Keepa calls (up to 100 ASINs per call)
- Process in parallel

### ❌ Problem 3: Duplicate API Calls
**Issue:** Analysis might re-fetch data even though it was just stored.

**Check:**
- `should_refresh_sp_data()` - checks if data is < 24 hours old
- `should_refresh_keepa_data()` - checks if data is < 24 hours old

**But:** If products are created and analyzed immediately, cache might not work.

---

## WHAT DATA IS MISSING?

### Check Your Database:
```sql
-- Products with ASINs but no API data
SELECT 
  COUNT(*) as missing_api_data,
  COUNT(*) FILTER (WHERE sp_api_raw_response IS NULL) as missing_sp_api,
  COUNT(*) FILTER (WHERE keepa_raw_response IS NULL) as missing_keepa
FROM products
WHERE asin IS NOT NULL 
  AND asin != ''
  AND asin NOT LIKE 'PENDING_%'
  AND user_id = 'your-user-id';
```

### Check Celery Logs:
Look for these log messages:
- `📡 Fetching complete API data for {asin}`
- `✅ Stored complete SP-API data for {asin}`
- `✅ Stored complete Keepa data for {asin}`
- `❌ Failed to fetch SP-API data for {asin}`

---

## FIXES NEEDED

### 1. Verify API Data Storage
Check if `fetch_and_store_all_api_data` is actually being called and succeeding:

```python
# In file_processing.py, add more logging:
logger.info(f"🔍 About to fetch API data for {asin}, user_id={product_user_id}")
result = run_async(fetch_and_store_all_api_data(asin, user_id=product_user_id, force_refresh=False))
logger.info(f"📦 API data result keys: {list(result.keys())}")
logger.info(f"📦 Has SP-API: {bool(result.get('sp_api_raw_response'))}")
logger.info(f"📦 Has Keepa: {bool(result.get('keepa_raw_response'))}")
```

### 2. Add Batching for API Calls
**SP-API:** Use `get_catalog_items_batch()` if available
**Keepa:** Already supports batching - use `get_products_batch([asin1, asin2, ...])`

### 3. Check for Errors
Look for exceptions in Celery logs:
- `❌ Failed to fetch SP-API data`
- `❌ Failed to fetch Keepa data`
- `Error storing API data`

---

## DEBUGGING STEPS

1. **Check if API calls are being made:**
   ```bash
   # In Celery worker logs, search for:
   grep "Fetching.*API data" celery.log
   ```

2. **Check if data is being stored:**
   ```sql
   SELECT asin, 
     sp_api_raw_response IS NOT NULL as has_sp,
     keepa_raw_response IS NOT NULL as has_keepa
   FROM products 
   WHERE user_id = 'your-user-id'
   ORDER BY created_at DESC;
   ```

3. **Check for errors:**
   ```bash
   grep "Failed to fetch\|Error storing" celery.log
   ```

4. **Verify user_id is being passed:**
   ```python
   # In file_processing.py line ~918
   # Should be:
   result = run_async(fetch_and_store_all_api_data(asin, user_id=product_user_id, force_refresh=False))
   # NOT:
   result = run_async(fetch_and_store_all_api_data(asin, force_refresh=False))
   ```

---

## EXPECTED BEHAVIOR

After uploading a file with 20 products:

1. ✅ 20 products created in database
2. ✅ UPCs converted to ASINs (batched SP-API calls)
3. ✅ For each product with ASIN:
   - SP-API data fetched and stored
   - Keepa data fetched and stored
   - Both raw responses saved to `products` table
4. ✅ Analysis queued (uses cached API data)
5. ✅ All data visible in "API Data" tab

---

## CURRENT STATUS

**What's working:**
- ✅ File upload and parsing
- ✅ UPC → ASIN conversion (batched)
- ✅ Product creation
- ✅ API data fetching code exists

**What might be broken:**
- ❓ API data not being stored (check logs)
- ❓ Missing `user_id` in storage calls (should be fixed)
- ❓ No batching for API data fetch (inefficient but should work)

**Next steps:**
1. Check Celery logs for API call errors
2. Verify database has `sp_api_raw_response` and `keepa_raw_response` columns
3. Check if `user_id` is being passed correctly
4. Add more logging to track data storage

