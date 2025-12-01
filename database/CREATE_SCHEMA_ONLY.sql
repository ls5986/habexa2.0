-- ============================================
-- HABEXA DATABASE SCHEMA - CREATE ONLY
-- ============================================
-- This script creates all tables, functions, triggers, and policies.
-- Run this AFTER manually deleting everything in Supabase.
-- ============================================

-- ============================================
-- PART 1: CREATE EXTENSIONS
-- ============================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- PART 2: CORE TABLES
-- ============================================

-- Users table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Suppliers
CREATE TABLE IF NOT EXISTS public.suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    telegram_username TEXT,
    telegram_channel_id TEXT,
    whatsapp_number TEXT,
    email TEXT,
    website TEXT,
    notes TEXT,
    rating DECIMAL(2,1) DEFAULT 0,
    avg_lead_time_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw Messages from Telegram/Email
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES public.suppliers(id),
    source TEXT NOT NULL CHECK (source IN ('telegram', 'email')),
    source_id TEXT,
    channel_name TEXT,
    raw_content TEXT NOT NULL,
    extracted_data JSONB,
    is_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, source_id)
);

-- Product Analyses (Deals)
CREATE TABLE IF NOT EXISTS public.deals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    message_id UUID REFERENCES public.messages(id),
    supplier_id UUID REFERENCES public.suppliers(id),
    
    -- Product Info
    asin TEXT NOT NULL,
    title TEXT,
    brand TEXT,
    category TEXT,
    image_url TEXT,
    
    -- Pricing
    buy_cost DECIMAL(10,2) NOT NULL,
    sell_price DECIMAL(10,2),
    lowest_fba_price DECIMAL(10,2),
    lowest_fbm_price DECIMAL(10,2),
    
    -- Fees
    fba_fee DECIMAL(10,2),
    referral_fee DECIMAL(10,2),
    prep_cost DECIMAL(10,2) DEFAULT 0.50,
    inbound_shipping DECIMAL(10,2) DEFAULT 0.50,
    
    -- Profitability
    net_profit DECIMAL(10,2),
    roi DECIMAL(5,2),
    profit_margin DECIMAL(5,2),
    
    -- Competition
    num_fba_sellers INTEGER,
    num_fbm_sellers INTEGER,
    amazon_is_seller BOOLEAN DEFAULT FALSE,
    buy_box_winner TEXT,
    
    -- Sales Data
    sales_rank INTEGER,
    sales_rank_category TEXT,
    estimated_monthly_sales INTEGER,
    
    -- Historical
    avg_price_90d DECIMAL(10,2),
    avg_rank_90d INTEGER,
    price_trend TEXT CHECK (price_trend IN ('up', 'down', 'stable')),
    
    -- Eligibility
    gating_status TEXT CHECK (gating_status IN ('ungated', 'gated', 'amazon_restricted', 'unknown')),
    
    -- Deal Assessment
    moq INTEGER DEFAULT 1,
    deal_score CHAR(1) CHECK (deal_score IN ('A', 'B', 'C', 'D', 'F')),
    is_profitable BOOLEAN,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'analyzed', 'saved', 'ordered', 'dismissed')),
    notes TEXT,
    
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analyses table (for storing detailed analysis results)
CREATE TABLE IF NOT EXISTS public.analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    deal_id UUID REFERENCES public.deals(id) ON DELETE SET NULL,
    asin TEXT NOT NULL,
    
    -- Analysis data
    analysis_data JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Watchlist
CREATE TABLE IF NOT EXISTS public.watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    asin TEXT NOT NULL,
    target_price DECIMAL(10,2),
    notes TEXT,
    notify_on_price_drop BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, asin)
);

-- Orders
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES public.suppliers(id),
    deal_id UUID REFERENCES public.deals(id),
    
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

