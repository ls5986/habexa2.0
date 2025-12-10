-- Ensure lookup_status, lookup_attempts, and asin_found_at columns exist
-- These are critical for the ASIN lookup system

-- Add lookup_status if missing
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS lookup_status VARCHAR(50);

-- Add lookup_attempts if missing
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS lookup_attempts INTEGER DEFAULT 0;

-- Add asin_found_at if missing
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS asin_found_at TIMESTAMP WITH TIME ZONE;

-- Set default lookup_status for products with PENDING_ ASINs
UPDATE products 
SET lookup_status = 'pending'
WHERE (asin LIKE 'PENDING_%' OR asin LIKE 'Unknown%')
  AND upc IS NOT NULL 
  AND upc != ''
  AND (lookup_status IS NULL OR lookup_status = '');

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_products_lookup_status 
ON products(lookup_status) 
WHERE lookup_status IN ('pending', 'retry_pending');

CREATE INDEX IF NOT EXISTS idx_products_pending_asin 
ON products(asin) 
WHERE asin LIKE 'PENDING_%';

