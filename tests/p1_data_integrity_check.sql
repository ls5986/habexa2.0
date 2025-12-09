-- ============================================================================
-- P1 DATA INTEGRITY CHECKS
-- ============================================================================
-- Run ALL queries in Supabase SQL Editor
-- Replace YOUR_USER_ID with actual user ID
-- ============================================================================

-- ============================================
-- 1. CHECK FOR ORPHANED PRODUCTS
-- ============================================
SELECT 
    COUNT(*) as orphaned_products,
    ARRAY_AGG(id) as orphaned_ids
FROM products 
WHERE user_id NOT IN (SELECT id FROM auth.users);

-- ✅ Expected: orphaned_products = 0
-- ❌ If > 0: Products exist without valid users - DATA CORRUPTION

-- ============================================
-- 2. CHECK PROFIT CALCULATIONS
-- ============================================
SELECT 
    COUNT(*) as incorrect_profits,
    ARRAY_AGG(id) as product_ids
FROM products
WHERE ABS(profit - (sell_price - buy_cost)) > 0.01;

-- ✅ Expected: incorrect_profits = 0
-- ❌ If > 0: Profit calculations wrong - LOGIC BUG
-- Note: This assumes profit = sell_price - buy_cost
-- Adjust if profit calculation includes fees

-- ============================================
-- 3. CHECK ROI CALCULATIONS
-- ============================================
SELECT 
    COUNT(*) as incorrect_rois,
    ARRAY_AGG(id) as product_ids
FROM products
WHERE buy_cost > 0 
  AND ABS(roi - ((profit / buy_cost) * 100)) > 0.1;

-- ✅ Expected: incorrect_rois = 0
-- ❌ If > 0: ROI calculations wrong - LOGIC BUG

-- ============================================
-- 4. CHECK FOR INVALID ASINS
-- ============================================
SELECT 
    COUNT(*) as pending_counted_as_found,
    ARRAY_AGG(id) as product_ids
FROM products 
WHERE asin IS NOT NULL 
  AND asin != '' 
  AND asin LIKE 'PENDING_%';

-- ✅ Expected: pending_counted_as_found = 0
-- ❌ If > 0: Placeholder ASINs being counted as real - FILTER BUG
-- Note: These should be filtered out by ASIN status filter

-- ============================================
-- 5. CHECK ORDERS HAVE LINE ITEMS
-- ============================================
SELECT 
    COUNT(*) as orders_without_items,
    ARRAY_AGG(o.id) as order_ids
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
WHERE oi.id IS NULL;

-- ✅ Expected: orders_without_items = 0
-- ❌ If > 0: Empty orders exist - DATA CORRUPTION

-- ============================================
-- 6. CHECK ORDER TOTALS MATCH LINE ITEMS
-- ============================================
SELECT 
    COUNT(*) as incorrect_totals,
    ARRAY_AGG(o.id) as order_ids
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id, o.total_amount
HAVING ABS(o.total_amount - SUM(oi.quantity * oi.unit_cost)) > 0.01;

-- ✅ Expected: incorrect_totals = 0
-- ❌ If > 0: Order totals don't match line items - CALCULATION BUG

-- ============================================
-- 7. CHECK FOR NULL CRITICAL FIELDS
-- ============================================
SELECT 
    'products' as table_name,
    COUNT(*) as null_user_ids
FROM products
WHERE user_id IS NULL

UNION ALL

SELECT 
    'orders' as table_name,
    COUNT(*) as null_user_ids
FROM orders
WHERE user_id IS NULL;

-- ✅ Expected: All counts = 0
-- ❌ If > 0: NULL user_ids exist - DATA CORRUPTION

-- ============================================
-- 8. CHECK FOREIGN KEY INTEGRITY
-- ============================================

-- Check products reference valid suppliers
SELECT 
    COUNT(*) as invalid_supplier_refs,
    ARRAY_AGG(p.id) as product_ids
FROM products p
WHERE p.supplier_id IS NOT NULL
  AND p.supplier_id NOT IN (SELECT id FROM suppliers);

-- Check order_items reference valid products
SELECT 
    COUNT(*) as invalid_product_refs,
    ARRAY_AGG(oi.id) as order_item_ids
FROM order_items oi
WHERE oi.product_id NOT IN (SELECT id FROM products);

-- Check order_items reference valid orders
SELECT 
    COUNT(*) as invalid_order_refs,
    ARRAY_AGG(oi.id) as order_item_ids
FROM order_items oi
WHERE oi.order_id NOT IN (SELECT id FROM orders);

