-- ============================================
-- CLEAR ALL DATA - HABEXA DATABASE
-- ============================================
-- This script deletes ALL data from all tables
-- but keeps the schema intact (tables, indexes, policies, etc.)
-- 
-- WARNING: This will DELETE ALL DATA and cannot be undone!
-- Run this in Supabase SQL Editor
-- ============================================

-- Disable triggers temporarily for faster deletion
SET session_replication_role = 'replica';

-- ============================================
-- DELETE DATA IN CORRECT ORDER (respecting foreign keys)
-- ============================================

-- 1. Delete child tables first (those with foreign keys)

-- Product sources (deals linked to products)
DELETE FROM product_sources;

-- Telegram deals (linked to analyses, messages, channels)
DELETE FROM telegram_deals;

-- Telegram messages (linked to channels)
DELETE FROM telegram_messages;

-- Jobs (may reference products/analyses)
DELETE FROM jobs;

-- Analyses (linked to products, users)
DELETE FROM analyses;

-- Products (parent table)
DELETE FROM products;

-- Telegram channels (linked to suppliers)
DELETE FROM telegram_channels;

-- Telegram sessions (user sessions)
DELETE FROM telegram_sessions;

-- Keepa analysis (detailed analysis for TOP PRODUCTS)
DELETE FROM keepa_analysis;

-- Keepa cache
DELETE FROM keepa_cache;

-- Keepa usage tracking
DELETE FROM keepa_usage;

-- Messages (linked to suppliers)
DELETE FROM messages;

-- Deals (legacy table, if exists)
DELETE FROM deals;

-- Suppliers (linked to users)
DELETE FROM suppliers;

-- Amazon connections (linked to users)
DELETE FROM amazon_connections;

-- Amazon credentials (linked to users)
DELETE FROM amazon_credentials;

-- Orders (if exists)
DELETE FROM orders;

-- Watchlist (if exists)
DELETE FROM watchlist;

-- Notifications (if exists)
DELETE FROM notifications;

-- User settings (if exists)
DELETE FROM user_settings;

-- Subscriptions (if exists)
DELETE FROM subscriptions;

-- Payments (if exists)
DELETE FROM payments;

-- Invoices (if exists)
DELETE FROM invoices;

-- Usage records (if exists)
DELETE FROM usage_records;

-- Brands (if exists)
DELETE FROM brands;

-- ============================================
-- VERIFY DELETION
-- ============================================

-- Re-enable triggers
SET session_replication_role = 'origin';

-- Show counts (should all be 0)
SELECT 
    'products' as table_name, COUNT(*) as count FROM products
UNION ALL
SELECT 'product_sources', COUNT(*) FROM product_sources
UNION ALL
SELECT 'analyses', COUNT(*) FROM analyses
UNION ALL
SELECT 'jobs', COUNT(*) FROM jobs
UNION ALL
SELECT 'telegram_deals', COUNT(*) FROM telegram_deals
UNION ALL
SELECT 'telegram_messages', COUNT(*) FROM telegram_messages
UNION ALL
SELECT 'telegram_channels', COUNT(*) FROM telegram_channels
UNION ALL
SELECT 'telegram_sessions', COUNT(*) FROM telegram_sessions
UNION ALL
SELECT 'keepa_analysis', COUNT(*) FROM keepa_analysis
UNION ALL
SELECT 'keepa_cache', COUNT(*) FROM keepa_cache
UNION ALL
SELECT 'keepa_usage', COUNT(*) FROM keepa_usage
UNION ALL
SELECT 'messages', COUNT(*) FROM messages
UNION ALL
SELECT 'deals', COUNT(*) FROM deals
UNION ALL
SELECT 'suppliers', COUNT(*) FROM suppliers
UNION ALL
SELECT 'amazon_connections', COUNT(*) FROM amazon_connections
UNION ALL
SELECT 'amazon_credentials', COUNT(*) FROM amazon_credentials
ORDER BY table_name;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ All data cleared successfully!';
    RAISE NOTICE '📋 Schema (tables, indexes, policies) is still intact.';
    RAISE NOTICE '🔄 You can now start fresh with new data.';
END $$;

