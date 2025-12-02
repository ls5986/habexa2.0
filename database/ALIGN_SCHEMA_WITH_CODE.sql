-- ============================================
-- SCHEMA ALIGNMENT WITH CODE
-- ============================================
-- Run this to ensure your schema matches the code expectations
-- ============================================

-- ============================================
-- 1. ANALYSES TABLE - Add unique constraint
-- ============================================
-- Code expects: on_conflict="user_id,supplier_id,asin"
-- This allows multiple analyses per ASIN if different suppliers

DO $$ 
BEGIN
    -- Drop old constraints if they exist
    ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_user_asin_unique;
    ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_supplier_asin_unique;
    ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_user_supplier_asin_unique;
    
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

-- Index for performance
DROP INDEX IF EXISTS idx_analyses_user_supplier_asin;
CREATE INDEX IF NOT EXISTS idx_analyses_user_supplier_asin 
ON analyses(user_id, supplier_id, asin);

-- ============================================
-- 2. PRODUCT_SOURCES - Add keepa_analyzed_at
-- ============================================
-- Code expects this column for Keepa analysis tracking

ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS keepa_analyzed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_product_sources_keepa_analyzed 
ON product_sources(keepa_analyzed_at) 
WHERE keepa_analyzed_at IS NOT NULL;

-- ============================================
-- 3. PRODUCTS - Add UPC column (if implementing UPC support)
-- ============================================

ALTER TABLE products ADD COLUMN IF NOT EXISTS upc TEXT;

CREATE INDEX IF NOT EXISTS idx_products_upc ON products(upc) WHERE upc IS NOT NULL;

-- ============================================
-- 4. PRODUCT_SOURCES - Add UPC column (if implementing UPC support)
-- ============================================

ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS upc TEXT;

-- ============================================
-- 5. VERIFY PRODUCTS TABLE HAS brand_name
-- ============================================
-- Code uses brand_name, not brand
-- Schema should have: brand_id (UUID) and brand_name (TEXT)
-- If you have a 'brand' column, you may need to migrate data

DO $$
BEGIN
    -- Check if 'brand' column exists (old schema)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'brand'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'brand_name'
    ) THEN
        -- Migrate: rename 'brand' to 'brand_name'
        ALTER TABLE products RENAME COLUMN brand TO brand_name;
        RAISE NOTICE 'Migrated products.brand to products.brand_name';
    END IF;
END $$;

-- ============================================
-- VERIFICATION
-- ============================================

-- Show analyses unique constraints
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conrelid = 'analyses'::regclass
AND contype = 'u';

-- Show product_sources columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'product_sources' 
AND column_name IN ('keepa_analyzed_at', 'upc')
ORDER BY column_name;

-- Show products brand columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name IN ('brand', 'brand_name', 'brand_id', 'upc')
ORDER BY column_name;

