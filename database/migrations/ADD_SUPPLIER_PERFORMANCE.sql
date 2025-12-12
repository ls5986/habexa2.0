-- HABEXA: Supplier Performance Tracking
-- Metrics, variance tracking, and scorecards

-- ============================================
-- 1. SUPPLIER PERFORMANCE METRICS
-- ============================================
CREATE TABLE IF NOT EXISTS supplier_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    
    -- Order Metrics
    total_orders INTEGER DEFAULT 0,
    total_spend DECIMAL(12,2) DEFAULT 0,
    average_order_value DECIMAL(10,2) DEFAULT 0,
    total_products_ordered INTEGER DEFAULT 0,
    total_units_ordered INTEGER DEFAULT 0,
    
    -- Delivery Performance
    orders_delivered_on_time INTEGER DEFAULT 0,
    orders_delivered_late INTEGER DEFAULT 0,
    orders_delivered_early INTEGER DEFAULT 0,
    on_time_delivery_rate DECIMAL(5,2) DEFAULT 0, -- Percentage
    average_delivery_days INTEGER DEFAULT 0,
    
    -- Quality Metrics
    total_units_received INTEGER DEFAULT 0,
    damaged_units INTEGER DEFAULT 0,
    missing_units INTEGER DEFAULT 0,
    quality_issue_rate DECIMAL(5,2) DEFAULT 0, -- Percentage
    
    -- Profitability Metrics
    total_profit_generated DECIMAL(12,2) DEFAULT 0,
    average_roi DECIMAL(5,2) DEFAULT 0,
    average_margin DECIMAL(5,2) DEFAULT 0,
    
    -- Scorecard Ratings (1-5 stars)
    delivery_rating DECIMAL(2,1) DEFAULT 0 CHECK (delivery_rating BETWEEN 0 AND 5),
    quality_rating DECIMAL(2,1) DEFAULT 0 CHECK (quality_rating BETWEEN 0 AND 5),
    profitability_rating DECIMAL(2,1) DEFAULT 0 CHECK (profitability_rating BETWEEN 0 AND 5),
    communication_rating DECIMAL(2,1) DEFAULT 0 CHECK (communication_rating BETWEEN 0 AND 5),
    overall_rating DECIMAL(2,1) DEFAULT 0 CHECK (overall_rating BETWEEN 0 AND 5),
    
    -- Best Sellers
    best_selling_products JSONB DEFAULT '[]', -- Array of product IDs with sales data
    
    -- Time Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_type TEXT DEFAULT 'all_time' CHECK (period_type IN ('all_time', 'year', 'quarter', 'month')),
    
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, supplier_id, period_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_supplier_performance_supplier ON supplier_performance(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_performance_user ON supplier_performance(user_id);
CREATE INDEX IF NOT EXISTS idx_supplier_performance_rating ON supplier_performance(overall_rating DESC);

-- ============================================
-- 2. ORDER VARIANCES
-- ============================================
-- Track ordered vs received quantities
CREATE TABLE IF NOT EXISTS order_variances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE CASCADE NOT NULL,
    supplier_order_item_id UUID REFERENCES supplier_order_items(id) ON DELETE CASCADE NOT NULL,
    
    -- Quantities
    ordered_quantity INTEGER NOT NULL,
    received_quantity INTEGER DEFAULT 0,
    variance_quantity INTEGER DEFAULT 0, -- received - ordered (positive = received more)
    
    -- Quality Issues
    damaged_quantity INTEGER DEFAULT 0,
    missing_quantity INTEGER DEFAULT 0,
    defective_quantity INTEGER DEFAULT 0,
    
    -- Cost Impact
    variance_amount DECIMAL(10,2) DEFAULT 0, -- Cost difference
    refund_amount DECIMAL(10,2) DEFAULT 0, -- Refund received for issues
    
    -- Notes
    notes TEXT,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_variances_order ON order_variances(supplier_order_id);
CREATE INDEX IF NOT EXISTS idx_order_variances_user ON order_variances(user_id);
CREATE INDEX IF NOT EXISTS idx_order_variances_unresolved ON order_variances(user_id, resolved) WHERE resolved = false;

-- ============================================
-- 3. HELPER FUNCTION: Calculate On-Time Rate
-- ============================================
CREATE OR REPLACE FUNCTION calculate_on_time_delivery_rate(
    p_supplier_id UUID,
    p_user_id UUID
)
RETURNS DECIMAL AS $$
DECLARE
    v_total_orders INTEGER;
    v_on_time_orders INTEGER;
    v_rate DECIMAL;
BEGIN
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE 
            actual_delivery_date IS NOT NULL 
            AND expected_delivery_date IS NOT NULL
            AND actual_delivery_date <= expected_delivery_date
        )
    INTO v_total_orders, v_on_time_orders
    FROM supplier_orders
    WHERE supplier_id = p_supplier_id
      AND user_id = p_user_id
      AND status IN ('received', 'completed');
    
    IF v_total_orders = 0 THEN
        RETURN 0;
    END IF;
    
    v_rate := (v_on_time_orders::DECIMAL / v_total_orders::DECIMAL) * 100;
    RETURN v_rate;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 4. HELPER FUNCTION: Calculate Overall Rating
-- ============================================
CREATE OR REPLACE FUNCTION calculate_overall_rating(
    p_delivery_rating DECIMAL,
    p_quality_rating DECIMAL,
    p_profitability_rating DECIMAL,
    p_communication_rating DECIMAL
)
RETURNS DECIMAL AS $$
DECLARE
    v_weights JSONB := '{"delivery": 0.3, "quality": 0.3, "profitability": 0.25, "communication": 0.15}'::JSONB;
    v_weighted_sum DECIMAL := 0;
BEGIN
    v_weighted_sum := 
        (p_delivery_rating * (v_weights->>'delivery')::DECIMAL) +
        (p_quality_rating * (v_weights->>'quality')::DECIMAL) +
        (p_profitability_rating * (v_weights->>'profitability')::DECIMAL) +
        (p_communication_rating * (v_weights->>'communication')::DECIMAL);
    
    RETURN ROUND(v_weighted_sum, 1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 5. COMMENTS
-- ============================================
COMMENT ON TABLE supplier_performance IS 'Aggregated performance metrics per supplier';
COMMENT ON TABLE order_variances IS 'Track ordered vs received quantities and quality issues';
COMMENT ON COLUMN supplier_performance.on_time_delivery_rate IS 'Percentage of orders delivered on or before expected date';
COMMENT ON COLUMN supplier_performance.quality_issue_rate IS 'Percentage of units with quality issues (damaged, missing, defective)';
COMMENT ON COLUMN order_variances.variance_quantity IS 'Received - Ordered (positive = received more, negative = received less)';

