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
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'deals') THEN
        DELETE FROM deals;
    END IF;
END $$;

-- Suppliers (linked to users)
DELETE FROM suppliers;

-- Amazon connections (linked to users)
DELETE FROM amazon_connections;

-- Amazon credentials (linked to users)
DELETE FROM amazon_credentials;

-- Orders (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'orders') THEN
        DELETE FROM orders;
    END IF;
END $$;

-- Watchlist (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'watchlist') THEN
        DELETE FROM watchlist;
    END IF;
END $$;

-- Notifications (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'notifications') THEN
        DELETE FROM notifications;
    END IF;
END $$;

-- User settings (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_settings') THEN
        DELETE FROM user_settings;
    END IF;
END $$;

-- Subscriptions (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'subscriptions') THEN
        DELETE FROM subscriptions;
    END IF;
END $$;

-- Payments (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'payments') THEN
        DELETE FROM payments;
    END IF;
END $$;

-- Invoices (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'invoices') THEN
        DELETE FROM invoices;
    END IF;
END $$;

-- Usage records (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'usage_records') THEN
        DELETE FROM usage_records;
    END IF;
END $$;

-- Brands (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'brands') THEN
        DELETE FROM brands;
    END IF;
END $$;

-- ============================================
-- VERIFY DELETION
-- ============================================

-- Re-enable triggers
SET session_replication_role = 'origin';

-- Show counts (should all be 0) - only for tables that exist
DO $$
DECLARE
    table_count INTEGER;
    result_text TEXT := '';
BEGIN
    -- Check each table and add to result if it exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'products') THEN
        SELECT COUNT(*) INTO table_count FROM products;
        result_text := result_text || 'products: ' || table_count || E'\n';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'product_sources') THEN
        SELECT COUNT(*) INTO table_count FROM product_sources;
        result_text := result_text || 'product_sources: ' || table_count || E'\n';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'analyses') THEN
        SELECT COUNT(*) INTO table_count FROM analyses;
        result_text := result_text || 'analyses: ' || table_count || E'\n';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'jobs') THEN
        SELECT COUNT(*) INTO table_count FROM jobs;
        result_text := result_text || 'jobs: ' || table_count || E'\n';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'keepa_analysis') THEN
        SELECT COUNT(*) INTO table_count FROM keepa_analysis;
        result_text := result_text || 'keepa_analysis: ' || table_count || E'\n';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'keepa_cache') THEN
        SELECT COUNT(*) INTO table_count FROM keepa_cache;
        result_text := result_text || 'keepa_cache: ' || table_count || E'\n';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'suppliers') THEN
        SELECT COUNT(*) INTO table_count FROM suppliers;
        result_text := result_text || 'suppliers: ' || table_count || E'\n';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'brands') THEN
        SELECT COUNT(*) INTO table_count FROM brands;
        result_text := result_text || 'brands: ' || table_count || E'\n';
    END IF;
    
    RAISE NOTICE 'Table counts after deletion:%', E'\n' || result_text;
END $$;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ All data cleared successfully!';
    RAISE NOTICE '📋 Schema (tables, indexes, policies) is still intact.';
    RAISE NOTICE '🔄 You can now start fresh with new data.';
END $$;

