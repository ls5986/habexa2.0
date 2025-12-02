-- ============================================
-- PRODUCTION-GRADE MATERIALIZED VIEWS
-- For complex aggregations and stats
-- ============================================

-- ============================================
-- VIEW 1: Deal Stats Summary (Materialized)
-- ============================================

-- Drop if exists
DROP MATERIALIZED VIEW IF EXISTS mv_deal_stats;

-- Create materialized view for deal statistics
CREATE MATERIALIZED VIEW mv_deal_stats AS
SELECT 
    td.user_id,
    COUNT(*) as total_deals,
    COUNT(*) FILTER (WHERE td.status = 'pending') as pending_deals,
    COUNT(*) FILTER (WHERE td.status = 'analyzed') as analyzed_deals,
    COUNT(*) FILTER (WHERE td.status = 'analyzing') as analyzing_deals,
    COUNT(*) FILTER (WHERE td.status = 'error') as error_deals,
    COUNT(*) FILTER (WHERE a.roi >= 30) as profitable_deals,
    COUNT(*) FILTER (WHERE a.roi >= 30 AND a.roi < 50) as good_deals,
    COUNT(*) FILTER (WHERE a.roi >= 50) as excellent_deals,
    AVG(a.roi) FILTER (WHERE a.roi IS NOT NULL) as avg_roi,
    AVG(a.profit) FILTER (WHERE a.profit IS NOT NULL) as avg_profit,
    SUM(a.profit) FILTER (WHERE a.profit IS NOT NULL) as total_profit,
    MAX(td.extracted_at) as last_deal_extracted
FROM telegram_deals td
LEFT JOIN analyses a ON td.analysis_id = a.id
WHERE td.user_id IS NOT NULL
GROUP BY td.user_id;

-- Index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_deal_stats_user 
ON mv_deal_stats(user_id);

-- ============================================
-- VIEW 2: Channel Performance (Materialized)
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS mv_channel_performance;

CREATE MATERIALIZED VIEW mv_channel_performance AS
SELECT 
    tc.user_id,
    tc.channel_id,
    tc.channel_name,
    tc.supplier_id,
    COUNT(DISTINCT td.id) as total_deals,
    COUNT(DISTINCT td.id) FILTER (WHERE td.status = 'analyzed') as analyzed_deals,
    COUNT(DISTINCT td.id) FILTER (WHERE a.roi >= 30) as profitable_deals,
    AVG(a.roi) FILTER (WHERE a.roi IS NOT NULL) as avg_roi,
    MAX(td.extracted_at) as last_deal_extracted,
    tc.messages_received,
    tc.deals_extracted
FROM telegram_channels tc
LEFT JOIN telegram_deals td ON tc.id = td.channel_id
LEFT JOIN analyses a ON td.analysis_id = a.id
WHERE tc.user_id IS NOT NULL AND tc.is_active = true
GROUP BY tc.user_id, tc.channel_id, tc.channel_name, tc.supplier_id, tc.messages_received, tc.deals_extracted;

-- Index on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_channel_performance_user 
ON mv_channel_performance(user_id);

CREATE INDEX IF NOT EXISTS idx_mv_channel_performance_supplier 
ON mv_channel_performance(supplier_id) 
WHERE supplier_id IS NOT NULL;

-- ============================================
-- VIEW 3: Supplier Performance (Materialized)
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS mv_supplier_performance;

CREATE MATERIALIZED VIEW mv_supplier_performance AS
SELECT 
    s.user_id,
    s.id as supplier_id,
    s.name as supplier_name,
    COUNT(DISTINCT tc.id) as total_channels,
    COUNT(DISTINCT td.id) as total_deals,
    COUNT(DISTINCT td.id) FILTER (WHERE td.status = 'analyzed') as analyzed_deals,
    COUNT(DISTINCT td.id) FILTER (WHERE a.roi >= 30) as profitable_deals,
    AVG(a.roi) FILTER (WHERE a.roi IS NOT NULL) as avg_roi,
    AVG(a.profit) FILTER (WHERE a.profit IS NOT NULL) as avg_profit,
    SUM(a.profit) FILTER (WHERE a.profit IS NOT NULL) as total_profit
FROM suppliers s
LEFT JOIN telegram_channels tc ON s.id = tc.supplier_id
LEFT JOIN telegram_deals td ON tc.id = td.channel_id
LEFT JOIN analyses a ON td.analysis_id = a.id
WHERE s.user_id IS NOT NULL AND s.is_active = true
GROUP BY s.user_id, s.id, s.name;

-- Index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_supplier_performance_supplier 
ON mv_supplier_performance(user_id, supplier_id);

-- ============================================
-- VIEW 4: Recent Profitable Deals (Regular View)
-- ============================================

DROP VIEW IF EXISTS v_recent_profitable_deals;

CREATE VIEW v_recent_profitable_deals AS
SELECT 
    td.id as deal_id,
    td.user_id,
    td.asin,
    td.buy_cost,
    td.extracted_at,
    a.id as analysis_id,
    a.sell_price,
    a.profit,
    a.roi,
    a.margin,
    a.product_title,
    a.image_url,
    a.gating_status,
    tc.channel_name,
    s.name as supplier_name
