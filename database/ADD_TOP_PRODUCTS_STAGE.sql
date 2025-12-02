-- Add "top_products" stage to product_sources
-- This stage triggers Keepa analysis

-- Update any existing stage constraints if needed
-- (Most schemas use TEXT without CHECK constraints, so this may not be needed)

-- Add keepa_analyzed_at column to product_sources for tracking
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS keepa_analyzed_at TIMESTAMPTZ;

-- Create index for keepa_analyzed_at
CREATE INDEX IF NOT EXISTS idx_product_sources_keepa_analyzed 
ON product_sources(keepa_analyzed_at) 
WHERE keepa_analyzed_at IS NOT NULL;

-- Add comment
COMMENT ON COLUMN product_sources.keepa_analyzed_at IS 'Timestamp when Keepa analysis was completed for TOP PRODUCTS stage';

