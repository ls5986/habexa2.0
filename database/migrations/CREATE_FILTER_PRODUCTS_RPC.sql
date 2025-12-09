-- ============================================================================
-- Filter Products by ASIN Status - 100% Database-Side Solution
-- ============================================================================
-- This RPC function filters product_deals with proper ASIN status logic.
-- Replicates the product_deals view structure but with filtering applied.
-- ============================================================================

-- Drop if exists (for updates)
DROP FUNCTION IF EXISTS filter_product_deals(
    p_user_id UUID,
    p_asin_status TEXT,
    p_stage TEXT,
    p_source TEXT,
    p_supplier_id UUID,
    p_min_roi DECIMAL,
    p_min_profit DECIMAL,
    p_search TEXT,
    p_limit INTEGER,
    p_offset INTEGER
);

-- Create filtering function that queries product_deals view with proper filtering
CREATE OR REPLACE FUNCTION filter_product_deals(
    p_user_id UUID,
    p_asin_status TEXT DEFAULT NULL,
    p_stage TEXT DEFAULT NULL,
    p_source TEXT DEFAULT NULL,
    p_supplier_id UUID DEFAULT NULL,
    p_min_roi DECIMAL DEFAULT NULL,
    p_min_profit DECIMAL DEFAULT NULL,
    p_search TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    -- Match product_deals view structure
    deal_id UUID,
    product_id UUID,
    user_id UUID,
    asin TEXT,
    title TEXT,
    image_url TEXT,
    sell_price DECIMAL,
    fees_total DECIMAL,
    bsr INTEGER,
    seller_count INTEGER,
    fba_seller_count INTEGER,
    amazon_sells BOOLEAN,
    product_status TEXT,
    analysis_id UUID,
    supplier_id UUID,
    supplier_name TEXT,
    buy_cost DECIMAL,
    moq INTEGER,
    source TEXT,
    source_detail TEXT,
    stage TEXT,
    notes TEXT,
    is_active BOOLEAN,
    deal_created_at TIMESTAMPTZ,
    deal_updated_at TIMESTAMPTZ,
    profit DECIMAL,
    roi DECIMAL,
    total_investment DECIMAL,
    -- Additional columns needed for filtering
    upc TEXT,
    asin_status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ps.id as deal_id,
        p.id as product_id,
        p.user_id,
        p.asin,
        p.title,
        p.image_url,
        p.sell_price,
        p.fees_total,
        p.bsr,
        p.seller_count,
        p.fba_seller_count,
        p.amazon_sells,
        p.status as product_status,
        p.analysis_id,
        ps.supplier_id,
        s.name as supplier_name,
        ps.buy_cost,
        ps.moq,
        ps.source,
        ps.source_detail,
        ps.stage,
        ps.notes,
        ps.is_active,
        ps.created_at as deal_created_at,
        ps.updated_at as deal_updated_at,
        -- Calculated fields (matching view)
        CASE 
            WHEN ps.buy_cost > 0 AND p.sell_price > 0 THEN 
                ROUND(p.sell_price - COALESCE(p.fees_total, 0) - ps.buy_cost, 2)
            ELSE NULL 
        END as profit,
        CASE 
            WHEN ps.buy_cost > 0 AND p.sell_price > 0 THEN 
                ROUND(((p.sell_price - COALESCE(p.fees_total, 0) - ps.buy_cost) / ps.buy_cost) * 100, 1)
            ELSE NULL 
        END as roi,
        CASE 
            WHEN ps.buy_cost > 0 THEN 
                ROUND(ps.buy_cost * ps.moq, 2)
            ELSE NULL 
        END as total_investment,
        -- Additional columns for filtering
        p.upc,
        -- Calculate asin_status (matching get_asin_stats logic)
        CASE
            WHEN p.asin IS NOT NULL 
                AND p.asin != '' 
                AND p.asin NOT LIKE 'PENDING_%'
                AND p.asin NOT LIKE 'Unknown%' THEN 'found'
            WHEN p.status = 'needs_selection' THEN 'multiple_found'
            WHEN (p.upc IS NOT NULL AND p.upc != '')
                AND (p.asin IS NULL OR p.asin = '' OR p.asin LIKE 'PENDING_%' OR p.asin LIKE 'Unknown%') THEN 'not_found'
            ELSE 'manual'
        END as asin_status
    FROM product_sources ps
    JOIN products p ON p.id = ps.product_id
    LEFT JOIN suppliers s ON s.id = ps.supplier_id
    WHERE ps.is_active = TRUE
        AND p.user_id = p_user_id
        
        -- ASIN status filter (100% database-side)
        AND (
            p_asin_status IS NULL
            OR (
                -- asin_found: Has real ASIN (not null, not empty, not PENDING_*, not Unknown)
                (p_asin_status = 'asin_found' 
                    AND p.asin IS NOT NULL 
                    AND p.asin != '' 
                    AND p.asin NOT LIKE 'PENDING_%'
                    AND p.asin NOT LIKE 'Unknown%')
            )
            OR (
                -- needs_selection: Status is needs_selection
                (p_asin_status = 'needs_selection' AND p.status = 'needs_selection')
            )
            OR (
                -- needs_asin: Has UPC but no real ASIN (includes PENDING_*)
                (p_asin_status = 'needs_asin'
                    AND p.upc IS NOT NULL 
                    AND p.upc != ''
                    AND (p.asin IS NULL 
                        OR p.asin = '' 
                        OR p.asin LIKE 'PENDING_%'
                        OR p.asin LIKE 'Unknown%'))
            )
            OR (
                -- manual_entry: No UPC and no real ASIN
                (p_asin_status = 'manual_entry'
                    AND (p.upc IS NULL OR p.upc = '')
                    AND (p.asin IS NULL 
                        OR p.asin = '' 
                        OR p.asin LIKE 'PENDING_%'
                        OR p.asin LIKE 'Unknown%'))
            )
        )
        
        -- Stage filter
        AND (p_stage IS NULL OR ps.stage = p_stage)
        
        -- Source filter
        AND (p_source IS NULL OR ps.source = p_source)
        
        -- Supplier filter
        AND (p_supplier_id IS NULL OR ps.supplier_id = p_supplier_id)
        
        -- ROI filter (calculated field)
        AND (
            p_min_roi IS NULL
            OR (ps.buy_cost > 0 
                AND p.sell_price > 0 
                AND ((p.sell_price - COALESCE(p.fees_total, 0) - ps.buy_cost) / ps.buy_cost) * 100 >= p_min_roi)
        )
        
        -- Profit filter (calculated field)
        AND (
            p_min_profit IS NULL
            OR (ps.buy_cost > 0 
                AND p.sell_price > 0 
                AND (p.sell_price - COALESCE(p.fees_total, 0) - ps.buy_cost) >= p_min_profit)
        )
        
        -- Search filter (ASIN, UPC, or title)
        AND (
            p_search IS NULL
            OR p.asin ILIKE '%' || p_search || '%'
            OR p.upc ILIKE '%' || p_search || '%'
            OR p.title ILIKE '%' || p_search || '%'
        )
    
    ORDER BY ps.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION filter_product_deals TO authenticated;
GRANT EXECUTE ON FUNCTION filter_product_deals TO anon;

-- Add comment
COMMENT ON FUNCTION filter_product_deals IS 'Filter product_deals with ASIN status and other filters - 100% database-side, highly scalable';

-- ============================================================================
-- PERFORMANCE: Ensure indexes exist
-- ============================================================================
-- These should already exist from CREATE_ASIN_STATS_RPC.sql, but ensure they do

CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_asin ON products(asin) WHERE asin IS NOT NULL AND asin != '';
CREATE INDEX IF NOT EXISTS idx_products_upc ON products(upc) WHERE upc IS NOT NULL AND upc != '';
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_asin_status ON products(user_id, asin, upc, status);

-- Analyze to update statistics
ANALYZE products;
ANALYZE product_sources;

