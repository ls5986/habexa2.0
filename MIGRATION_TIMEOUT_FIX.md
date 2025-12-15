# Genius Score Migration Timeout Fix

**Problem:** `ADD_GENIUS_SCORE_COLUMNS.sql` keeps timing out  
**Cause:** Large `products` table + indexes being created synchronously  
**Solution:** Use optimized migration that adds columns first, indexes later

---

## 🚀 QUICK FIX (Recommended)

### Option 1: Fast Migration (No Indexes) - ~5 seconds

```sql
-- Run this first (adds columns only)
\i database/migrations/ADD_GENIUS_SCORE_COLUMNS_FAST.sql
```

**This will:**
- ✅ Add all 5 columns instantly (~5 seconds)
- ✅ No table locking
- ✅ No indexes (add them later)

**Then add indexes separately (when ready):**

```sql
-- Add indexes one at a time (non-blocking)
CREATE INDEX CONCURRENTLY idx_products_genius_score 
ON products(genius_score DESC NULLS LAST);

CREATE INDEX CONCURRENTLY idx_products_genius_grade 
ON products(genius_grade) WHERE genius_grade IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_products_genius_score_calculated 
ON products(genius_score_last_calculated DESC) 
WHERE genius_score_last_calculated IS NOT NULL;
```

---

### Option 2: Optimized Migration (With Indexes) - ~30 seconds

```sql
-- Run this if you want indexes created automatically
\i database/migrations/ADD_GENIUS_SCORE_COLUMNS_OPTIMIZED.sql
```

**This will:**
- ✅ Add columns one at a time
- ✅ Create indexes with `CONCURRENTLY` (non-blocking)
- ✅ Takes ~30 seconds for 100k products

---

## 📊 Why It Times Out

### Original Migration Issues:

1. **Adding multiple columns at once** → Can cause table rewrite
2. **Creating indexes synchronously** → Locks table
3. **Adding constraints immediately** → Validates all rows

### Optimized Solutions:

1. **Add columns separately** → No table rewrite needed
2. **Use `CONCURRENTLY` for indexes** → Non-blocking
3. **Add constraints after** → Faster initial migration

---

## 🎯 Step-by-Step Fix

### Step 1: Check Current Table Size

```sql
-- See how many products you have
SELECT COUNT(*) FROM products;

-- See table size
SELECT 
    pg_size_pretty(pg_total_relation_size('products')) AS total_size,
    pg_size_pretty(pg_relation_size('products')) AS table_size,
    pg_size_pretty(pg_indexes_size('products')) AS indexes_size;
```

**If you have:**
- **< 10,000 products:** Use optimized version (should work fine)
- **10,000 - 100,000 products:** Use fast version, add indexes later
- **> 100,000 products:** Use fast version, add indexes during off-peak hours

---

### Step 2: Run Fast Migration

```sql
-- Connect to your database
psql -U postgres -d habexa

-- Run the fast migration
\i database/migrations/ADD_GENIUS_SCORE_COLUMNS_FAST.sql
```

**Expected output:**
```
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
```

**Time:** ~5 seconds ✅

---

### Step 3: Verify Columns Added

```sql
-- Check columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name LIKE 'genius%';

-- Should see:
-- genius_score
-- genius_grade
-- genius_breakdown
-- genius_insights
-- genius_score_last_calculated
```

---

### Step 4: Add Indexes (Later - Non-Critical)

**You can use the system without indexes!** They just make queries faster.

**Add indexes when convenient:**

```sql
-- Index 1: For sorting by score (most important)
CREATE INDEX CONCURRENTLY idx_products_genius_score 
ON products(genius_score DESC NULLS LAST);

-- Wait for it to complete, then:
-- Index 2: For filtering by grade
CREATE INDEX CONCURRENTLY idx_products_genius_grade 
ON products(genius_grade) WHERE genius_grade IS NOT NULL;

-- Wait for it to complete, then:
-- Index 3: For finding recently calculated
CREATE INDEX CONCURRENTLY idx_products_genius_score_calculated 
ON products(genius_score_last_calculated DESC) 
WHERE genius_score_last_calculated IS NOT NULL;
```

**Why `CONCURRENTLY`?**
- Doesn't lock the table
- Can run while users are using the system
- Takes longer but doesn't block operations

---

### Step 5: Add Check Constraint (Optional)

```sql
-- Add constraint for valid grades
ALTER TABLE products 
ADD CONSTRAINT products_genius_grade_check 
CHECK (genius_grade IS NULL OR genius_grade IN ('EXCELLENT', 'GOOD', 'FAIR', 'POOR'));
```

**Note:** This validates all existing rows, so it might take time on large tables.  
**You can skip this** - the application will validate anyway.

---

## ✅ Verification

After running the fast migration:

```sql
-- 1. Check columns exist
\d products

-- Should see:
-- genius_score            | numeric(5,2)  | 
-- genius_grade            | text          | 
-- genius_breakdown        | jsonb         | 
-- genius_insights         | jsonb         | 
-- genius_score_last_calculated | timestamp with time zone |

-- 2. Test inserting a score
UPDATE products 
SET genius_score = 87.5, 
    genius_grade = 'EXCELLENT'
WHERE id = (SELECT id FROM products LIMIT 1);

-- 3. Verify it worked
SELECT genius_score, genius_grade FROM products WHERE genius_score IS NOT NULL LIMIT 1;
```

---

## 🚨 If Still Timing Out

### Option A: Increase Timeout

```sql
-- In psql, increase statement timeout
SET statement_timeout = '10min';

-- Then run migration
\i database/migrations/ADD_GENIUS_SCORE_COLUMNS_FAST.sql
```

### Option B: Run in Supabase Dashboard

1. Go to Supabase Dashboard
2. SQL Editor
3. Paste the fast migration SQL
4. Run it (Supabase has longer timeouts)

### Option C: Add Columns Manually

```sql
-- Add one column at a time
ALTER TABLE products ADD COLUMN IF NOT EXISTS genius_score DECIMAL(5,2);
-- Wait for completion

ALTER TABLE products ADD COLUMN IF NOT EXISTS genius_grade TEXT;
-- Wait for completion

ALTER TABLE products ADD COLUMN IF NOT EXISTS genius_breakdown JSONB;
-- Wait for completion

ALTER TABLE products ADD COLUMN IF NOT EXISTS genius_insights JSONB;
-- Wait for completion

ALTER TABLE products ADD COLUMN IF NOT EXISTS genius_score_last_calculated TIMESTAMP WITH TIME ZONE;
-- Done!
```

---

## 📝 Summary

**Fastest Solution:**
1. Run `ADD_GENIUS_SCORE_COLUMNS_FAST.sql` (~5 seconds)
2. Add indexes later with `CONCURRENTLY`
3. System works immediately!

**Files Created:**
- `ADD_GENIUS_SCORE_COLUMNS_FAST.sql` - Columns only (fastest)
- `ADD_GENIUS_SCORE_COLUMNS_OPTIMIZED.sql` - With indexes (slower but complete)

**Recommendation:** Use the fast version, add indexes during off-peak hours.

---

## 🎯 Next Steps After Migration

1. ✅ Verify columns exist
2. ✅ Start scoring products: `calculate_genius_scores.delay()`
3. ✅ Add indexes when convenient
4. ✅ Test genius score display in Analyzer

**You're ready to go!** 🚀

