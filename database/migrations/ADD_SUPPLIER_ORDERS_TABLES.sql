-- ============================================================================
-- SUPPLIER ORDERS SYSTEM - Phase 3 Implementation
-- ============================================================================
-- This migration creates supplier_orders and supplier_order_items tables
-- to support creating orders from buy lists, grouped by supplier.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS supplier_order_items CASCADE;
DROP TABLE IF EXISTS supplier_orders CASCADE;

-- Create supplier_orders table
CREATE TABLE supplier_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    buy_list_id UUID REFERENCES buy_lists(id) ON DELETE SET NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    
    -- Order details
    order_number VARCHAR(255), -- Supplier's order number (filled after sending)
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'confirmed', 'in_transit', 'received', 'cancelled')),
    
    -- Summary metrics (calculated)
    total_products INTEGER DEFAULT 0,
    total_units INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 2) DEFAULT 0,
    expected_revenue DECIMAL(10, 2) DEFAULT 0,
    expected_profit DECIMAL(10, 2) DEFAULT 0,
    expected_roi DECIMAL(10, 2) DEFAULT 0,
    
    -- Shipping and dates
    shipping_method VARCHAR(255),
    estimated_delivery_date DATE,
    sent_date TIMESTAMPTZ,
    received_date TIMESTAMPTZ,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create supplier_order_items table
CREATE TABLE supplier_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE CASCADE NOT NULL,
    buy_list_item_id UUID REFERENCES buy_list_items(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    product_source_id UUID REFERENCES product_sources(id) ON DELETE SET NULL,
    
    -- Quantity and pricing (snapshot at time of order creation)
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost DECIMAL(10, 2) NOT NULL,
    total_cost DECIMAL(10, 2) NOT NULL,
    
    -- Expected profitability (from product at time of order creation)
    expected_sell_price DECIMAL(10, 2),
    expected_profit DECIMAL(10, 2),
    expected_roi DECIMAL(10, 2),
    expected_margin DECIMAL(10, 2),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one item per product per order
    UNIQUE(supplier_order_id, product_id, product_source_id)
);

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_supplier_orders_user_id;
DROP INDEX IF EXISTS idx_supplier_orders_supplier_id;
DROP INDEX IF EXISTS idx_supplier_orders_buy_list_id;
DROP INDEX IF EXISTS idx_supplier_orders_status;
DROP INDEX IF EXISTS idx_supplier_orders_created_at;
DROP INDEX IF EXISTS idx_supplier_order_items_order_id;
DROP INDEX IF EXISTS idx_supplier_order_items_product_id;
DROP INDEX IF EXISTS idx_supplier_order_items_buy_list_item_id;

-- Create indexes for performance
CREATE INDEX idx_supplier_orders_user_id ON supplier_orders(user_id);
CREATE INDEX idx_supplier_orders_supplier_id ON supplier_orders(supplier_id);
CREATE INDEX idx_supplier_orders_buy_list_id ON supplier_orders(buy_list_id);
CREATE INDEX idx_supplier_orders_status ON supplier_orders(status);
CREATE INDEX idx_supplier_orders_created_at ON supplier_orders(created_at DESC);

CREATE INDEX idx_supplier_order_items_order_id ON supplier_order_items(supplier_order_id);
CREATE INDEX idx_supplier_order_items_product_id ON supplier_order_items(product_id);
CREATE INDEX idx_supplier_order_items_buy_list_item_id ON supplier_order_items(buy_list_item_id);

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS update_supplier_order_summary() CASCADE;

-- Create function to update supplier_order summary metrics
CREATE FUNCTION update_supplier_order_summary()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE supplier_orders
    SET
        total_products = (
            SELECT COUNT(DISTINCT product_id)
            FROM supplier_order_items
            WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
        ),
        total_units = (
            SELECT COALESCE(SUM(quantity), 0)
            FROM supplier_order_items
            WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
        ),
        total_cost = (
            SELECT COALESCE(SUM(total_cost), 0)
            FROM supplier_order_items
            WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
        ),
        expected_revenue = (
            SELECT COALESCE(SUM(quantity * expected_sell_price), 0)
            FROM supplier_order_items
            WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
            AND expected_sell_price IS NOT NULL
        ),
        expected_profit = (
            SELECT COALESCE(SUM(expected_profit), 0)
            FROM supplier_order_items
            WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
            AND expected_profit IS NOT NULL
        ),
        expected_roi = CASE
            WHEN (
                SELECT COALESCE(SUM(total_cost), 0)
                FROM supplier_order_items
                WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
            ) > 0 THEN
                (
                    SELECT COALESCE(SUM(expected_profit), 0)
                    FROM supplier_order_items
                    WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
                    AND expected_profit IS NOT NULL
                ) / (
                    SELECT COALESCE(SUM(total_cost), 0)
                    FROM supplier_order_items
                    WHERE supplier_order_id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id)
                ) * 100
            ELSE 0
        END,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.supplier_order_id, OLD.supplier_order_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS trigger_update_supplier_order_summary_insert ON supplier_order_items;