-- User Settings
CREATE TABLE IF NOT EXISTS public.user_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    
    -- Profit thresholds
    min_roi DECIMAL(5,2) DEFAULT 20.00,
    min_profit DECIMAL(10,2) DEFAULT 3.00,
    max_rank INTEGER DEFAULT 100000,
    
    -- Costs
    default_prep_cost DECIMAL(10,2) DEFAULT 0.50,
    default_inbound_shipping DECIMAL(10,2) DEFAULT 0.50,
    
    -- Alerts
    alerts_enabled BOOLEAN DEFAULT TRUE,
    alert_min_roi DECIMAL(5,2) DEFAULT 30.00,
    alert_channels JSONB DEFAULT '["push", "email"]',
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    
    -- Preferences
    preferred_categories TEXT[] DEFAULT '{}',
    excluded_categories TEXT[] DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    deal_id UUID REFERENCES public.deals(id),
    
    type TEXT NOT NULL CHECK (type IN ('profitable_deal', 'price_drop', 'restock', 'system')),
    title TEXT NOT NULL,
    message TEXT,
    data JSONB,
    
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);

-- ============================================
-- PART 3: STRIPE TABLES
-- ============================================

-- Subscriptions table
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Stripe IDs
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    stripe_price_id TEXT,
    
    -- Subscription details
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'pro', 'agency')),
    billing_interval TEXT CHECK (billing_interval IN ('month', 'year')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    
    -- Dates
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    
    -- Usage tracking
    analyses_used_this_period INTEGER DEFAULT 0,
    last_usage_reset TIMESTAMPTZ DEFAULT NOW(),
    telegram_channels_count INTEGER DEFAULT 0,
    suppliers_count INTEGER DEFAULT 0,
    team_members_count INTEGER DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Payment history
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    subscription_id UUID REFERENCES public.subscriptions(id),
    
    -- Stripe data
    stripe_payment_intent_id TEXT,
    stripe_invoice_id TEXT,
    
    -- Payment details
    amount INTEGER NOT NULL,  -- in cents
    currency TEXT DEFAULT 'usd',
    status TEXT CHECK (status IN ('succeeded', 'failed', 'pending', 'refunded')),
    
    -- Metadata
    description TEXT,
    receipt_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices (for display)
CREATE TABLE IF NOT EXISTS public.invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    stripe_invoice_id TEXT UNIQUE,
    stripe_invoice_url TEXT,
    stripe_pdf_url TEXT,
    
    amount_due INTEGER,
    amount_paid INTEGER,
    currency TEXT DEFAULT 'usd',
    status TEXT,
    
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking (for metered features)
CREATE TABLE IF NOT EXISTS public.usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    feature TEXT NOT NULL,  -- 'analysis', 'channel_add', etc.
    quantity INTEGER DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- PART 4: AMAZON SP-API TABLES
-- ============================================

-- Amazon Credentials (legacy - for global credentials)
CREATE TABLE IF NOT EXISTS public.amazon_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    seller_id TEXT,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    refresh_token TEXT, -- Store encrypted
    is_connected BOOLEAN DEFAULT FALSE,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Amazon Connections (per-user OAuth)
CREATE TABLE IF NOT EXISTS public.amazon_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Seller info
    seller_id TEXT,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    
    -- OAuth tokens (encrypted!)
    refresh_token_encrypted TEXT,
    
    -- Connection status
    is_connected BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    
    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, marketplace_id)
);

-- Eligibility Cache
CREATE TABLE IF NOT EXISTS public.eligibility_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    asin TEXT NOT NULL,
    seller_id TEXT,
    
    -- Eligibility result
    status TEXT CHECK (status IN ('ELIGIBLE', 'NOT_ELIGIBLE', 'APPROVAL_REQUIRED', 'UNKNOWN', 'NOT_CONNECTED')),
    reasons JSONB DEFAULT '[]'::JSONB,
    
    -- Raw response for debugging
    raw_response JSONB,
    
    -- Cache management
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    
    UNIQUE(user_id, asin, seller_id)
);

-- Fee Estimate Cache
CREATE TABLE IF NOT EXISTS public.fee_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    asin TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    
    -- Fee breakdown
    referral_fee DECIMAL(10,2),
    fba_fulfillment_fee DECIMAL(10,2),
    variable_closing_fee DECIMAL(10,2),
    total_fees DECIMAL(10,2),
    
    -- Raw response
    raw_response JSONB,
    
    -- Cache management  
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    
    UNIQUE(user_id, asin, price)
);

