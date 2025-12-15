-- HABEXA: Add Genius Score Columns to Products (OPTIMIZED VERSION)
-- This version adds columns one at a time to avoid timeouts on large tables

-- ============================================
-- 1. ADD COLUMNS ONE AT A TIME (FASTER)
-- ============================================

-- Add genius_score column (nullable, no default = fast)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS genius_score DECIMAL(5,2);

-- Add genius_grade column (nullable, no default = fast)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS genius_grade TEXT;

-- Add genius_breakdown column (JSONB, nullable = fast)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS genius_breakdown JSONB;

-- Add genius_insights column (JSONB, nullable = fast)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS genius_insights JSONB;

-- Add timestamp column (nullable, no default = fast)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS genius_score_last_calculated TIMESTAMP WITH TIME ZONE;

-- ============================================
-- 2. ADD CHECK CONSTRAINT (AFTER COLUMNS EXIST)
-- ============================================

-- Add check constraint for genius_grade (only if column exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' 
        AND column_name = 'genius_grade'
    ) THEN
        -- Drop existing constraint if it exists
        ALTER TABLE products DROP CONSTRAINT IF EXISTS products_genius_grade_check;
        
        -- Add new constraint
        ALTER TABLE products 
        ADD CONSTRAINT products_genius_grade_check 
        CHECK (genius_grade IS NULL OR genius_grade IN ('EXCELLENT', 'GOOD', 'FAIR', 'POOR'));
    END IF;
END $$;

-- ============================================
-- 3. CREATE INDEXES (ONE AT A TIME)
-- ============================================

-- Index for sorting by score (most important)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_genius_score 
ON products(genius_score DESC NULLS LAST);

-- Index for filtering by grade
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_genius_grade 
ON products(genius_grade) 
WHERE genius_grade IS NOT NULL;

-- Index for finding recently calculated scores
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_genius_score_calculated 
ON products(genius_score_last_calculated DESC) 
WHERE genius_score_last_calculated IS NOT NULL;

-- ============================================
-- 4. ADD COMMENTS
-- ============================================

COMMENT ON COLUMN products.genius_score IS '0-100 composite score from Genius Scoring Algorithm';
COMMENT ON COLUMN products.genius_grade IS 'Grade: EXCELLENT (85+), GOOD (70+), FAIR (50+), POOR (<50)';
COMMENT ON COLUMN products.genius_breakdown IS 'JSONB with breakdown by dimension (profitability, velocity, competition, risk, opportunity)';
COMMENT ON COLUMN products.genius_insights IS 'JSONB with strengths, weaknesses, opportunities, warnings';

-- ============================================
-- ✅ MIGRATION COMPLETE
-- ============================================
-- 
-- This optimized version:
-- 1. Adds columns one at a time (faster on large tables)
-- 2. Uses CONCURRENTLY for indexes (non-blocking)
-- 3. Adds constraints after columns exist
-- 4. All columns are nullable (no table rewrite needed)
--
-- Expected time: ~30 seconds for 100k products
-- ============================================

