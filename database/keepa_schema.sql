-- Keepa Integration Schema
-- Run this in Supabase SQL Editor

-- ============================================
-- KEEPA PRODUCT CACHE
-- ============================================

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

CREATE INDEX IF NOT EXISTS idx_keepa_cache_asin ON public.keepa_cache(asin);
CREATE INDEX IF NOT EXISTS idx_keepa_cache_expires ON public.keepa_cache(expires_at);

-- ============================================
-- KEEPA USAGE TRACKING
-- ============================================

CREATE TABLE IF NOT EXISTS public.keepa_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE DEFAULT CURRENT_DATE,
    tokens_used INTEGER DEFAULT 0,
    requests_made INTEGER DEFAULT 0,
    
    UNIQUE(date)
);

-- Function to track Keepa usage
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

-- ============================================
-- CLEANUP EXPIRED CACHE
-- ============================================

CREATE OR REPLACE FUNCTION cleanup_keepa_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.keepa_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

