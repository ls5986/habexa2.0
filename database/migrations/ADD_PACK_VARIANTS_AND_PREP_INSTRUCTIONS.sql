-- ============================================
-- HABEXA v2.1: Multi-Pack PPU & Prep Instructions
-- ============================================
-- Adds support for:
-- 1. Tracking Amazon pack size variants (1-pack, 2-pack, 3-pack, etc.)
-- 2. Calculating profit per unit (PPU) for each variant
-- 3. Auto-generating prep instructions for 3PL
-- ============================================

-- ============================================
-- 1. PRODUCT PACK VARIANTS TABLE
-- ============================================
-- Tracks all Amazon pack size variants for a product
-- Used to calculate which pack size is most profitable
CREATE TABLE IF NOT EXISTS product_pack_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    asin TEXT NOT NULL,
    pack_size INTEGER NOT NULL CHECK (pack_size > 0), -- 1, 2, 3, 4, etc.
    
    -- Pricing Data
    current_price DECIMAL(10,2),
    buy_box_price_365d_avg DECIMAL(10,2),
    buy_box_price_90d_avg DECIMAL(10,2),
    buy_box_price_30d_avg DECIMAL(10,2),
    lowest_price_365d DECIMAL(10,2),
    
    -- Calculated Metrics
    profit_per_unit DECIMAL(10,2), -- PPU (Profit Per Unit)
    roi DECIMAL(10,2),
    margin DECIMAL(10,2),
    total_profit DECIMAL(10,2), -- Total profit if all units sold as this pack
    
    -- Recommendation
    is_recommended BOOLEAN DEFAULT FALSE,
    recommendation_reason TEXT, -- "Highest PPU", "Best ROI", etc.
    
    -- Metadata
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(product_id, pack_size),
    CONSTRAINT valid_pack_size CHECK (pack_size BETWEEN 1 AND 100)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pack_variants_product_id ON product_pack_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_pack_variants_asin ON product_pack_variants(asin);
CREATE INDEX IF NOT EXISTS idx_pack_variants_recommended ON product_pack_variants(is_recommended) WHERE is_recommended = TRUE;
CREATE INDEX IF NOT EXISTS idx_pack_variants_ppu ON product_pack_variants(profit_per_unit DESC);

-- ============================================
-- 2. PREP INSTRUCTIONS TABLE
-- ============================================
-- Auto-generated prep instructions for 3PL
-- Links to supplier order items
CREATE TABLE IF NOT EXISTS prep_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_item_id UUID REFERENCES supplier_order_items(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    
    -- Order Details
    expected_units INTEGER NOT NULL, -- Total units received
    target_pack_size INTEGER NOT NULL, -- Which pack size to create (e.g., 4-pack)
    packs_to_create INTEGER NOT NULL, -- How many packs to make (e.g., 120)
    leftover_units INTEGER DEFAULT 0, -- Units that don't make a full pack
    
    -- Calculated Economics
    profit_per_unit DECIMAL(10,2), -- PPU for target pack
    total_profit DECIMAL(10,2), -- Total profit if all packs sell
    roi DECIMAL(10,2),
    
    -- Prep Steps (JSONB for flexibility)
    prep_steps JSONB DEFAULT '[]'::jsonb, -- Array of step objects
    /*
    Example prep_steps:
    [
      {
        "step": 1,
        "action": "Receive inventory",
        "quantity": 480,
        "unit": "units"
      },
      {
        "step": 2,
        "action": "Bundle into packs",
        "quantity": 120,
        "unit": "4-packs",
        "notes": "Use polybags"
      },
      {
        "step": 3,
        "action": "Apply FNSKU labels",
        "quantity": 120,
        "unit": "labels"
      }
    ]
    */
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'in_progress', 'completed', 'cancelled')),
    
    -- PDF Generation
    pdf_url TEXT, -- URL to generated PDF
    pdf_generated_at TIMESTAMP WITH TIME ZONE,
    
    -- Email Tracking
    email_sent_at TIMESTAMP WITH TIME ZONE,
    email_recipient TEXT, -- 3PL email address
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_prep_instructions_order_item ON prep_instructions(order_item_id);
CREATE INDEX IF NOT EXISTS idx_prep_instructions_product ON prep_instructions(product_id);
CREATE INDEX IF NOT EXISTS idx_prep_instructions_order ON prep_instructions(supplier_order_id);
CREATE INDEX IF NOT EXISTS idx_prep_instructions_user ON prep_instructions(user_id);
CREATE INDEX IF NOT EXISTS idx_prep_instructions_status ON prep_instructions(status);

