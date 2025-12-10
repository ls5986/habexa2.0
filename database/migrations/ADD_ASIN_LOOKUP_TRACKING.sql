-- Add lookup tracking fields to products table
-- Run in Supabase SQL Editor

ALTER TABLE products ADD COLUMN IF NOT EXISTS lookup_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE products ADD COLUMN IF NOT EXISTS lookup_attempts INTEGER DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS asin_found_at TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN IF NOT EXISTS potential_asins JSONB;

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_products_lookup_status ON products(lookup_status);
CREATE INDEX IF NOT EXISTS idx_products_pending_lookup ON products(user_id, lookup_status) 
WHERE lookup_status IN ('pending', 'retry_pending', 'looking_up');

-- Add comments
COMMENT ON COLUMN products.lookup_status IS 'Status of ASIN lookup: pending, looking_up, found, retry_pending, failed, multiple_found, no_upc';
COMMENT ON COLUMN products.lookup_attempts IS 'Number of ASIN lookup attempts made';
COMMENT ON COLUMN products.asin_found_at IS 'Timestamp when ASIN was successfully found';
COMMENT ON COLUMN products.potential_asins IS 'Array of potential ASINs when multiple matches found (user must choose)';

