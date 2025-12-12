-- ============================================================================
-- 3PL (THIRD-PARTY LOGISTICS) INTEGRATION - Phase 4 Implementation
-- ============================================================================
-- This migration creates tables for managing 3PL warehouses, inbound shipments,
-- and tracking inventory through the 3PL process.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS tpl_inbound_items CASCADE;
DROP TABLE IF EXISTS tpl_inbounds CASCADE;
DROP TABLE IF EXISTS tpl_warehouses CASCADE;

-- Create tpl_warehouses table (3PL warehouse locations)
CREATE TABLE tpl_warehouses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Warehouse details
    name VARCHAR(255) NOT NULL,
    company VARCHAR(255), -- 3PL company name (e.g., "ShipBob", "Fulfillment by Amazon Prep")
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'United States',
    
    -- Contact info
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    
    -- Settings
    is_active BOOLEAN DEFAULT true,
    prep_services_available BOOLEAN DEFAULT true, -- Can they do prep/labeling?
    storage_fee_per_unit DECIMAL(10, 2), -- Monthly storage fee per unit
    prep_fee_per_unit DECIMAL(10, 2), -- Prep fee per unit
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create tpl_inbounds table (inbound shipments to 3PL)
CREATE TABLE tpl_inbounds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE SET NULL,
    tpl_warehouse_id UUID REFERENCES tpl_warehouses(id) ON DELETE SET NULL,
    
    -- Shipment details
    inbound_number VARCHAR(255), -- 3PL's inbound shipment number
    tracking_number VARCHAR(255), -- Carrier tracking number
    carrier VARCHAR(100), -- Shipping carrier (UPS, FedEx, etc.)
    
    -- Status workflow
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_transit', 'received', 'prep_in_progress', 'prep_complete', 'ready_for_fba', 'cancelled')),
    
    -- Dates
    shipped_date TIMESTAMPTZ,
    expected_delivery_date DATE,
    received_date TIMESTAMPTZ,
    prep_started_date TIMESTAMPTZ,
    prep_completed_date TIMESTAMPTZ,
    
    -- Summary metrics
    total_products INTEGER DEFAULT 0,
    total_units INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 2) DEFAULT 0,
    
    -- Prep requirements
    requires_prep BOOLEAN DEFAULT false,
    prep_instructions TEXT, -- Special prep instructions
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create tpl_inbound_items table (products in inbound shipment)
CREATE TABLE tpl_inbound_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tpl_inbound_id UUID REFERENCES tpl_inbounds(id) ON DELETE CASCADE NOT NULL,
    supplier_order_item_id UUID REFERENCES supplier_order_items(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    
    -- Quantity
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    quantity_received INTEGER DEFAULT 0, -- Actual quantity received at 3PL
    quantity_prepped INTEGER DEFAULT 0, -- Quantity that has been prepped
    
    -- Prep status
    prep_status VARCHAR(50) DEFAULT 'pending' CHECK (prep_status IN ('pending', 'in_progress', 'complete', 'not_required')),
    prep_notes TEXT,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one item per product per inbound
    UNIQUE(tpl_inbound_id, product_id, supplier_order_item_id)
);

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_tpl_warehouses_user_id;
DROP INDEX IF EXISTS idx_tpl_warehouses_is_active;
DROP INDEX IF EXISTS idx_tpl_inbounds_user_id;
DROP INDEX IF EXISTS idx_tpl_inbounds_supplier_order_id;
DROP INDEX IF EXISTS idx_tpl_inbounds_tpl_warehouse_id;
DROP INDEX IF EXISTS idx_tpl_inbounds_status;
DROP INDEX IF EXISTS idx_tpl_inbounds_tracking_number;
DROP INDEX IF EXISTS idx_tpl_inbound_items_inbound_id;
DROP INDEX IF EXISTS idx_tpl_inbound_items_product_id;

-- Create indexes for performance
CREATE INDEX idx_tpl_warehouses_user_id ON tpl_warehouses(user_id);
CREATE INDEX idx_tpl_warehouses_is_active ON tpl_warehouses(is_active) WHERE is_active = true;

CREATE INDEX idx_tpl_inbounds_user_id ON tpl_inbounds(user_id);
CREATE INDEX idx_tpl_inbounds_supplier_order_id ON tpl_inbounds(supplier_order_id);
CREATE INDEX idx_tpl_inbounds_tpl_warehouse_id ON tpl_inbounds(tpl_warehouse_id);
CREATE INDEX idx_tpl_inbounds_status ON tpl_inbounds(status);
CREATE INDEX idx_tpl_inbounds_tracking_number ON tpl_inbounds(tracking_number);

CREATE INDEX idx_tpl_inbound_items_inbound_id ON tpl_inbound_items(tpl_inbound_id);
CREATE INDEX idx_tpl_inbound_items_product_id ON tpl_inbound_items(product_id);

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS update_tpl_inbound_summary() CASCADE;

