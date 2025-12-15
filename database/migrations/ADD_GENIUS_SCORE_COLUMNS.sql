-- HABEXA: Add Genius Score Columns to Products
-- Stores the 0-100 genius score, grade, breakdown, and insights

-- ============================================
-- 1. ADD GENIUS SCORE COLUMNS
-- ============================================
ALTER TABLE products
ADD COLUMN IF NOT EXISTS genius_score DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS genius_grade TEXT CHECK (genius_grade IN ('EXCELLENT', 'GOOD', 'FAIR', 'POOR')),
ADD COLUMN IF NOT EXISTS genius_breakdown JSONB,
ADD COLUMN IF NOT EXISTS genius_insights JSONB,
ADD COLUMN IF NOT EXISTS genius_score_last_calculated TIMESTAMP WITH TIME ZONE;

-- ============================================
-- 2. CREATE INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_products_genius_score ON products(genius_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_products_genius_grade ON products(genius_grade);
CREATE INDEX IF NOT EXISTS idx_products_genius_score_calculated ON products(genius_score_last_calculated DESC);

-- ============================================
-- 3. COMMENTS
-- ============================================
COMMENT ON COLUMN products.genius_score IS '0-100 composite score from Genius Scoring Algorithm';
COMMENT ON COLUMN products.genius_grade IS 'Grade: EXCELLENT (85+), GOOD (70+), FAIR (50+), POOR (<50)';
COMMENT ON COLUMN products.genius_breakdown IS 'JSONB with breakdown by dimension (profitability, velocity, competition, risk, opportunity)';
COMMENT ON COLUMN products.genius_insights IS 'JSONB with strengths, weaknesses, opportunities, warnings';

