-- Add pack_size, wholesale_cost, percent_off, promo_qty to product_deals view
-- These fields exist in product_sources but weren't being returned
--
-- IMPORTANT: Run these migrations in order:
-- 1. ADD_PACK_AND_WHOLESALE_COLUMNS.sql (adds pack_size, wholesale_cost)
-- 2. ADD_SALES_COLUMNS_TO_PRODUCT_SOURCES.sql (adds percent_off, promo_qty)
-- 3. This file (updates the view to include all fields)

-- Drop and recreate the view with new fields
DROP VIEW IF EXISTS product_deals CASCADE;

CREATE OR REPLACE VIEW product_deals AS
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
    ps.pack_size,
    ps.wholesale_cost,
    ps.percent_off,
    ps.promo_qty,
    ps.source,
    ps.source_detail,
    ps.stage,
    ps.notes,
    ps.is_active,
    ps.created_at as deal_created_at,
    ps.updated_at as deal_updated_at,
    -- Calculated fields
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
    END as total_investment
FROM product_sources ps
JOIN products p ON p.id = ps.product_id
LEFT JOIN suppliers s ON s.id = ps.supplier_id
WHERE ps.is_active = TRUE;

-- Grant permissions
GRANT SELECT ON product_deals TO authenticated;
GRANT SELECT ON product_deals TO anon;

-- Update the RPC function to include these fields
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
    pack_size INTEGER,
    wholesale_cost DECIMAL,
    percent_off DECIMAL,
    promo_qty INTEGER,
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
        ps.pack_size,
        ps.wholesale_cost,
        ps.percent_off,
        ps.promo_qty,
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
COMMENT ON FUNCTION filter_product_deals IS 'Filter product_deals with ASIN status and other filters - includes pack_size, wholesale_cost, percent_off, promo_qty';

