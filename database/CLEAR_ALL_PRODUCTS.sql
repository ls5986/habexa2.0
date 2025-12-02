-- ============================================
-- CLEAR ALL PRODUCTS AND DEALS
-- ============================================
-- This will delete ALL products and deals data
-- Use with caution - this cannot be undone!

-- Delete all product sources (deals) first (due to foreign key)
DELETE FROM product_sources;

-- Delete all products
DELETE FROM products;

-- Optional: Reset sequences if you have any
-- (Not needed for UUID primary keys, but included for completeness)

-- Verify deletion
SELECT 
    (SELECT COUNT(*) FROM products) as products_count,
    (SELECT COUNT(*) FROM product_sources) as deals_count;

