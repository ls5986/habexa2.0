-- ============================================================================
-- FBA SHIPMENT CREATION - Phase 5 Implementation
-- ============================================================================
-- This migration creates tables for managing FBA shipments from 3PL prepped
-- inventory to Amazon fulfillment centers.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS fba_shipment_items CASCADE;
DROP TABLE IF EXISTS fba_shipment_boxes CASCADE;
DROP TABLE IF EXISTS fnsku_labels CASCADE;
DROP TABLE IF EXISTS fba_shipments CASCADE;

-- Create fba_shipments table
CREATE TABLE fba_shipments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    tpl_inbound_id UUID REFERENCES tpl_inbounds(id) ON DELETE SET NULL,
    
    -- Amazon shipment details
    shipment_id VARCHAR(255), -- Amazon's shipment ID (from SP-API)
    shipment_name VARCHAR(255), -- User-friendly name
    destination_fulfillment_center_id VARCHAR(100), -- Amazon FC ID
    
    -- Status workflow
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'working', 'ready_to_ship', 'shipped', 'in_transit', 'delivered', 'received', 'closed', 'cancelled')),
    
    -- Shipment details
    shipment_type VARCHAR(50) DEFAULT 'SP' CHECK (shipment_type IN ('SP', 'LTL')), -- SP = Small Parcel, LTL = Less Than Truckload
    label_prep_type VARCHAR(50) DEFAULT 'SELLER_LABEL', -- SELLER_LABEL, AMAZON_LABEL, NO_LABEL
    
    -- Dates
    created_date TIMESTAMPTZ,
    estimated_arrival_date DATE,
    shipped_date TIMESTAMPTZ,
    delivered_date TIMESTAMPTZ,
    received_date TIMESTAMPTZ,
    closed_date TIMESTAMPTZ,
    
    -- Shipping info
    carrier_name VARCHAR(100),
    tracking_number VARCHAR(255),
    freight_class VARCHAR(50), -- For LTL shipments
    
    -- Summary metrics
    total_boxes INTEGER DEFAULT 0,
    total_units INTEGER DEFAULT 0,
    total_skus INTEGER DEFAULT 0,
    
    -- Costs
    estimated_shipping_cost DECIMAL(10, 2),
    actual_shipping_cost DECIMAL(10, 2),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create fba_shipment_items table (products in FBA shipment)
CREATE TABLE fba_shipment_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fba_shipment_id UUID REFERENCES fba_shipments(id) ON DELETE CASCADE NOT NULL,
    tpl_inbound_item_id UUID REFERENCES tpl_inbound_items(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    
    -- Amazon identifiers
    seller_sku VARCHAR(255), -- Your SKU
    fnsku VARCHAR(255), -- Amazon's FNSKU (Fulfillment Network SKU)
    asin VARCHAR(20) NOT NULL,
    
    -- Quantities
    quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
    quantity_received INTEGER DEFAULT 0, -- Actual quantity received at Amazon
    quantity_in_case INTEGER DEFAULT 1, -- Units per case (for case-packed items)
    
    -- Prep requirements
    prep_owner VARCHAR(50) DEFAULT 'SELLER', -- SELLER or AMAZON
    prep_details_list JSONB, -- Prep requirements from Amazon
    
    -- Box assignment
    box_id UUID, -- Reference to fba_shipment_boxes (nullable, assigned later)
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one item per product per shipment
    UNIQUE(fba_shipment_id, product_id, fnsku)
);

-- Create fba_shipment_boxes table (boxes/pallets in shipment)
CREATE TABLE fba_shipment_boxes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fba_shipment_id UUID REFERENCES fba_shipments(id) ON DELETE CASCADE NOT NULL,
    
    -- Box details
    box_number INTEGER NOT NULL, -- Box 1, 2, 3, etc.
    box_name VARCHAR(255), -- User-friendly name
    weight DECIMAL(10, 2), -- Weight in lbs
    dimensions_length DECIMAL(10, 2),
    dimensions_width DECIMAL(10, 2),
    dimensions_height DECIMAL(10, 2),
    dimensions_unit VARCHAR(10) DEFAULT 'inches',
    
    -- Tracking
    tracking_number VARCHAR(255), -- Individual box tracking (for SP shipments)
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'packed', 'shipped', 'delivered', 'received')),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one box number per shipment
    UNIQUE(fba_shipment_id, box_number)
);

