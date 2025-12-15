-- Add pack_size and wholesale_cost columns to product_sources table
-- These columns are needed for case/pack pricing

ALTER TABLE product_sources 
ADD COLUMN IF NOT EXISTS pack_size INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS wholesale_cost DECIMAL(10,2);

-- Add comments
COMMENT ON COLUMN product_sources.pack_size IS 'Number of units per case/pack (e.g., 12 for a case of 12)';
COMMENT ON COLUMN product_sources.wholesale_cost IS 'Total cost for the entire case/pack (used when pack_size > 1)';

-- Add check constraint for pack_size (must be positive)
ALTER TABLE product_sources
DROP CONSTRAINT IF EXISTS check_pack_size_positive;

ALTER TABLE product_sources
ADD CONSTRAINT check_pack_size_positive 
CHECK (pack_size IS NULL OR pack_size > 0);