-- ✅ Expected: All counts = 0
-- ❌ If > 0: Orphaned references - REFERENTIAL INTEGRITY VIOLATION

-- ============================================
-- 9. CHECK DUPLICATE ASINS/UPCS
-- ============================================

-- Check for duplicate ASINs per user
SELECT 
    user_id,
    asin,
    COUNT(*) as duplicate_count
FROM products
WHERE asin IS NOT NULL AND asin != ''
GROUP BY user_id, asin
HAVING COUNT(*) > 1;

-- Check for duplicate UPCs per user
SELECT 
    user_id,
    upc,
    COUNT(*) as duplicate_count
FROM products
WHERE upc IS NOT NULL AND upc != ''
GROUP BY user_id, upc
HAVING COUNT(*) > 1;

-- ✅ Expected: 0 rows (no duplicates)
-- ❌ If rows returned: Duplicate products exist - NEEDS CLEANUP
-- Note: Some duplicates may be intentional (same product, different suppliers)

-- ============================================
-- 10. CHECK INDEX HEALTH
-- ============================================
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as times_used,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename IN ('products', 'orders', 'order_items', 'product_sources')
ORDER BY tablename, indexname;

-- ✅ Expected: All critical indexes showing idx_scan > 0
-- ❌ If idx_scan = 0: Index not being used - PERFORMANCE ISSUE
-- Critical indexes:
--   - idx_products_user_id (should have high idx_scan)
--   - idx_products_asin (should have high idx_scan)
--   - idx_products_upc (should have high idx_scan)

-- ============================================
-- 11. CHECK ASIN STATUS CONSISTENCY
-- ============================================
-- Verify that ASIN status filter logic matches get_asin_stats RPC

-- Count products that should be "asin_found"
SELECT 
    'asin_found' as status,
    COUNT(*) as count
FROM products
WHERE asin IS NOT NULL 
  AND asin != ''
  AND asin NOT LIKE 'PENDING_%'
  AND asin NOT LIKE 'Unknown%'

UNION ALL

-- Count products that should be "needs_asin"
SELECT 
    'needs_asin' as status,
    COUNT(*) as count
FROM products
WHERE upc IS NOT NULL 
  AND upc != ''
  AND (
    asin IS NULL 
    OR asin = ''
    OR asin LIKE 'PENDING_%'
    OR asin LIKE 'Unknown%'
  )

UNION ALL

-- Count products that should be "manual_entry"
SELECT 
    'manual_entry' as status,
    COUNT(*) as count
FROM products
WHERE (upc IS NULL OR upc = '')
  AND (
    asin IS NULL 
    OR asin = ''
    OR asin LIKE 'PENDING_%'
    OR asin LIKE 'Unknown%'
  );

-- Compare these counts with get_asin_stats() RPC results
-- They should match exactly

-- ============================================
-- SUMMARY REPORT
-- ============================================
SELECT 
    'Data Integrity Report' as report,
    NOW() as checked_at,
    (SELECT COUNT(*) FROM products) as total_products,
    (SELECT COUNT(*) FROM orders) as total_orders,
    (SELECT COUNT(*) FROM order_items) as total_order_items,
    (SELECT COUNT(*) FROM products WHERE user_id NOT IN (SELECT id FROM auth.users)) as orphaned_products,
    (SELECT COUNT(*) FROM products WHERE ABS(profit - (sell_price - buy_cost)) > 0.01) as incorrect_profits,
    (SELECT COUNT(*) FROM products WHERE buy_cost > 0 AND ABS(roi - ((profit / buy_cost) * 100)) > 0.1) as incorrect_rois,
    (SELECT COUNT(*) FROM orders o LEFT JOIN order_items oi ON o.id = oi.order_id WHERE oi.id IS NULL) as empty_orders,
    (SELECT COUNT(*) FROM products WHERE asin IS NOT NULL AND asin != '' AND asin LIKE 'PENDING_%') as pending_asins;

-- ============================================
-- INTERPRETATION GUIDE
-- ============================================
-- 
-- ✅ ALL TESTS PASS if:
--   - orphaned_products = 0
--   - incorrect_profits = 0
--   - incorrect_rois = 0
--   - empty_orders = 0
--   - pending_asins = 0 (or acceptable)
--   - All foreign key checks = 0
--   - All indexes being used (idx_scan > 0)
--
-- ❌ TESTS FAIL if:
--   - Any corruption found
--   - Any calculation errors
--   - Any referential integrity violations
--   - Critical indexes not being used
--
-- ============================================================================