-- Create fnsku_labels table (FNSKU label tracking)
CREATE TABLE fnsku_labels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    fba_shipment_item_id UUID REFERENCES fba_shipment_items(id) ON DELETE SET NULL,
    
    -- Label details
    fnsku VARCHAR(255) NOT NULL,
    asin VARCHAR(20) NOT NULL,
    seller_sku VARCHAR(255),
    
    -- Label status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'generated', 'printed', 'applied', 'verified')),
    
    -- Label generation
    label_type VARCHAR(50) DEFAULT 'FNSKU', -- FNSKU, COMMINGLING
    label_format VARCHAR(50) DEFAULT 'PDF', -- PDF, PNG, ZPL
    
    -- File storage
    label_file_url TEXT, -- URL to generated label file
    label_file_path TEXT, -- Local file path (if stored locally)
    
    -- Quantity
    quantity INTEGER DEFAULT 1, -- Number of labels needed
    
    -- Dates
    generated_at TIMESTAMPTZ,
    printed_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one label record per FNSKU per shipment item
    UNIQUE(fba_shipment_item_id, fnsku)
);

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_fba_shipments_user_id;
DROP INDEX IF EXISTS idx_fba_shipments_tpl_inbound_id;
DROP INDEX IF EXISTS idx_fba_shipments_status;
DROP INDEX IF EXISTS idx_fba_shipments_shipment_id;
DROP INDEX IF EXISTS idx_fba_shipment_items_shipment_id;
DROP INDEX IF EXISTS idx_fba_shipment_items_product_id;
DROP INDEX IF EXISTS idx_fba_shipment_items_fnsku;
DROP INDEX IF EXISTS idx_fba_shipment_boxes_shipment_id;
DROP INDEX IF EXISTS idx_fnsku_labels_user_id;
DROP INDEX IF EXISTS idx_fnsku_labels_product_id;
DROP INDEX IF EXISTS idx_fnsku_labels_fnsku;

-- Create indexes for performance
CREATE INDEX idx_fba_shipments_user_id ON fba_shipments(user_id);
CREATE INDEX idx_fba_shipments_tpl_inbound_id ON fba_shipments(tpl_inbound_id);
CREATE INDEX idx_fba_shipments_status ON fba_shipments(status);
CREATE INDEX idx_fba_shipments_shipment_id ON fba_shipments(shipment_id);

CREATE INDEX idx_fba_shipment_items_shipment_id ON fba_shipment_items(fba_shipment_id);
CREATE INDEX idx_fba_shipment_items_product_id ON fba_shipment_items(product_id);
CREATE INDEX idx_fba_shipment_items_fnsku ON fba_shipment_items(fnsku);
CREATE INDEX idx_fba_shipment_items_box_id ON fba_shipment_items(box_id);

CREATE INDEX idx_fba_shipment_boxes_shipment_id ON fba_shipment_boxes(fba_shipment_id);

CREATE INDEX idx_fnsku_labels_user_id ON fnsku_labels(user_id);
CREATE INDEX idx_fnsku_labels_product_id ON fnsku_labels(product_id);
CREATE INDEX idx_fnsku_labels_fnsku ON fnsku_labels(fnsku);
CREATE INDEX idx_fnsku_labels_fba_shipment_item_id ON fnsku_labels(fba_shipment_item_id);

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS update_fba_shipment_summary() CASCADE;

