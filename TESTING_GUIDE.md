# Analyzer Dashboard - Testing Guide (Phases 1-3)

## ✅ Pre-Test Checklist

- [x] Migration `ADD_ANALYZER_PROFITABILITY_COLUMNS.sql` has been run
- [x] Backend code deployed to Render
- [x] Calculator tests pass (run `python3 backend/test_profitability_calculator.py`)

## Test 1: Verify Migration

Run this in Supabase SQL Editor:

```sql
-- File: database/migrations/VERIFY_ANALYZER_MIGRATION.sql
```

**Expected:** 12 columns in `products` table, 3 columns in `product_sources` table, 6 indexes created.

## Test 2: Upload Test CSV

Create a CSV with these columns:

```csv
UPC,TITLE,WHOLESALE,PACK,SUPPLIER
825325690596,Test Product 1,12.99,1,Test Supplier
123456789012,Test Product 2,8.50,6,Test Supplier
234567890123,Test Product 3,15.00,1,Test Supplier
```

**Watch for these log messages in Render/Celery:**

```
💰 Calculating profitability metrics for X products...
💰 Calculating profitability for X products with supplier costs...
✅ Calculated profitability for X products
```

## Test 3: Verify Database Values

Run this query **after** your upload completes:

```sql
SELECT 
    asin,
    title,
    sell_price,
    (SELECT wholesale_cost FROM product_sources WHERE product_id = p.id LIMIT 1) as wholesale,
    profit_amount,
    roi_percentage,
    margin_percentage,
    break_even_price,
    is_profitable,
    profit_tier,
    risk_level,
    est_monthly_sales,
    created_at
FROM products p
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 10;
```

**Expected Results:**

| Column | Should Be |
|--------|-----------|
| `profit_amount` | NOT NULL (e.g., 3.45) |
| `roi_percentage` | NOT NULL (e.g., 42.5) |
| `margin_percentage` | NOT NULL (e.g., 28.3) |
| `profit_tier` | 'excellent', 'good', 'marginal', or 'unprofitable' |
| `risk_level` | 'low', 'medium', or 'high' |
| `est_monthly_sales` | NOT NULL if BSR exists (e.g., 45) |

## Test 4: Check Product Sources

```sql
SELECT 
    ps.product_id,
    ps.wholesale_cost,
    ps.pack_size,
    ps.profit,
    ps.roi,
    ps.margin,
    p.asin,
    p.profit_tier
FROM product_sources ps
JOIN products p ON p.id = ps.product_id
WHERE ps.created_at > NOW() - INTERVAL '1 hour'
ORDER BY ps.created_at DESC
LIMIT 10;
```

**Expected:** `profit`, `roi`, `margin` columns should be populated.

## Troubleshooting

### Issue: All columns are NULL

**Check:**
1. Did you see the "💰 Calculating profitability" logs?
2. Do products have `sell_price` or `amazon_price_current`?
3. Do product_sources have `wholesale_cost` or `buy_cost`?

**Fix:** Check Celery logs for errors. Calculation requires both pricing data (from API) and cost data (from CSV).

### Issue: Some products have metrics, others don't

**Normal:** Products without pricing data (no API response) or cost data (missing from CSV) will have NULL metrics.

### Issue: Wrong calculations

**Check:** Verify the test script passes:
```bash
python3 backend/test_profitability_calculator.py
```

## Success Criteria

✅ Migration columns exist  
✅ Logs show profitability calculation  
✅ Database has populated `profit_amount`, `roi_percentage`, `profit_tier`  
✅ Product_sources have `profit`, `roi`, `margin`  
✅ Calculations look reasonable (ROI between -50% and 200% for most products)

## Next Steps

Once all tests pass, proceed to **Phases 4-5** (Analyzer API + Frontend Dashboard).

