-- Add columns for uploaded data
ALTER TABLE products
ADD COLUMN IF NOT EXISTS uploaded_title TEXT,
ADD COLUMN IF NOT EXISTS uploaded_brand TEXT,
ADD COLUMN IF NOT EXISTS uploaded_category TEXT,
ADD COLUMN IF NOT EXISTS upload_source VARCHAR(50),
ADD COLUMN IF NOT EXISTS source_filename TEXT,
ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS original_upload_data JSONB,
ADD COLUMN IF NOT EXISTS asin_status VARCHAR(50) DEFAULT 'pending';

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_products_asin_status ON products(user_id, asin_status);
CREATE INDEX IF NOT EXISTS idx_products_upload_source ON products(user_id, upload_source);
CREATE INDEX IF NOT EXISTS idx_products_uploaded_at ON products(uploaded_at DESC);

-- Update existing products
UPDATE products
SET 
  upload_source = COALESCE(upload_source, 'manual'),
  uploaded_at = COALESCE(uploaded_at, created_at),
  asin_status = CASE
    WHEN asin IS NOT NULL AND asin != '' THEN 'found'
    WHEN upc IS NOT NULL AND upc != '' THEN 'pending_lookup'
    ELSE 'needs_input'
  END
WHERE upload_source IS NULL OR uploaded_at IS NULL OR asin_status IS NULL;

