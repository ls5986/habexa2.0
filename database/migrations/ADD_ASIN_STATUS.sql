-- Migration: Add asin_status column to products table
-- Date: 2025-12-04
-- Purpose: Track products where UPC→ASIN conversion failed, allowing manual ASIN entry later

-- Add asin_status column
ALTER TABLE products ADD COLUMN IF NOT EXISTS asin_status TEXT DEFAULT 'found';

-- Add comment explaining values
COMMENT ON COLUMN products.asin_status IS 'Status of ASIN lookup: found (ASIN found via UPC), not_found (UPC conversion failed), manual (user entered ASIN), pending (awaiting lookup)';

-- Add index for filtering products needing ASIN
CREATE INDEX IF NOT EXISTS idx_products_asin_status ON products(asin_status) WHERE asin_status != 'found';

-- Update existing products to have 'found' status if they have an ASIN
UPDATE products SET asin_status = 'found' WHERE asin IS NOT NULL AND asin_status IS NULL;

-- Update products without ASIN to 'not_found' if they have a UPC
UPDATE products SET asin_status = 'not_found' WHERE asin IS NULL AND upc IS NOT NULL AND asin_status IS NULL;

