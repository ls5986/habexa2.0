-- HABEXA: Pack Type & Cost Intelligence
-- Adds cost_type (Unit/Pack/Case) and case_size columns to track true unit costs

-- ============================================
-- 1. ADD COST TYPE TO PRODUCT_SOURCES
-- ============================================
ALTER TABLE product_sources
ADD COLUMN IF NOT EXISTS cost_type TEXT DEFAULT 'unit' CHECK (cost_type IN ('unit', 'pack', 'case')),
ADD COLUMN IF NOT EXISTS case_size INTEGER DEFAULT NULL, -- Number of units per case (if cost_type = 'case')
ADD COLUMN IF NOT EXISTS pack_size_for_cost INTEGER DEFAULT NULL; -- Pack size when cost_type = 'pack'

-- Index for cost type filtering
CREATE INDEX IF NOT EXISTS idx_product_sources_cost_type ON product_sources(cost_type);

-- Comments
COMMENT ON COLUMN product_sources.cost_type IS 'How supplier sells: unit (per individual), pack (per pack), case (per case)';
COMMENT ON COLUMN product_sources.case_size IS 'Number of units per case (required if cost_type = case)';
COMMENT ON COLUMN product_sources.pack_size_for_cost IS 'Pack size when cost_type = pack (e.g., 6-pack, 12-pack)';

-- ============================================
-- 2. ADD AMAZON PACK SIZE TO PRODUCTS
-- ============================================
-- Track Amazon's selling pack size (from SP-API item_package_quantity)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS amazon_pack_size INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS cost_per_amazon_unit DECIMAL(10,2);

-- Comments
COMMENT ON COLUMN products.amazon_pack_size IS 'Amazon selling pack size (1-pack, 2-pack, etc.) from SP-API item_package_quantity';
COMMENT ON COLUMN products.cost_per_amazon_unit IS 'Calculated: unit_cost × amazon_pack_size (for accurate profitability)';

-- ============================================
-- 3. HELPER FUNCTION: Calculate True Unit Cost
-- ============================================
CREATE OR REPLACE FUNCTION calculate_true_unit_cost(
    p_wholesale_cost DECIMAL,
    p_cost_type TEXT,
    p_pack_size_for_cost INTEGER,
    p_case_size INTEGER
)
RETURNS DECIMAL AS $$
DECLARE
    v_unit_cost DECIMAL;
BEGIN
    IF p_cost_type = 'unit' THEN
        -- Supplier sells per unit
        v_unit_cost := p_wholesale_cost;
    ELSIF p_cost_type = 'pack' THEN
        -- Supplier sells per pack (e.g., $48 for 12-pack)
        IF p_pack_size_for_cost IS NULL OR p_pack_size_for_cost = 0 THEN
            v_unit_cost := p_wholesale_cost; -- Fallback to treating as unit
        ELSE
            v_unit_cost := p_wholesale_cost / p_pack_size_for_cost;
        END IF;
    ELSIF p_cost_type = 'case' THEN
        -- Supplier sells per case (e.g., $200 for case of 48)
        IF p_case_size IS NULL OR p_case_size = 0 THEN
            v_unit_cost := p_wholesale_cost; -- Fallback to treating as unit
        ELSE
            v_unit_cost := p_wholesale_cost / p_case_size;
        END IF;
    ELSE
        -- Default to unit
        v_unit_cost := p_wholesale_cost;
    END IF;
    
    RETURN v_unit_cost;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 4. HELPER FUNCTION: Calculate Cost Per Amazon Unit
-- ============================================
CREATE OR REPLACE FUNCTION calculate_amazon_unit_cost(
    p_unit_cost DECIMAL,
    p_amazon_pack_size INTEGER
)
RETURNS DECIMAL AS $$
BEGIN
    RETURN p_unit_cost * COALESCE(p_amazon_pack_size, 1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 5. UPDATE EXISTING RECORDS (if needed)
-- ============================================
-- Set default cost_type for existing records
UPDATE product_sources
SET cost_type = 'unit'
WHERE cost_type IS NULL;

-- ============================================
-- 6. COMMENTS
-- ============================================
COMMENT ON FUNCTION calculate_true_unit_cost IS 'Calculates true per-unit cost based on cost_type (unit/pack/case)';
COMMENT ON FUNCTION calculate_amazon_unit_cost IS 'Calculates cost per Amazon selling unit (unit_cost × amazon_pack_size)';

