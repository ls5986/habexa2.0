-- Amazon SP-API Integration Schema
-- Run this in Supabase SQL Editor

-- ============================================
-- AMAZON CREDENTIALS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS public.amazon_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    
    -- Seller identification
    seller_id TEXT NOT NULL,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    
    -- OAuth tokens (ENCRYPTED!)
    refresh_token_encrypted TEXT NOT NULL,
    access_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    
    -- Connection status
    is_connected BOOLEAN DEFAULT TRUE,
    connection_error TEXT,
    
    -- Sync tracking
    last_sync_at TIMESTAMPTZ,
    last_eligibility_check TIMESTAMPTZ,
    
    -- Metadata
    seller_name TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.amazon_credentials ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own amazon credentials" 
    ON public.amazon_credentials FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage amazon credentials" 
    ON public.amazon_credentials FOR ALL 
    USING (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_amazon_creds_user ON public.amazon_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_amazon_creds_seller ON public.amazon_credentials(seller_id);

-- ============================================
-- ELIGIBILITY CACHE TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS public.eligibility_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    asin TEXT NOT NULL,
    
    -- Eligibility result
    status TEXT CHECK (status IN ('ELIGIBLE', 'NOT_ELIGIBLE', 'APPROVAL_REQUIRED', 'UNKNOWN')),
    reasons JSONB DEFAULT '[]'::JSONB,
    
    -- Raw response for debugging
    raw_response JSONB,
    
    -- Cache management
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    
    UNIQUE(user_id, asin)
);

ALTER TABLE public.eligibility_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own eligibility cache" 
    ON public.eligibility_cache FOR SELECT 
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_eligibility_user_asin ON public.eligibility_cache(user_id, asin);
CREATE INDEX IF NOT EXISTS idx_eligibility_expires ON public.eligibility_cache(expires_at);

-- ============================================
-- FEE ESTIMATE CACHE TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS public.fee_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    
    UNIQUE(asin, price, marketplace_id)
);

CREATE INDEX IF NOT EXISTS idx_fee_cache_asin ON public.fee_cache(asin, price);
CREATE INDEX IF NOT EXISTS idx_fee_cache_expires ON public.fee_cache(expires_at);

-- ============================================
-- CLEANUP FUNCTION FOR EXPIRED CACHE
-- ============================================

CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.eligibility_cache WHERE expires_at < NOW();
    DELETE FROM public.fee_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_amazon_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_amazon_credentials_updated_at
    BEFORE UPDATE ON public.amazon_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_amazon_credentials_updated_at();

