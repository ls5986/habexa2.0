-- ============================================================================
-- 3PL/PREP CENTER MANAGEMENT SYSTEM - Database Schema
-- ============================================================================
-- This migration creates tables for managing prep centers, fee structures,
-- product assignments, work orders, and invoice reconciliation.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS prep_work_order_items CASCADE;
DROP TABLE IF EXISTS prep_work_orders CASCADE;
DROP TABLE IF EXISTS product_prep_assignments CASCADE;
DROP TABLE IF EXISTS prep_center_fees CASCADE;
DROP TABLE IF EXISTS prep_centers CASCADE;

-- Create prep_centers table
CREATE TABLE prep_centers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Company Info
    company_name VARCHAR(255) NOT NULL,
    short_code VARCHAR(50),
    website VARCHAR(255),
    
    -- Contact Info
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    business_hours VARCHAR(255),
    
    -- Shipping Address
    shipping_address_line1 VARCHAR(255) NOT NULL,
    shipping_address_line2 VARCHAR(255),
    shipping_city VARCHAR(100) NOT NULL,
    shipping_state VARCHAR(50) NOT NULL,
    shipping_zip VARCHAR(20) NOT NULL,
    shipping_country VARCHAR(100) DEFAULT 'USA',
    
    -- Billing Info
    billing_email VARCHAR(255),
    payment_terms VARCHAR(100),
    account_number VARCHAR(100),
    
    -- Capabilities (stored as JSONB)
    capabilities JSONB DEFAULT '{}', -- {"fnsku": true, "polybagging": true, "hazmat": true, "climate_control": true, "oversized": true}
    
    -- Storage
    max_pallet_capacity INTEGER,
    storage_available BOOLEAN DEFAULT true,
    free_storage_days INTEGER DEFAULT 30,
    
    -- API Integration
    api_available BOOLEAN DEFAULT false,
    api_endpoint VARCHAR(255),
    api_key_encrypted TEXT,
    
    -- Metadata
    notes TEXT,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'suspended'
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, short_code)
);

