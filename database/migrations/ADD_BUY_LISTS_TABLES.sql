-- ============================================================================
-- BUY LISTS SYSTEM - Phase 2 Implementation
-- ============================================================================
-- This migration creates the proper buy_lists and buy_list_items tables
-- to support multiple buy lists per user with detailed item tracking.

-- Drop existing buy_list_items if it exists (from old schema)
DROP TABLE IF EXISTS buy_list_items CASCADE;

-- Drop existing buy_lists if it exists (to recreate with proper schema)
DROP TABLE IF EXISTS buy_lists CASCADE;

-- Create buy_lists table
CREATE TABLE buy_lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'ordered', 'received', 'archived')),
    
    -- Summary metrics (calculated)
    total_products INTEGER DEFAULT 0,
    total_units INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 2) DEFAULT 0,
    expected_revenue DECIMAL(10, 2) DEFAULT 0,
    expected_profit DECIMAL(10, 2) DEFAULT 0,
    expected_roi DECIMAL(10, 2) DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create buy_list_items table
CREATE TABLE buy_list_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    buy_list_id UUID REFERENCES buy_lists(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    product_source_id UUID REFERENCES product_sources(id) ON DELETE SET NULL,
    
    -- Quantity and pricing
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost DECIMAL(10, 2) NOT NULL,
    total_cost DECIMAL(10, 2) NOT NULL,
    
    -- Expected profitability (from product at time of adding)
    expected_sell_price DECIMAL(10, 2),
    expected_profit DECIMAL(10, 2),
    expected_roi DECIMAL(10, 2),
    expected_margin DECIMAL(10, 2),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one item per product per buy list
    UNIQUE(buy_list_id, product_id, product_source_id)
);

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_buy_lists_user_id;
DROP INDEX IF EXISTS idx_buy_lists_status;
DROP INDEX IF EXISTS idx_buy_lists_created_at;
DROP INDEX IF EXISTS idx_buy_list_items_buy_list_id;
DROP INDEX IF EXISTS idx_buy_list_items_product_id;
DROP INDEX IF EXISTS idx_buy_list_items_product_source_id;

-- Create indexes for performance
CREATE INDEX idx_buy_lists_user_id ON buy_lists(user_id);
CREATE INDEX idx_buy_lists_status ON buy_lists(status);
CREATE INDEX idx_buy_lists_created_at ON buy_lists(created_at DESC);

CREATE INDEX idx_buy_list_items_buy_list_id ON buy_list_items(buy_list_id);
CREATE INDEX idx_buy_list_items_product_id ON buy_list_items(product_id);
CREATE INDEX idx_buy_list_items_product_source_id ON buy_list_items(product_source_id);

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS update_buy_list_summary() CASCADE;

-- Create function to update buy_list summary metrics
CREATE FUNCTION update_buy_list_summary()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE buy_lists
    SET
        total_products = (
            SELECT COUNT(DISTINCT product_id)
            FROM buy_list_items
            WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
        ),
        total_units = (
            SELECT COALESCE(SUM(quantity), 0)
            FROM buy_list_items
            WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
        ),
        total_cost = (
            SELECT COALESCE(SUM(total_cost), 0)
            FROM buy_list_items
            WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
        ),
        expected_revenue = (
            SELECT COALESCE(SUM(quantity * expected_sell_price), 0)
            FROM buy_list_items
            WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
            AND expected_sell_price IS NOT NULL
        ),
        expected_profit = (
            SELECT COALESCE(SUM(expected_profit), 0)
            FROM buy_list_items
            WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
            AND expected_profit IS NOT NULL
        ),
        expected_roi = CASE
            WHEN (
                SELECT COALESCE(SUM(total_cost), 0)
                FROM buy_list_items
                WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
            ) > 0 THEN
                (
                    SELECT COALESCE(SUM(expected_profit), 0)
                    FROM buy_list_items
                    WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
                    AND expected_profit IS NOT NULL
                ) / (
                    SELECT COALESCE(SUM(total_cost), 0)
                    FROM buy_list_items
                    WHERE buy_list_id = COALESCE(NEW.buy_list_id, OLD.buy_list_id)
                ) * 100
            ELSE 0
        END,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.buy_list_id, OLD.buy_list_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS trigger_update_buy_list_summary_insert ON buy_list_items;
DROP TRIGGER IF EXISTS trigger_update_buy_list_summary_update ON buy_list_items;
DROP TRIGGER IF EXISTS trigger_update_buy_list_summary_delete ON buy_list_items;

-- Create triggers to auto-update summary metrics
CREATE TRIGGER trigger_update_buy_list_summary_insert
    AFTER INSERT ON buy_list_items
    FOR EACH ROW
    EXECUTE FUNCTION update_buy_list_summary();

CREATE TRIGGER trigger_update_buy_list_summary_update
    AFTER UPDATE ON buy_list_items
    FOR EACH ROW
    EXECUTE FUNCTION update_buy_list_summary();

CREATE TRIGGER trigger_update_buy_list_summary_delete
    AFTER DELETE ON buy_list_items
    FOR EACH ROW
    EXECUTE FUNCTION update_buy_list_summary();

-- Enable RLS (Row Level Security)
ALTER TABLE buy_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE buy_list_items ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own buy lists" ON buy_lists;
DROP POLICY IF EXISTS "Users can create their own buy lists" ON buy_lists;
DROP POLICY IF EXISTS "Users can update their own buy lists" ON buy_lists;
DROP POLICY IF EXISTS "Users can delete their own buy lists" ON buy_lists;
DROP POLICY IF EXISTS "Users can view items in their buy lists" ON buy_list_items;
DROP POLICY IF EXISTS "Users can add items to their buy lists" ON buy_list_items;
DROP POLICY IF EXISTS "Users can update items in their buy lists" ON buy_list_items;
DROP POLICY IF EXISTS "Users can delete items from their buy lists" ON buy_list_items;

-- RLS Policies for buy_lists
CREATE POLICY "Users can view their own buy lists"
    ON buy_lists FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own buy lists"
    ON buy_lists FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own buy lists"
    ON buy_lists FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own buy lists"
    ON buy_lists FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for buy_list_items
CREATE POLICY "Users can view items in their buy lists"
    ON buy_list_items FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM buy_lists
            WHERE buy_lists.id = buy_list_items.buy_list_id
            AND buy_lists.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add items to their buy lists"
    ON buy_list_items FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM buy_lists
            WHERE buy_lists.id = buy_list_items.buy_list_id
            AND buy_lists.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update items in their buy lists"
    ON buy_list_items FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM buy_lists
            WHERE buy_lists.id = buy_list_items.buy_list_id
            AND buy_lists.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete items from their buy lists"
    ON buy_list_items FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM buy_lists
            WHERE buy_lists.id = buy_list_items.buy_list_id
            AND buy_lists.user_id = auth.uid()
        )
    );

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON buy_lists TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON buy_list_items TO authenticated;

-- Comments
COMMENT ON TABLE buy_lists IS 'User-created buy lists for grouping products to purchase';
COMMENT ON TABLE buy_list_items IS 'Individual products/quantities within a buy list';
COMMENT ON COLUMN buy_lists.status IS 'draft: being created, approved: ready to order, ordered: sent to supplier, received: inventory received, archived: completed';
COMMENT ON COLUMN buy_list_items.unit_cost IS 'Cost per unit from product_source at time of adding to buy list';
COMMENT ON COLUMN buy_list_items.expected_sell_price IS 'Expected selling price from product at time of adding';

