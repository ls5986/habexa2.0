-- ============================================
-- DROP EVERYTHING - HABEXA DATABASE
-- ============================================
-- This script drops all tables, functions, triggers, policies, and indexes.
-- Run this BEFORE running CREATE_SCHEMA_FIXED.sql
-- WARNING: This will DELETE ALL DATA!
-- ============================================

-- ============================================
-- PART 1: DROP TRIGGERS
-- ============================================

DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles CASCADE;
DROP TRIGGER IF EXISTS update_suppliers_updated_at ON public.suppliers CASCADE;
DROP TRIGGER IF EXISTS update_deals_updated_at ON public.deals CASCADE;
DROP TRIGGER IF EXISTS update_analyses_updated_at ON public.analyses CASCADE;
DROP TRIGGER IF EXISTS update_orders_updated_at ON public.orders CASCADE;
DROP TRIGGER IF EXISTS update_user_settings_updated_at ON public.user_settings CASCADE;
DROP TRIGGER IF EXISTS update_amazon_creds_updated_at ON public.amazon_credentials CASCADE;
DROP TRIGGER IF EXISTS update_telegram_creds_updated_at ON public.telegram_credentials CASCADE;
DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON public.subscriptions CASCADE;
DROP TRIGGER IF EXISTS trigger_amazon_credentials_updated_at ON public.amazon_credentials CASCADE;
DROP TRIGGER IF EXISTS trigger_telegram_session_updated ON public.telegram_sessions CASCADE;
DROP TRIGGER IF EXISTS trigger_update_channel_stats ON public.telegram_messages CASCADE;
DROP TRIGGER IF EXISTS trigger_increment_deals ON public.telegram_deals CASCADE;
DROP TRIGGER IF EXISTS update_amazon_connections_updated_at ON public.amazon_connections CASCADE;

-- ============================================
-- PART 2: DROP POLICIES
-- ============================================

DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles CASCADE;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles CASCADE;
DROP POLICY IF EXISTS "Users can view own suppliers" ON public.suppliers CASCADE;
DROP POLICY IF EXISTS "Users can view own messages" ON public.messages CASCADE;
DROP POLICY IF EXISTS "Users can view own deals" ON public.deals CASCADE;
DROP POLICY IF EXISTS "Users can view own analyses" ON public.analyses CASCADE;
DROP POLICY IF EXISTS "Users can view own watchlist" ON public.watchlist CASCADE;
DROP POLICY IF EXISTS "Users can view own orders" ON public.orders CASCADE;
DROP POLICY IF EXISTS "Users can view own settings" ON public.user_settings CASCADE;
DROP POLICY IF EXISTS "Users can view own notifications" ON public.notifications CASCADE;
DROP POLICY IF EXISTS "Users can view own subscription" ON public.subscriptions CASCADE;
DROP POLICY IF EXISTS "Users can view own payments" ON public.payments CASCADE;
DROP POLICY IF EXISTS "Users can view own invoices" ON public.invoices CASCADE;
DROP POLICY IF EXISTS "Users can view own usage" ON public.usage_records CASCADE;
DROP POLICY IF EXISTS "Users can view own amazon credentials" ON public.amazon_credentials CASCADE;
DROP POLICY IF EXISTS "Service role can manage amazon credentials" ON public.amazon_credentials CASCADE;
DROP POLICY IF EXISTS "Users can view own amazon connection" ON public.amazon_connections CASCADE;
DROP POLICY IF EXISTS "Users can manage own amazon connection" ON public.amazon_connections CASCADE;
DROP POLICY IF EXISTS "Service can manage amazon connections" ON public.amazon_connections CASCADE;
DROP POLICY IF EXISTS "Users can view own eligibility cache" ON public.eligibility_cache CASCADE;
DROP POLICY IF EXISTS "Users can view own fee cache" ON public.fee_cache CASCADE;
DROP POLICY IF EXISTS "Users can view own telegram session" ON public.telegram_sessions CASCADE;
DROP POLICY IF EXISTS "Service role can manage telegram sessions" ON public.telegram_sessions CASCADE;
DROP POLICY IF EXISTS "Users can view own telegram creds" ON public.telegram_credentials CASCADE;
DROP POLICY IF EXISTS "Users can manage own channels" ON public.telegram_channels CASCADE;
DROP POLICY IF EXISTS "Users can view own messages" ON public.telegram_messages CASCADE;
DROP POLICY IF EXISTS "Users can view own telegram deals" ON public.telegram_deals CASCADE;
DROP POLICY IF EXISTS "Users can manage own channels" ON public.monitored_channels CASCADE;

-- ============================================
-- PART 3: DROP INDEXES
-- ============================================

