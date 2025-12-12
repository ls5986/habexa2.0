-- HABEXA: Inventory Forecasting System
-- Daily inventory snapshots, sales velocity, reorder points, stockout alerts

-- ============================================
-- 1. INVENTORY SNAPSHOTS
-- ============================================
-- Daily snapshots of FBA inventory levels
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    
    -- Snapshot Date
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- FBA Inventory Levels (from SP-API)
    fba_fulfillable_qty INTEGER DEFAULT 0,
    fba_inbound_working_qty INTEGER DEFAULT 0,
    fba_inbound_shipped_qty INTEGER DEFAULT 0,
    fba_reserved_qty INTEGER DEFAULT 0,
    fba_unsellable_qty INTEGER DEFAULT 0,
    fba_total_qty INTEGER DEFAULT 0, -- Sum of above
    
    -- Calculated Fields
    available_qty INTEGER DEFAULT 0, -- fulfillable (sellable now)
    total_inbound_qty INTEGER DEFAULT 0, -- working + shipped (on the way)
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, product_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_product ON inventory_snapshots(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_date ON inventory_snapshots(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_user ON inventory_snapshots(user_id);

-- ============================================
-- 2. INVENTORY FORECASTS
-- ============================================
-- Calculated forecasts and sales velocity
CREATE TABLE IF NOT EXISTS inventory_forecasts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    
    -- Sales Velocity
    avg_daily_sales DECIMAL(10,2) DEFAULT 0,
    sales_velocity_7d DECIMAL(10,2) DEFAULT 0,
    sales_velocity_30d DECIMAL(10,2) DEFAULT 0,
    sales_velocity_90d DECIMAL(10,2) DEFAULT 0,
    
    -- Reorder Point Calculation
    lead_time_days INTEGER DEFAULT 14, -- Days from order to FBA
    safety_stock_days INTEGER DEFAULT 7, -- Safety buffer
    reorder_point INTEGER DEFAULT 0, -- (avg_daily_sales × lead_time) + safety_stock
    
    -- Optimal Order Quantity
    months_coverage DECIMAL(3,1) DEFAULT 2.0, -- How many months to order
    optimal_order_qty INTEGER DEFAULT 0, -- (monthly_sales × months) - current - inbound
    
    -- Days Remaining
    current_fba_qty INTEGER DEFAULT 0, -- Latest snapshot
    days_of_inventory_remaining DECIMAL(5,1) DEFAULT 0, -- current ÷ avg_daily_sales
    projected_stockout_date DATE, -- CURRENT_DATE + days_remaining
    
    -- Status
    status TEXT DEFAULT 'healthy' CHECK (status IN (
        'out_of_stock',    -- 0 units
        'reorder_now',     -- Below reorder point
        'low_stock',       -- 10-20 days remaining
        'healthy',         -- 30+ days remaining
        'overstock'        -- 90+ days remaining
    )),
    
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_forecasts_product ON inventory_forecasts(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_forecasts_status ON inventory_forecasts(status);
CREATE INDEX IF NOT EXISTS idx_inventory_forecasts_user ON inventory_forecasts(user_id);
CREATE INDEX IF NOT EXISTS idx_inventory_forecasts_days_remaining ON inventory_forecasts(days_of_inventory_remaining);

-- ============================================
-- 3. REORDER ALERTS
-- ============================================
-- Alerts for products needing reorder
CREATE TABLE IF NOT EXISTS reorder_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    
    -- Alert Details
    alert_type TEXT NOT NULL CHECK (alert_type IN (
        'reorder_point',   -- Below reorder point
        'out_of_stock',    -- 0 units
        'overstock',       -- 90+ days inventory
        'slow_moving'      -- No sales in 30 days
    )),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Message
    message TEXT NOT NULL,
    suggested_order_qty INTEGER,
    estimated_stockout_date DATE,
    
    -- User Actions
    is_read BOOLEAN DEFAULT false,
    is_dismissed BOOLEAN DEFAULT false,
    is_actioned BOOLEAN DEFAULT false, -- User created order
    actioned_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, product_id, alert_type, created_at::DATE)
);

CREATE INDEX IF NOT EXISTS idx_reorder_alerts_user ON reorder_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_reorder_alerts_product ON reorder_alerts(product_id);
CREATE INDEX IF NOT EXISTS idx_reorder_alerts_unread ON reorder_alerts(user_id, is_read) WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_reorder_alerts_severity ON reorder_alerts(severity);

-- ============================================
-- 4. HELPER FUNCTION: Calculate Reorder Point
-- ============================================
CREATE OR REPLACE FUNCTION calculate_reorder_point(
    p_avg_daily_sales DECIMAL,
    p_lead_time_days INTEGER DEFAULT 14,
    p_safety_stock_days INTEGER DEFAULT 7
)
RETURNS INTEGER AS $$
DECLARE
    v_safety_stock INTEGER;
    v_reorder_point INTEGER;
BEGIN
    v_safety_stock := CEIL(p_avg_daily_sales * p_safety_stock_days);
    v_reorder_point := CEIL(p_avg_daily_sales * p_lead_time_days) + v_safety_stock;
    RETURN v_reorder_point;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 5. HELPER FUNCTION: Calculate Days Remaining
-- ============================================
CREATE OR REPLACE FUNCTION calculate_days_remaining(
    p_current_qty INTEGER,
    p_avg_daily_sales DECIMAL
)
RETURNS DECIMAL AS $$
BEGIN
    IF p_avg_daily_sales <= 0 THEN
        RETURN 999; -- Infinite if no sales
    END IF;
    RETURN p_current_qty / p_avg_daily_sales;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 6. HELPER FUNCTION: Calculate Inventory Status
-- ============================================
CREATE OR REPLACE FUNCTION calculate_inventory_status(
    p_current_qty INTEGER,
    p_days_remaining DECIMAL,
    p_reorder_point INTEGER
)
RETURNS TEXT AS $$
BEGIN
    IF p_current_qty = 0 THEN
        RETURN 'out_of_stock';
    ELSIF p_current_qty < p_reorder_point THEN
        RETURN 'reorder_now';
    ELSIF p_days_remaining < 10 THEN
        RETURN 'low_stock';
    ELSIF p_days_remaining > 90 THEN
        RETURN 'overstock';
    ELSE
        RETURN 'healthy';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 7. COMMENTS
-- ============================================
COMMENT ON TABLE inventory_snapshots IS 'Daily snapshots of FBA inventory levels from SP-API';
COMMENT ON TABLE inventory_forecasts IS 'Calculated sales velocity, reorder points, and inventory status';
COMMENT ON TABLE reorder_alerts IS 'Alerts for products needing reorder or attention';
COMMENT ON COLUMN inventory_forecasts.reorder_point IS 'Calculated: (avg_daily_sales × lead_time_days) + safety_stock';
COMMENT ON COLUMN inventory_forecasts.optimal_order_qty IS 'Suggested order quantity to maintain healthy inventory';
COMMENT ON COLUMN inventory_forecasts.days_of_inventory_remaining IS 'Days until stockout: current_qty ÷ avg_daily_sales';

