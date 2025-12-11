-- ============================================================================
-- VERIFY ANALYZER MIGRATION - Run this after ADD_ANALYZER_PROFITABILITY_COLUMNS.sql
-- ============================================================================

-- Check if all columns exist
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name IN (
    'profit_amount', 
    'roi_percentage', 
    'margin_percentage', 
    'break_even_price',
    'is_profitable',
    'profit_tier',
    'risk_level',
    'est_monthly_sales',
    'avg_buybox_90d',
    'avg_sales_rank_90d',
    'avg_sales_rank_30d',
    'lowest_price_90d'
)
ORDER BY column_name;

-- Check product_sources columns
SELECT 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'product_sources' 
AND column_name IN ('profit', 'roi', 'margin')
ORDER BY column_name;

-- Check if indexes exist
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'products'
AND indexname LIKE 'idx_products_%'
ORDER BY indexname;

-- Count products with profitability data (after test upload)
SELECT 
    COUNT(*) as total_products,
    COUNT(profit_amount) as with_profit,
    COUNT(roi_percentage) as with_roi,
    COUNT(profit_tier) as with_tier,
    COUNT(CASE WHEN is_profitable = true THEN 1 END) as profitable_count,
    COUNT(CASE WHEN profit_tier = 'excellent' THEN 1 END) as excellent_count,
    COUNT(CASE WHEN profit_tier = 'good' THEN 1 END) as good_count,
    COUNT(CASE WHEN profit_tier = 'marginal' THEN 1 END) as marginal_count,
    COUNT(CASE WHEN profit_tier = 'unprofitable' THEN 1 END) as unprofitable_count
FROM products
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Sample products with profitability (recent uploads)
SELECT 
    asin,
    title,
    sell_price,
    profit_amount,
    roi_percentage,
    margin_percentage,
    break_even_price,
    is_profitable,
    profit_tier,
    risk_level,
    est_monthly_sales,
    bsr,
    created_at
FROM products
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 10;

