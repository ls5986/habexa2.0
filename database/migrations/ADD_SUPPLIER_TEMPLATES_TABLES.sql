-- ============================================================================
-- SUPPLIER TEMPLATE MAPPING SYSTEM - Database Schema
-- ============================================================================
-- This migration creates tables for supplier-specific Excel/CSV templates
-- with pre-configured column mappings, custom calculations, and validation.

-- Drop existing tables if they exist
DROP TABLE IF EXISTS template_versions CASCADE;
DROP TABLE IF EXISTS supplier_category_mappings CASCADE;
DROP TABLE IF EXISTS supplier_templates CASCADE;

-- Create supplier_templates table
CREATE TABLE supplier_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Template metadata
    template_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- File structure
    file_format VARCHAR(20) NOT NULL, -- 'xlsx', 'csv', 'tsv'
    sheet_name VARCHAR(255), -- For Excel files with multiple sheets
    header_row INTEGER DEFAULT 1,
    data_start_row INTEGER DEFAULT 2,
    
    -- Mappings & Rules (stored as JSONB for flexibility)
    column_mappings JSONB NOT NULL DEFAULT '{}', -- {"Supplier Column": "habexa_field"}
    calculations JSONB DEFAULT '[]', -- [{"field": "wholesale_cost", "formula": "..."}]
    default_values JSONB DEFAULT '{}', -- {"field": "default_value"}
    validation_rules JSONB DEFAULT '{}', -- {"field": {"type": "...", "value": "..."}}
    transformations JSONB DEFAULT '[]', -- [{"field": "upc", "transform": "REMOVE_DASHES"}]
    row_filters JSONB DEFAULT '[]', -- [{"condition": "...", "action": "skip"}]
    
    -- Auto-detection settings
    filename_pattern VARCHAR(255), -- Regex pattern for filename matching
    column_fingerprint JSONB, -- Array of unique column names for matching
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0, -- How many times template used
    last_used_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, supplier_id, template_name)
);

-- Create template_versions table (for version control)
CREATE TABLE template_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES supplier_templates(id) ON DELETE CASCADE NOT NULL,
    version_number INTEGER NOT NULL,
    
    -- Snapshot of template configuration
    column_mappings JSONB,
    calculations JSONB,
    default_values JSONB,
    validation_rules JSONB,
    transformations JSONB,
    row_filters JSONB,
    
    -- Change tracking
    changed_by UUID REFERENCES auth.users(id),
    change_description TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique version per template
    UNIQUE(template_id, version_number)
);

-- Create supplier_category_mappings table (for lookup tables)
CREATE TABLE supplier_category_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Mapping data
    supplier_code VARCHAR(100) NOT NULL, -- Supplier's category code
    habexa_category VARCHAR(255) NOT NULL, -- Standardized category
    description TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique mapping per supplier
    UNIQUE(user_id, supplier_id, supplier_code)
);

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS idx_supplier_templates_supplier_id;
DROP INDEX IF EXISTS idx_supplier_templates_user_id;
DROP INDEX IF EXISTS idx_supplier_templates_active;
DROP INDEX IF EXISTS idx_template_versions_template_id;
DROP INDEX IF EXISTS idx_supplier_category_mappings_supplier;
DROP INDEX IF EXISTS idx_supplier_category_mappings_user;

-- Create indexes for performance
CREATE INDEX idx_supplier_templates_supplier_id ON supplier_templates(supplier_id);
CREATE INDEX idx_supplier_templates_user_id ON supplier_templates(user_id);
CREATE INDEX idx_supplier_templates_active ON supplier_templates(is_active) WHERE is_active = true;
CREATE INDEX idx_template_versions_template_id ON template_versions(template_id);
CREATE INDEX idx_supplier_category_mappings_supplier ON supplier_category_mappings(supplier_id, supplier_code);
CREATE INDEX idx_supplier_category_mappings_user ON supplier_category_mappings(user_id);