DROP INDEX IF EXISTS public.idx_deals_user_status CASCADE;
DROP INDEX IF EXISTS public.idx_deals_asin CASCADE;
DROP INDEX IF EXISTS public.idx_deals_created CASCADE;
DROP INDEX IF EXISTS public.idx_suppliers_user CASCADE;
DROP INDEX IF EXISTS public.idx_messages_user CASCADE;
DROP INDEX IF EXISTS public.idx_notifications_user_read CASCADE;
DROP INDEX IF EXISTS public.idx_analyses_user CASCADE;
DROP INDEX IF EXISTS public.idx_analyses_asin CASCADE;
DROP INDEX IF EXISTS public.idx_subscriptions_user CASCADE;
DROP INDEX IF EXISTS public.idx_subscriptions_stripe_customer CASCADE;
DROP INDEX IF EXISTS public.idx_subscriptions_stripe_sub CASCADE;
DROP INDEX IF EXISTS public.idx_payments_user CASCADE;
DROP INDEX IF EXISTS public.idx_usage_user_created CASCADE;
DROP INDEX IF EXISTS public.idx_amazon_creds_user CASCADE;
DROP INDEX IF EXISTS public.idx_amazon_creds_seller CASCADE;
DROP INDEX IF EXISTS public.idx_amazon_connections_user CASCADE;
DROP INDEX IF EXISTS public.idx_eligibility_user_asin CASCADE;
DROP INDEX IF EXISTS public.idx_eligibility_expires CASCADE;
DROP INDEX IF EXISTS public.idx_fee_cache_asin CASCADE;
DROP INDEX IF EXISTS public.idx_fee_cache_expires CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_channels_user CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_channels_active CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_messages_user CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_messages_channel CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_messages_unprocessed CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_deals_user CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_deals_asin CASCADE;
DROP INDEX IF EXISTS public.idx_telegram_deals_pending CASCADE;
DROP INDEX IF EXISTS public.idx_monitored_channels_user CASCADE;
DROP INDEX IF EXISTS public.idx_keepa_cache_asin CASCADE;
DROP INDEX IF EXISTS public.idx_keepa_cache_expires CASCADE;

-- ============================================
-- PART 4: DROP FUNCTIONS
-- ============================================

DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS get_tier_limits(TEXT) CASCADE;
DROP FUNCTION IF EXISTS check_user_limit(UUID, TEXT) CASCADE;
DROP FUNCTION IF EXISTS increment_usage(UUID, TEXT, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS decrement_usage(UUID, TEXT, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS increment_analyses(UUID, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS cleanup_expired_cache() CASCADE;
DROP FUNCTION IF EXISTS update_amazon_credentials_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_channel_stats() CASCADE;
DROP FUNCTION IF EXISTS increment_deals_extracted() CASCADE;
DROP FUNCTION IF EXISTS update_telegram_session_timestamp() CASCADE;
DROP FUNCTION IF EXISTS cleanup_keepa_cache() CASCADE;
DROP FUNCTION IF EXISTS track_keepa_usage(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS update_amazon_connections_updated_at() CASCADE;

-- ============================================
-- PART 5: DROP TABLES (in reverse dependency order)
-- ============================================

DROP TABLE IF EXISTS public.telegram_deals CASCADE;
DROP TABLE IF EXISTS public.telegram_messages CASCADE;
DROP TABLE IF EXISTS public.telegram_channels CASCADE;
DROP TABLE IF EXISTS public.telegram_sessions CASCADE;
DROP TABLE IF EXISTS public.telegram_credentials CASCADE;
DROP TABLE IF EXISTS public.monitored_channels CASCADE;
DROP TABLE IF EXISTS public.keepa_usage CASCADE;
DROP TABLE IF EXISTS public.keepa_cache CASCADE;
DROP TABLE IF EXISTS public.fee_cache CASCADE;
DROP TABLE IF EXISTS public.eligibility_cache CASCADE;
DROP TABLE IF EXISTS public.amazon_connections CASCADE;
DROP TABLE IF EXISTS public.amazon_credentials CASCADE;
DROP TABLE IF EXISTS public.usage_records CASCADE;
DROP TABLE IF EXISTS public.invoices CASCADE;
DROP TABLE IF EXISTS public.payments CASCADE;
DROP TABLE IF EXISTS public.subscriptions CASCADE;
DROP TABLE IF EXISTS public.notifications CASCADE;
DROP TABLE IF EXISTS public.user_settings CASCADE;
DROP TABLE IF EXISTS public.orders CASCADE;
DROP TABLE IF EXISTS public.watchlist CASCADE;
DROP TABLE IF EXISTS public.analyses CASCADE;
DROP TABLE IF EXISTS public.deals CASCADE;
DROP TABLE IF EXISTS public.messages CASCADE;
DROP TABLE IF EXISTS public.suppliers CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;

-- ============================================
-- DONE!
-- ============================================

-- Everything has been dropped. Now you can run CREATE_SCHEMA_FIXED.sql

