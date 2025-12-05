# Manual Actions Required

## Date: 2025-12-05

This document lists all tasks that require manual intervention (cannot be automated).

---

## 1. Database Migrations

### Verify All Tables Exist

Run this SQL in Supabase Dashboard → SQL Editor to verify all tables exist:

```sql
-- Check core tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'profiles', 'suppliers', 'products', 'product_sources', 
    'analyses', 'deals', 'orders', 'watchlist', 'favorites',
    'subscriptions', 'jobs', 'upload_jobs', 'upload_chunks',
    'supplier_column_mappings', 'upc_asin_cache',
    'amazon_connections', 'telegram_channels', 'keepa_cache',
    'notifications', 'user_settings', 'user_cost_settings'
)
ORDER BY table_name;
```

### Missing Tables

If any tables are missing, run the appropriate migration from `database/migrations/`:
- `CREATE_UPLOAD_SYSTEM.sql` - For upload system tables
- `ADD_ASIN_STATUS.sql` - For ASIN status tracking
- Other migrations as needed

### Indexes for Performance

Run these indexes to improve query performance (currently slow queries 0.8-2.9s):

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

---

## 2. Render Environment Variables

### Backend Service (habexa-backend)

Verify these are set in Render dashboard:

**Required:**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service role key
- `SUPABASE_JWT_SECRET` - Supabase JWT secret
- `SP_API_REFRESH_TOKEN` - Amazon SP-API refresh token
- `SP_API_LWA_APP_ID` - Amazon LWA app ID
- `SP_API_LWA_CLIENT_SECRET` - Amazon LWA client secret
- `SP_API_ROLE_ARN` - Amazon IAM role ARN
- `KEEPA_API_KEY` - Keepa API key
- `STRIPE_SECRET_KEY` - Stripe secret key
- `REDIS_URL` - Redis connection URL
- `CELERY_BROKER_URL` - Celery broker URL (usually same as REDIS_URL)

**Optional:**
- `SUPER_ADMIN_EMAILS` - Comma-separated admin emails
- `FRONTEND_URL` - Frontend URL for CORS
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - For S3 (if used)

### Celery Worker Service (habexa-celery-worker)

**CRITICAL:** Ensure ALL backend env vars are copied to the worker service, especially:
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`
- `SP_API_*` variables
- `KEEPA_API_KEY`
- `REDIS_URL`, `CELERY_BROKER_URL`

### Frontend Service (habexa-frontend)

Verify in `frontend/.env.production`:
- `VITE_API_URL` - Should be `https://habexa-backend-w5u5.onrender.com`
- `VITE_SUPABASE_URL` - Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anon key

---

## 3. Code Deployment

### Deploy Backend Fixes

After fixes are committed:
1. Push to main branch (or trigger Render auto-deploy)
2. Wait for backend deployment to complete
3. Verify health endpoint: `curl https://habexa-backend-w5u5.onrender.com/health`

### Deploy Frontend

1. Rebuild frontend: `cd frontend && pnpm build`
2. Verify `dist/` contains built files
3. Push to trigger Render static site deployment

---

## 4. Frontend Components to Implement

### Favorites Feature

**Backend:** ✅ Complete (all endpoints ready)
**Frontend:** ⏳ Needs implementation

**Files to create/modify:**
- `frontend/src/components/features/products/FavoriteButton.jsx` - Toggle favorite button
- `frontend/src/pages/Favorites.jsx` - Favorites list page
- Add to `frontend/src/App.jsx` - Route for `/favorites`
- Add to `frontend/src/components/layout/Sidebar.jsx` - Menu item

**API Endpoints Available:**
- `POST /api/v1/favorites` - Add favorite
- `DELETE /api/v1/favorites/{product_id}` - Remove favorite
- `GET /api/v1/favorites/check/{product_id}` - Check if favorited
- `GET /api/v1/favorites` - List all favorites

---

## 5. Performance Optimizations

### Slow API Requests (2-3 seconds)

**Current Issues:**
- `/api/v1/billing/user/limits` - 1.3s
- `/api/v1/deals` - 0.8s
- `/api/v1/sp-api/product/{asin}/sales-estimate` - 2.9s

**Recommendations:**

1. **Add Response Caching:**
   - Cache user limits for 5 minutes
   - Cache deals list for 1 minute
   - Cache SP-API responses per ASIN for 1 hour

2. **Database Query Optimization:**
   - Add indexes (see section 1)
   - Use materialized views for aggregations
   - Add query result caching in Redis

3. **API Call Optimization:**
   - Batch SP-API calls where possible
   - Use Keepa cache more aggressively
   - Parallelize independent API calls

---

## 6. Testing

### API Endpoint Testing

Create and run test script (see `AUDIT_OUTPUT/test_api.py`):
1. Get auth token from browser DevTools
2. Update `TOKEN` variable in script
3. Run: `python3 AUDIT_OUTPUT/test_api.py`
4. Review results in `09_TEST_RESULTS.md`

### Manual Testing Checklist

- [ ] Login/Register works
- [ ] Products page loads
- [ ] File upload works
- [ ] Product analysis completes
- [ ] Deal detail page shows all data
- [ ] Keepa charts display
- [ ] SP-API data loads
- [ ] Favorites button works (after implementation)
- [ ] Settings page saves changes
- [ ] Billing/subscription works

---

## 7. Monitoring

### Set Up Log Monitoring

**Render Logs:**
- Monitor backend logs for errors
- Check Celery worker logs for task failures
- Watch for slow request warnings

**Key Metrics to Track:**
- API response times
- Celery task completion rates
- Keepa API token usage
- SP-API rate limit hits
- Database query times

---

## 8. Documentation Updates

### API Documentation

- Generate OpenAPI/Swagger docs from FastAPI
- Document all endpoints with examples
- Add authentication requirements

### User Documentation

- Create user guide for file upload
- Document column mapping process
- Explain analysis stages
- Guide for subscription tiers

---

## Summary

| Category | Items | Priority |
|----------|-------|----------|
| Database | Indexes, table verification | HIGH |
| Environment | Verify all env vars | CRITICAL |
| Frontend | Favorites UI | MEDIUM |
| Performance | Caching, optimization | MEDIUM |
| Testing | API tests, manual tests | HIGH |
| Monitoring | Log monitoring setup | MEDIUM |

---

**Last Updated:** 2025-12-05

