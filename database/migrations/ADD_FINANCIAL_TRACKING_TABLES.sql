-- ============================================================================
-- FINANCIAL TRACKING & ROI ANALYSIS - Financial Dashboard Implementation
-- ============================================================================
-- This migration creates tables for tracking costs, sales, and ROI across
-- the entire workflow from supplier orders to FBA sales.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS financial_summaries CASCADE;
DROP TABLE IF EXISTS cost_tracking CASCADE;
DROP TABLE IF EXISTS sales_tracking CASCADE;

-- Create financial_summaries table (aggregated financial data per product/order)
CREATE TABLE financial_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Links to workflow entities
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    product_source_id UUID REFERENCES product_sources(id) ON DELETE SET NULL,
    buy_list_id UUID REFERENCES buy_lists(id) ON DELETE SET NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE SET NULL,
    tpl_inbound_id UUID REFERENCES tpl_inbounds(id) ON DELETE SET NULL,
    fba_shipment_id UUID REFERENCES fba_shipments(id) ON DELETE SET NULL,
    
    -- Cost breakdown (aggregated from workflow)
    supplier_cost DECIMAL(10, 2) DEFAULT 0, -- Cost from supplier order
    tpl_prep_cost DECIMAL(10, 2) DEFAULT 0, -- 3PL prep fees
    tpl_storage_cost DECIMAL(10, 2) DEFAULT 0, -- 3PL storage fees
    shipping_cost DECIMAL(10, 2) DEFAULT 0, -- Shipping to 3PL and to Amazon
    fba_fees DECIMAL(10, 2) DEFAULT 0, -- FBA fulfillment fees
    referral_fee DECIMAL(10, 2) DEFAULT 0, -- Amazon referral fees
    other_fees DECIMAL(10, 2) DEFAULT 0, -- Other Amazon fees
    total_cost DECIMAL(10, 2) DEFAULT 0, -- Total landed cost
    
    -- Revenue and profit
    sell_price DECIMAL(10, 2), -- Actual or expected sell price
    revenue DECIMAL(10, 2) DEFAULT 0, -- Actual revenue from sales
    profit DECIMAL(10, 2) DEFAULT 0, -- revenue - total_cost
    roi_percentage DECIMAL(10, 2), -- (profit / total_cost) * 100
    margin_percentage DECIMAL(10, 2), -- (profit / revenue) * 100
    
    -- Sales tracking
    units_sold INTEGER DEFAULT 0, -- Actual units sold
    units_in_stock INTEGER DEFAULT 0, -- Units currently in FBA
    units_shipped INTEGER DEFAULT 0, -- Units shipped to Amazon
    
    -- Time periods
    period_start DATE, -- Start of tracking period
    period_end DATE, -- End of tracking period
    period_type VARCHAR(50) DEFAULT 'lifetime', -- 'lifetime', 'monthly', 'quarterly', 'yearly'
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one summary per product per period
    UNIQUE(user_id, product_id, product_source_id, period_start, period_type)
);

-- Create cost_tracking table (detailed cost line items)
CREATE TABLE cost_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    financial_summary_id UUID REFERENCES financial_summaries(id) ON DELETE CASCADE,
    
    -- Cost details
    cost_type VARCHAR(50) NOT NULL, -- 'supplier', 'tpl_prep', 'tpl_storage', 'shipping', 'fba_fee', 'referral_fee', 'other'
    cost_category VARCHAR(50), -- 'product_cost', 'prep_cost', 'shipping_cost', 'amazon_fee'
    description TEXT,
    amount DECIMAL(10, 2) NOT NULL,
    quantity INTEGER DEFAULT 1, -- Quantity this cost applies to
    unit_cost DECIMAL(10, 2), -- amount / quantity
    
    -- Links to source entities
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE SET NULL,
    tpl_inbound_id UUID REFERENCES tpl_inbounds(id) ON DELETE SET NULL,
    fba_shipment_id UUID REFERENCES fba_shipments(id) ON DELETE SET NULL,
    
    -- Dates
    cost_date DATE NOT NULL, -- When cost was incurred
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create sales_tracking table (actual sales data from Amazon)
CREATE TABLE sales_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    financial_summary_id UUID REFERENCES financial_summaries(id) ON DELETE SET NULL,
    
    -- Sales details
    asin VARCHAR(20) NOT NULL,
    order_date DATE NOT NULL,
    sale_price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER DEFAULT 1,
    total_revenue DECIMAL(10, 2) NOT NULL, -- sale_price * quantity
    
    -- Amazon fees (from settlement report)
    fba_fee DECIMAL(10, 2) DEFAULT 0,
    referral_fee DECIMAL(10, 2) DEFAULT 0,
    other_fees DECIMAL(10, 2) DEFAULT 0,
    total_fees DECIMAL(10, 2) DEFAULT 0,
    
    -- Net revenue
    net_revenue DECIMAL(10, 2) NOT NULL, -- total_revenue - total_fees
    
    -- Amazon order ID
    amazon_order_id VARCHAR(255),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_financial_summaries_user_id;
