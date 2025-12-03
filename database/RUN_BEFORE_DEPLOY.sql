-- ============================================
-- HABEXA - PRE-DEPLOYMENT MIGRATIONS
-- ============================================
-- Run this in Supabase SQL Editor BEFORE deploying
-- All statements use IF NOT EXISTS / IF EXISTS for safety
-- Safe to run multiple times
-- ============================================

-- ============================================
-- 1. SUBSCRIPTION TRIAL TRACKING
-- ============================================
-- Add trial tracking fields to subscriptions table

ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS had_free_trial BOOLEAN DEFAULT FALSE;

ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS trial_start TIMESTAMPTZ;

ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS trial_end TIMESTAMPTZ;

ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE;

-- Update existing records: if they have trial_end set, they had a trial
UPDATE public.subscriptions
SET had_free_trial = TRUE
WHERE trial_end IS NOT NULL AND had_free_trial IS NULL;

-- Add comments
COMMENT ON COLUMN public.subscriptions.had_free_trial IS 'Prevents users from getting multiple free trials';
COMMENT ON COLUMN public.subscriptions.cancel_at_period_end IS 'True if subscription is set to cancel at period end';

-- ============================================
-- 2. PRODUCT_SOURCES STAGE ENUM
-- ============================================
-- Ensure 'buy_list' stage exists in product_sources.stage

-- Check if stage column exists and add 'buy_list' if needed
DO $$
BEGIN
    -- Check if product_sources table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'product_sources') THEN
        -- If stage is a text column (not enum), no action needed
        -- If stage is an enum, add 'buy_list' value
        IF EXISTS (
            SELECT 1 FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid 
            WHERE t.typname = 'product_stage_enum' 
            AND e.enumlabel = 'buy_list'
        ) THEN
            -- 'buy_list' already exists in enum
            RAISE NOTICE 'buy_list stage already exists in enum';
        ELSIF EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'product_stage_enum'
        ) THEN
            -- Enum exists but 'buy_list' doesn't - add it
            ALTER TYPE product_stage_enum ADD VALUE IF NOT EXISTS 'buy_list';
            RAISE NOTICE 'Added buy_list to product_stage_enum';
        ELSE
            -- No enum, stage is likely TEXT - no action needed
            RAISE NOTICE 'product_sources.stage is TEXT, no enum update needed';
        END IF;
    END IF;
END $$;

-- ============================================
-- 3. ORDERS TABLE (if not exists)
-- ============================================
-- Create orders table if it doesn't exist

CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES public.suppliers(id) ON DELETE SET NULL,
    deal_id UUID REFERENCES public.deals(id) ON DELETE SET NULL,
    
    asin TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10,2) NOT NULL,
    total_cost DECIMAL(10,2) NOT NULL,
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'shipped', 'received', 'cancelled')),
    expected_delivery DATE,
    actual_delivery DATE,
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_user ON public.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON public.orders(created_at DESC);

-- RLS
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

-- Policies (if not exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'orders' 
        AND policyname = 'Users can view own orders'
    ) THEN
        CREATE POLICY "Users can view own orders" ON public.orders FOR SELECT USING (auth.uid() = user_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'orders' 
        AND policyname = 'Users can insert own orders'
    ) THEN
        CREATE POLICY "Users can insert own orders" ON public.orders FOR INSERT WITH CHECK (auth.uid() = user_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'orders' 
        AND policyname = 'Users can update own orders'
    ) THEN
        CREATE POLICY "Users can update own orders" ON public.orders FOR UPDATE USING (auth.uid() = user_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'orders' 
        AND policyname = 'Users can delete own orders'
    ) THEN
        CREATE POLICY "Users can delete own orders" ON public.orders FOR DELETE USING (auth.uid() = user_id);
    END IF;
END $$;

-- ============================================
-- 4. TELEGRAM TABLES (if not exists)
-- ============================================
-- Create telegram_credentials if not exists

CREATE TABLE IF NOT EXISTS public.telegram_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    telegram_user_id TEXT,
    session_string TEXT, -- Store encrypted
    is_connected BOOLEAN DEFAULT FALSE,
    connected_channels JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_telegram_creds_user ON public.telegram_credentials(user_id);

-- RLS
ALTER TABLE public.telegram_credentials ENABLE ROW LEVEL SECURITY;

-- Policies
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'telegram_credentials' 
        AND policyname = 'Users can view own telegram creds'
    ) THEN
        CREATE POLICY "Users can view own telegram creds" ON public.telegram_credentials FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

-- telegram_channels table (from telegram_schema.sql)
CREATE TABLE IF NOT EXISTS public.telegram_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES public.suppliers(id) ON DELETE SET NULL,
    
    channel_id BIGINT NOT NULL,
    channel_name TEXT NOT NULL,
    channel_username TEXT,
    channel_type TEXT DEFAULT 'channel',
    
    is_active BOOLEAN DEFAULT TRUE,
    messages_received INTEGER DEFAULT 0,
    deals_extracted INTEGER DEFAULT 0,
    
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, channel_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_telegram_channels_user ON public.telegram_channels(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_channels_active ON public.telegram_channels(user_id, is_active) WHERE is_active = TRUE;

-- RLS
ALTER TABLE public.telegram_channels ENABLE ROW LEVEL SECURITY;

-- Policies
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'telegram_channels' 
        AND policyname = 'Users can manage own telegram channels'
    ) THEN
        CREATE POLICY "Users can manage own telegram channels" ON public.telegram_channels FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

