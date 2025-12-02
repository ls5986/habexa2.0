-- ============================================
-- PRODUCTION-GRADE INDEXES FOR HABEXA
-- Run this in Supabase SQL Editor
-- ============================================

-- ============================================
-- TELEGRAM_DEALS TABLE
-- ============================================

-- Primary lookup: user_id + status (most common filter)
CREATE INDEX IF NOT EXISTS idx_telegram_deals_user_status 
ON telegram_deals(user_id, status) 
WHERE user_id IS NOT NULL;

-- Time-based queries: user_id + extracted_at (for sorting)
CREATE INDEX IF NOT EXISTS idx_telegram_deals_user_extracted 
ON telegram_deals(user_id, extracted_at DESC NULLS LAST) 
WHERE user_id IS NOT NULL;

-- Analysis lookup: analysis_id (for joins)
CREATE INDEX IF NOT EXISTS idx_telegram_deals_analysis 
ON telegram_deals(analysis_id) 
WHERE analysis_id IS NOT NULL;

-- Channel lookup: channel_id (for filtering by channel)
CREATE INDEX IF NOT EXISTS idx_telegram_deals_channel 
ON telegram_deals(channel_id) 
WHERE channel_id IS NOT NULL;

-- Composite: user + channel + status (for channel-specific queries)
CREATE INDEX IF NOT EXISTS idx_telegram_deals_user_channel_status 
ON telegram_deals(user_id, channel_id, status) 
WHERE user_id IS NOT NULL AND channel_id IS NOT NULL;

-- ASIN lookup: for duplicate detection
CREATE INDEX IF NOT EXISTS idx_telegram_deals_asin 
ON telegram_deals(asin) 
WHERE asin IS NOT NULL;

-- Composite: user + asin (for unique constraint enforcement)
CREATE INDEX IF NOT EXISTS idx_telegram_deals_user_asin 
ON telegram_deals(user_id, asin) 
WHERE user_id IS NOT NULL AND asin IS NOT NULL;

-- ============================================
-- ANALYSES TABLE
-- ============================================

-- Primary lookup: user_id + supplier_id + asin (unique constraint)
CREATE INDEX IF NOT EXISTS idx_analyses_user_supplier_asin 
ON analyses(user_id, supplier_id, asin) 
WHERE user_id IS NOT NULL;

-- ROI filtering: user_id + roi (for profitable deals)
CREATE INDEX IF NOT EXISTS idx_analyses_user_roi 
ON analyses(user_id, roi DESC NULLS LAST) 
WHERE user_id IS NOT NULL AND roi IS NOT NULL;

-- Status filtering: user_id + status
CREATE INDEX IF NOT EXISTS idx_analyses_user_status 
ON analyses(user_id, status) 
WHERE user_id IS NOT NULL;

-- ASIN lookup: for finding existing analyses
CREATE INDEX IF NOT EXISTS idx_analyses_asin 
ON analyses(asin) 
WHERE asin IS NOT NULL;

-- Supplier lookup: user_id + supplier_id
CREATE INDEX IF NOT EXISTS idx_analyses_user_supplier 
ON analyses(user_id, supplier_id) 
WHERE user_id IS NOT NULL;

-- Time-based: created_at for recent analyses
CREATE INDEX IF NOT EXISTS idx_analyses_created 
ON analyses(created_at DESC NULLS LAST) 
WHERE created_at IS NOT NULL;

-- Composite: user + status + roi (for stats queries)
CREATE INDEX IF NOT EXISTS idx_analyses_user_status_roi 
ON analyses(user_id, status, roi DESC) 
WHERE user_id IS NOT NULL AND status = 'complete';

-- ============================================
-- TELEGRAM_CHANNELS TABLE
-- ============================================

-- Primary lookup: user_id + channel_id
CREATE INDEX IF NOT EXISTS idx_telegram_channels_user_channel 
ON telegram_channels(user_id, channel_id) 
WHERE user_id IS NOT NULL;

-- Active channels: user_id + is_active
CREATE INDEX IF NOT EXISTS idx_telegram_channels_user_active 
ON telegram_channels(user_id, is_active) 
WHERE user_id IS NOT NULL AND is_active = true;

-- Supplier lookup: supplier_id (for supplier-based queries)
CREATE INDEX IF NOT EXISTS idx_telegram_channels_supplier 
ON telegram_channels(supplier_id) 
WHERE supplier_id IS NOT NULL;

-- Username lookup: channel_username (for entity resolution)
CREATE INDEX IF NOT EXISTS idx_telegram_channels_username 
ON telegram_channels(channel_username) 
WHERE channel_username IS NOT NULL;