DROP INDEX IF EXISTS idx_financial_summaries_product_id;
DROP INDEX IF EXISTS idx_financial_summaries_supplier_order_id;
DROP INDEX IF EXISTS idx_financial_summaries_period;
DROP INDEX IF EXISTS idx_cost_tracking_user_id;
DROP INDEX IF EXISTS idx_cost_tracking_financial_summary_id;
DROP INDEX IF EXISTS idx_cost_tracking_cost_type;
DROP INDEX IF EXISTS idx_cost_tracking_cost_date;
DROP INDEX IF EXISTS idx_sales_tracking_user_id;
DROP INDEX IF EXISTS idx_sales_tracking_product_id;
DROP INDEX IF EXISTS idx_sales_tracking_order_date;
DROP INDEX IF EXISTS idx_sales_tracking_asin;

-- Create indexes for performance
CREATE INDEX idx_financial_summaries_user_id ON financial_summaries(user_id);
CREATE INDEX idx_financial_summaries_product_id ON financial_summaries(product_id);
CREATE INDEX idx_financial_summaries_supplier_order_id ON financial_summaries(supplier_order_id);
CREATE INDEX idx_financial_summaries_period ON financial_summaries(period_start, period_end, period_type);

CREATE INDEX idx_cost_tracking_user_id ON cost_tracking(user_id);
CREATE INDEX idx_cost_tracking_financial_summary_id ON cost_tracking(financial_summary_id);
CREATE INDEX idx_cost_tracking_cost_type ON cost_tracking(cost_type);
CREATE INDEX idx_cost_tracking_cost_date ON cost_tracking(cost_date);

CREATE INDEX idx_sales_tracking_user_id ON sales_tracking(user_id);
CREATE INDEX idx_sales_tracking_product_id ON sales_tracking(product_id);
CREATE INDEX idx_sales_tracking_order_date ON sales_tracking(order_date);
CREATE INDEX idx_sales_tracking_asin ON sales_tracking(asin);

-- Enable RLS (Row Level Security)
ALTER TABLE financial_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_tracking ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own financial summaries" ON financial_summaries;
DROP POLICY IF EXISTS "Users can create their own financial summaries" ON financial_summaries;
DROP POLICY IF EXISTS "Users can update their own financial summaries" ON financial_summaries;
DROP POLICY IF EXISTS "Users can delete their own financial summaries" ON financial_summaries;
DROP POLICY IF EXISTS "Users can view their own cost tracking" ON cost_tracking;
DROP POLICY IF EXISTS "Users can create their own cost tracking" ON cost_tracking;
DROP POLICY IF EXISTS "Users can update their own cost tracking" ON cost_tracking;
DROP POLICY IF EXISTS "Users can delete their own cost tracking" ON cost_tracking;
DROP POLICY IF EXISTS "Users can view their own sales tracking" ON sales_tracking;
DROP POLICY IF EXISTS "Users can create their own sales tracking" ON sales_tracking;
DROP POLICY IF EXISTS "Users can update their own sales tracking" ON sales_tracking;
DROP POLICY IF EXISTS "Users can delete their own sales tracking" ON sales_tracking;

-- RLS Policies for financial_summaries
CREATE POLICY "Users can view their own financial summaries"
    ON financial_summaries FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own financial summaries"
    ON financial_summaries FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own financial summaries"
    ON financial_summaries FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own financial summaries"
    ON financial_summaries FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for cost_tracking
CREATE POLICY "Users can view their own cost tracking"
    ON cost_tracking FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own cost tracking"
    ON cost_tracking FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own cost tracking"
    ON cost_tracking FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own cost tracking"
    ON cost_tracking FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for sales_tracking
CREATE POLICY "Users can view their own sales tracking"
    ON sales_tracking FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own sales tracking"
    ON sales_tracking FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own sales tracking"
    ON sales_tracking FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own sales tracking"
    ON sales_tracking FOR DELETE
    USING (auth.uid() = user_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON financial_summaries TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON cost_tracking TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON sales_tracking TO authenticated;

-- Comments
COMMENT ON TABLE financial_summaries IS 'Aggregated financial data per product/order across the entire workflow';
COMMENT ON TABLE cost_tracking IS 'Detailed cost line items for tracking all costs incurred';
COMMENT ON TABLE sales_tracking IS 'Actual sales data from Amazon for revenue tracking';
COMMENT ON COLUMN financial_summaries.total_cost IS 'Sum of all costs: supplier + prep + storage + shipping + fees';
COMMENT ON COLUMN financial_summaries.profit IS 'revenue - total_cost';
COMMENT ON COLUMN financial_summaries.roi_percentage IS '(profit / total_cost) * 100';
COMMENT ON COLUMN financial_summaries.margin_percentage IS '(profit / revenue) * 100';
COMMENT ON COLUMN cost_tracking.cost_type IS 'Type of cost: supplier, tpl_prep, tpl_storage, shipping, fba_fee, referral_fee, other';