-- ============================================
-- PART 5: TELEGRAM TABLES
-- ============================================

-- Telegram Sessions
CREATE TABLE IF NOT EXISTS public.telegram_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    
    -- Telethon session string (encrypted)
    session_string_encrypted TEXT,
    
    -- Connection status
    phone_number TEXT,
    is_connected BOOLEAN DEFAULT FALSE,
    is_authorized BOOLEAN DEFAULT FALSE,
    
    -- Monitoring status
    is_monitoring BOOLEAN DEFAULT FALSE,
    monitoring_started_at TIMESTAMPTZ,
    
    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Telegram Credentials (legacy)
CREATE TABLE IF NOT EXISTS public.telegram_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    telegram_user_id TEXT,
    session_string TEXT, -- Store encrypted
    is_connected BOOLEAN DEFAULT FALSE,
    connected_channels JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Monitored Channels (legacy - for feature gating)
CREATE TABLE IF NOT EXISTS public.monitored_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    channel_type TEXT DEFAULT 'telegram',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, channel_id)
);

-- Telegram Channels
CREATE TABLE IF NOT EXISTS public.telegram_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Channel info
    channel_id BIGINT NOT NULL,
    channel_name TEXT,
    channel_username TEXT,
    channel_type TEXT DEFAULT 'channel', -- 'channel', 'group', 'supergroup'
    
    -- Monitoring settings
    is_active BOOLEAN DEFAULT TRUE,
    auto_analyze BOOLEAN DEFAULT TRUE,
    
    -- Stats
    messages_received INTEGER DEFAULT 0,
    deals_extracted INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, channel_id)
);

-- Telegram Messages
CREATE TABLE IF NOT EXISTS public.telegram_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    channel_id UUID REFERENCES public.telegram_channels(id) ON DELETE CASCADE,
    
    -- Message details
    telegram_message_id BIGINT NOT NULL,
    telegram_channel_id BIGINT NOT NULL,
    
    -- Content
    content TEXT,
    has_media BOOLEAN DEFAULT FALSE,
    media_type TEXT,
    
    -- Sender info
    sender_id BIGINT,
    sender_name TEXT,
    
    -- Extraction results
    is_processed BOOLEAN DEFAULT FALSE,
    extracted_products JSONB DEFAULT '[]'::JSONB,
    extraction_error TEXT,
    
    -- Timestamps
    telegram_date TIMESTAMPTZ,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Telegram Deals (extracted from messages)
CREATE TABLE IF NOT EXISTS public.telegram_deals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    message_id UUID REFERENCES public.telegram_messages(id) ON DELETE SET NULL,
    channel_id UUID REFERENCES public.telegram_channels(id) ON DELETE SET NULL,
    
    -- Product info
    asin TEXT NOT NULL,
    buy_cost DECIMAL(10,2),
    moq INTEGER DEFAULT 1,
    
    -- Extracted details
    product_title TEXT,
    notes TEXT,
    
    -- Analysis link
    analysis_id UUID REFERENCES public.analyses(id) ON DELETE SET NULL,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'analyzing', 'analyzed', 'error', 'skipped')),
    
    -- Timestamps
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    analyzed_at TIMESTAMPTZ
);

-- ============================================
-- PART 6: KEEPA TABLES
-- ============================================

