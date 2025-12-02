-- Add UPC support to products and product_sources tables
-- UPC can be used to convert to ASIN when ASIN is not available

-- Add UPC column to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS upc TEXT;

-- Add UPC column to product_sources table (for tracking source UPC)
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS upc TEXT;

-- Create index for UPC lookups
CREATE INDEX IF NOT EXISTS idx_products_upc ON products(upc) WHERE upc IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_product_sources_upc ON product_sources(upc) WHERE upc IS NOT NULL;

-- Add comment
COMMENT ON COLUMN products.upc IS 'UPC/EAN/GTIN code - can be converted to ASIN via SP-API';
COMMENT ON COLUMN product_sources.upc IS 'Original UPC from source (CSV/Telegram) before ASIN conversion';

