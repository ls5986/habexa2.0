-- ============================================
-- MAINTENANCE SCHEDULE FOR MATERIALIZED VIEWS
-- Run these via cron job or scheduled task
-- ============================================

-- ============================================
-- REFRESH SCHEDULE
-- ============================================

-- Refresh every 5 minutes (for high-traffic)
-- Refresh every 15 minutes (for normal traffic)
-- Refresh every 30 minutes (for low traffic)

-- Recommended: Refresh every 15 minutes
-- Add to Supabase cron jobs or pg_cron extension

-- ============================================
-- REFRESH ALL VIEWS
-- ============================================

-- Full refresh (blocks writes, faster)
-- REFRESH MATERIALIZED VIEW mv_deal_stats;
-- REFRESH MATERIALIZED VIEW mv_channel_performance;
-- REFRESH MATERIALIZED VIEW mv_supplier_performance;
-- REFRESH MATERIALIZED VIEW mv_analysis_summary;

-- Concurrent refresh (doesn't block, slower but safer)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_deal_stats;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_channel_performance;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_supplier_performance;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analysis_summary;

-- ============================================
-- SET UP PG_CRON (if available)
-- ============================================

-- Enable pg_cron extension (requires superuser)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule refresh every 15 minutes
-- SELECT cron.schedule(
--     'refresh-materialized-views',
--     '*/15 * * * *',  -- Every 15 minutes
--     $$SELECT refresh_all_materialized_views()$$
-- );

-- ============================================
-- VACUUM AND ANALYZE
-- ============================================

-- Run VACUUM ANALYZE weekly on large tables
-- VACUUM ANALYZE telegram_deals;
-- VACUUM ANALYZE analyses;
-- VACUUM ANALYZE telegram_messages;

-- ============================================
-- INDEX MAINTENANCE
-- ============================================

-- Check for unused indexes (run monthly)
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan as index_scans,
--     pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
--   AND idx_scan = 0  -- Never used
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- Check for missing indexes (run after query analysis)
-- Enable pg_stat_statements extension first:
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries:
-- SELECT 
--     query,
--     calls,
--     total_exec_time,
--     mean_exec_time,
--     max_exec_time
-- FROM pg_stat_statements
-- WHERE query LIKE '%telegram_deals%'
--   OR query LIKE '%analyses%'
-- ORDER BY mean_exec_time DESC
-- LIMIT 20;

-- ============================================
-- MONITORING QUERIES
-- ============================================

-- Check materialized view sizes
-- SELECT 
--     schemaname,
--     matviewname,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
-- FROM pg_matviews
-- WHERE schemaname = 'public';

-- Check table sizes
-- SELECT 
--     schemaname,
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
--     pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
-- ORDER BY idx_scan DESC;