-- Keepa Product Cache
CREATE TABLE IF NOT EXISTS public.keepa_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin TEXT NOT NULL,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    
    -- Current prices (in cents, divide by 100)
    amazon_price INTEGER,
    new_price INTEGER,
    new_fba_price INTEGER,
    buy_box_price INTEGER,
    used_price INTEGER,
    
    -- Sales rank
    sales_rank INTEGER,
    sales_rank_category TEXT,
    
    -- Averages (30 day)
    avg_amazon_30 INTEGER,
    avg_new_30 INTEGER,
    avg_buy_box_30 INTEGER,
    avg_rank_30 INTEGER,
    
    -- Averages (90 day)
    avg_amazon_90 INTEGER,
    avg_new_90 INTEGER,
    avg_buy_box_90 INTEGER,
    avg_rank_90 INTEGER,
    
    -- Sales estimates (rank drops)
    drops_30 INTEGER,
    drops_90 INTEGER,
    drops_180 INTEGER,
    
    -- Product info from Keepa
    title TEXT,
    brand TEXT,
    product_group TEXT,
    category_tree JSONB,
    image_url TEXT,
    
    -- Stats
    offer_count_new INTEGER,
    offer_count_fba INTEGER,
    rating DECIMAL(3,2),
    review_count INTEGER,
    
    -- Out of stock tracking
    oos_percentage_30 INTEGER,
    oos_percentage_90 INTEGER,
    
    -- Raw history data (for charts)
    price_history JSONB,
    rank_history JSONB,
    
    -- Full raw response
    raw_response JSONB,
    
    -- Cache management
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    
    UNIQUE(asin, marketplace_id)
);

-- Keepa Usage Tracking
CREATE TABLE IF NOT EXISTS public.keepa_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE DEFAULT CURRENT_DATE,
    tokens_used INTEGER DEFAULT 0,
    requests_made INTEGER DEFAULT 0,
    
    UNIQUE(date)
);

-- ============================================
-- PART 7: INDEXES
-- ============================================

-- Core indexes
CREATE INDEX idx_deals_user_status ON public.deals(user_id, status);
CREATE INDEX idx_deals_asin ON public.deals(asin);
CREATE INDEX idx_deals_created ON public.deals(created_at DESC);
CREATE INDEX idx_suppliers_user ON public.suppliers(user_id);
CREATE INDEX idx_messages_user ON public.messages(user_id);
CREATE INDEX idx_notifications_user_read ON public.notifications(user_id, is_read);
CREATE INDEX idx_analyses_user ON public.analyses(user_id);
CREATE INDEX idx_analyses_asin ON public.analyses(asin);

-- Stripe indexes
CREATE INDEX idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer ON public.subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_stripe_sub ON public.subscriptions(stripe_subscription_id);
CREATE INDEX idx_payments_user ON public.payments(user_id);
CREATE INDEX idx_usage_user_created ON public.usage_records(user_id, created_at);

-- SP-API indexes
CREATE INDEX idx_amazon_creds_user ON public.amazon_credentials(user_id);
CREATE INDEX idx_amazon_creds_seller ON public.amazon_credentials(seller_id);
CREATE INDEX idx_amazon_connections_user ON public.amazon_connections(user_id);
CREATE INDEX idx_eligibility_user_asin ON public.eligibility_cache(user_id, asin);
CREATE INDEX idx_eligibility_expires ON public.eligibility_cache(expires_at);
CREATE INDEX idx_fee_cache_asin ON public.fee_cache(asin, price);
CREATE INDEX idx_fee_cache_expires ON public.fee_cache(expires_at);

-- Telegram indexes
CREATE INDEX idx_telegram_channels_user ON public.telegram_channels(user_id);
CREATE INDEX idx_telegram_channels_active ON public.telegram_channels(user_id, is_active);
CREATE INDEX idx_telegram_messages_user ON public.telegram_messages(user_id);
CREATE INDEX idx_telegram_messages_channel ON public.telegram_messages(channel_id);
CREATE INDEX idx_telegram_messages_unprocessed ON public.telegram_messages(user_id, is_processed) WHERE is_processed = FALSE;
CREATE INDEX idx_telegram_deals_user ON public.telegram_deals(user_id);
CREATE INDEX idx_telegram_deals_asin ON public.telegram_deals(asin);
CREATE INDEX idx_telegram_deals_pending ON public.telegram_deals(user_id, status) WHERE status = 'pending';
CREATE INDEX idx_monitored_channels_user ON public.monitored_channels(user_id);

-- Keepa indexes
CREATE INDEX idx_keepa_cache_asin ON public.keepa_cache(asin);
CREATE INDEX idx_keepa_cache_expires ON public.keepa_cache(expires_at);

-- ============================================
-- PART 8: FUNCTIONS
-- ============================================

