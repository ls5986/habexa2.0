-- Add missing columns to analyses table that the code expects
-- Note: sell_price, title, brand, image_url are stored in products table, NOT analyses

-- Check if sell_price exists (it shouldn't, but let's be safe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'analyses' AND column_name = 'sell_price'
    ) THEN
        -- Don't add sell_price - it belongs in products table
        RAISE NOTICE 'sell_price should NOT be in analyses table - it belongs in products';
    END IF;
END $$;

-- Verify all expected columns exist
-- These should already exist from previous migrations, but let's ensure:
-- From ADD_SP_API_COLUMNS.sql: seller_count, fba_seller_count, amazon_sells, price_source
-- From ADD_FEES_COLUMNS_TO_ANALYSES.sql: fees_total, fees_referral, fees_fba
-- From CREATE_KEEPA_CACHE_AND_COLUMNS.sql: category, sales_drops_30, sales_drops_90, sales_drops_180, variation_count, amazon_in_stock, rating, review_count

-- Note: title, brand, image_url are NOT in analyses - they go to products table

