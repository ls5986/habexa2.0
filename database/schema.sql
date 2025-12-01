-- Habexa Database Schema for Supabase
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (extends Supabase auth.users)
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Suppliers
CREATE TABLE public.suppliers (
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
CREATE TABLE public.messages (
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
CREATE TABLE public.deals (
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

-- Watchlist
CREATE TABLE public.watchlist (
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
CREATE TABLE public.orders (
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
CREATE TABLE public.user_settings (
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
CREATE TABLE public.notifications (
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

-- Amazon Credentials (encrypted)
CREATE TABLE public.amazon_credentials (
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

-- Telegram Credentials
CREATE TABLE public.telegram_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    telegram_user_id TEXT,
    session_string TEXT, -- Store encrypted
    is_connected BOOLEAN DEFAULT FALSE,
    connected_channels JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security Policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amazon_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_credentials ENABLE ROW LEVEL SECURITY;

-- Policies: Users can only access their own data
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own suppliers" ON public.suppliers FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own messages" ON public.messages FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own deals" ON public.deals FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own watchlist" ON public.watchlist FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own orders" ON public.orders FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own settings" ON public.user_settings FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own notifications" ON public.notifications FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own amazon creds" ON public.amazon_credentials FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own telegram creds" ON public.telegram_credentials FOR ALL USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX idx_deals_user_status ON public.deals(user_id, status);
CREATE INDEX idx_deals_asin ON public.deals(asin);
CREATE INDEX idx_deals_created ON public.deals(created_at DESC);
CREATE INDEX idx_suppliers_user ON public.suppliers(user_id);
CREATE INDEX idx_messages_user ON public.messages(user_id);
CREATE INDEX idx_notifications_user_read ON public.notifications(user_id, is_read);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON public.suppliers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deals_updated_at BEFORE UPDATE ON public.deals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON public.user_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_amazon_creds_updated_at BEFORE UPDATE ON public.amazon_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_telegram_creds_updated_at BEFORE UPDATE ON public.telegram_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