-- Update updated_at timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Get tier limits function
CREATE OR REPLACE FUNCTION get_tier_limits(p_tier TEXT)
RETURNS JSONB AS $$
BEGIN
    RETURN CASE p_tier
        WHEN 'free' THEN '{
            "telegram_channels": 1,
            "analyses_per_month": 10,
            "suppliers": 3,
            "alerts": false,
            "bulk_analyze": false,
            "api_access": false,
            "team_seats": 1,
            "export_data": false,
            "priority_support": false
        }'::JSONB
        WHEN 'starter' THEN '{
            "telegram_channels": 3,
            "analyses_per_month": 100,
            "suppliers": 10,
            "alerts": true,
            "bulk_analyze": false,
            "api_access": false,
            "team_seats": 1,
            "export_data": true,
            "priority_support": false
        }'::JSONB
        WHEN 'pro' THEN '{
            "telegram_channels": 10,
            "analyses_per_month": 500,
            "suppliers": 50,
            "alerts": true,
            "bulk_analyze": true,
            "api_access": false,
            "team_seats": 3,
            "export_data": true,
            "priority_support": true
        }'::JSONB
        WHEN 'agency' THEN '{
            "telegram_channels": -1,
            "analyses_per_month": -1,
            "suppliers": -1,
            "alerts": true,
            "bulk_analyze": true,
            "api_access": true,
            "team_seats": 10,
            "export_data": true,
            "priority_support": true
        }'::JSONB
        ELSE '{
            "telegram_channels": 1,
            "analyses_per_month": 10,
            "suppliers": 3,
            "alerts": false,
            "bulk_analyze": false,
            "api_access": false,
            "team_seats": 1,
            "export_data": false,
            "priority_support": false
        }'::JSONB
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Check user limit function
CREATE OR REPLACE FUNCTION check_user_limit(
    p_user_id UUID,
    p_feature TEXT
) RETURNS JSONB AS $$
DECLARE
    v_tier TEXT;
    v_limits JSONB;
    v_limit INTEGER;
    v_current_usage INTEGER;
    v_can_proceed BOOLEAN;
