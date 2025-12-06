-- ============================================
-- HABEXA PRODUCT IMPORT FLOW - DATABASE MIGRATION
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. Add ASIN status tracking (may already exist, so IF NOT EXISTS)
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS asin_status TEXT DEFAULT 'found';

COMMENT ON COLUMN products.asin_status IS 
'ASIN lookup status: found, not_found, multiple_found, manual';

-- 2. Store multiple ASIN options when found
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS potential_asins JSONB;

COMMENT ON COLUMN products.potential_asins IS 
'Array of ASIN objects when multiple found: [{"asin":"B07...", "title":"...", "image":"..."}]';

-- 3. Parent/Child ASIN tracking
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS parent_asin TEXT;

ALTER TABLE products 
ADD COLUMN IF NOT EXISTS is_variation BOOLEAN DEFAULT FALSE;

ALTER TABLE products 
ADD COLUMN IF NOT EXISTS variation_count INTEGER DEFAULT 1;

ALTER TABLE products 
ADD COLUMN IF NOT EXISTS variation_theme TEXT;

COMMENT ON COLUMN products.parent_asin IS 
'Parent ASIN if this is a variation (from Keepa parentAsin)';

COMMENT ON COLUMN products.is_variation IS 
'True if this product has a parent ASIN (is part of variation family)';

COMMENT ON COLUMN products.variation_count IS 
'Number of sibling variations (from Keepa variationCSV length)';

COMMENT ON COLUMN products.variation_theme IS 
'Variation type: Size, Color, Size-Color, etc.';

-- 4. Make product name optional (it's from supplier, not required)
-- Note: This might fail if there's a NOT NULL constraint, but that's ok - we'll handle it in code
DO $$ 
BEGIN
    -- Try to drop NOT NULL constraint if it exists
    ALTER TABLE products ALTER COLUMN title DROP NOT NULL;
EXCEPTION
    WHEN OTHERS THEN
        -- Column might not have NOT NULL, or might not exist - that's ok
        RAISE NOTICE 'Could not drop NOT NULL from title column: %', SQLERRM;
END $$;

-- 5. Add supplier title (what supplier calls it)
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS supplier_title TEXT;

COMMENT ON COLUMN products.supplier_title IS 
'Product name from supplier (CSV), vs title which is from Amazon';

-- 6. Add indexes for filtering
CREATE INDEX IF NOT EXISTS idx_products_asin_status 
ON products(asin_status);

CREATE INDEX IF NOT EXISTS idx_products_parent_asin 
ON products(parent_asin);

CREATE INDEX IF NOT EXISTS idx_products_is_variation 
ON products(is_variation);

-- 7. Add check constraint for asin_status values (drop first if exists)
ALTER TABLE products 
DROP CONSTRAINT IF EXISTS products_asin_status_check;

ALTER TABLE products 
ADD CONSTRAINT products_asin_status_check 
CHECK (asin_status IN ('found', 'not_found', 'multiple_found', 'manual'));

-- 8. Update existing products to have correct status
UPDATE products 
SET asin_status = 'found' 
WHERE asin IS NOT NULL 
  AND asin_status IS NULL;

UPDATE products 
SET asin_status = 'not_found' 
WHERE asin IS NULL 
  AND upc IS NOT NULL 
  AND asin_status IS NULL;

-- 9. Verify changes
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'products' 
AND column_name IN (
    'asin_status', 
    'potential_asins', 
    'parent_asin', 
    'is_variation', 
    'variation_count',
    'variation_theme',
    'supplier_title'
)
ORDER BY ordinal_position;

-- 10. Show indexes created
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'products'
AND indexname LIKE 'idx_products_%';

-- ============================================
-- MIGRATION COMPLETE
-- ============================================

