# Post-Migration Steps - Genius Score Columns Added ✅

**Status:** Fast migration completed successfully!

---

## ✅ STEP 1: VERIFY COLUMNS EXIST

Run this to confirm:

```sql
-- Check columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name LIKE 'genius%'
ORDER BY column_name;
```

**Expected output:**
```
column_name                      | data_type                  | is_nullable
---------------------------------+----------------------------+-------------
genius_breakdown                | jsonb                      | YES
genius_grade                    | text                       | YES
genius_insights                 | jsonb                      | YES
genius_score                    | numeric                    | YES
genius_score_last_calculated    | timestamp with time zone   | YES
```

---

## 🚀 STEP 2: START SCORING PRODUCTS

### Option A: Score All Products (Background Job)

```python
# In Python shell or Celery task
from app.tasks.genius_scoring_tasks import calculate_genius_scores

# Score all products for all users
calculate_genius_scores.delay()

# Or score specific products
product_ids = ['uuid1', 'uuid2', 'uuid3']
calculate_genius_scores.delay(product_ids=product_ids)

# Or score for specific user
calculate_genius_scores.delay(user_id='your-user-id')
```

### Option B: Score via API Endpoint

```bash
# Trigger scoring for all products
curl -X POST http://localhost:8000/api/v1/products/calculate-scores \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Option C: Score Single Product (Test)

```python
from app.services.genius_scorer import GeniusScorer
from app.services.supabase_client import supabase

# Get a test product
product = supabase.table('products').select('*').limit(1).execute().data[0]

# Score it
scorer = GeniusScorer()
result = scorer.calculate_genius_score(
    product_data=product,
    keepa_data=product.get('keepa_raw_response', {}),
    sp_api_data=product.get('sp_api_raw_response', {}),
    user_config={'min_roi': 25, 'max_fba_sellers': 30}
)

# Save to database
supabase.table('products').update({
    'genius_score': result['total_score'],
    'genius_grade': result['grade'],
    'genius_breakdown': result['breakdown'],
    'genius_insights': result['insights'],
    'genius_score_last_calculated': 'now()'
}).eq('id', product['id']).execute()
```

---

## 📊 STEP 3: VERIFY SCORES ARE BEING CALCULATED

```sql
-- Check if any products have scores
SELECT 
    COUNT(*) as total_products,
    COUNT(genius_score) as scored_products,
    AVG(genius_score) as avg_score,
    COUNT(CASE WHEN genius_grade = 'EXCELLENT' THEN 1 END) as excellent,
    COUNT(CASE WHEN genius_grade = 'GOOD' THEN 1 END) as good,
    COUNT(CASE WHEN genius_grade = 'FAIR' THEN 1 END) as fair,
    COUNT(CASE WHEN genius_grade = 'POOR' THEN 1 END) as poor
FROM products;

-- See top scored products
SELECT 
    title,
    genius_score,
    genius_grade,
    roi_percentage,
    profit_amount
FROM products
WHERE genius_score IS NOT NULL
ORDER BY genius_score DESC
LIMIT 10;
```

---

## 🎨 STEP 4: TEST IN FRONTEND

1. **Open Analyzer** (`/analyzer`)
2. **Look for "Genius Score" column**
3. **Should see:**
   - Numbers (0-100)
   - Grade badges (🟢 EXCELLENT, 🟡 GOOD, 🟠 FAIR, 🔴 POOR)
4. **Click column header to sort by score**
5. **Filter by score** (if filter UI exists)

---

## ⚡ STEP 5: ADD INDEXES (LATER - NON-CRITICAL)

**The system works without indexes!** They just make queries faster.

**Add indexes when convenient (during off-peak hours):**

```sql
-- Index 1: For sorting by score (most important)
CREATE INDEX CONCURRENTLY idx_products_genius_score 
ON products(genius_score DESC NULLS LAST);

-- Wait for completion (check with: \d+ products)
-- Then:

-- Index 2: For filtering by grade
CREATE INDEX CONCURRENTLY idx_products_genius_grade 
ON products(genius_grade) WHERE genius_grade IS NOT NULL;

-- Wait for completion, then:

