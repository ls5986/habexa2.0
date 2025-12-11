-- ============================================================================
-- HABEXA ANALYZER DASHBOARD - PROFITABILITY METRICS
-- ============================================================================
-- Adds columns for profitability calculations and analyzer dashboard
-- Run this migration before implementing the analyzer dashboard

-- ============================================================================
-- PRODUCTS TABLE: Profitability Metrics
-- ============================================================================

-- Core profitability calculations
ALTER TABLE products ADD COLUMN IF NOT EXISTS profit_amount NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS roi_percentage NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS margin_percentage NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS break_even_price NUMERIC(10,2);

-- Classification flags
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_profitable BOOLEAN DEFAULT false;
ALTER TABLE products ADD COLUMN IF NOT EXISTS profit_tier TEXT CHECK (profit_tier IN ('excellent', 'good', 'marginal', 'unprofitable'));
ALTER TABLE products ADD COLUMN IF NOT EXISTS risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high'));

-- Sales estimates (calculated from BSR)
ALTER TABLE products ADD COLUMN IF NOT EXISTS est_monthly_sales INTEGER;

-- 90-day averages (calculated from Keepa data)
ALTER TABLE products ADD COLUMN IF NOT EXISTS avg_buybox_90d NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS avg_sales_rank_90d INTEGER;

-- 30-day averages
ALTER TABLE products ADD COLUMN IF NOT EXISTS avg_sales_rank_30d INTEGER;

-- Lowest price over 90 days (from Keepa)
ALTER TABLE products ADD COLUMN IF NOT EXISTS lowest_price_90d NUMERIC(10,2);

-- Comments for documentation
COMMENT ON COLUMN products.profit_amount IS 'Calculated profit per unit: sell_price - (buy_cost + fees + prep + shipping)';
COMMENT ON COLUMN products.roi_percentage IS 'Return on Investment: (profit / total_cost) * 100';
COMMENT ON COLUMN products.margin_percentage IS 'Profit margin: (profit / sell_price) * 100';
COMMENT ON COLUMN products.break_even_price IS 'Minimum sell price to break even (total costs)';
COMMENT ON COLUMN products.is_profitable IS 'True if ROI >= 15% and profit > 0';
COMMENT ON COLUMN products.profit_tier IS 'Classification: excellent (50%+ ROI), good (30-50%), marginal (15-30%), unprofitable (<15%)';
COMMENT ON COLUMN products.risk_level IS 'Risk assessment: low (high margin + low competition), medium, high (low margin + high competition)';
COMMENT ON COLUMN products.est_monthly_sales IS 'Estimated monthly sales based on BSR and category';
COMMENT ON COLUMN products.avg_buybox_90d IS 'Average buy box price over last 90 days (from Keepa)';
COMMENT ON COLUMN products.avg_sales_rank_90d IS 'Average sales rank over last 90 days';
COMMENT ON COLUMN products.avg_sales_rank_30d IS 'Average sales rank over last 30 days';
COMMENT ON COLUMN products.lowest_price_90d IS 'Lowest price seen in last 90 days';

-- ============================================================================
-- PRODUCT_SOURCES TABLE: Per-Supplier Profitability
-- ============================================================================
-- Note: These columns may already exist from previous migrations, but ensure they're there

ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS profit NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS roi NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS margin NUMERIC(10,2);

COMMENT ON COLUMN product_sources.profit IS 'Profit per unit for this supplier deal';
COMMENT ON COLUMN product_sources.roi IS 'ROI percentage for this supplier deal';
COMMENT ON COLUMN product_sources.margin IS 'Margin percentage for this supplier deal';

-- ============================================================================
-- INDEXES FOR ANALYZER QUERIES
-- ============================================================================
-- These indexes optimize the analyzer dashboard queries

CREATE INDEX IF NOT EXISTS idx_products_roi ON products(roi_percentage DESC) WHERE roi_percentage IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_profit_tier ON products(profit_tier) WHERE profit_tier IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_is_profitable ON products(is_profitable) WHERE is_profitable = true;
CREATE INDEX IF NOT EXISTS idx_products_risk_level ON products(risk_level) WHERE risk_level IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_bsr ON products(bsr) WHERE bsr IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_seller_count ON products(seller_count) WHERE seller_count IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category) WHERE category IS NOT NULL;

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_products_analyzer_filter ON products(user_id, is_profitable, profit_tier, category) 
WHERE is_profitable IS NOT NULL;

-- ============================================================================
-- VERIFY COLUMNS WERE ADDED
-- ============================================================================

SELECT 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name IN (
    'profit_amount', 'roi_percentage', 'margin_percentage', 'break_even_price',
    'is_profitable', 'profit_tier', 'risk_level', 'est_monthly_sales',
    'avg_buybox_90d', 'avg_sales_rank_90d', 'avg_sales_rank_30d', 'lowest_price_90d'
)
ORDER BY column_name;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. These columns will be populated by the profitability_calculator service
-- 2. Calculations run automatically after API data fetch during file upload
-- 3. Can be manually triggered via POST /analyzer/bulk-analyze
-- 4. Profit tier thresholds:
--    - excellent: ROI >= 50%
--    - good: ROI >= 30% and < 50%
--    - marginal: ROI >= 15% and < 30%
--    - unprofitable: ROI < 15% or profit <= 0
-- 5. Risk level calculation:
--    - low: margin > 40% AND seller_count < 10 AND BSR < 10,000
--    - high: margin < 20% OR seller_count > 50 OR BSR > 100,000
--    - medium: everything else

