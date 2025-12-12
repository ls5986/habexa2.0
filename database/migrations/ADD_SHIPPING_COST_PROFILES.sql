-- HABEXA: Shipping Cost Profiles
-- Per-supplier shipping cost configurations

-- ============================================
-- 1. SHIPPING COST PROFILES
-- ============================================
CREATE TABLE IF NOT EXISTS shipping_cost_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    
    -- Profile Info
    name TEXT NOT NULL, -- e.g., "Standard Shipping", "Express"
    is_default BOOLEAN DEFAULT false,
    
    -- Cost Type
    cost_type TEXT NOT NULL CHECK (cost_type IN (
        'flat_rate',      -- Fixed cost per order
        'per_pound',      -- Cost per pound
        'per_unit',       -- Cost per unit
        'tiered',         -- Tiered pricing (0-10 lbs = $X, 10-20 lbs = $Y)
        'percentage',     -- Percentage of order value
        'free_above'      -- Free shipping above threshold
    )),
    
    -- Cost Parameters (JSONB for flexibility)
    cost_params JSONB NOT NULL, -- {
    --   "flat_rate": 25.00,
    --   "per_pound": 0.50,
    --   "per_unit": 0.25,
    --   "tiers": [{"min": 0, "max": 10, "cost": 20}, {"min": 10, "max": 20, "cost": 30}],
    --   "percentage": 5.0,
    --   "free_threshold": 500.00
    -- }
    
    -- Free Shipping Threshold
    free_shipping_threshold DECIMAL(10,2), -- Order value above which shipping is free
    
    -- Minimum/Maximum
    min_shipping_cost DECIMAL(10,2) DEFAULT 0,
    max_shipping_cost DECIMAL(10,2),
    
    -- Effective Dates
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE, -- NULL = no end date
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, supplier_id, name)
);

CREATE INDEX IF NOT EXISTS idx_shipping_profiles_supplier ON shipping_cost_profiles(supplier_id);
CREATE INDEX IF NOT EXISTS idx_shipping_profiles_user ON shipping_cost_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_shipping_profiles_default ON shipping_cost_profiles(supplier_id, is_default) WHERE is_default = true;

-- ============================================
-- 2. ADD SHIPPING COLUMNS TO PRODUCT_SOURCES
-- ============================================
ALTER TABLE product_sources
ADD COLUMN IF NOT EXISTS shipping_cost_per_unit DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS shipping_profile_id UUID REFERENCES shipping_cost_profiles(id);

CREATE INDEX IF NOT EXISTS idx_product_sources_shipping_profile ON product_sources(shipping_profile_id);

-- ============================================
-- 3. ADD LANDED COST COLUMNS
-- ============================================
ALTER TABLE product_sources
ADD COLUMN IF NOT EXISTS total_landed_cost DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS profit_after_shipping DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS roi_after_shipping DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS margin_after_shipping DECIMAL(5,2);

-- ============================================
-- 4. HELPER FUNCTION: Calculate Shipping Cost
-- ============================================
CREATE OR REPLACE FUNCTION calculate_shipping_cost(
    p_profile_id UUID,
    p_order_value DECIMAL,
    p_total_weight DECIMAL,
    p_unit_count INTEGER
)
RETURNS DECIMAL AS $$
DECLARE
    v_profile RECORD;
    v_cost DECIMAL := 0;
    v_tier_cost DECIMAL;
BEGIN
    -- Get profile
    SELECT * INTO v_profile
    FROM shipping_cost_profiles
    WHERE id = p_profile_id;
    
    IF NOT FOUND THEN
        RETURN 0;
    END IF;
    
    -- Check free shipping threshold
    IF v_profile.free_shipping_threshold IS NOT NULL 
       AND p_order_value >= v_profile.free_shipping_threshold THEN
        RETURN 0;
    END IF
    
    -- Calculate based on cost type
    IF v_profile.cost_type = 'flat_rate' THEN
        v_cost := COALESCE((v_profile.cost_params->>'flat_rate')::DECIMAL, 0);
    
    ELSIF v_profile.cost_type = 'per_pound' THEN
        v_cost := p_total_weight * COALESCE((v_profile.cost_params->>'per_pound')::DECIMAL, 0);
    
    ELSIF v_profile.cost_type = 'per_unit' THEN
        v_cost := p_unit_count * COALESCE((v_profile.cost_params->>'per_unit')::DECIMAL, 0);
    
    ELSIF v_profile.cost_type = 'percentage' THEN
        v_cost := p_order_value * (COALESCE((v_profile.cost_params->>'percentage')::DECIMAL, 0) / 100);
    
    ELSIF v_profile.cost_type = 'tiered' THEN
        -- Find matching tier
        FOR v_tier_cost IN 
            SELECT (tier->>'cost')::DECIMAL
            FROM jsonb_array_elements(v_profile.cost_params->'tiers') AS tier
            WHERE (tier->>'min')::DECIMAL <= p_total_weight
              AND (tier->>'max')::DECIMAL >= p_total_weight
            LIMIT 1
        LOOP
            v_cost := v_tier_cost;
        END LOOP;
    END IF;
    
    -- Apply min/max
    IF v_profile.min_shipping_cost IS NOT NULL AND v_cost < v_profile.min_shipping_cost THEN
        v_cost := v_profile.min_shipping_cost;
    END IF;
    
    IF v_profile.max_shipping_cost IS NOT NULL AND v_cost > v_profile.max_shipping_cost THEN
        v_cost := v_profile.max_shipping_cost;
    END IF;
    
    RETURN v_cost;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 5. COMMENTS
-- ============================================
COMMENT ON TABLE shipping_cost_profiles IS 'Per-supplier shipping cost configurations (flat rate, per pound, tiered, etc.)';
COMMENT ON COLUMN shipping_cost_profiles.cost_params IS 'JSONB with cost parameters based on cost_type';
COMMENT ON COLUMN product_sources.shipping_cost_per_unit IS 'Calculated shipping cost per unit for this product';
COMMENT ON COLUMN product_sources.total_landed_cost IS 'Total cost including wholesale + shipping + prep + inbound';
COMMENT ON FUNCTION calculate_shipping_cost IS 'Calculates shipping cost based on profile, order value, weight, and unit count';