-- Index 3: For finding recently calculated
CREATE INDEX CONCURRENTLY idx_products_genius_score_calculated 
ON products(genius_score_last_calculated DESC) 
WHERE genius_score_last_calculated IS NOT NULL;
```

**Why `CONCURRENTLY`?**
- ✅ Doesn't lock the table
- ✅ Can run while users are using the system
- ✅ Takes longer but doesn't block operations

---

## 🔍 STEP 6: MONITOR SCORING PROGRESS

### Check Celery Task Status

```python
# In Python shell
from celery.result import AsyncResult
from app.core.celery_app import celery_app

# Get task result
task_id = 'your-task-id'
result = AsyncResult(task_id, app=celery_app)
print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

### Check Database Progress

```sql
-- See how many products have been scored
SELECT 
    COUNT(*) as total,
    COUNT(genius_score) as scored,
    COUNT(genius_score) * 100.0 / COUNT(*) as percent_complete
FROM products;

-- See when scores were last calculated
SELECT 
    MAX(genius_score_last_calculated) as last_calculated,
    COUNT(*) as total_scored
FROM products
WHERE genius_score IS NOT NULL;
```

---

## ⏰ STEP 7: VERIFY DAILY JOB IS SCHEDULED

The daily genius scoring job should run at 3 AM automatically.

**Check Celery Beat schedule:**

```bash
# Check if Celery Beat is running
celery -A app.core.celery_app inspect scheduled

# Should see:
# refresh-genius-scores-daily (runs at 3:00 AM daily)
```

**Check logs at 3 AM to verify it runs:**

```bash
# In your logs, look for:
# "Starting daily genius score refresh"
# "Scored X products"
```

---

## 🎯 QUICK TEST CHECKLIST

- [ ] Columns exist in database
- [ ] Started scoring job
- [ ] Scores appearing in database
- [ ] Scores visible in Analyzer UI
- [ ] Can sort by genius score
- [ ] Grade badges display correctly
- [ ] Daily job scheduled (check Celery Beat)

---

## 🚨 TROUBLESHOOTING

### No Scores Appearing?

1. **Check if scoring job ran:**
   ```sql
   SELECT COUNT(*) FROM products WHERE genius_score IS NOT NULL;
   ```

2. **Check if products have required data:**
   ```sql
   -- Products need ASIN, pricing, and API data
   SELECT COUNT(*) FROM products 
   WHERE asin IS NOT NULL 
   AND asin NOT LIKE 'PENDING_%';
   ```

3. **Manually trigger scoring:**
   ```python
   calculate_genius_scores.delay()
   ```

### Scores Not Showing in UI?

1. **Check API response:**
   - Open browser dev tools
   - Check Network tab
   - Look for `/api/v1/products` or `/api/v1/analyzer`
   - Verify `genius_score` is in response

2. **Check frontend code:**
   - Verify `genius_score` column is in `analyzerColumns.js`
   - Verify rendering code in `AnalyzerTableRow.jsx`

### Daily Job Not Running?

1. **Check Celery Beat is running:**
   ```bash
   celery -A app.core.celery_app beat
   ```

2. **Check schedule in `celery_app.py`:**
   ```python
   'refresh-genius-scores-daily': {
       'task': 'app.tasks.genius_scoring_tasks.refresh_genius_scores_daily',
       'schedule': crontab(hour=3, minute=0),
   }
   ```

---

## ✅ SUCCESS INDICATORS

You'll know it's working when:

1. ✅ Columns exist in database
2. ✅ Products have `genius_score` values (0-100)
3. ✅ Products have `genius_grade` values (EXCELLENT/GOOD/FAIR/POOR)
4. ✅ Scores visible in Analyzer UI
5. ✅ Can sort/filter by score
6. ✅ Daily job runs at 3 AM

---

## 🎉 YOU'RE READY!

The migration is complete. Now:

1. **Start scoring products** (use one of the methods above)
2. **Wait for scores to populate** (check progress with SQL queries)
3. **View scores in Analyzer** (should appear automatically)
4. **Add indexes later** (when convenient)

**Everything is set up and ready to go!** 🚀