FROM telegram_deals td
INNER JOIN analyses a ON td.analysis_id = a.id
LEFT JOIN telegram_channels tc ON td.channel_id = tc.id
LEFT JOIN suppliers s ON tc.supplier_id = s.id
WHERE a.roi >= 30
  AND td.status = 'analyzed'
  AND a.status = 'complete'
ORDER BY td.extracted_at DESC;

-- ============================================
-- VIEW 5: Analysis Summary (Materialized)
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS mv_analysis_summary;

CREATE MATERIALIZED VIEW mv_analysis_summary AS
SELECT 
    a.user_id,
    a.supplier_id,
    COUNT(*) as total_analyses,
    COUNT(*) FILTER (WHERE a.status = 'complete') as complete_analyses,
    COUNT(*) FILTER (WHERE a.status = 'pending') as pending_analyses,
    COUNT(*) FILTER (WHERE a.status = 'error') as error_analyses,
    COUNT(*) FILTER (WHERE a.roi >= 30) as profitable_analyses,
    AVG(a.roi) FILTER (WHERE a.roi IS NOT NULL) as avg_roi,
    AVG(a.profit) FILTER (WHERE a.profit IS NOT NULL) as avg_profit,
    MIN(a.roi) FILTER (WHERE a.roi IS NOT NULL) as min_roi,
    MAX(a.roi) FILTER (WHERE a.roi IS NOT NULL) as max_roi,
    COUNT(*) FILTER (WHERE a.gating_status = 'ELIGIBLE') as eligible_count,
    COUNT(*) FILTER (WHERE a.gating_status = 'APPROVAL_REQUIRED') as approval_required_count,
    COUNT(*) FILTER (WHERE a.gating_status = 'NOT_ELIGIBLE') as not_eligible_count
FROM analyses a
WHERE a.user_id IS NOT NULL
GROUP BY a.user_id, a.supplier_id;

-- Index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_analysis_summary_user_supplier 
ON mv_analysis_summary(user_id, supplier_id);

-- ============================================
-- REFRESH FUNCTIONS
-- ============================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_deal_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_channel_performance;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_supplier_performance;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analysis_summary;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh deal stats for a specific user
CREATE OR REPLACE FUNCTION refresh_user_deal_stats(p_user_id UUID)
RETURNS void AS $$
BEGIN
    -- Delete old stats for user
    DELETE FROM mv_deal_stats WHERE user_id = p_user_id;
    
    -- Re-insert fresh stats
    INSERT INTO mv_deal_stats
    SELECT 
        td.user_id,
        COUNT(*) as total_deals,
        COUNT(*) FILTER (WHERE td.status = 'pending') as pending_deals,
        COUNT(*) FILTER (WHERE td.status = 'analyzed') as analyzed_deals,
        COUNT(*) FILTER (WHERE td.status = 'analyzing') as analyzing_deals,
        COUNT(*) FILTER (WHERE td.status = 'error') as error_deals,
        COUNT(*) FILTER (WHERE a.roi >= 30) as profitable_deals,
        COUNT(*) FILTER (WHERE a.roi >= 30 AND a.roi < 50) as good_deals,
        COUNT(*) FILTER (WHERE a.roi >= 50) as excellent_deals,
        AVG(a.roi) FILTER (WHERE a.roi IS NOT NULL) as avg_roi,
        AVG(a.profit) FILTER (WHERE a.profit IS NOT NULL) as avg_profit,
        SUM(a.profit) FILTER (WHERE a.profit IS NOT NULL) as total_profit,
        MAX(td.extracted_at) as last_deal_extracted
    FROM telegram_deals td
    LEFT JOIN analyses a ON td.analysis_id = a.id
    WHERE td.user_id = p_user_id
    GROUP BY td.user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- AUTO-REFRESH TRIGGERS (Optional)
-- ============================================

-- Trigger to refresh stats when deals change
-- Note: This can be slow for high-volume writes
-- Consider using a scheduled job instead

-- CREATE OR REPLACE FUNCTION trigger_refresh_deal_stats()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     PERFORM refresh_user_deal_stats(NEW.user_id);
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE TRIGGER refresh_deal_stats_on_insert
--     AFTER INSERT ON telegram_deals
--     FOR EACH ROW
--     EXECUTE FUNCTION trigger_refresh_deal_stats();

-- CREATE TRIGGER refresh_deal_stats_on_update
--     AFTER UPDATE ON telegram_deals
--     FOR EACH ROW
--     WHEN (OLD.status IS DISTINCT FROM NEW.status)
--     EXECUTE FUNCTION trigger_refresh_deal_stats();

-- ============================================
-- INITIAL REFRESH
-- ============================================

-- Refresh all views initially
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_deal_stats;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_channel_performance;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_supplier_performance;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analysis_summary;

-- ============================================
-- USAGE EXAMPLES
-- ============================================

-- Get deal stats for a user (FAST - uses materialized view)
-- SELECT * FROM mv_deal_stats WHERE user_id = 'your-user-id';

-- Get channel performance (FAST)
-- SELECT * FROM mv_channel_performance WHERE user_id = 'your-user-id' ORDER BY profitable_deals DESC;

-- Get recent profitable deals (uses regular view, still fast with indexes)
-- SELECT * FROM v_recent_profitable_deals WHERE user_id = 'your-user-id' LIMIT 20;

-- Refresh stats manually
-- SELECT refresh_user_deal_stats('your-user-id');

-- Refresh all views (run via cron job every 5-15 minutes)
-- SELECT refresh_all_materialized_views();