-- Create function to update fba_shipment summary metrics
CREATE FUNCTION update_fba_shipment_summary()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE fba_shipments
    SET
        total_skus = (
            SELECT COUNT(DISTINCT product_id)
            FROM fba_shipment_items
            WHERE fba_shipment_id = COALESCE(NEW.fba_shipment_id, OLD.fba_shipment_id)
        ),
        total_units = (
            SELECT COALESCE(SUM(quantity_shipped), 0)
            FROM fba_shipment_items
            WHERE fba_shipment_id = COALESCE(NEW.fba_shipment_id, OLD.fba_shipment_id)
        ),
        total_boxes = (
            SELECT COUNT(*)
            FROM fba_shipment_boxes
            WHERE fba_shipment_id = COALESCE(NEW.fba_shipment_id, OLD.fba_shipment_id)
        ),
        updated_at = NOW()
    WHERE id = COALESCE(NEW.fba_shipment_id, OLD.fba_shipment_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS trigger_update_fba_shipment_summary_insert ON fba_shipment_items;
DROP TRIGGER IF EXISTS trigger_update_fba_shipment_summary_update ON fba_shipment_items;
DROP TRIGGER IF EXISTS trigger_update_fba_shipment_summary_delete ON fba_shipment_items;
DROP TRIGGER IF EXISTS trigger_update_fba_shipment_summary_boxes_insert ON fba_shipment_boxes;
DROP TRIGGER IF EXISTS trigger_update_fba_shipment_summary_boxes_delete ON fba_shipment_boxes;

-- Create triggers to auto-update summary metrics
CREATE TRIGGER trigger_update_fba_shipment_summary_insert
    AFTER INSERT ON fba_shipment_items
    FOR EACH ROW
    EXECUTE FUNCTION update_fba_shipment_summary();

CREATE TRIGGER trigger_update_fba_shipment_summary_update
    AFTER UPDATE ON fba_shipment_items
    FOR EACH ROW
    EXECUTE FUNCTION update_fba_shipment_summary();

CREATE TRIGGER trigger_update_fba_shipment_summary_delete
    AFTER DELETE ON fba_shipment_items
    FOR EACH ROW
    EXECUTE FUNCTION update_fba_shipment_summary();

CREATE TRIGGER trigger_update_fba_shipment_summary_boxes_insert
    AFTER INSERT ON fba_shipment_boxes
    FOR EACH ROW
    EXECUTE FUNCTION update_fba_shipment_summary();

CREATE TRIGGER trigger_update_fba_shipment_summary_boxes_delete
    AFTER DELETE ON fba_shipment_boxes
    FOR EACH ROW
    EXECUTE FUNCTION update_fba_shipment_summary();

-- Enable RLS (Row Level Security)
ALTER TABLE fba_shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE fba_shipment_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE fba_shipment_boxes ENABLE ROW LEVEL SECURITY;
ALTER TABLE fnsku_labels ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own FBA shipments" ON fba_shipments;
DROP POLICY IF EXISTS "Users can create their own FBA shipments" ON fba_shipments;
DROP POLICY IF EXISTS "Users can update their own FBA shipments" ON fba_shipments;
DROP POLICY IF EXISTS "Users can delete their own FBA shipments" ON fba_shipments;
DROP POLICY IF EXISTS "Users can view items in their FBA shipments" ON fba_shipment_items;
DROP POLICY IF EXISTS "Users can add items to their FBA shipments" ON fba_shipment_items;
DROP POLICY IF EXISTS "Users can update items in their FBA shipments" ON fba_shipment_items;
DROP POLICY IF EXISTS "Users can delete items from their FBA shipments" ON fba_shipment_items;
DROP POLICY IF EXISTS "Users can view boxes in their FBA shipments" ON fba_shipment_boxes;
DROP POLICY IF EXISTS "Users can add boxes to their FBA shipments" ON fba_shipment_boxes;
DROP POLICY IF EXISTS "Users can update boxes in their FBA shipments" ON fba_shipment_boxes;
DROP POLICY IF EXISTS "Users can delete boxes from their FBA shipments" ON fba_shipment_boxes;
DROP POLICY IF EXISTS "Users can view their own FNSKU labels" ON fnsku_labels;
DROP POLICY IF EXISTS "Users can create their own FNSKU labels" ON fnsku_labels;
DROP POLICY IF EXISTS "Users can update their own FNSKU labels" ON fnsku_labels;
DROP POLICY IF EXISTS "Users can delete their own FNSKU labels" ON fnsku_labels;

-- RLS Policies for fba_shipments
CREATE POLICY "Users can view their own FBA shipments"
    ON fba_shipments FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own FBA shipments"
    ON fba_shipments FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own FBA shipments"
    ON fba_shipments FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own FBA shipments"
    ON fba_shipments FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for fba_shipment_items
CREATE POLICY "Users can view items in their FBA shipments"
    ON fba_shipment_items FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_items.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add items to their FBA shipments"
    ON fba_shipment_items FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_items.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update items in their FBA shipments"
    ON fba_shipment_items FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_items.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete items from their FBA shipments"
    ON fba_shipment_items FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_items.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

-- RLS Policies for fba_shipment_boxes
CREATE POLICY "Users can view boxes in their FBA shipments"
    ON fba_shipment_boxes FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_boxes.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add boxes to their FBA shipments"
    ON fba_shipment_boxes FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_boxes.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update boxes in their FBA shipments"
    ON fba_shipment_boxes FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_boxes.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete boxes from their FBA shipments"
    ON fba_shipment_boxes FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM fba_shipments
            WHERE fba_shipments.id = fba_shipment_boxes.fba_shipment_id
            AND fba_shipments.user_id = auth.uid()
        )
    );

-- RLS Policies for fnsku_labels
CREATE POLICY "Users can view their own FNSKU labels"
    ON fnsku_labels FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own FNSKU labels"
    ON fnsku_labels FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own FNSKU labels"
    ON fnsku_labels FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own FNSKU labels"
    ON fnsku_labels FOR DELETE
    USING (auth.uid() = user_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON fba_shipments TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON fba_shipment_items TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON fba_shipment_boxes TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON fnsku_labels TO authenticated;

-- Comments
COMMENT ON TABLE fba_shipments IS 'FBA shipments from 3PL prepped inventory to Amazon fulfillment centers';
COMMENT ON TABLE fba_shipment_items IS 'Individual products in an FBA shipment';
COMMENT ON TABLE fba_shipment_boxes IS 'Boxes/pallets in an FBA shipment';
COMMENT ON TABLE fnsku_labels IS 'FNSKU label tracking for FBA products';
COMMENT ON COLUMN fba_shipments.status IS 'draft: being created, working: shipment plan created, ready_to_ship: ready, shipped: sent to Amazon, in_transit: shipping, delivered: at FC, received: checked in, closed: complete, cancelled: cancelled';
COMMENT ON COLUMN fba_shipment_items.fnsku IS 'Amazon FNSKU (Fulfillment Network SKU) - unique identifier for FBA inventory';
COMMENT ON COLUMN fba_shipment_items.prep_owner IS 'SELLER: you prep, AMAZON: Amazon preps (for a fee)';