-- ============================================
-- TELEGRAM_MESSAGES TABLE
-- ============================================

-- Primary lookup: user_id + channel_id + message_id
CREATE INDEX IF NOT EXISTS idx_telegram_messages_user_channel_msg 
ON telegram_messages(user_id, telegram_channel_id, telegram_message_id) 
WHERE user_id IS NOT NULL;

-- Time-based: telegram_date for backfill queries
CREATE INDEX IF NOT EXISTS idx_telegram_messages_date 
ON telegram_messages(telegram_date DESC NULLS LAST) 
WHERE telegram_date IS NOT NULL;

-- Processing status: is_processed
CREATE INDEX IF NOT EXISTS idx_telegram_messages_processed 
ON telegram_messages(user_id, is_processed) 
WHERE user_id IS NOT NULL AND is_processed = false;

-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================

-- Primary lookup: user_id + is_read + created_at
CREATE INDEX IF NOT EXISTS idx_notifications_user_read_created 
ON notifications(user_id, is_read, created_at DESC NULLS LAST) 
WHERE user_id IS NOT NULL;

-- Unread count: user_id + is_read (for badge counts)
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, is_read) 
WHERE user_id IS NOT NULL AND is_read = false;

-- Deal notifications: deal_id (for linking)
CREATE INDEX IF NOT EXISTS idx_notifications_deal 
ON notifications(deal_id) 
WHERE deal_id IS NOT NULL;

-- ============================================
-- SUBSCRIPTIONS TABLE
-- ============================================

-- Primary lookup: user_id (most common)
CREATE INDEX IF NOT EXISTS idx_subscriptions_user 
ON subscriptions(user_id) 
WHERE user_id IS NOT NULL;

-- Stripe customer lookup: stripe_customer_id
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer 
ON subscriptions(stripe_customer_id) 
WHERE stripe_customer_id IS NOT NULL;

-- Stripe subscription lookup: stripe_subscription_id
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_sub 
ON subscriptions(stripe_subscription_id) 
WHERE stripe_subscription_id IS NOT NULL;

-- Active subscriptions: user_id + status
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status 
ON subscriptions(user_id, status) 
WHERE user_id IS NOT NULL AND status IN ('active', 'trialing');

-- ============================================
-- SUPPLIERS TABLE
-- ============================================

-- Primary lookup: user_id
CREATE INDEX IF NOT EXISTS idx_suppliers_user 
ON suppliers(user_id) 
WHERE user_id IS NOT NULL;

-- Active suppliers: user_id + is_active
CREATE INDEX IF NOT EXISTS idx_suppliers_user_active 
ON suppliers(user_id, is_active) 
WHERE user_id IS NOT NULL AND is_active = true;

-- ============================================
-- FEATURE_USAGE TABLE
-- ============================================

-- Primary lookup: user_id + feature
CREATE INDEX IF NOT EXISTS idx_feature_usage_user_feature 
ON feature_usage(user_id, feature) 
WHERE user_id IS NOT NULL;

-- Time-based: user_id + date (for monthly resets)
CREATE INDEX IF NOT EXISTS idx_feature_usage_user_date 
ON feature_usage(user_id, date DESC) 
WHERE user_id IS NOT NULL;

-- ============================================
-- FOREIGN KEY INDEXES (for JOIN performance)
-- ============================================

-- These are automatically created by PostgreSQL for foreign keys,
-- but we ensure they exist for performance

-- telegram_deals -> analyses
-- (covered by idx_telegram_deals_analysis above)

-- telegram_deals -> telegram_channels
-- (covered by idx_telegram_deals_channel above)

-- telegram_channels -> suppliers
-- (covered by idx_telegram_channels_supplier above)

-- ============================================
-- UPDATE TABLE STATISTICS
-- ============================================

-- Run ANALYZE to update query planner statistics
ANALYZE telegram_deals;
ANALYZE analyses;
ANALYZE telegram_channels;
ANALYZE telegram_messages;
ANALYZE notifications;
ANALYZE subscriptions;
ANALYZE suppliers;
ANALYZE feature_usage;

-- ============================================
-- INDEX MAINTENANCE
-- ============================================

-- Check index usage (run periodically to identify unused indexes)
-- SELECT schemaname, tablename, indexname, idx_scan 
-- FROM pg_stat_user_indexes 
-- WHERE schemaname = 'public' 
-- ORDER BY idx_scan ASC;

-- Check index sizes
-- SELECT schemaname, tablename, indexname, 
--        pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes 
-- WHERE schemaname = 'public'
-- ORDER BY pg_relation_size(indexrelid) DESC;

