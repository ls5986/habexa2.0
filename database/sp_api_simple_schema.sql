-- Simplified SP-API Schema (Self-authorized - no OAuth)
-- Run this in Supabase SQL Editor

-- ============================================
-- ELIGIBILITY CACHE
-- ============================================

CREATE TABLE IF NOT EXISTS public.eligibility_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin TEXT NOT NULL,
    seller_id TEXT NOT NULL,
    
    status TEXT CHECK (status IN ('ELIGIBLE', 'NOT_ELIGIBLE', 'APPROVAL_REQUIRED', 'UNKNOWN')),
    reasons JSONB DEFAULT '[]'::JSONB,
    raw_response JSONB,
    
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    
    UNIQUE(asin, seller_id)
);

CREATE INDEX IF NOT EXISTS idx_eligibility_asin ON public.eligibility_cache(asin);
CREATE INDEX IF NOT EXISTS idx_eligibility_expires ON public.eligibility_cache(expires_at);

-- ============================================
-- FEE CACHE
-- ============================================

CREATE TABLE IF NOT EXISTS public.fee_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    
    referral_fee DECIMAL(10,2),
    fba_fulfillment_fee DECIMAL(10,2),
    variable_closing_fee DECIMAL(10,2),
    total_fees DECIMAL(10,2),
    
    raw_response JSONB,
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    
    UNIQUE(asin, price)
);

CREATE INDEX IF NOT EXISTS idx_fee_cache_asin ON public.fee_cache(asin, price);
CREATE INDEX IF NOT EXISTS idx_fee_cache_expires ON public.fee_cache(expires_at);

-- ============================================
-- CLEANUP FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION cleanup_sp_api_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.eligibility_cache WHERE expires_at < NOW();
    DELETE FROM public.fee_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

