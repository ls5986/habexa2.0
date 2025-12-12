-- HABEXA: Financial Transaction Tracking
-- Complete P&L, transaction history, and reporting

-- ============================================
-- 1. FINANCIAL TRANSACTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS financial_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Transaction Type
    transaction_type TEXT NOT NULL CHECK (transaction_type IN (
        'purchase',        -- Buying from supplier
        'sale',            -- Amazon sales
        'fee',             -- Amazon fees (FBA, referral)
        'shipping',        -- Shipping costs
        'tpl_fee',         -- 3PL/prep center fees
        'refund',          -- Customer refunds
        'reimbursement',   -- Amazon reimbursements
        'adjustment'       -- Manual adjustments
    )),
    
    -- Amount
    amount DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    
    -- Quantity (for purchase/sale)
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    
    -- Links
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE SET NULL,
    sale_id TEXT, -- Amazon sale ID or order ID
    
    -- Transaction Details
    description TEXT,
    category TEXT, -- 'product_cost', 'prep_cost', 'shipping_cost', 'amazon_fee'
    
    -- Dates
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    posted_date DATE, -- When it actually posted to account
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_financial_transactions_user ON financial_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_type ON financial_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_date ON financial_transactions(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_product ON financial_transactions(product_id);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_order ON financial_transactions(supplier_order_id);

-- ============================================
-- 2. P&L SUMMARIES (Monthly Aggregations)
-- ============================================
CREATE TABLE IF NOT EXISTS pl_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_type TEXT DEFAULT 'month' CHECK (period_type IN ('month', 'quarter', 'year')),
    
    -- Revenue
    total_revenue DECIMAL(12,2) DEFAULT 0,
    total_sales_count INTEGER DEFAULT 0,
    
    -- COGS (Cost of Goods Sold)
    total_cogs DECIMAL(12,2) DEFAULT 0,
    total_purchases DECIMAL(12,2) DEFAULT 0,
    
    -- Expenses
    total_amazon_fees DECIMAL(12,2) DEFAULT 0,
    total_shipping_costs DECIMAL(12,2) DEFAULT 0,
    total_tpl_fees DECIMAL(12,2) DEFAULT 0,
    total_other_expenses DECIMAL(12,2) DEFAULT 0,
    
    -- Adjustments
    total_refunds DECIMAL(12,2) DEFAULT 0,
    total_reimbursements DECIMAL(12,2) DEFAULT 0,
    
    -- Net
    net_profit DECIMAL(12,2) DEFAULT 0,
    profit_margin DECIMAL(5,2) DEFAULT 0, -- Percentage
    
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, period_start, period_end, period_type)
);

CREATE INDEX IF NOT EXISTS idx_pl_summaries_user ON pl_summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_pl_summaries_period ON pl_summaries(period_start DESC);

-- ============================================
-- 3. HELPER FUNCTION: Calculate P&L for Period
-- ============================================
CREATE OR REPLACE FUNCTION calculate_pl_summary(
    p_user_id UUID,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    total_revenue DECIMAL,
    total_cogs DECIMAL,
    total_fees DECIMAL,
    total_shipping DECIMAL,
    total_tpl DECIMAL,
    total_refunds DECIMAL,
    total_reimbursements DECIMAL,
    net_profit DECIMAL,
    profit_margin DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'sale'), 0) as total_revenue,
        COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'purchase'), 0) as total_cogs,
        COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'fee'), 0) as total_fees,
        COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'shipping'), 0) as total_shipping,
        COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'tpl_fee'), 0) as total_tpl,
        COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'refund'), 0) as total_refunds,
        COALESCE(SUM(amount) FILTER (WHERE transaction_type = 'reimbursement'), 0) as total_reimbursements,
        COALESCE(
            SUM(amount) FILTER (WHERE transaction_type = 'sale') +
            SUM(amount) FILTER (WHERE transaction_type = 'reimbursement') -
            SUM(amount) FILTER (WHERE transaction_type = 'purchase') -
            SUM(amount) FILTER (WHERE transaction_type = 'fee') -
            SUM(amount) FILTER (WHERE transaction_type = 'shipping') -
            SUM(amount) FILTER (WHERE transaction_type = 'tpl_fee') -
            SUM(amount) FILTER (WHERE transaction_type = 'refund'),
            0
        ) as net_profit,
        CASE 
            WHEN SUM(amount) FILTER (WHERE transaction_type = 'sale') > 0 THEN
                ((
                    SUM(amount) FILTER (WHERE transaction_type = 'sale') +
                    SUM(amount) FILTER (WHERE transaction_type = 'reimbursement') -
                    SUM(amount) FILTER (WHERE transaction_type = 'purchase') -
                    SUM(amount) FILTER (WHERE transaction_type = 'fee') -
                    SUM(amount) FILTER (WHERE transaction_type = 'shipping') -
                    SUM(amount) FILTER (WHERE transaction_type = 'tpl_fee') -
                    SUM(amount) FILTER (WHERE transaction_type = 'refund')
                ) / SUM(amount) FILTER (WHERE transaction_type = 'sale')) * 100
            ELSE 0
        END as profit_margin
    FROM financial_transactions
    WHERE user_id = p_user_id
      AND transaction_date BETWEEN p_start_date AND p_end_date;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 4. COMMENTS
-- ============================================
COMMENT ON TABLE financial_transactions IS 'All financial transactions (purchases, sales, fees, etc.)';
COMMENT ON TABLE pl_summaries IS 'Monthly/quarterly/yearly P&L summaries';
COMMENT ON COLUMN financial_transactions.amount IS 'Positive for revenue/reimbursements, negative for costs/fees/refunds';
COMMENT ON FUNCTION calculate_pl_summary IS 'Calculates P&L summary for a date range';

