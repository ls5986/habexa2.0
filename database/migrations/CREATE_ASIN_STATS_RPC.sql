-- ============================================================================
-- ASIN Status Stats - Enterprise-Grade Database-Side Solution
-- ============================================================================
-- This migration creates a PostgreSQL RPC function for efficient ASIN status
-- counting that scales to millions of products.
-- ============================================================================

-- Drop if exists (for updates)
DROP FUNCTION IF EXISTS get_asin_stats(UUID);

-- Create optimized stats function using FILTER clauses
CREATE OR REPLACE FUNCTION get_asin_stats(p_user_id UUID)
RETURNS JSON AS $$
DECLARE
  result JSON;
BEGIN
  -- Single aggregation query with FILTER clauses
  -- This is highly optimized and scales to millions of rows
  SELECT json_build_object(
    'all', COUNT(*),
    'asin_found', COUNT(*) FILTER (
      WHERE asin IS NOT NULL AND asin != ''
    ),
    'needs_selection', COUNT(*) FILTER (
      WHERE status = 'needs_selection'
    ),
    'needs_asin', COUNT(*) FILTER (
      WHERE (asin IS NULL OR asin = '') 
        AND upc IS NOT NULL 
        AND upc != ''
    ),
    'manual_entry', COUNT(*) FILTER (
      WHERE (asin IS NULL OR asin = '') 
        AND (upc IS NULL OR upc = '')
    )
  )
  INTO result
  FROM products
  WHERE user_id = p_user_id;
  
  RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_asin_stats(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_asin_stats(UUID) TO anon;

-- Add comment
COMMENT ON FUNCTION get_asin_stats IS 'Get product counts by ASIN status for a user - Enterprise-grade scalable solution';

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Index on user_id (should already exist, but ensure it does)
CREATE INDEX IF NOT EXISTS idx_products_user_id 
ON products(user_id);

-- Index on asin for fast ASIN lookups (partial index - only non-null ASINs)
CREATE INDEX IF NOT EXISTS idx_products_asin 
ON products(asin) 
WHERE asin IS NOT NULL AND asin != '';

-- Index on UPC for fast UPC lookups (partial index - only non-null UPCs)
CREATE INDEX IF NOT EXISTS idx_products_upc 
ON products(upc) 
WHERE upc IS NOT NULL AND upc != '';

-- Index on status for fast status filtering
CREATE INDEX IF NOT EXISTS idx_products_status 
ON products(status);

-- Composite index for ASIN status queries (MOST IMPORTANT)
-- This covers the most common query pattern: user_id + asin/upc/status
CREATE INDEX IF NOT EXISTS idx_products_asin_status 
ON products(user_id, asin, upc, status);

-- Analyze to update statistics (helps query planner)
ANALYZE products;