DROP TRIGGER IF EXISTS trigger_update_supplier_order_summary_update ON supplier_order_items;
DROP TRIGGER IF EXISTS trigger_update_supplier_order_summary_delete ON supplier_order_items;

-- Create triggers to auto-update summary metrics
CREATE TRIGGER trigger_update_supplier_order_summary_insert
    AFTER INSERT ON supplier_order_items
    FOR EACH ROW
    EXECUTE FUNCTION update_supplier_order_summary();

CREATE TRIGGER trigger_update_supplier_order_summary_update
    AFTER UPDATE ON supplier_order_items
    FOR EACH ROW
    EXECUTE FUNCTION update_supplier_order_summary();

CREATE TRIGGER trigger_update_supplier_order_summary_delete
    AFTER DELETE ON supplier_order_items
    FOR EACH ROW
    EXECUTE FUNCTION update_supplier_order_summary();

-- Enable RLS (Row Level Security)
ALTER TABLE supplier_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_order_items ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own supplier orders" ON supplier_orders;
DROP POLICY IF EXISTS "Users can create their own supplier orders" ON supplier_orders;
DROP POLICY IF EXISTS "Users can update their own supplier orders" ON supplier_orders;
DROP POLICY IF EXISTS "Users can delete their own supplier orders" ON supplier_orders;
DROP POLICY IF EXISTS "Users can view items in their supplier orders" ON supplier_order_items;
DROP POLICY IF EXISTS "Users can add items to their supplier orders" ON supplier_order_items;
DROP POLICY IF EXISTS "Users can update items in their supplier orders" ON supplier_order_items;
DROP POLICY IF EXISTS "Users can delete items from their supplier orders" ON supplier_order_items;

-- RLS Policies for supplier_orders
CREATE POLICY "Users can view their own supplier orders"
    ON supplier_orders FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own supplier orders"
    ON supplier_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own supplier orders"
    ON supplier_orders FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own supplier orders"
    ON supplier_orders FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for supplier_order_items
CREATE POLICY "Users can view items in their supplier orders"
    ON supplier_order_items FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM supplier_orders
            WHERE supplier_orders.id = supplier_order_items.supplier_order_id
            AND supplier_orders.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add items to their supplier orders"
    ON supplier_order_items FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM supplier_orders
            WHERE supplier_orders.id = supplier_order_items.supplier_order_id
            AND supplier_orders.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update items in their supplier orders"
    ON supplier_order_items FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM supplier_orders
            WHERE supplier_orders.id = supplier_order_items.supplier_order_id
            AND supplier_orders.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete items from their supplier orders"
    ON supplier_order_items FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM supplier_orders
            WHERE supplier_orders.id = supplier_order_items.supplier_order_id
            AND supplier_orders.user_id = auth.uid()
        )
    );

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON supplier_orders TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON supplier_order_items TO authenticated;

-- Comments
COMMENT ON TABLE supplier_orders IS 'Orders sent to suppliers, created from buy lists';
COMMENT ON TABLE supplier_order_items IS 'Individual products/quantities within a supplier order';
COMMENT ON COLUMN supplier_orders.status IS 'draft: being created, sent: sent to supplier, confirmed: supplier confirmed, in_transit: shipping, received: inventory received, cancelled: cancelled';
COMMENT ON COLUMN supplier_orders.buy_list_id IS 'Reference to the buy list this order was created from';
COMMENT ON COLUMN supplier_order_items.buy_list_item_id IS 'Reference to the buy list item this order item came from';
COMMENT ON COLUMN supplier_order_items.unit_cost IS 'Cost per unit from product_source at time of order creation (snapshot)';

