-- ============================================================================
-- Fix existing products with fake PENDING_ ASINs
-- ============================================================================

-- Set asin to NULL for products with fake PENDING_ ASINs
UPDATE products 
SET asin = NULL,
    asin_status = CASE 
        WHEN asin_status = 'not_found' THEN 'not_found'
        WHEN potential_asins IS NOT NULL AND jsonb_array_length(potential_asins) > 1 THEN 'multiple_found'
        ELSE 'not_found'
    END
WHERE asin LIKE 'PENDING_%' OR asin LIKE 'Unknown%';

-- Update lookup_status for products that now have NULL ASINs
UPDATE products
SET lookup_status = CASE
    WHEN potential_asins IS NOT NULL AND jsonb_array_length(potential_asins) > 1 THEN 'pending_selection'
    WHEN upc IS NOT NULL AND upc != '' THEN 'pending'
    ELSE 'manual'
END
WHERE asin IS NULL;

-- Add comment
COMMENT ON COLUMN products.asin IS 'Amazon ASIN - NULL if not found yet, never use fake PENDING_ values';

