# Deployment Checklist

**Date:** 2025-12-05
**Status:** ✅ Code fixes deployed

## ✅ Step 1: Code Fixes Deployed

```bash
✅ Committed fixes
✅ Pushed to origin/main
⏳ Waiting for Render deployment (~2-3 minutes)
```

**Files Deployed:**
- `backend/app/api/v1/keepa.py` - Keepa 404 fixes + fallback
- `backend/app/api/v1/sp_api.py` - SP-API fees parameter fix

**Check Deployment:**
```bash
# Wait 2-3 minutes, then check:
curl https://habexa-backend-w5u5.onrender.com/health
# Should return: {"status":"healthy","timestamp":"..."}
```

---

## ⏳ Step 2: Database Indexes (Manual - Supabase)

**Go to:** Supabase Dashboard → SQL Editor

**Run this SQL:**

```sql
-- Products indexes
CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_asin ON products(asin);
CREATE INDEX IF NOT EXISTS idx_products_asin_status ON products(asin_status) WHERE asin_status IS NOT NULL;

-- Product sources indexes
CREATE INDEX IF NOT EXISTS idx_product_sources_product_id ON product_sources(product_id);
CREATE INDEX IF NOT EXISTS idx_product_sources_supplier_id ON product_sources(supplier_id);
CREATE INDEX IF NOT EXISTS idx_product_sources_stage ON product_sources(stage);

-- Analyses indexes
CREATE INDEX IF NOT EXISTS idx_analyses_product_id ON analyses(product_id);
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_pricing_status ON analyses(pricing_status);

-- Deals indexes
CREATE INDEX IF NOT EXISTS idx_deals_user_id ON deals(user_id);
CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);

-- Jobs indexes
CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
```

**Expected Result:** All indexes created successfully

---

## ⏳ Step 3: Verify Environment Variables (Manual - Render)

**Go to:** Render Dashboard → habexa-celery-worker → Environment

**Verify these exist:**

| Variable | Status | Notes |
|----------|--------|-------|
| `KEEPA_API_KEY` | ⬜ | Must match backend |
| `SP_API_REFRESH_TOKEN` | ⬜ | Must match backend |
| `SP_API_LWA_APP_ID` | ⬜ | Must match backend |
| `SP_API_LWA_CLIENT_SECRET` | ⬜ | Must match backend |
| `SUPABASE_URL` | ⬜ | Must match backend |
| `SUPABASE_KEY` | ⬜ | Must match backend |
| `SUPABASE_JWT_SECRET` | ⬜ | Must match backend |
| `REDIS_URL` | ⬜ | Must match backend |
| `CELERY_BROKER_URL` | ⬜ | Usually same as REDIS_URL |

**Action:** Copy all env vars from `habexa-backend` to `habexa-celery-worker` if missing

---

## ⏳ Step 4: Test After Deploy

**Wait for deployment to complete, then:**

### 4.1 Get Auth Token

1. Go to https://habexa-frontend.onrender.com
2. Login
3. Open DevTools → Network tab
4. Click any action (e.g., go to Products page)
5. Find any API request (e.g., `/api/v1/products`)
6. Copy the `Authorization: Bearer <token>` value

### 4.2 Run API Tests

```bash
cd ~/habexa2.0/AUDIT_OUTPUT

# Edit test file
nano test_api.py
# Update: TOKEN = "your_token_here"

# Run tests
python3 test_api.py
```

**Expected:** Most endpoints return 200 OK

### 4.3 Manual Testing

1. **Open Product Detail:**
   - Go to Products page
   - Click any product
   - Verify Keepa charts load (no 404 errors)
   - Verify SP-API data displays

2. **Check Browser Console:**
   - Open DevTools → Console
   - Look for errors
   - Should see no Keepa 404 errors

3. **Check Network Tab:**
   - Look for `/api/v1/keepa/product/...` requests
   - Should return 200 (not 404)
   - Response should have structure (even if empty)

---

## ✅ Step 5: Verify Fixes

### Keepa Fix Verification

**Before:** `GET /api/v1/keepa/product/{asin} 404 Not Found`

**After:** Should return 200 with structure:
```json
{
  "asin": "B07Y93SMRV",
  "error": "No data available from Keepa",
  "stats": {},
  "price_history": [],
  "rank_history": [],
  "current": {},
  "averages": {}
}
```

### SP-API Fees Fix Verification

**Before:** `SPAPIClient.get_fee_estimate() got an unexpected keyword argument 'is_fba'`

**After:** Should return 200 with fees data:
```json
{
  "asin": "B07Y93SMRV",
  "price": 19.99,
  "total_fees": 3.45,
  "referral_fee": 1.20,
  "fba_fulfillment_fee": 2.25
}
```

---

## Summary

| Task | Status | Notes |
|------|--------|-------|
| Code fixes deployed | ✅ | Pushed to main |
| Render deployment | ⏳ | Wait 2-3 min |
| Database indexes | ⏳ | Manual - Supabase |
| Env vars verified | ⏳ | Manual - Render |
| API tests run | ⏳ | Needs token |
| Manual testing | ⏳ | After deploy |

---

**Next:** Complete steps 2-4 after deployment finishes.