-- Create function to update tpl_inbound summary metrics
CREATE FUNCTION update_tpl_inbound_summary()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE tpl_inbounds
    SET
        total_products = (
            SELECT COUNT(DISTINCT product_id)
            FROM tpl_inbound_items
            WHERE tpl_inbound_id = COALESCE(NEW.tpl_inbound_id, OLD.tpl_inbound_id)
        ),
        total_units = (
            SELECT COALESCE(SUM(quantity), 0)
            FROM tpl_inbound_items
            WHERE tpl_inbound_id = COALESCE(NEW.tpl_inbound_id, OLD.tpl_inbound_id)
        ),
        updated_at = NOW()
    WHERE id = COALESCE(NEW.tpl_inbound_id, OLD.tpl_inbound_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS trigger_update_tpl_inbound_summary_insert ON tpl_inbound_items;
DROP TRIGGER IF EXISTS trigger_update_tpl_inbound_summary_update ON tpl_inbound_items;
DROP TRIGGER IF EXISTS trigger_update_tpl_inbound_summary_delete ON tpl_inbound_items;

-- Create triggers to auto-update summary metrics
CREATE TRIGGER trigger_update_tpl_inbound_summary_insert
    AFTER INSERT ON tpl_inbound_items
    FOR EACH ROW
    EXECUTE FUNCTION update_tpl_inbound_summary();

CREATE TRIGGER trigger_update_tpl_inbound_summary_update
    AFTER UPDATE ON tpl_inbound_items
    FOR EACH ROW
    EXECUTE FUNCTION update_tpl_inbound_summary();

CREATE TRIGGER trigger_update_tpl_inbound_summary_delete
    AFTER DELETE ON tpl_inbound_items
    FOR EACH ROW
    EXECUTE FUNCTION update_tpl_inbound_summary();

-- Enable RLS (Row Level Security)
ALTER TABLE tpl_warehouses ENABLE ROW LEVEL SECURITY;
ALTER TABLE tpl_inbounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE tpl_inbound_items ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own 3PL warehouses" ON tpl_warehouses;
DROP POLICY IF EXISTS "Users can create their own 3PL warehouses" ON tpl_warehouses;
DROP POLICY IF EXISTS "Users can update their own 3PL warehouses" ON tpl_warehouses;
DROP POLICY IF EXISTS "Users can delete their own 3PL warehouses" ON tpl_warehouses;
DROP POLICY IF EXISTS "Users can view their own 3PL inbounds" ON tpl_inbounds;
DROP POLICY IF EXISTS "Users can create their own 3PL inbounds" ON tpl_inbounds;
DROP POLICY IF EXISTS "Users can update their own 3PL inbounds" ON tpl_inbounds;
DROP POLICY IF EXISTS "Users can delete their own 3PL inbounds" ON tpl_inbounds;
DROP POLICY IF EXISTS "Users can view items in their 3PL inbounds" ON tpl_inbound_items;
DROP POLICY IF EXISTS "Users can add items to their 3PL inbounds" ON tpl_inbound_items;
DROP POLICY IF EXISTS "Users can update items in their 3PL inbounds" ON tpl_inbound_items;
DROP POLICY IF EXISTS "Users can delete items from their 3PL inbounds" ON tpl_inbound_items;

-- RLS Policies for tpl_warehouses
CREATE POLICY "Users can view their own 3PL warehouses"
    ON tpl_warehouses FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own 3PL warehouses"
    ON tpl_warehouses FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own 3PL warehouses"
    ON tpl_warehouses FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own 3PL warehouses"
    ON tpl_warehouses FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for tpl_inbounds
CREATE POLICY "Users can view their own 3PL inbounds"
    ON tpl_inbounds FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own 3PL inbounds"
    ON tpl_inbounds FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own 3PL inbounds"
    ON tpl_inbounds FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own 3PL inbounds"
    ON tpl_inbounds FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for tpl_inbound_items
CREATE POLICY "Users can view items in their 3PL inbounds"
    ON tpl_inbound_items FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM tpl_inbounds
            WHERE tpl_inbounds.id = tpl_inbound_items.tpl_inbound_id
            AND tpl_inbounds.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add items to their 3PL inbounds"
    ON tpl_inbound_items FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM tpl_inbounds
            WHERE tpl_inbounds.id = tpl_inbound_items.tpl_inbound_id
            AND tpl_inbounds.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update items in their 3PL inbounds"
    ON tpl_inbound_items FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM tpl_inbounds
            WHERE tpl_inbounds.id = tpl_inbound_items.tpl_inbound_id
            AND tpl_inbounds.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete items from their 3PL inbounds"
    ON tpl_inbound_items FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM tpl_inbounds
            WHERE tpl_inbounds.id = tpl_inbound_items.tpl_inbound_id
            AND tpl_inbounds.user_id = auth.uid()
        )
    );

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON tpl_warehouses TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON tpl_inbounds TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON tpl_inbound_items TO authenticated;

-- Comments
COMMENT ON TABLE tpl_warehouses IS '3PL warehouse locations where inventory is stored and prepped';
COMMENT ON TABLE tpl_inbounds IS 'Inbound shipments from suppliers to 3PL warehouses';
COMMENT ON TABLE tpl_inbound_items IS 'Individual products in a 3PL inbound shipment';
COMMENT ON COLUMN tpl_inbounds.status IS 'pending: created, in_transit: shipping to 3PL, received: at 3PL, prep_in_progress: being prepped, prep_complete: ready, ready_for_fba: can create FBA shipment, cancelled: cancelled';
COMMENT ON COLUMN tpl_inbound_items.prep_status IS 'pending: not started, in_progress: being prepped, complete: prepped, not_required: no prep needed';

