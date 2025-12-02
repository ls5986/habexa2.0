-- ============================================
-- ENSURE BRANDS TABLE EXISTS
-- ============================================
-- Creates the brands table if it doesn't exist
-- Used for tracking brand ungating status
-- ============================================

CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    is_ungated BOOLEAN DEFAULT FALSE,
    ungated_at TIMESTAMPTZ,
    category TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, name)
);

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_brands_user ON brands(user_id);
CREATE INDEX IF NOT EXISTS idx_brands_ungated ON brands(user_id, is_ungated);

-- Enable RLS
ALTER TABLE brands ENABLE ROW LEVEL SECURITY;

-- Create policies if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'brands' 
        AND policyname = 'Users can manage own brands'
    ) THEN
        CREATE POLICY "Users can manage own brands" ON brands
            FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

-- Add comment
COMMENT ON TABLE brands IS 'Brand tracking for ungating status - tracks which brands users are ungated for';

