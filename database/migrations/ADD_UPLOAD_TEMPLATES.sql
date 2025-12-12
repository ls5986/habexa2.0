-- HABEXA: Upload Template System
-- Templates for CSV/Excel column mappings per supplier

-- ============================================
-- 1. UPLOAD TEMPLATES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS upload_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    
    -- Template Info
    name TEXT NOT NULL, -- e.g., "KEHE Standard Format"
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    
    -- Column Mappings (JSONB)
    column_mappings JSONB NOT NULL, -- {
    --   "upc": "UPC Code",
    --   "title": "Product Name",
    --   "wholesale_cost": "Cost",
    --   "pack_size": "Units per Case",
    --   "brand": "Brand Name"
    -- }
    
    -- Default Values (JSONB)
    default_values JSONB DEFAULT '{}'::jsonb, -- {
    --   "supplier_id": "uuid",
    --   "cost_type": "case",
    --   "prep_required": true
    -- }
    
    -- Validation Rules (JSONB)
    validation_rules JSONB DEFAULT '[]'::jsonb, -- [
    --   {"field": "upc", "rule": "length", "min": 12, "max": 14},
    --   {"field": "wholesale_cost", "rule": "min", "value": 0}
    -- ]
    
    -- Transformations (JSONB)
    transformations JSONB DEFAULT '[]'::jsonb, -- [
    --   {"field": "upc", "transformation": "remove_dashes"},
    --   {"field": "price", "transformation": "parse_currency"}
    -- ]
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, supplier_id, name)
);

CREATE INDEX IF NOT EXISTS idx_upload_templates_user ON upload_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_upload_templates_supplier ON upload_templates(supplier_id);
CREATE INDEX IF NOT EXISTS idx_upload_templates_default ON upload_templates(user_id, supplier_id, is_default) WHERE is_default = true;

-- ============================================
-- 2. COMMENTS
-- ============================================
COMMENT ON TABLE upload_templates IS 'Column mapping templates for CSV/Excel uploads per supplier';
COMMENT ON COLUMN upload_templates.column_mappings IS 'JSONB mapping Habexa fields to CSV column names';
COMMENT ON COLUMN upload_templates.default_values IS 'Default values to apply when field is missing';
COMMENT ON COLUMN upload_templates.validation_rules IS 'JSONB array of validation rules to apply during import';
COMMENT ON COLUMN upload_templates.transformations IS 'JSONB array of data transformations (remove_dashes, parse_currency, etc.)';

