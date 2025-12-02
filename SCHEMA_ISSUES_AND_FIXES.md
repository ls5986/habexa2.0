# Schema Alignment Issues & Fixes

## 🔴 CRITICAL ISSUES

### 1. **analyses table - Missing UNIQUE constraint**
**Problem:** Code expects `on_conflict="user_id,supplier_id,asin"` but schema doesn't show this constraint.

**Fix:** Run this SQL:
```sql
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_user_asin_unique;
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_supplier_asin_unique;
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_user_supplier_asin_unique;
ALTER TABLE analyses ADD CONSTRAINT analyses_user_supplier_asin_unique 
UNIQUE (user_id, supplier_id, asin);
```

**File:** `database/FIX_ANALYSES_UNIQUE_KEY.sql` (already exists)

---

### 2. **products table - Code uses `brand` but schema has `brand_name`**
**Problem:** 
- Schema has: `brand_id` (UUID) and `brand_name` (TEXT)
- Code in `analysis.py` line 88 tries to update `"brand"` which doesn't exist

**Fix:** Update code to use `brand_name` instead of `brand`:
```python
# WRONG (line 88 in analysis.py):
"brand": result.get("brand"),

# RIGHT:
"brand_name": result.get("brand"),
```

**Files to fix:**
- `backend/app/tasks/analysis.py` (lines 88, 273, 466)
- Check all other files that update products table

---

### 3. **product_sources table - Missing `keepa_analyzed_at` column**
**Problem:** Code expects this column but schema doesn't show it.

**Fix:** Run this SQL:
```sql
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS keepa_analyzed_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_product_sources_keepa_analyzed 
ON product_sources(keepa_analyzed_at) 
WHERE keepa_analyzed_at IS NOT NULL;
```

**File:** `database/ADD_TOP_PRODUCTS_STAGE.sql` (already exists)

---

## 🟡 OPTIONAL / RECOMMENDED

### 4. **products table - Missing `upc` column**
**Problem:** If implementing UPC support, schema doesn't have `upc` column.

**Fix:** Run this SQL:
```sql
ALTER TABLE products ADD COLUMN IF NOT EXISTS upc TEXT;
CREATE INDEX IF NOT EXISTS idx_products_upc ON products(upc);
```

**File:** `database/ADD_UPC_SUPPORT.sql` (already exists)

---

### 5. **product_sources table - Missing `upc` column**
**Problem:** If implementing UPC support, schema doesn't have `upc` column.

**Fix:** Run this SQL:
```sql
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS upc TEXT;
```

---

## ✅ VERIFIED - NO ISSUES

### 6. **keepa_analysis table**
**Status:** ✅ Schema matches code
- Schema has: `asin TEXT NOT NULL UNIQUE` (no user_id needed)
- Code uses: `on_conflict="asin"` ✅

---

### 7. **brands table**
**Status:** ✅ Schema exists and matches code
- Schema has: `id`, `user_id`, `name`, `is_ungated`, etc.
- Code uses: `brands` table correctly ✅

---

## 📋 ACTION ITEMS

### SQL Migrations to Run:
1. ✅ `database/FIX_ANALYSES_UNIQUE_KEY.sql` - Add unique constraint
2. ✅ `database/ADD_TOP_PRODUCTS_STAGE.sql` - Add keepa_analyzed_at
3. ✅ `database/ADD_UPC_SUPPORT.sql` - Add UPC columns (if implementing)

### Code Changes Needed:
1. ✅ **FIXED:** `backend/app/tasks/analysis.py` - Changed `"brand"` to `"brand_name"` in products.update() calls
   - Line 88: ✅ Fixed
   - Line 285: ✅ Fixed
   - Line 498: ✅ Fixed

---

## 🔍 VERIFICATION QUERIES

After running fixes, verify:

```sql
-- 1. Check analyses unique constraint exists
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'analyses'::regclass 
AND contype = 'u';

-- 2. Check product_sources has keepa_analyzed_at
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'product_sources' 
AND column_name = 'keepa_analyzed_at';

-- 3. Check products has brand_name (not brand)
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name IN ('brand', 'brand_name', 'brand_id');
```

