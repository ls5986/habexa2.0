-- Drop if exists to start fresh
DROP TABLE IF EXISTS products;

-- Create unified products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    asin VARCHAR(10) NOT NULL,
    buy_cost DECIMAL(10,2),
    moq INTEGER DEFAULT 1,
    supplier_id UUID REFERENCES suppliers(id),
    
    -- Source tracking
    source TEXT NOT NULL DEFAULT 'manual',  -- 'telegram', 'csv', 'manual', 'quick_analyze'
    source_detail TEXT,                      -- Channel name, filename, etc.
    
    -- Pipeline
    stage TEXT DEFAULT 'new',  -- 'new', 'analyzing', 'reviewed', 'buy_list', 'ordered'
    status TEXT DEFAULT 'pending',  -- 'pending', 'analyzed', 'error'
    
    -- Links
    analysis_id UUID REFERENCES analyses(id),
    
    -- Meta
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- CORRECT UNIQUE: Same ASIN from different suppliers = different products
    -- supplier_id can be NULL for unknown supplier
    UNIQUE(user_id, asin, supplier_id)
);

-- Indexes
CREATE INDEX idx_products_user ON products(user_id);
CREATE INDEX idx_products_stage ON products(user_id, stage);
CREATE INDEX idx_products_source ON products(user_id, source);
CREATE INDEX idx_products_asin ON products(asin);
CREATE INDEX idx_products_supplier ON products(supplier_id);

-- Handle NULL supplier case - only one product per ASIN when supplier is unknown
-- PostgreSQL unique constraints don't work with NULL (NULL != NULL), so we need a partial index
-- This ensures: (user_id, asin, NULL) is unique
CREATE UNIQUE INDEX idx_products_user_asin_no_supplier 
ON products(user_id, asin) 
WHERE supplier_id IS NULL;

-- Handle NULL supplier case - only one product per ASIN when supplier is unknown
-- PostgreSQL unique constraints don't work with NULL (NULL != NULL), so we need a partial index
CREATE UNIQUE INDEX idx_products_user_asin_no_supplier 
ON products(user_id, asin) 
WHERE supplier_id IS NULL;

-- Migrate existing telegram_deals
-- Note: For NULL supplier_id, conflicts are handled by the partial unique index
INSERT INTO products (user_id, asin, buy_cost, moq, supplier_id, source, source_detail, stage, status, analysis_id, created_at, updated_at)
SELECT 
    user_id,
    asin,
    buy_cost,
    COALESCE(moq, 1) as moq,
    supplier_id,
    'telegram' as source,
    (SELECT channel_name FROM telegram_channels WHERE id = telegram_deals.channel_id) as source_detail,
    CASE 
        WHEN status = 'analyzed' THEN 'reviewed' 
        WHEN stage IS NOT NULL THEN stage
        ELSE 'new' 
    END as stage,
    COALESCE(status, 'pending') as status,
    analysis_id,
    COALESCE(extracted_at, NOW()) as created_at,
    NOW() as updated_at
FROM telegram_deals
WHERE asin IS NOT NULL
ON CONFLICT (user_id, asin, supplier_id) DO UPDATE SET
    buy_cost = EXCLUDED.buy_cost,
    moq = EXCLUDED.moq,
    updated_at = NOW()
-- Handle NULL supplier conflicts separately (partial index)
ON CONFLICT ON CONSTRAINT idx_products_user_asin_no_supplier DO UPDATE SET
    buy_cost = EXCLUDED.buy_cost,
    moq = EXCLUDED.moq,
    updated_at = NOW();

-- Add RLS policies
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own products"
    ON products FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own products"
    ON products FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own products"
    ON products FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own products"
    ON products FOR DELETE
    USING (auth.uid() = user_id);

