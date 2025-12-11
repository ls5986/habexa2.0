-- ============================================================================
-- RAW API RESPONSE STORAGE - Store complete JSON responses
-- ============================================================================

ALTER TABLE products ADD COLUMN IF NOT EXISTS keepa_raw_response JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sp_api_raw_response JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS keepa_last_fetched TIMESTAMP WITH TIME ZONE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sp_api_last_fetched TIMESTAMP WITH TIME ZONE;

-- Indexes for checking if we have API data
CREATE INDEX IF NOT EXISTS idx_products_has_keepa ON products(keepa_last_fetched) 
  WHERE keepa_last_fetched IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_has_sp_api ON products(sp_api_last_fetched) 
  WHERE sp_api_last_fetched IS NOT NULL;

-- ============================================================================
-- STRUCTURED DATA FROM SP-API - Extract useful fields
-- ============================================================================

-- Product identification & catalog
ALTER TABLE products ADD COLUMN IF NOT EXISTS manufacturer TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS model_number TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS part_number TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS ean TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS isbn TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS product_group TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS product_type TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS binding TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS color TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS size TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS style TEXT;

-- Dimensions & weight (critical for FBA fees!)
ALTER TABLE products ADD COLUMN IF NOT EXISTS item_length NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS item_width NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS item_height NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS item_weight NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS dimension_unit TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS weight_unit TEXT;

ALTER TABLE products ADD COLUMN IF NOT EXISTS package_length NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS package_width NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS package_height NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS package_weight NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS package_quantity INTEGER;

-- Pricing & offers
ALTER TABLE products ADD COLUMN IF NOT EXISTS list_price NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS lowest_price NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS buy_box_price NUMERIC(10,2);

-- Categories & classification  
ALTER TABLE products ADD COLUMN IF NOT EXISTS category_rank INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS category_path TEXT[];
ALTER TABLE products ADD COLUMN IF NOT EXISTS browse_nodes JSONB;

-- Product features
ALTER TABLE products ADD COLUMN IF NOT EXISTS features TEXT[];
ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS bullet_points TEXT[];

-- Images
ALTER TABLE products ADD COLUMN IF NOT EXISTS images JSONB; -- Array of image URLs with variants

-- ============================================================================
-- STRUCTURED DATA FROM KEEPA - Sales rank trends, pricing history, etc.
-- ============================================================================

-- Sales rank metrics (critical for demand analysis!)
ALTER TABLE products ADD COLUMN IF NOT EXISTS current_sales_rank INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sales_rank_30_day_avg INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sales_rank_90_day_avg INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sales_rank_180_day_avg INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS sales_rank_drops_30_day INTEGER; -- Estimated sales
ALTER TABLE products ADD COLUMN IF NOT EXISTS sales_rank_drops_90_day INTEGER;

-- Pricing history (track price changes over time)
ALTER TABLE products ADD COLUMN IF NOT EXISTS amazon_price_current NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS amazon_price_30_day_avg NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS amazon_price_90_day_avg NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS new_price_current NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS new_price_30_day_avg NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS new_price_90_day_avg NUMERIC(10,2);

-- Buybox & availability
ALTER TABLE products ADD COLUMN IF NOT EXISTS buybox_price_current NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS buybox_seller TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS in_stock BOOLEAN;
ALTER TABLE products ADD COLUMN IF NOT EXISTS out_of_stock_percentage INTEGER; -- % of time OOS in last 90 days

-- Rating & review metrics
ALTER TABLE products ADD COLUMN IF NOT EXISTS rating_average NUMERIC(3,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS review_count INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS review_velocity INTEGER; -- Reviews per month

-- FBA & shipping
ALTER TABLE products ADD COLUMN IF NOT EXISTS fba_fees NUMERIC(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS referral_fee_percentage NUMERIC(5,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_hazmat BOOLEAN;
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_meltable BOOLEAN;

-- Historical tracking
ALTER TABLE products ADD COLUMN IF NOT EXISTS first_available_date DATE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS age_in_days INTEGER;

-- Add index on sales rank for filtering high-demand products
CREATE INDEX IF NOT EXISTS idx_products_sales_rank ON products(current_sales_rank) 
  WHERE current_sales_rank IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating_average) 
  WHERE rating_average IS NOT NULL;