-- Enable RLS (Row Level Security)
ALTER TABLE supplier_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_category_mappings ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own templates" ON supplier_templates;
DROP POLICY IF EXISTS "Users can create their own templates" ON supplier_templates;
DROP POLICY IF EXISTS "Users can update their own templates" ON supplier_templates;
DROP POLICY IF EXISTS "Users can delete their own templates" ON supplier_templates;
DROP POLICY IF EXISTS "Users can view their own template versions" ON template_versions;
DROP POLICY IF EXISTS "Users can create their own template versions" ON template_versions;
DROP POLICY IF EXISTS "Users can view their own category mappings" ON supplier_category_mappings;
DROP POLICY IF EXISTS "Users can create their own category mappings" ON supplier_category_mappings;
DROP POLICY IF EXISTS "Users can update their own category mappings" ON supplier_category_mappings;
DROP POLICY IF EXISTS "Users can delete their own category mappings" ON supplier_category_mappings;

-- RLS Policies for supplier_templates
CREATE POLICY "Users can view their own templates"
    ON supplier_templates FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own templates"
    ON supplier_templates FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own templates"
    ON supplier_templates FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own templates"
    ON supplier_templates FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for template_versions
CREATE POLICY "Users can view their own template versions"
    ON template_versions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM supplier_templates
            WHERE supplier_templates.id = template_versions.template_id
            AND supplier_templates.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create their own template versions"
    ON template_versions FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM supplier_templates
            WHERE supplier_templates.id = template_versions.template_id
            AND supplier_templates.user_id = auth.uid()
        )
    );

-- RLS Policies for supplier_category_mappings
CREATE POLICY "Users can view their own category mappings"
    ON supplier_category_mappings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own category mappings"
    ON supplier_category_mappings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own category mappings"
    ON supplier_category_mappings FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own category mappings"
    ON supplier_category_mappings FOR DELETE
    USING (auth.uid() = user_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON supplier_templates TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON template_versions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON supplier_category_mappings TO authenticated;

-- Add columns to existing tables if they don't exist
DO $$ 
BEGIN
    -- Add supplier_id to file_uploads if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_uploads' AND column_name = 'supplier_id'
    ) THEN
        ALTER TABLE file_uploads ADD COLUMN supplier_id UUID REFERENCES suppliers(id);
        CREATE INDEX idx_file_uploads_supplier ON file_uploads(supplier_id);
    END IF;
    
    -- Add template_id to file_uploads if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_uploads' AND column_name = 'template_id'
    ) THEN
        ALTER TABLE file_uploads ADD COLUMN template_id UUID REFERENCES supplier_templates(id);
        CREATE INDEX idx_file_uploads_template ON file_uploads(template_id);
    END IF;
    
    -- Add template_applied to file_uploads if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_uploads' AND column_name = 'template_applied'
    ) THEN
        ALTER TABLE file_uploads ADD COLUMN template_applied BOOLEAN DEFAULT false;
    END IF;
    
    -- Add validation_errors to file_uploads if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_uploads' AND column_name = 'validation_errors'
    ) THEN
        ALTER TABLE file_uploads ADD COLUMN validation_errors JSONB;
    END IF;
END $$;

-- Comments
COMMENT ON TABLE supplier_templates IS 'Supplier-specific file templates with column mappings, calculations, and validation rules';
COMMENT ON TABLE template_versions IS 'Version history for template changes';
COMMENT ON TABLE supplier_category_mappings IS 'Lookup table for mapping supplier category codes to standardized categories';
COMMENT ON COLUMN supplier_templates.column_mappings IS 'JSON mapping of supplier column names to Habexa field names';
COMMENT ON COLUMN supplier_templates.calculations IS 'JSON array of calculated fields with formulas';
COMMENT ON COLUMN supplier_templates.filename_pattern IS 'Regex pattern for auto-detecting supplier from filename';
COMMENT ON COLUMN supplier_templates.column_fingerprint IS 'Array of unique column names for template matching';