-- ============================================
-- 5. AMAZON CONNECTIONS (if not exists)
-- ============================================
-- Code uses 'amazon_connections' table (not 'amazon_credentials')

CREATE TABLE IF NOT EXISTS public.amazon_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    seller_id TEXT,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    refresh_token_encrypted TEXT, -- Store encrypted
    is_connected BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, marketplace_id)
);

-- Also create amazon_credentials for backward compatibility (if code references it)
CREATE TABLE IF NOT EXISTS public.amazon_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    seller_id TEXT,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    refresh_token TEXT, -- Store encrypted
    is_connected BOOLEAN DEFAULT FALSE,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_amazon_connections_user ON public.amazon_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_amazon_connections_marketplace ON public.amazon_connections(user_id, marketplace_id);
CREATE INDEX IF NOT EXISTS idx_amazon_creds_user ON public.amazon_credentials(user_id);

-- RLS
ALTER TABLE public.amazon_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amazon_credentials ENABLE ROW LEVEL SECURITY;

-- Policies
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'amazon_connections' 
        AND policyname = 'Users can view own amazon connections'
    ) THEN
        CREATE POLICY "Users can view own amazon connections" ON public.amazon_connections FOR ALL USING (auth.uid() = user_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'amazon_credentials' 
        AND policyname = 'Users can view own amazon creds'
    ) THEN
        CREATE POLICY "Users can view own amazon creds" ON public.amazon_credentials FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

-- ============================================
-- 6. PRODUCT_SOURCES TABLE (if not exists)
-- ============================================
-- This is critical for buy list functionality

CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    asin VARCHAR(10) NOT NULL,
    
    title TEXT,
    image_url TEXT,
    category TEXT,
    brand TEXT,
    
    sell_price DECIMAL(10,2),
    fees_total DECIMAL(10,2),
    
    bsr INTEGER,
    seller_count INTEGER,
    fba_seller_count INTEGER,
    amazon_sells BOOLEAN DEFAULT FALSE,
    
    analysis_id UUID,
    status TEXT DEFAULT 'pending',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, asin)
);

CREATE TABLE IF NOT EXISTS public.product_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES public.suppliers(id) ON DELETE SET NULL,
    
    buy_cost DECIMAL(10,2),
    moq INTEGER DEFAULT 1,
    
    source TEXT NOT NULL DEFAULT 'manual',
    source_detail TEXT,
    
    stage TEXT DEFAULT 'new',  -- new, analyzing, reviewed, buy_list, ordered
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(product_id, supplier_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_user ON public.products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_asin ON public.products(asin);
CREATE INDEX IF NOT EXISTS idx_product_sources_product ON public.product_sources(product_id);
CREATE INDEX IF NOT EXISTS idx_product_sources_stage ON public.product_sources(stage);
CREATE INDEX IF NOT EXISTS idx_product_sources_user_stage ON public.product_sources(product_id, stage) 
    WHERE stage = 'buy_list';

-- RLS
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_sources ENABLE ROW LEVEL SECURITY;

-- Policies
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'products' 
        AND policyname = 'Users can view own products'
    ) THEN
        CREATE POLICY "Users can view own products" ON public.products FOR SELECT USING (auth.uid() = user_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'product_sources' 
        AND policyname = 'Users can view own product sources'
    ) THEN
        CREATE POLICY "Users can view own product sources" ON public.product_sources FOR SELECT USING (
            EXISTS (SELECT 1 FROM products WHERE products.id = product_sources.product_id AND products.user_id = auth.uid())
        );
    END IF;
END $$;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Run these after migration to verify

-- Check subscription columns
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns 
    WHERE table_name = 'subscriptions' 
    AND column_name IN ('had_free_trial', 'trial_start', 'trial_end', 'cancel_at_period_end');
    
    IF col_count = 4 THEN
        RAISE NOTICE '✅ Subscription trial columns: All 4 exist';
    ELSE
        RAISE WARNING '⚠️ Subscription trial columns: Only % of 4 exist', col_count;
    END IF;
END $$;

-- Check tables
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'orders') THEN
        RAISE NOTICE '✅ orders table: EXISTS';
    ELSE
        RAISE WARNING '❌ orders table: MISSING';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'telegram_credentials') THEN
        RAISE NOTICE '✅ telegram_credentials table: EXISTS';
    ELSE
        RAISE WARNING '❌ telegram_credentials table: MISSING';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'telegram_channels') THEN
        RAISE NOTICE '✅ telegram_channels table: EXISTS';
    ELSE
        RAISE WARNING '❌ telegram_channels table: MISSING';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'amazon_connections') THEN
        RAISE NOTICE '✅ amazon_connections table: EXISTS';
    ELSE
        RAISE WARNING '❌ amazon_connections table: MISSING';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'amazon_credentials') THEN
        RAISE NOTICE '✅ amazon_credentials table: EXISTS (backward compatibility)';
    ELSE
        RAISE NOTICE 'ℹ️ amazon_credentials table: Not created (using amazon_connections)';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'product_sources') THEN
        RAISE NOTICE '✅ product_sources table: EXISTS';
    ELSE
        RAISE WARNING '❌ product_sources table: MISSING';
    END IF;
END $$;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- All migrations applied. Check NOTICE messages above for verification.

