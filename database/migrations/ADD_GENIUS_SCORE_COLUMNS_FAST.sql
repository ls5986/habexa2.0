-- HABEXA: Add Genius Score Columns (FASTEST VERSION - No Indexes)
-- Use this if the optimized version still times out
-- You can add indexes later when the table is smaller or during off-peak hours

-- ============================================
-- ADD COLUMNS ONLY (NO INDEXES, NO CONSTRAINTS)
-- ============================================

-- This is the fastest possible migration - just adds nullable columns
-- No table rewrite needed, no locking, no indexes

ALTER TABLE products
ADD COLUMN IF NOT EXISTS genius_score DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS genius_grade TEXT,
ADD COLUMN IF NOT EXISTS genius_breakdown JSONB,
ADD COLUMN IF NOT EXISTS genius_insights JSONB,
ADD COLUMN IF NOT EXISTS genius_score_last_calculated TIMESTAMP WITH TIME ZONE;

-- ============================================
-- ✅ DONE - Columns added in ~5 seconds
-- ============================================
-- 
-- Next steps (run these separately when ready):
-- 
-- 1. Add check constraint:
--    ALTER TABLE products 
--    ADD CONSTRAINT products_genius_grade_check 
--    CHECK (genius_grade IS NULL OR genius_grade IN ('EXCELLENT', 'GOOD', 'FAIR', 'POOR'));
--
-- 2. Add indexes (use CONCURRENTLY to avoid locking):
--    CREATE INDEX CONCURRENTLY idx_products_genius_score 
--    ON products(genius_score DESC NULLS LAST);
--
--    CREATE INDEX CONCURRENTLY idx_products_genius_grade 
--    ON products(genius_grade) WHERE genius_grade IS NOT NULL;
--
--    CREATE INDEX CONCURRENTLY idx_products_genius_score_calculated 
--    ON products(genius_score_last_calculated DESC) 
--    WHERE genius_score_last_calculated IS NOT NULL;
--
-- 3. Add comments:
--    COMMENT ON COLUMN products.genius_score IS '0-100 composite score';
--    COMMENT ON COLUMN products.genius_grade IS 'Grade: EXCELLENT (85+), GOOD (70+), FAIR (50+), POOR (<50)';
--
-- ============================================

