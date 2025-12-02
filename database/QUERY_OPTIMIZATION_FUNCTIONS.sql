-- ============================================
-- PRODUCTION-GRADE QUERY OPTIMIZATION FUNCTIONS
-- Pre-built functions for common queries
-- ============================================

-- ============================================
-- FUNCTION 1: Get Deals with Analysis (Optimized)
-- ============================================

CREATE OR REPLACE FUNCTION get_deals_optimized(
    p_user_id UUID,
    p_status TEXT DEFAULT NULL,
    p_min_roi NUMERIC DEFAULT NULL,
    p_is_profitable BOOLEAN DEFAULT NULL,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    deal_id UUID,
    asin TEXT,
    buy_cost NUMERIC,
    status TEXT,
    extracted_at TIMESTAMPTZ,
    analysis_id UUID,
    product_title TEXT,
    sell_price NUMERIC,
    profit NUMERIC,
    roi NUMERIC,
    margin NUMERIC,
    image_url TEXT,
    gating_status TEXT,
    channel_name TEXT,
    channel_id BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        td.id as deal_id,
        td.asin,
        td.buy_cost,
        td.status,
        td.extracted_at,
        a.id as analysis_id,
        COALESCE(a.product_title, td.product_title) as product_title,
        a.sell_price,
        a.profit,
        a.roi,
        a.margin,
        a.image_url,
        a.gating_status,
        tc.channel_name,
        tc.channel_id
    FROM telegram_deals td
    LEFT JOIN analyses a ON td.analysis_id = a.id
    LEFT JOIN telegram_channels tc ON td.channel_id = tc.id
    WHERE td.user_id = p_user_id
      AND (p_status IS NULL OR td.status = p_status)
      AND (p_min_roi IS NULL OR a.roi >= p_min_roi)
      AND (p_is_profitable IS NULL OR (p_is_profitable = true AND a.roi >= 30) OR (p_is_profitable = false AND (a.roi < 30 OR a.roi IS NULL)))
    ORDER BY td.extracted_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION 2: Get Deal Stats (Optimized)
-- ============================================

CREATE OR REPLACE FUNCTION get_deal_stats_optimized(p_user_id UUID)
RETURNS TABLE (
    total INTEGER,
    pending INTEGER,
    analyzed INTEGER,
    profitable INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total,
        COUNT(*) FILTER (WHERE td.status = 'pending' OR td.status IS NULL)::INTEGER as pending,
        COUNT(*) FILTER (WHERE td.status = 'analyzed')::INTEGER as analyzed,
        COUNT(*) FILTER (WHERE a.roi >= 30)::INTEGER as profitable
    FROM telegram_deals td
    LEFT JOIN analyses a ON td.analysis_id = a.id
    WHERE td.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION 3: Get Single Deal with Full Data
-- ============================================

CREATE OR REPLACE FUNCTION get_deal_full(p_user_id UUID, p_deal_id UUID)
RETURNS TABLE (
    deal_data JSONB,
    analysis_data JSONB,
    channel_data JSONB
) AS $$
DECLARE
    v_deal JSONB;
    v_analysis JSONB;
    v_channel JSONB;
BEGIN
    -- Get deal
    SELECT to_jsonb(td.*) INTO v_deal
    FROM telegram_deals td
    WHERE td.id = p_deal_id AND td.user_id = p_user_id;
    
    IF v_deal IS NULL THEN
        RETURN;
    END IF;
    
    -- Get analysis
    SELECT to_jsonb(a.*) INTO v_analysis
    FROM analyses a
    WHERE a.id = (v_deal->>'analysis_id')::UUID;
    
    -- If no linked analysis, try to find by ASIN
    IF v_analysis IS NULL THEN
        SELECT to_jsonb(a.*) INTO v_analysis
        FROM analyses a
        WHERE a.user_id = p_user_id
          AND a.asin = v_deal->>'asin'
        ORDER BY a.created_at DESC
        LIMIT 1;
    END IF;
    
    -- Get channel
    SELECT to_jsonb(tc.*) INTO v_channel
    FROM telegram_channels tc
    WHERE tc.id = (v_deal->>'channel_id')::BIGINT;
    
    RETURN QUERY SELECT v_deal, v_analysis, v_channel;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION 4: Batch Get Analyses by IDs
-- ============================================

CREATE OR REPLACE FUNCTION get_analyses_batch(p_analysis_ids UUID[])
RETURNS TABLE (
    id UUID,
    user_id UUID,
    supplier_id UUID,
    asin TEXT,
    product_title TEXT,
    sell_price NUMERIC,
    profit NUMERIC,
    roi NUMERIC,
    margin NUMERIC,
    image_url TEXT,
    gating_status TEXT,
    sales_rank INTEGER,
    review_count INTEGER,
    rating NUMERIC,
    analysis_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.user_id,
        a.supplier_id,
        a.asin,
        a.product_title,
        a.sell_price,
        a.profit,
        a.roi,
        a.margin,
        a.image_url,
        a.gating_status,
        a.sales_rank,
        a.review_count,
        a.rating,
        a.analysis_data
    FROM analyses a
    WHERE a.id = ANY(p_analysis_ids);
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION 5: Get Profitable Deals (Fast)
-- ============================================

CREATE OR REPLACE FUNCTION get_profitable_deals(
    p_user_id UUID,
    p_min_roi NUMERIC DEFAULT 30,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    deal_id UUID,
    asin TEXT,
    buy_cost NUMERIC,
    profit NUMERIC,
    roi NUMERIC,
    product_title TEXT,
    image_url TEXT,
    channel_name TEXT,
    extracted_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        td.id as deal_id,
        td.asin,
        td.buy_cost,
        a.profit,
        a.roi,
        COALESCE(a.product_title, td.product_title) as product_title,
        a.image_url,
        tc.channel_name,
        td.extracted_at
    FROM telegram_deals td
    INNER JOIN analyses a ON td.analysis_id = a.id
    LEFT JOIN telegram_channels tc ON td.channel_id = tc.id
    WHERE td.user_id = p_user_id
      AND td.status = 'analyzed'
      AND a.status = 'complete'
      AND a.roi >= p_min_roi
    ORDER BY a.roi DESC, td.extracted_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION 6: Search Deals (Full-text search)
-- ============================================

CREATE OR REPLACE FUNCTION search_deals(
    p_user_id UUID,
    p_search_term TEXT,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    deal_id UUID,
    asin TEXT,
    product_title TEXT,
    channel_name TEXT,
    roi NUMERIC,
    match_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        td.id as deal_id,
        td.asin,
        COALESCE(a.product_title, td.product_title) as product_title,
        tc.channel_name,
        a.roi,
        CASE 
            WHEN td.asin ILIKE '%' || p_search_term || '%' THEN 'asin'
            WHEN COALESCE(a.product_title, td.product_title) ILIKE '%' || p_search_term || '%' THEN 'title'
            WHEN tc.channel_name ILIKE '%' || p_search_term || '%' THEN 'channel'
            ELSE 'other'
        END as match_type
    FROM telegram_deals td
    LEFT JOIN analyses a ON td.analysis_id = a.id
    LEFT JOIN telegram_channels tc ON td.channel_id = tc.id
    WHERE td.user_id = p_user_id
      AND (
          td.asin ILIKE '%' || p_search_term || '%'
          OR COALESCE(a.product_title, td.product_title) ILIKE '%' || p_search_term || '%'
          OR tc.channel_name ILIKE '%' || p_search_term || '%'
      )
    ORDER BY 
        CASE match_type
            WHEN 'asin' THEN 1
            WHEN 'title' THEN 2
            WHEN 'channel' THEN 3
            ELSE 4
        END,
        td.extracted_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION 7: Get Channel Stats
-- ============================================

CREATE OR REPLACE FUNCTION get_channel_stats(p_user_id UUID, p_channel_id BIGINT)
RETURNS TABLE (
    total_deals INTEGER,
    analyzed_deals INTEGER,
    profitable_deals INTEGER,
    avg_roi NUMERIC,
    total_profit NUMERIC,
    messages_received INTEGER,
    deals_extracted INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_deals,
        COUNT(*) FILTER (WHERE td.status = 'analyzed')::INTEGER as analyzed_deals,
        COUNT(*) FILTER (WHERE a.roi >= 30)::INTEGER as profitable_deals,
        AVG(a.roi)::NUMERIC as avg_roi,
        SUM(a.profit)::NUMERIC as total_profit,
        tc.messages_received,
        tc.deals_extracted
    FROM telegram_channels tc
    LEFT JOIN telegram_deals td ON tc.id = td.channel_id
    LEFT JOIN analyses a ON td.analysis_id = a.id
    WHERE tc.user_id = p_user_id
      AND tc.channel_id = p_channel_id
    GROUP BY tc.messages_received, tc.deals_extracted;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- GRANT PERMISSIONS
-- ============================================

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION get_deals_optimized TO authenticated;
GRANT EXECUTE ON FUNCTION get_deal_stats_optimized TO authenticated;
GRANT EXECUTE ON FUNCTION get_deal_full TO authenticated;
GRANT EXECUTE ON FUNCTION get_analyses_batch TO authenticated;
GRANT EXECUTE ON FUNCTION get_profitable_deals TO authenticated;
GRANT EXECUTE ON FUNCTION search_deals TO authenticated;
GRANT EXECUTE ON FUNCTION get_channel_stats TO authenticated;

-- ============================================
-- USAGE EXAMPLES
-- ============================================

-- Get deals with filters
-- SELECT * FROM get_deals_optimized('user-id', 'analyzed', 30, true, 50, 0);

-- Get stats
-- SELECT * FROM get_deal_stats_optimized('user-id');

-- Get single deal
-- SELECT * FROM get_deal_full('user-id', 'deal-id');

-- Get profitable deals
-- SELECT * FROM get_profitable_deals('user-id', 30, 50);

-- Search deals
-- SELECT * FROM search_deals('user-id', 'B08XYZ', 20);

