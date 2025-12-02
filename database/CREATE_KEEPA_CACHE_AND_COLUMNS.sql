-- Keepa cache to reduce API calls
CREATE TABLE IF NOT EXISTS keepa_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin TEXT NOT NULL,
    marketplace_id TEXT NOT NULL DEFAULT 'ATVPDKIKX0DER',
    data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(asin, marketplace_id)
);

-- If table exists with old structure, add the data column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'keepa_cache' AND column_name = 'data'
    ) THEN
        -- Add data column if it doesn't exist
        ALTER TABLE keepa_cache ADD COLUMN data JSONB;
        
        -- If there are existing rows with old structure, we can't migrate them easily
        -- So we'll just add the column and let new data populate it
        -- Old cached data will be ignored (which is fine, it will be re-fetched)
    END IF;
END $$;

-- Index for cache lookups
CREATE INDEX IF NOT EXISTS idx_keepa_cache_asin ON keepa_cache(asin);
CREATE INDEX IF NOT EXISTS idx_keepa_cache_expires ON keepa_cache(expires_at);

-- Add new columns to analyses table for Keepa data
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_30 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_90 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_180 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS variation_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS amazon_in_stock BOOLEAN;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS rating NUMERIC(3,1);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS review_count INTEGER;

-- RLS policies for keepa_cache
ALTER TABLE keepa_cache ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can read keepa_cache" ON keepa_cache;
DROP POLICY IF EXISTS "Service role can manage keepa_cache" ON keepa_cache;

-- Policy: Users can read all cached data (it's public data)
CREATE POLICY "Users can read keepa_cache"
    ON keepa_cache FOR SELECT
    USING (true);

-- Policy: Service role can manage cache
CREATE POLICY "Service role can manage keepa_cache"
    ON keepa_cache FOR ALL
    USING (auth.role() = 'service_role');

