-- ============================================
-- VERIFY MIGRATION - Check if columns were added correctly
-- ============================================

-- Check if all columns exist
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'analyses'
  AND column_name IN (
    'product_title', 'brand', 'category', 'image_url',
    'buy_cost', 'sell_price', 'profit', 'roi', 'margin',
    'referral_fee', 'fba_fee', 'total_fees',
    'sales_rank', 'gating_status', 'gating_reasons',
    'review_count', 'rating', 'drops_30', 'drops_90', 'status'
  )
ORDER BY column_name;

-- Check data migration - see if data was migrated from JSONB
SELECT 
    COUNT(*) as total_analyses,
    COUNT(product_title) as has_product_title,
    COUNT(roi) as has_roi,
    COUNT(profit) as has_profit,
    COUNT(sell_price) as has_sell_price,
    COUNT(analysis_data) as has_jsonb_data
FROM analyses;

-- Check sample migrated data
SELECT 
    id,
    asin,
    product_title,
    roi,
    profit,
    sell_price,
    buy_cost,
    gating_status,
    status,
    CASE 
        WHEN analysis_data IS NOT NULL THEN 'Has JSONB'
        ELSE 'No JSONB'
    END as jsonb_status
FROM analyses
ORDER BY created_at DESC
LIMIT 10;

-- Check indexes were created
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'analyses'
  AND indexname LIKE 'idx_analyses%'
ORDER BY indexname;

-- Check for any NULL values that should have been migrated
SELECT 
    COUNT(*) as missing_product_title,
    COUNT(*) FILTER (WHERE analysis_data->>'product_title' IS NOT NULL) as jsonb_has_title
FROM analyses
WHERE product_title IS NULL
  AND analysis_data IS NOT NULL;

