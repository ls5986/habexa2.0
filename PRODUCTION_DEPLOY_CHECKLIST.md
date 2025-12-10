# Production Deployment Checklist

## Pre-Deploy

- [ ] All code committed and pushed to main branch
- [ ] requirements.txt up to date
- [ ] Database migrations ready
- [ ] Environment variables documented
- [ ] Celery tasks tested locally
- [ ] Redis connection tested

## Database Setup

- [ ] Run all migrations in Supabase SQL Editor:
  - [ ] `VERIFY_PRODUCTS_SCHEMA.sql` - Verify all columns exist
  - [ ] `ADD_ASIN_LOOKUP_TRACKING.sql` - Add lookup_status, lookup_attempts, asin_found_at
  - [ ] `CREATE_ASIN_STATS_RPC.sql` - Create get_asin_stats function
  - [ ] `CREATE_FILTER_PRODUCTS_RPC.sql` - Create filter_product_deals function
- [ ] Verify all columns exist: `SELECT * FROM products LIMIT 1`
- [ ] Verify indexes created: Check Supabase dashboard
- [ ] Test RLS policies work

## Render Configuration

### Backend Service

- [ ] **REDIS_URL** set (internal URL: `redis://red-xxxxx:6379`)
- [ ] **DATABASE_URL** set (Supabase connection string)
- [ ] **SUPABASE_URL** set
- [ ] **SUPABASE_KEY** set (service role key)
- [ ] **CELERY_BROKER_URL** = REDIS_URL
- [ ] **CELERY_RESULT_BACKEND** = REDIS_URL
- [ ] **SELLERAMP_API_KEY** set
- [ ] **STRIPE_API_KEY** set (if using Stripe)
- [ ] **JWT_SECRET_KEY** set
- [ ] **OPENAI_API_KEY** set (for column mapping)
- [ ] Auto-deploy enabled from main branch

### Celery Workers (if separate service)

- [ ] Same environment variables as backend
- [ ] Start command: `celery -A app.core.celery_app worker -l info --concurrency=4`
- [ ] 4 worker instances configured
- [ ] Health check endpoint configured

### Celery Beat (if separate service)

- [ ] Same environment variables
- [ ] Start command: `celery -A app.core.celery_app beat -l info`
- [ ] Only 1 instance (Beat should not scale)
- [ ] Health check endpoint configured

### Redis Service

- [ ] Plan: Starter or higher
- [ ] Region: Same as backend (Oregon)
- [ ] Status: Available (green)
- [ ] Internal URL copied to backend env vars
- [ ] Memory limit appropriate for cache size

## Deploy Steps

1. [ ] Push code to GitHub
2. [ ] Verify Render auto-deploy triggers
3. [ ] Watch build logs for errors
4. [ ] Wait for "Live" status
5. [ ] Check logs for startup messages:
   - [ ] "✅ Redis connected successfully"
   - [ ] "✅ Application started successfully"
   - [ ] Celery tasks imported successfully

## Post-Deploy Verification

### API Tests

- [ ] Test auth: `curl -X POST https://habexa-backend-w5u5.onrender.com/api/v1/auth/login`
- [ ] Test Redis: Check `/api/v1/products/cache-status`
- [ ] Test stats: Check `/api/v1/products/stats/asin-status` (should be <50ms on cache hit)
- [ ] Test upload: Upload test CSV via `/api/v1/products/upload/preview`
- [ ] Test lookup status: Check `/api/v1/products/lookup-status`
- [ ] Run production test script: `python tests/production_test.py`

### Celery Verification

- [ ] Check Celery worker logs for task processing
- [ ] Check Celery Beat logs for scheduled tasks
- [ ] Verify `process-pending-asins` task runs every 5 minutes
- [ ] Upload a test CSV and verify ASIN lookup is queued
- [ ] Check lookup-status endpoint shows progress

### Performance Checks

- [ ] Stats endpoint <50ms (cached)
- [ ] Products list endpoint <500ms
- [ ] Upload preview <5 seconds
- [ ] Redis cache hit rate >40%

### Functional Tests

- [ ] Upload CSV with UPCs → ASINs found within 5 minutes
- [ ] Products appear in products list after upload
- [ ] ASIN status filters work correctly
- [ ] Bulk actions work (analyze, delete, move)
- [ ] Analysis completes for products with ASINs

## Monitoring

- [ ] Monitor logs for 30 minutes after deploy
- [ ] Check for any error patterns
- [ ] Verify Celery tasks are processing
- [ ] Check Redis memory usage
- [ ] Monitor API response times

## Rollback Plan

If deploy fails:

1. [ ] Revert to previous Git commit
2. [ ] Redeploy from Render dashboard
3. [ ] Verify rollback successful
4. [ ] Debug issue in separate branch
5. [ ] Fix and redeploy

## Success Criteria

- [ ] Auth works (login/signup)
- [ ] Redis cache hit rate > 40%
- [ ] Stats endpoint < 50ms (cached)
- [ ] CSV upload completes in < 5 seconds
- [ ] ASINs found within 5 minutes
- [ ] Celery tasks processing
- [ ] No errors in logs for 1 hour
- [ ] Test user can complete full workflow:
  - [ ] Upload CSV
  - [ ] See products in list
  - [ ] ASINs auto-lookup
  - [ ] Products analyzed
  - [ ] Can filter by ASIN status
  - [ ] Can bulk delete/analyze

## Environment Variables Reference

### Required

```bash
# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Redis
REDIS_URL=redis://red-xxxxx:6379
CELERY_BROKER_URL=redis://red-xxxxx:6379
CELERY_RESULT_BACKEND=redis://red-xxxxx:6379

# APIs
SELLERAMP_API_KEY=xxxxx
OPENAI_API_KEY=sk-xxxxx

# Auth
JWT_SECRET_KEY=xxxxx

# Optional
STRIPE_API_KEY=sk_xxxxx
```

## Troubleshooting

### Redis not connecting
- Check REDIS_URL is correct
- Verify Redis service is running
- Check network connectivity between services

### Celery tasks not running
- Verify Celery workers are running
- Check CELERY_BROKER_URL is set
- Check task imports in celery_app.py

### ASIN lookup not working
- Check UPCs are valid
- Verify SP-API credentials
- Check Celery task logs for errors

### Upload failing
- Check file size limits
- Verify column mapping
- Check NaN handling in logs