BEGIN
    -- Get user's tier
    SELECT COALESCE(tier, 'free') INTO v_tier 
    FROM public.subscriptions 
    WHERE user_id = p_user_id;
    
    IF v_tier IS NULL THEN 
        v_tier := 'free'; 
    END IF;
    
    -- Get limits for tier
    v_limits := get_tier_limits(v_tier);
    
    -- Handle boolean features
    IF p_feature IN ('alerts', 'bulk_analyze', 'api_access', 'export_data', 'priority_support') THEN
        RETURN jsonb_build_object(
            'allowed', (v_limits->>p_feature)::BOOLEAN,
            'tier', v_tier,
            'feature', p_feature,
            'upgrade_required', NOT (v_limits->>p_feature)::BOOLEAN
        );
    END IF;
    
    -- Get numeric limit
    v_limit := (v_limits->>p_feature)::INTEGER;
    
    -- Unlimited check (-1)
    IF v_limit = -1 THEN
        RETURN jsonb_build_object(
            'allowed', true,
            'tier', v_tier,
            'feature', p_feature,
            'limit', -1,
            'used', 0,
            'remaining', -1,
            'unlimited', true
        );
    END IF;
    
    -- Get current usage based on feature
    CASE p_feature
        WHEN 'analyses_per_month' THEN
            SELECT COALESCE(analyses_used_this_period, 0) INTO v_current_usage
            FROM public.subscriptions WHERE user_id = p_user_id;
        WHEN 'telegram_channels' THEN
            SELECT COALESCE(telegram_channels_count, 0) INTO v_current_usage
            FROM public.subscriptions WHERE user_id = p_user_id;
        WHEN 'suppliers' THEN
            SELECT COUNT(*) INTO v_current_usage
            FROM public.suppliers WHERE user_id = p_user_id;
        WHEN 'team_seats' THEN
            SELECT COALESCE(team_members_count, 1) INTO v_current_usage
            FROM public.subscriptions WHERE user_id = p_user_id;
        ELSE
            v_current_usage := 0;
    END CASE;
    
    v_current_usage := COALESCE(v_current_usage, 0);
    v_can_proceed := v_current_usage < v_limit;
    
    RETURN jsonb_build_object(
        'allowed', v_can_proceed,
        'tier', v_tier,
        'feature', p_feature,
        'limit', v_limit,
        'used', v_current_usage,
        'remaining', GREATEST(0, v_limit - v_current_usage),
        'unlimited', false,
        'upgrade_required', NOT v_can_proceed
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Increment usage function
CREATE OR REPLACE FUNCTION increment_usage(
    p_user_id UUID,
    p_feature TEXT,
    p_amount INTEGER DEFAULT 1
) RETURNS JSONB AS $$
DECLARE
    v_check JSONB;
BEGIN
    -- First check if allowed
    v_check := check_user_limit(p_user_id, p_feature);
    
    IF NOT (v_check->>'allowed')::BOOLEAN THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Limit reached',
            'check', v_check
        );
    END IF;
    
    -- Increment based on feature
    CASE p_feature
        WHEN 'analyses_per_month' THEN
            UPDATE public.subscriptions
            SET analyses_used_this_period = COALESCE(analyses_used_this_period, 0) + p_amount,
                updated_at = NOW()
            WHERE user_id = p_user_id;
        WHEN 'telegram_channels' THEN
            UPDATE public.subscriptions
            SET telegram_channels_count = COALESCE(telegram_channels_count, 0) + p_amount,
                updated_at = NOW()
            WHERE user_id = p_user_id;
        WHEN 'team_seats' THEN
            UPDATE public.subscriptions
            SET team_members_count = COALESCE(team_members_count, 1) + p_amount,
                updated_at = NOW()
            WHERE user_id = p_user_id;
    END CASE;
    
    -- Log usage
    INSERT INTO public.usage_records (user_id, feature, quantity)
    VALUES (p_user_id, p_feature, p_amount);
    
    RETURN jsonb_build_object(
        'success', true,
        'feature', p_feature,
        'incremented_by', p_amount
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Decrement usage function
CREATE OR REPLACE FUNCTION decrement_usage(
    p_user_id UUID,
    p_feature TEXT,
    p_amount INTEGER DEFAULT 1
) RETURNS VOID AS $$
BEGIN
    CASE p_feature
        WHEN 'telegram_channels' THEN
            UPDATE public.subscriptions
            SET telegram_channels_count = GREATEST(0, COALESCE(telegram_channels_count, 0) - p_amount),
                updated_at = NOW()
            WHERE user_id = p_user_id;
        WHEN 'team_seats' THEN
            UPDATE public.subscriptions
            SET team_members_count = GREATEST(1, COALESCE(team_members_count, 1) - p_amount),
                updated_at = NOW()
            WHERE user_id = p_user_id;
    END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Increment analyses function
CREATE OR REPLACE FUNCTION increment_analyses(
    p_user_id UUID,
    p_amount INTEGER DEFAULT 1
) RETURNS VOID AS $$
BEGIN
    UPDATE public.subscriptions
    SET analyses_used_this_period = COALESCE(analyses_used_this_period, 0) + p_amount,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- If no subscription exists, create a free one
    IF NOT FOUND THEN
        INSERT INTO public.subscriptions (user_id, tier, status, analyses_used_this_period)
        VALUES (p_user_id, 'free', 'active', p_amount)
        ON CONFLICT (user_id) DO UPDATE
        SET analyses_used_this_period = COALESCE(public.subscriptions.analyses_used_this_period, 0) + p_amount,
            updated_at = NOW();
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Cleanup expired cache function
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.eligibility_cache WHERE expires_at < NOW();
    DELETE FROM public.fee_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update Amazon credentials timestamp function
CREATE OR REPLACE FUNCTION update_amazon_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update channel stats function
CREATE OR REPLACE FUNCTION update_channel_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.telegram_channels
    SET 
        messages_received = messages_received + 1,
        last_message_at = NEW.telegram_date
    WHERE id = NEW.channel_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Increment deals extracted function
CREATE OR REPLACE FUNCTION increment_deals_extracted()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.telegram_channels
    SET deals_extracted = deals_extracted + 1
    WHERE id = NEW.channel_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update Telegram session timestamp function
CREATE OR REPLACE FUNCTION update_telegram_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Cleanup Keepa cache function
CREATE OR REPLACE FUNCTION cleanup_keepa_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.keepa_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Track Keepa usage function
CREATE OR REPLACE FUNCTION track_keepa_usage(p_tokens INTEGER)
RETURNS void AS $$
BEGIN
    INSERT INTO public.keepa_usage (date, tokens_used, requests_made)
    VALUES (CURRENT_DATE, p_tokens, 1)
    ON CONFLICT (date) DO UPDATE
    SET tokens_used = keepa_usage.tokens_used + p_tokens,
        requests_made = keepa_usage.requests_made + 1;
END;
$$ LANGUAGE plpgsql;

-- Update Amazon connections timestamp function
CREATE OR REPLACE FUNCTION update_amazon_connections_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- PART 9: TRIGGERS
-- ============================================

-- Updated_at triggers
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON public.suppliers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deals_updated_at BEFORE UPDATE ON public.deals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_analyses_updated_at BEFORE UPDATE ON public.analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON public.user_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_amazon_creds_updated_at BEFORE UPDATE ON public.amazon_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_telegram_creds_updated_at BEFORE UPDATE ON public.telegram_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_amazon_credentials_updated_at BEFORE UPDATE ON public.amazon_credentials FOR EACH ROW EXECUTE FUNCTION update_amazon_credentials_updated_at();
CREATE TRIGGER trigger_telegram_session_updated BEFORE UPDATE ON public.telegram_sessions FOR EACH ROW EXECUTE FUNCTION update_telegram_session_timestamp();
CREATE TRIGGER trigger_update_channel_stats AFTER INSERT ON public.telegram_messages FOR EACH ROW EXECUTE FUNCTION update_channel_stats();
CREATE TRIGGER trigger_increment_deals AFTER INSERT ON public.telegram_deals FOR EACH ROW EXECUTE FUNCTION increment_deals_extracted();
CREATE TRIGGER update_amazon_connections_updated_at BEFORE UPDATE ON public.amazon_connections FOR EACH ROW EXECUTE FUNCTION update_amazon_connections_updated_at();

-- ============================================
-- PART 10: ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amazon_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amazon_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.eligibility_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fee_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monitored_channels ENABLE ROW LEVEL SECURITY;

-- Core policies
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own suppliers" ON public.suppliers FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own messages" ON public.messages FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own deals" ON public.deals FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own analyses" ON public.analyses FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own watchlist" ON public.watchlist FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own orders" ON public.orders FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own settings" ON public.user_settings FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own notifications" ON public.notifications FOR ALL USING (auth.uid() = user_id);

-- Stripe policies
CREATE POLICY "Users can view own subscription" ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own payments" ON public.payments FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own invoices" ON public.invoices FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own usage" ON public.usage_records FOR SELECT USING (auth.uid() = user_id);

-- SP-API policies
CREATE POLICY "Users can view own amazon credentials" ON public.amazon_credentials FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage amazon credentials" ON public.amazon_credentials FOR ALL USING (true);
CREATE POLICY "Users can view own amazon connection" ON public.amazon_connections FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own amazon connection" ON public.amazon_connections FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Service can manage amazon connections" ON public.amazon_connections FOR ALL USING (true);
CREATE POLICY "Users can view own eligibility cache" ON public.eligibility_cache FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own fee cache" ON public.fee_cache FOR SELECT USING (auth.uid() = user_id);

-- Telegram policies
CREATE POLICY "Users can view own telegram session" ON public.telegram_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage telegram sessions" ON public.telegram_sessions FOR ALL USING (true);
CREATE POLICY "Users can view own telegram creds" ON public.telegram_credentials FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own channels" ON public.telegram_channels FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own messages" ON public.telegram_messages FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own telegram deals" ON public.telegram_deals FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own channels" ON public.monitored_channels FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- DONE!
-- ============================================

-- All tables, functions, triggers, and policies have been created.
-- Your database is ready to use!