-- Create prep_center_fees table
CREATE TABLE prep_center_fees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prep_center_id UUID REFERENCES prep_centers(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Service Info
    service_name VARCHAR(255) NOT NULL,
    service_code VARCHAR(50),
    service_category VARCHAR(100), -- 'prep', 'reboxing', 'palletizing', 'storage', 'other'
    
    -- Fee Structure
    fee_type VARCHAR(50) NOT NULL, -- 'per_unit', 'per_pound', 'per_pallet', 'per_day', 'percentage', 'flat'
    base_cost DECIMAL(10, 4),
    percentage_rate DECIMAL(10, 4), -- For percentage-based fees
    minimum_charge DECIMAL(10, 2),
    maximum_charge DECIMAL(10, 2),
    
    -- Tiered Pricing (stored as JSONB)
    tiered_pricing JSONB, -- [{"min_qty": 0, "max_qty": 100, "cost": 0.25}, {"min_qty": 101, "max_qty": null, "cost": 0.20}]
    
    -- Service Details
    includes TEXT,
    requirements TEXT,
    size_category VARCHAR(50), -- 'small', 'medium', 'large'
    max_dimensions VARCHAR(50), -- '12x12x12'
    max_weight DECIMAL(10, 2),
    
    -- Applicability
    applies_to_hazmat BOOLEAN DEFAULT true,
    applies_to_oversized BOOLEAN DEFAULT true,
    applies_to_standard BOOLEAN DEFAULT true,
    
    -- Metadata
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create product_prep_assignments table
CREATE TABLE product_prep_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    prep_center_id UUID REFERENCES prep_centers(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Assignment Info
    assignment_reason VARCHAR(100), -- 'auto_cheapest', 'auto_capability', 'manual', 'hazmat_required'
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Services Required (stored as JSONB)
    required_services JSONB DEFAULT '[]', -- [{"service_code": "FNSKU", "fee_id": "uuid", "service_name": "FNSKU Labeling"}]
    
    -- Costs
    total_prep_cost_per_unit DECIMAL(10, 2) DEFAULT 0,
    breakdown JSONB DEFAULT '{}', -- {"FNSKU": 0.25, "POLYBAG_MED": 0.20, "STORAGE": 0.60}
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique: one active assignment per product
    UNIQUE(product_id, user_id) WHERE is_active = true
);

-- Create prep_work_orders table
CREATE TABLE prep_work_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prep_center_id UUID REFERENCES prep_centers(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Related Entities
    buy_list_id UUID REFERENCES buy_lists(id) ON DELETE SET NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE SET NULL,
    
    -- Order Info
    order_number VARCHAR(100) UNIQUE NOT NULL,
    order_date TIMESTAMPTZ DEFAULT NOW(),
    expected_arrival_date DATE,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'submitted', 'received', 'in_progress', 'completed', 'invoiced', 'cancelled'
    
    -- Quantities
    total_units INTEGER DEFAULT 0,
    
    -- Costs
    estimated_total_cost DECIMAL(10, 2) DEFAULT 0,
    actual_total_cost DECIMAL(10, 2),
    
    -- Tracking
    tracking_number VARCHAR(255),
    received_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Invoice
    invoice_number VARCHAR(100),
    invoice_date DATE,
    invoice_amount DECIMAL(10, 2),
    variance_amount DECIMAL(10, 2),
    variance_reason TEXT,
    
    -- External Integration
    external_work_order_id VARCHAR(255), -- Prep center's work order ID if API integrated
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create prep_work_order_items table
CREATE TABLE prep_work_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prep_work_order_id UUID REFERENCES prep_work_orders(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    
    -- Quantity
    quantity INTEGER NOT NULL,
    
    -- Services Required (stored as JSONB)
    services_required JSONB DEFAULT '[]', -- [{"service_code": "FNSKU", "fee_id": "uuid"}]
    
    -- Costs
    unit_prep_cost DECIMAL(10, 2) DEFAULT 0,
    total_prep_cost DECIMAL(10, 2) DEFAULT 0, -- quantity * unit_prep_cost
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
    completed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_prep_centers_user_id;
DROP INDEX IF EXISTS idx_prep_centers_status;
DROP INDEX IF EXISTS idx_prep_center_fees_prep_center_id;
DROP INDEX IF EXISTS idx_prep_center_fees_user_id;
DROP INDEX IF EXISTS idx_product_prep_assignments_product_id;
DROP INDEX IF EXISTS idx_product_prep_assignments_prep_center_id;
DROP INDEX IF EXISTS idx_product_prep_assignments_user_id;
DROP INDEX IF EXISTS idx_prep_work_orders_prep_center_id;
DROP INDEX IF EXISTS idx_prep_work_orders_user_id;
DROP INDEX IF EXISTS idx_prep_work_orders_buy_list_id;
DROP INDEX IF EXISTS idx_prep_work_orders_status;
DROP INDEX IF EXISTS idx_prep_work_order_items_work_order_id;
DROP INDEX IF EXISTS idx_prep_work_order_items_product_id;

-- Create indexes for performance
CREATE INDEX idx_prep_centers_user_id ON prep_centers(user_id);
CREATE INDEX idx_prep_centers_status ON prep_centers(status) WHERE status = 'active';

CREATE INDEX idx_prep_center_fees_prep_center_id ON prep_center_fees(prep_center_id);
CREATE INDEX idx_prep_center_fees_user_id ON prep_center_fees(user_id);
CREATE INDEX idx_prep_center_fees_active ON prep_center_fees(is_active) WHERE is_active = true;

CREATE INDEX idx_product_prep_assignments_product_id ON product_prep_assignments(product_id);
CREATE INDEX idx_product_prep_assignments_prep_center_id ON product_prep_assignments(prep_center_id);
CREATE INDEX idx_product_prep_assignments_user_id ON product_prep_assignments(user_id);
CREATE INDEX idx_product_prep_assignments_active ON product_prep_assignments(is_active) WHERE is_active = true;

CREATE INDEX idx_prep_work_orders_prep_center_id ON prep_work_orders(prep_center_id);
CREATE INDEX idx_prep_work_orders_user_id ON prep_work_orders(user_id);
CREATE INDEX idx_prep_work_orders_buy_list_id ON prep_work_orders(buy_list_id);
CREATE INDEX idx_prep_work_orders_status ON prep_work_orders(status);
CREATE INDEX idx_prep_work_orders_order_number ON prep_work_orders(order_number);

CREATE INDEX idx_prep_work_order_items_work_order_id ON prep_work_order_items(prep_work_order_id);
CREATE INDEX idx_prep_work_order_items_product_id ON prep_work_order_items(product_id);

-- Enable RLS (Row Level Security)
ALTER TABLE prep_centers ENABLE ROW LEVEL SECURITY;
ALTER TABLE prep_center_fees ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_prep_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE prep_work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE prep_work_order_items ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own prep centers" ON prep_centers;
DROP POLICY IF EXISTS "Users can create their own prep centers" ON prep_centers;
DROP POLICY IF EXISTS "Users can update their own prep centers" ON prep_centers;
DROP POLICY IF EXISTS "Users can delete their own prep centers" ON prep_centers;
DROP POLICY IF EXISTS "Users can view their own prep center fees" ON prep_center_fees;
DROP POLICY IF EXISTS "Users can create their own prep center fees" ON prep_center_fees;
DROP POLICY IF EXISTS "Users can update their own prep center fees" ON prep_center_fees;
DROP POLICY IF EXISTS "Users can delete their own prep center fees" ON prep_center_fees;
DROP POLICY IF EXISTS "Users can view their own prep assignments" ON product_prep_assignments;
DROP POLICY IF EXISTS "Users can create their own prep assignments" ON product_prep_assignments;
DROP POLICY IF EXISTS "Users can update their own prep assignments" ON product_prep_assignments;
DROP POLICY IF EXISTS "Users can delete their own prep assignments" ON product_prep_assignments;
DROP POLICY IF EXISTS "Users can view their own work orders" ON prep_work_orders;
DROP POLICY IF EXISTS "Users can create their own work orders" ON prep_work_orders;
DROP POLICY IF EXISTS "Users can update their own work orders" ON prep_work_orders;
DROP POLICY IF EXISTS "Users can delete their own work orders" ON prep_work_orders;
DROP POLICY IF EXISTS "Users can view their own work order items" ON prep_work_order_items;
DROP POLICY IF EXISTS "Users can create their own work order items" ON prep_work_order_items;
DROP POLICY IF EXISTS "Users can update their own work order items" ON prep_work_order_items;
DROP POLICY IF EXISTS "Users can delete their own work order items" ON prep_work_order_items;

-- RLS Policies for prep_centers
CREATE POLICY "Users can view their own prep centers"
    ON prep_centers FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own prep centers"
    ON prep_centers FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own prep centers"
    ON prep_centers FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own prep centers"
    ON prep_centers FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for prep_center_fees
CREATE POLICY "Users can view their own prep center fees"
    ON prep_center_fees FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own prep center fees"
    ON prep_center_fees FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own prep center fees"
    ON prep_center_fees FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own prep center fees"
    ON prep_center_fees FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for product_prep_assignments
CREATE POLICY "Users can view their own prep assignments"
    ON product_prep_assignments FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own prep assignments"
    ON product_prep_assignments FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own prep assignments"
    ON product_prep_assignments FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own prep assignments"
    ON product_prep_assignments FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for prep_work_orders
CREATE POLICY "Users can view their own work orders"
    ON prep_work_orders FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own work orders"
    ON prep_work_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own work orders"
    ON prep_work_orders FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own work orders"
    ON prep_work_orders FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for prep_work_order_items
CREATE POLICY "Users can view their own work order items"
    ON prep_work_order_items FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM prep_work_orders
            WHERE prep_work_orders.id = prep_work_order_items.prep_work_order_id
            AND prep_work_orders.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create their own work order items"
    ON prep_work_order_items FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM prep_work_orders
            WHERE prep_work_orders.id = prep_work_order_items.prep_work_order_id
            AND prep_work_orders.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own work order items"
    ON prep_work_order_items FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM prep_work_orders
            WHERE prep_work_orders.id = prep_work_order_items.prep_work_order_id
            AND prep_work_orders.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete their own work order items"
    ON prep_work_order_items FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM prep_work_orders
            WHERE prep_work_orders.id = prep_work_order_items.prep_work_order_id
            AND prep_work_orders.user_id = auth.uid()
        )
    );

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON prep_centers TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON prep_center_fees TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON product_prep_assignments TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON prep_work_orders TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON prep_work_order_items TO authenticated;

-- Add prep_cost_per_unit and prep_center_id to products table if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'prep_cost_per_unit'
    ) THEN
        ALTER TABLE products ADD COLUMN prep_cost_per_unit DECIMAL(10, 2) DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'prep_center_id'
    ) THEN
        ALTER TABLE products ADD COLUMN prep_center_id UUID REFERENCES prep_centers(id);
        CREATE INDEX idx_products_prep_center_id ON products(prep_center_id);
    END IF;
END $$;

-- Comments
COMMENT ON TABLE prep_centers IS '3PL/Prep center profiles with capabilities and contact info';
COMMENT ON TABLE prep_center_fees IS 'Flexible fee structures for prep services (per-unit, per-pound, tiered, etc.)';
COMMENT ON TABLE product_prep_assignments IS 'Product assignments to prep centers with required services and costs';
COMMENT ON TABLE prep_work_orders IS 'Work orders sent to prep centers for processing inventory';
COMMENT ON TABLE prep_work_order_items IS 'Line items in work orders with quantities and services';
COMMENT ON COLUMN prep_center_fees.tiered_pricing IS 'JSON array of quantity tiers: [{"min_qty": 0, "max_qty": 100, "cost": 0.25}]';
COMMENT ON COLUMN product_prep_assignments.required_services IS 'JSON array of services: [{"service_code": "FNSKU", "fee_id": "uuid"}]';
COMMENT ON COLUMN product_prep_assignments.breakdown IS 'JSON object with cost breakdown: {"FNSKU": 0.25, "POLYBAG": 0.20}';

