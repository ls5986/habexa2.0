# Post-Migration Checklist

**Migration Status:** ✅ Complete  
**Date:** December 12, 2024

---

## ✅ STEP 1: Verify Database Tables

Run this in Supabase SQL Editor to verify all tables were created:

```sql
-- Check all new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'recommendation_configs',
    'recommendation_runs',
    'recommendation_results',
    'product_pack_variants',
    'prep_instructions',
    'brand_restrictions',
    'supplier_brand_overrides',
    'product_brand_flags',
    'email_templates',
    'po_generations',
    'email_tracking',
    'inventory_snapshots',
    'inventory_forecasts',
    'reorder_alerts',
    'shipping_cost_profiles',
    'supplier_performance',
    'order_variances',
    'financial_transactions',
    'pl_summaries',
    'upload_templates'
  )
ORDER BY table_name;
```

**Expected:** Should return 20 rows (all tables)

---

## ✅ STEP 2: Test Backend Services

### 2.1 Test Recommendations API
```bash
# Start backend if not running
cd backend
python -m uvicorn app.main:app --reload

# Test endpoint (in another terminal)
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": "YOUR_SUPPLIER_ID",
    "goal_type": "meet_minimum",
    "goal_params": {"budget": 2000},
    "min_roi": 30
  }'
```

### 2.2 Test Shipping Profiles API
```bash
curl -X GET http://localhost:8000/api/v1/shipping-profiles?supplier_id=YOUR_SUPPLIER_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2.3 Test Upload Templates API
```bash
curl -X GET http://localhost:8000/api/v1/upload-templates \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ✅ STEP 3: Test Frontend Components

### 3.1 Recommendations Page
1. Navigate to `/recommendations` in your app
2. Select a supplier
3. Set a goal (e.g., "Meet Minimum Order: $2000")
4. Click "Generate Recommendations"
5. Verify results display

### 3.2 Pack Selector
1. Go to Analyzer
2. Find a product with multiple pack sizes
3. Click on pack size dropdown
4. Verify "Pack Economics" dialog opens
5. Check PPU calculations

### 3.3 Brand Restrictions Tab
1. Go to a Supplier Detail page
2. Click "Brand Restrictions" tab
3. Click "Add Brand Restriction"
4. Add a test brand
5. Verify it saves

### 3.4 Cost Type Selector
1. Go to a product detail page
2. Find cost type selector
3. Switch between Unit/Pack/Case
4. Verify cost breakdown updates

---

## ✅ STEP 4: Schedule Background Jobs

### 4.1 Inventory Sync (Daily)
Add to your Celery beat schedule:

```python
# In celery_app.py or wherever you configure Celery beat
from celery.schedules import crontab

app.conf.beat_schedule = {
    'sync-inventory-daily': {
        'task': 'app.tasks.inventory_tasks.sync_fba_inventory_daily',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'update-forecasts-daily': {
        'task': 'app.tasks.inventory_tasks.update_inventory_forecasts',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily (after inventory sync)
    },
    'calculate-supplier-performance': {
        'task': 'app.tasks.supplier_performance_tasks.calculate_supplier_performance',
        'schedule': crontab(hour=4, minute=0, day_of_week=1),  # Monday 4 AM
    },
}
```

### 4.2 Start Celery Worker & Beat
```bash
# Terminal 1: Celery Worker
celery -A app.celery_app worker --loglevel=info

# Terminal 2: Celery Beat (scheduler)
celery -A app.celery_app beat --loglevel=info
```

---

## ✅ STEP 5: Seed Initial Data (Optional)

### 5.1 Seed Brand Restrictions
```sql
-- Add some common restricted brands
INSERT INTO brand_restrictions (brand_name, brand_name_normalized, restriction_type, verified_at, verified_by)
VALUES
  ('Nike', 'nike', 'globally_gated', NOW(), 'system'),
  ('Apple', 'apple', 'globally_gated', NOW(), 'system'),
  ('Sony', 'sony', 'globally_gated', NOW(), 'system'),
  ('Disney', 'disney', 'globally_gated', NOW(), 'system'),
  ('Adidas', 'adidas', 'globally_gated', NOW(), 'system')
ON CONFLICT (brand_name_normalized) DO NOTHING;
```

### 5.2 Create Default Shipping Profile
Do this via the UI or API for each supplier you use.

---

## ✅ STEP 6: Integration Testing

### 6.1 Test Full Workflow
1. **Upload Products** → Verify pack variants are discovered
2. **Create Buy List** → Add products with different pack sizes
3. **Generate Recommendations** → Test recommendation engine
4. **Create Supplier Order** → Verify prep instructions generate
5. **Track Inventory** → Verify snapshots are created

### 6.2 Test Error Handling
- Try invalid data
- Test with missing supplier
- Test with restricted brands
- Verify error messages are clear

---

## ✅ STEP 7: Monitor & Debug

### 7.1 Check Logs
```bash
# Backend logs
tail -f backend/logs/app.log

# Celery worker logs
tail -f celery_worker.log

# Check for errors
grep -i error backend/logs/app.log
```

### 7.2 Monitor Database
```sql
-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'recommendation%'
  OR tablename LIKE 'inventory%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🎯 QUICK START GUIDE

**If you just want to test one feature right now:**

1. **Test Recommendations:**
   - Go to `/recommendations`
   - Select a supplier
   - Set goal: "Meet Minimum: $2000"
   - Generate recommendations
   - Add to buy list

2. **Test Pack Variants:**
   - Go to Analyzer
   - Find a product
   - Check if pack variants are shown
   - Click "View Pack Economics"

3. **Test Brand Restrictions:**
   - Go to Supplier Detail
   - Click "Brand Restrictions" tab
   - Add a test brand

---

## ⚠️ COMMON ISSUES

### Issue: "Table doesn't exist"
- **Fix:** Re-run the migration
- **Check:** Verify table exists with SQL query above

### Issue: "Column doesn't exist"
- **Fix:** Check if column was added to existing table
- **Run:** `\d table_name` in psql to see columns

### Issue: "API endpoint not found"
- **Fix:** Restart backend server
- **Check:** Verify router is included in `main.py`

### Issue: "Background jobs not running"
- **Fix:** Start Celery worker and beat
- **Check:** Verify Redis is running

---

## 📊 SUCCESS CRITERIA

✅ All 20 tables created  
✅ Backend APIs respond without errors  
✅ Frontend pages load and display data  
✅ Background jobs run on schedule  
✅ Can create recommendations  
✅ Can add brand restrictions  
✅ Pack variants display correctly  

**When all checked → System is ready for production use!** 🚀

---

## 🆘 NEED HELP?

If something doesn't work:
1. Check error logs
2. Verify database tables exist
3. Check backend is running
4. Verify API endpoints are registered
5. Test with curl/Postman first, then frontend

