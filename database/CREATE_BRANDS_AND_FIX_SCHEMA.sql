-- ============================================
-- FRESH START - Drop existing tables
-- ============================================
DROP VIEW IF EXISTS product_deals CASCADE;
DROP TABLE IF EXISTS product_sources CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS brands CASCADE;

-- ============================================
-- BRANDS TABLE (for ungating tracking)
-- ============================================
CREATE TABLE brands (
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

CREATE INDEX idx_brands_user ON brands(user_id);
CREATE INDEX idx_brands_ungated ON brands(user_id, is_ungated);

ALTER TABLE brands ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own brands" ON brands
    FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- UPDATE SUPPLIERS TABLE (add missing fields)
-- ============================================
-- Add columns if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'suppliers' AND column_name = 'contact_name') THEN
        ALTER TABLE suppliers ADD COLUMN contact_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'suppliers' AND column_name = 'email') THEN
        ALTER TABLE suppliers ADD COLUMN email TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'suppliers' AND column_name = 'phone') THEN
        ALTER TABLE suppliers ADD COLUMN phone TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'suppliers' AND column_name = 'website') THEN
        ALTER TABLE suppliers ADD COLUMN website TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'suppliers' AND column_name = 'payment_terms') THEN
        ALTER TABLE suppliers ADD COLUMN payment_terms TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'suppliers' AND column_name = 'notes') THEN
        ALTER TABLE suppliers ADD COLUMN notes TEXT;
    END IF;
END $$;

-- ============================================
-- PRODUCTS TABLE (one per ASIN)
-- ============================================
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    asin VARCHAR(10) NOT NULL,
    
    -- Product info
    title TEXT,
    image_url TEXT,
    category TEXT,
    
    -- Brand link (for ungating)
    brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
    brand_name TEXT,  -- Cached for display
    
    -- Pricing (from analysis)
    sell_price DECIMAL(10,2),
    fees_total DECIMAL(10,2),
    
    -- Market data
    bsr INTEGER,
    seller_count INTEGER,
    fba_seller_count INTEGER,
    amazon_sells BOOLEAN DEFAULT FALSE,
    
    -- Analysis
    analysis_id UUID REFERENCES analyses(id),
    status TEXT DEFAULT 'pending',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, asin)
);

CREATE INDEX idx_products_user ON products(user_id);
CREATE INDEX idx_products_asin ON products(asin);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_products_status ON products(user_id, status);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own products" ON products
    FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- PRODUCT_SOURCES TABLE (deals from suppliers)
-- ============================================
CREATE TABLE product_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    
    -- Deal details
    buy_cost DECIMAL(10,2),
    moq INTEGER DEFAULT 1,
    
    -- Source tracking
    source TEXT NOT NULL DEFAULT 'manual',  -- telegram, csv, manual
    source_detail TEXT,  -- channel name, filename
    
    -- Pipeline
    stage TEXT DEFAULT 'new',
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(product_id, supplier_id)
);

CREATE UNIQUE INDEX idx_product_sources_no_supplier 
ON product_sources(product_id) 
WHERE supplier_id IS NULL;

CREATE INDEX idx_product_sources_product ON product_sources(product_id);
CREATE INDEX idx_product_sources_supplier ON product_sources(supplier_id);
CREATE INDEX idx_product_sources_stage ON product_sources(stage);

ALTER TABLE product_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own product sources" ON product_sources
    FOR ALL USING (EXISTS (
        SELECT 1 FROM products WHERE products.id = product_sources.product_id AND products.user_id = auth.uid()
    ));

-- ============================================
-- VIEW: Flattened deals with calculated fields
-- ============================================
CREATE OR REPLACE VIEW product_deals AS
SELECT 
    ps.id as deal_id,
    p.id as product_id,
    p.user_id,
    p.asin,
    p.title,
    p.image_url,
    p.category,
    p.brand_id,
    p.brand_name,
    b.is_ungated as brand_ungated,
    p.sell_price,
    p.fees_total,
    p.bsr,
    p.seller_count,
    p.amazon_sells,
    p.status as product_status,
    p.analysis_id,
    ps.supplier_id,
    s.name as supplier_name,
    ps.buy_cost,
    ps.moq,
    ps.source,
    ps.source_detail,
    ps.stage,
    ps.notes,
    ps.is_active,
    ps.created_at as deal_created_at,
    -- Calculated
    CASE 
        WHEN ps.buy_cost > 0 AND p.sell_price > 0 THEN 
            ROUND(p.sell_price - COALESCE(p.fees_total, 0) - ps.buy_cost, 2)
        ELSE NULL 
    END as profit,
    CASE 
        WHEN ps.buy_cost > 0 AND p.sell_price > 0 THEN 
            ROUND(((p.sell_price - COALESCE(p.fees_total, 0) - ps.buy_cost) / ps.buy_cost) * 100, 1)
        ELSE NULL 
    END as roi,
    CASE 
        WHEN ps.buy_cost > 0 THEN 
            ROUND(ps.buy_cost * ps.moq, 2)
        ELSE NULL 
    END as total_investment
FROM product_sources ps
JOIN products p ON p.id = ps.product_id
LEFT JOIN suppliers s ON s.id = ps.supplier_id
LEFT JOIN brands b ON b.id = p.brand_id
WHERE ps.is_active = TRUE;

