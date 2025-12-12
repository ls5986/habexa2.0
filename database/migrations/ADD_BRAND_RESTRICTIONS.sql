-- HABEXA: Brand Restrictions System
-- Tracks globally gated brands and supplier-specific overrides

-- ============================================
-- 1. BRAND RESTRICTIONS TABLE
-- ============================================
-- Global brand restriction database
CREATE TABLE IF NOT EXISTS brand_restrictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_name TEXT NOT NULL,
    brand_name_normalized TEXT NOT NULL, -- Lowercase, trimmed for matching
    
    -- Restriction Type
    restriction_type TEXT NOT NULL CHECK (restriction_type IN (
        'globally_gated',      -- Amazon globally restricts this brand
        'seller_specific',     -- Some sellers can sell, others can't
        'category_gated',      -- Gated in specific categories only
        'ungated'              -- Not restricted
    )),
    
    -- Details
    category TEXT, -- If category_gated, which category
    notes TEXT,    -- Additional information
    
    -- Verification
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by TEXT, -- User ID or 'system'
    verification_source TEXT, -- 'manual', 'sp_api', 'keepa', 'user_report'
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(brand_name_normalized)
);

CREATE INDEX IF NOT EXISTS idx_brand_restrictions_name ON brand_restrictions(brand_name_normalized);
CREATE INDEX IF NOT EXISTS idx_brand_restrictions_type ON brand_restrictions(restriction_type);

-- ============================================
-- 2. SUPPLIER BRAND OVERRIDES
-- ============================================
-- Supplier-specific brand permissions
CREATE TABLE IF NOT EXISTS supplier_brand_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    brand_name TEXT NOT NULL,
    brand_name_normalized TEXT NOT NULL,
    
    -- Override Type
    override_type TEXT NOT NULL CHECK (override_type IN (
        'can_sell',        -- Supplier CAN sell this restricted brand
        'cannot_sell',     -- Supplier CANNOT sell (even if normally allowed)
        'requires_approval' -- Requires special approval
    )),
    
    -- Approval Details
    approval_status TEXT CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approval_date TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    
    -- Supplier Notes
    supplier_notes TEXT, -- Notes from supplier about this brand
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(supplier_id, brand_name_normalized)
);

CREATE INDEX IF NOT EXISTS idx_supplier_brand_overrides_supplier ON supplier_brand_overrides(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_brand_overrides_brand ON supplier_brand_overrides(brand_name_normalized);
CREATE INDEX IF NOT EXISTS idx_supplier_brand_overrides_user ON supplier_brand_overrides(user_id);

-- ============================================
-- 3. PRODUCT BRAND FLAGS
-- ============================================
-- Track brand restriction status per product
CREATE TABLE IF NOT EXISTS product_brand_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    brand_name TEXT NOT NULL,
    
    -- Status
    brand_status TEXT NOT NULL CHECK (brand_status IN (
        'unrestricted',        -- ✅ Green: Can sell
        'supplier_restricted', -- ⚠️ Yellow: Supplier restriction
        'globally_restricted', -- 🚫 Red: Cannot sell
        'requires_approval',   -- ⚠️ Yellow: Needs approval
        'unknown'              -- Gray: Not checked yet
    )),
    
    -- Source
    restriction_id UUID REFERENCES brand_restrictions(id),
    override_id UUID REFERENCES supplier_brand_overrides(id),
    
    -- Detection
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    detection_method TEXT, -- 'auto', 'manual', 'sp_api', 'keepa'
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(product_id, brand_name)
);

CREATE INDEX IF NOT EXISTS idx_product_brand_flags_product ON product_brand_flags(product_id);
CREATE INDEX IF NOT EXISTS idx_product_brand_flags_status ON product_brand_flags(brand_status);
CREATE INDEX IF NOT EXISTS idx_product_brand_flags_user ON product_brand_flags(user_id);

-- ============================================
-- 4. HELPER FUNCTION: Normalize Brand Name
-- ============================================
CREATE OR REPLACE FUNCTION normalize_brand_name(brand TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(TRIM(brand));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 5. HELPER FUNCTION: Get Brand Status
-- ============================================
CREATE OR REPLACE FUNCTION get_product_brand_status(
    p_product_id UUID,
    p_brand_name TEXT,
    p_supplier_id UUID
)
RETURNS TEXT AS $$
DECLARE
    v_normalized_brand TEXT;
    v_global_restriction TEXT;
    v_supplier_override TEXT;
BEGIN
    v_normalized_brand := normalize_brand_name(p_brand_name);
    
    -- Check global restrictions
    SELECT restriction_type INTO v_global_restriction
    FROM brand_restrictions
    WHERE brand_name_normalized = v_normalized_brand;
    
    -- Check supplier override
    SELECT override_type INTO v_supplier_override
    FROM supplier_brand_overrides
    WHERE supplier_id = p_supplier_id
      AND brand_name_normalized = v_normalized_brand;
    
    -- Determine status
    IF v_supplier_override = 'can_sell' THEN
        RETURN 'unrestricted';
    ELSIF v_supplier_override = 'cannot_sell' THEN
        RETURN 'supplier_restricted';
    ELSIF v_supplier_override = 'requires_approval' THEN
        RETURN 'requires_approval';
    ELSIF v_global_restriction = 'globally_gated' THEN
        RETURN 'globally_restricted';
    ELSIF v_global_restriction = 'seller_specific' THEN
        RETURN 'requires_approval';
    ELSIF v_global_restriction IS NULL THEN
        RETURN 'unknown';
    ELSE
        RETURN 'unrestricted';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 6. COMMENTS
-- ============================================
COMMENT ON TABLE brand_restrictions IS 'Global database of brand restrictions (gated brands)';
COMMENT ON TABLE supplier_brand_overrides IS 'Supplier-specific brand permissions (can sell restricted brands)';
COMMENT ON TABLE product_brand_flags IS 'Brand restriction status per product';
COMMENT ON COLUMN brand_restrictions.restriction_type IS 'Type of restriction: globally_gated, seller_specific, category_gated, ungated';
COMMENT ON COLUMN supplier_brand_overrides.override_type IS 'Override: can_sell, cannot_sell, requires_approval';
COMMENT ON COLUMN product_brand_flags.brand_status IS 'Status: unrestricted, supplier_restricted, globally_restricted, requires_approval, unknown';

-- ============================================
-- 7. ROW LEVEL SECURITY (if needed)
-- ============================================
-- Brand restrictions are global (public read)
-- Supplier overrides are user-specific
-- Product flags are user-specific

-- ALTER TABLE brand_restrictions ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY brand_restrictions_read ON brand_restrictions FOR SELECT USING (true);

-- ALTER TABLE supplier_brand_overrides ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY supplier_brand_overrides_user ON supplier_brand_overrides
--     FOR ALL USING (auth.uid() = user_id);

-- ALTER TABLE product_brand_flags ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY product_brand_flags_user ON product_brand_flags
--     FOR ALL USING (auth.uid() = user_id);

