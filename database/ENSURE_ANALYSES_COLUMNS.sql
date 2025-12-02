-- Ensure all required columns exist in analyses table
-- Run this to fix any missing columns

-- Product info columns (may be used by some code paths)
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS brand TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS image_url TEXT;

-- SP-API columns (from ADD_SP_API_COLUMNS.sql)
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS seller_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fba_seller_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS amazon_sells BOOLEAN DEFAULT FALSE;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS price_source TEXT DEFAULT 'unknown';

-- Fee columns (from ADD_FEES_COLUMNS_TO_ANALYSES.sql)
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_total DECIMAL(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_referral DECIMAL(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_fba DECIMAL(10,2);

-- Keepa columns (from CREATE_KEEPA_CACHE_AND_COLUMNS.sql)
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_30 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_90 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_180 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS variation_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS amazon_in_stock BOOLEAN;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS rating NUMERIC(3,1);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS review_count INTEGER;

-- Supplier ID (from FIX_ANALYSES_UNIQUE_KEY.sql)
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL;

-- Ensure unique constraint exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'analyses_user_supplier_asin_unique'
    ) THEN
        ALTER TABLE analyses ADD CONSTRAINT analyses_user_supplier_asin_unique 
        UNIQUE (user_id, supplier_id, asin);
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_analyses_fees_total ON analyses(fees_total);
CREATE INDEX IF NOT EXISTS idx_analyses_price_source ON analyses(price_source);
CREATE INDEX IF NOT EXISTS idx_analyses_user_supplier_asin ON analyses(user_id, supplier_id, asin);

