-- Keepa Analysis Table
-- Stores detailed Keepa analysis results for TOP PRODUCTS stage

CREATE TABLE IF NOT EXISTS public.keepa_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin TEXT NOT NULL UNIQUE,
    
    -- Raw API responses (for debugging/reference)
    raw_basic_response JSONB,
    raw_offers_response JSONB,
    
    -- Parsed metrics
    lowest_fba_price_12m DECIMAL(10,2),
    lowest_fba_date TIMESTAMPTZ,
    lowest_fba_seller TEXT,
    
    current_fba_price DECIMAL(10,2),
    current_fbm_price DECIMAL(10,2),
    fba_seller_count INTEGER DEFAULT 0,
    fbm_seller_count INTEGER DEFAULT 0,
    
    current_sales_rank INTEGER,
    avg_sales_rank_90d INTEGER,
    
    price_range_12m JSONB,  -- {min, max, range}
    price_volatility JSONB,  -- {coefficient, std_dev, mean}
    
    -- Worst-case profit analysis
    worst_case_profit DECIMAL(10,2),
    worst_case_margin DECIMAL(5,2),
    still_profitable BOOLEAN,
    
    -- Metadata
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_keepa_analysis_asin ON public.keepa_analysis(asin);
CREATE INDEX IF NOT EXISTS idx_keepa_analysis_analyzed ON public.keepa_analysis(analyzed_at DESC);

-- Add comment
COMMENT ON TABLE public.keepa_analysis IS 'Detailed Keepa analysis results for products in TOP PRODUCTS stage';