-- ============================================
-- 3. ADD 365-DAY AVERAGE COLUMNS TO PRODUCTS
-- ============================================
-- Add buy box price averages for different time periods
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS buy_box_price_365d_avg DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS buy_box_price_90d_avg DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS buy_box_price_30d_avg DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS pricing_mode TEXT DEFAULT 'current' CHECK (pricing_mode IN ('current', '30d_avg', '90d_avg', '365d_avg'));

-- Index for pricing mode filtering
CREATE INDEX IF NOT EXISTS idx_products_pricing_mode ON products(pricing_mode);

-- ============================================
-- 4. ADD PACK VARIANT TRACKING TO PRODUCT_SOURCES
-- ============================================
-- Track which pack sizes are available on Amazon
ALTER TABLE product_sources
ADD COLUMN IF NOT EXISTS available_pack_sizes INTEGER[] DEFAULT ARRAY[1], -- [1, 2, 3, 4]
ADD COLUMN IF NOT EXISTS recommended_pack_size INTEGER, -- Which pack size to sell
ADD COLUMN IF NOT EXISTS pack_variants_calculated_at TIMESTAMP WITH TIME ZONE;

-- ============================================
-- 5. HELPER FUNCTIONS
-- ============================================

-- Function to get recommended pack size for a product
CREATE OR REPLACE FUNCTION get_recommended_pack_size(p_product_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_pack_size INTEGER;
BEGIN
    SELECT pack_size INTO v_pack_size
    FROM product_pack_variants
    WHERE product_id = p_product_id
      AND is_recommended = TRUE
    ORDER BY profit_per_unit DESC
    LIMIT 1;
    
    RETURN COALESCE(v_pack_size, 1); -- Default to 1-pack if none found
END;
$$ LANGUAGE plpgsql;

-- Function to calculate packs to create
CREATE OR REPLACE FUNCTION calculate_packs_to_create(
    p_total_units INTEGER,
    p_pack_size INTEGER
)
RETURNS TABLE(
    packs_to_create INTEGER,
    leftover_units INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (p_total_units / p_pack_size)::INTEGER as packs_to_create,
        (p_total_units % p_pack_size)::INTEGER as leftover_units;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 6. RLS POLICIES (if using Row Level Security)
-- ============================================
-- Note: Adjust based on your RLS setup

-- Pack Variants: Users can only see their own product variants
-- ALTER TABLE product_pack_variants ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY pack_variants_user_policy ON product_pack_variants
--     FOR ALL USING (
--         product_id IN (
--             SELECT id FROM products WHERE user_id = auth.uid()
--         )
--     );

-- Prep Instructions: Users can only see their own instructions
-- ALTER TABLE prep_instructions ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY prep_instructions_user_policy ON prep_instructions
--     FOR ALL USING (user_id = auth.uid());

-- ============================================
-- 7. COMMENTS
-- ============================================
COMMENT ON TABLE product_pack_variants IS 'Tracks Amazon pack size variants (1-pack, 2-pack, etc.) and calculates profit per unit for each';
COMMENT ON TABLE prep_instructions IS 'Auto-generated prep instructions for 3PL based on order quantities and recommended pack sizes';
COMMENT ON COLUMN product_pack_variants.profit_per_unit IS 'Profit Per Unit (PPU) - the key metric for pack size selection';
COMMENT ON COLUMN prep_instructions.prep_steps IS 'JSONB array of step-by-step prep instructions for 3PL';

-- ============================================
-- ✅ MIGRATION COMPLETE
-- ============================================
-- Next steps:
-- 1. Run this migration in Supabase
-- 2. Update backend services to populate pack variants
-- 3. Build frontend components for pack selection
-- 4. Generate prep instructions on order creation

