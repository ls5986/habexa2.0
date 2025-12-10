-- Add sales/promotional columns to product_sources table
-- These columns store promotional information from CSV uploads

ALTER TABLE product_sources 
ADD COLUMN IF NOT EXISTS percent_off DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS promo_qty INTEGER;

-- Add comments
COMMENT ON COLUMN product_sources.percent_off IS 'Discount percentage (e.g., 15.00 for 15% off)';
COMMENT ON COLUMN product_sources.promo_qty IS 'Minimum quantity required for promotional pricing';

-- Add check constraint for percent_off (0-100)
ALTER TABLE product_sources
DROP CONSTRAINT IF EXISTS check_percent_off_range;

ALTER TABLE product_sources
ADD CONSTRAINT check_percent_off_range 
CHECK (percent_off IS NULL OR (percent_off >= 0 AND percent_off <= 100));

-- Add check constraint for promo_qty (must be positive)
ALTER TABLE product_sources
DROP CONSTRAINT IF EXISTS check_promo_qty_positive;

ALTER TABLE product_sources
ADD CONSTRAINT check_promo_qty_positive 
CHECK (promo_qty IS NULL OR promo_qty > 0);


