-- ============================================
-- SCHEMA ALIGNMENT FIXES
-- ============================================
-- Fixes to align code with actual database schema
-- Run this after reviewing your schema
-- ============================================

-- ============================================
-- 1. ANALYSES TABLE - Add unique constraint
-- ============================================
-- Code expects: on_conflict="user_id,supplier_id,asin"
-- But schema might not have this constraint

DO $$ 
BEGIN
    -- Drop old constraints if they exist
    ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_user_asin_unique;
    ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_supplier_asin_unique;
    
    -- Add the correct unique constraint (allows NULL supplier_id)
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'analyses_user_supplier_asin_unique'
    ) THEN
        ALTER TABLE analyses 
        ADD CONSTRAINT analyses_user_supplier_asin_unique 
        UNIQUE (user_id, supplier_id, asin);
    END IF;
END $$;

-- ============================================
-- 2. PRODUCT_SOURCES - Add keepa_analyzed_at
-- ============================================
-- Code expects this column for Keepa analysis tracking

ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS keepa_analyzed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_product_sources_keepa_analyzed 
ON product_sources(keepa_analyzed_at) 
WHERE keepa_analyzed_at IS NOT NULL;

-- ============================================
-- 3. PRODUCTS TABLE - Ensure brand fields match
-- ============================================
-- Schema has: brand_id (UUID) and brand_name (TEXT)
-- Code might use: brand (TEXT)
-- Check if we need to add 'brand' column or update code

-- Option A: Add 'brand' column if code uses it
-- ALTER TABLE products ADD COLUMN IF NOT EXISTS brand TEXT;

-- Option B: Keep only brand_id and brand_name (recommended)
-- Code should use brand_name instead of brand

-- ============================================
-- 4. ANALYSES TABLE - Ensure all columns exist
-- ============================================
-- Code uses these columns, verify they exist:

ALTER TABLE analyses ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS brand TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_30 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_90 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sales_drops_180 INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS variation_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS amazon_in_stock BOOLEAN;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS rating NUMERIC(3,1);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS review_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS price_source TEXT DEFAULT 'unknown';
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_total NUMERIC(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_referral NUMERIC(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_fba NUMERIC(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS seller_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fba_seller_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS amazon_sells BOOLEAN DEFAULT FALSE;

-- ============================================
-- 5. PRODUCT_SOURCES - Add UPC column
-- ============================================
-- For UPC support (if implementing)

ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS upc TEXT;

-- ============================================
-- 6. PRODUCTS - Add UPC column
-- ============================================
-- For UPC support (if implementing)

ALTER TABLE products ADD COLUMN IF NOT EXISTS upc TEXT;

-- ============================================
-- VERIFY CONSTRAINTS
-- ============================================

-- Check if analyses unique constraint exists
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conrelid = 'analyses'::regclass
AND contype = 'u';

-- Show all analyses columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'analyses' 
ORDER BY ordinal_position;

