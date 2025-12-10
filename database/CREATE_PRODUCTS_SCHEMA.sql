-- ============================================
-- FRESH START: Drop existing tables/view first
-- ============================================
-- This will delete all existing products and deals data
DROP VIEW IF EXISTS product_deals CASCADE;
DROP TABLE IF EXISTS product_sources CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- ============================================
-- PRODUCTS TABLE (Parent - one per ASIN)
-- ============================================
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    asin VARCHAR(10) NOT NULL,
    
    -- Product info (from analysis)
    title TEXT,
    image_url TEXT,
    category TEXT,
    brand TEXT,
    
    -- Cached pricing (from analysis, for quick display)
    sell_price DECIMAL(10,2),
    fees_total DECIMAL(10,2),
    
    -- Market data (from analysis)
    bsr INTEGER,
    seller_count INTEGER,
    fba_seller_count INTEGER,
    amazon_sells BOOLEAN DEFAULT FALSE,
    
    -- Analysis link
    analysis_id UUID REFERENCES analyses(id),
    status TEXT DEFAULT 'pending',  -- pending, analyzed, error
    
    -- Meta
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, asin)
);

CREATE INDEX idx_products_user ON products(user_id);
CREATE INDEX idx_products_asin ON products(asin);
CREATE INDEX idx_products_status ON products(user_id, status);
CREATE INDEX idx_products_analysis ON products(analysis_id);

-- RLS
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own products" ON products
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own products" ON products
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own products" ON products
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own products" ON products
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- PRODUCT_SOURCES TABLE (Child - supplier deals)
-- ============================================
CREATE TABLE product_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    
    -- Deal specifics
    buy_cost DECIMAL(10,2),
    moq INTEGER DEFAULT 1,
    
    -- Source tracking
    source TEXT NOT NULL DEFAULT 'manual',  -- telegram, csv, manual, quick_analyze
    source_detail TEXT,                      -- channel name, filename, etc.
    
    -- Pipeline stage (per-deal, not per-product)
    stage TEXT DEFAULT 'new',  -- new, analyzing, reviewed, buy_list, ordered
    
    -- Notes
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Meta
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One deal per product per supplier
    UNIQUE(product_id, supplier_id)
);

CREATE INDEX idx_product_sources_product ON product_sources(product_id);
CREATE INDEX idx_product_sources_supplier ON product_sources(supplier_id);
CREATE INDEX idx_product_sources_stage ON product_sources(stage);
CREATE INDEX idx_product_sources_source ON product_sources(source);
CREATE INDEX idx_product_sources_active ON product_sources(product_id, is_active) WHERE is_active = TRUE;

-- Handle NULL supplier - only one "unknown supplier" deal per product
CREATE UNIQUE INDEX idx_product_sources_no_supplier 
ON product_sources(product_id) 
WHERE supplier_id IS NULL;

-- RLS (access via parent product)
ALTER TABLE product_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own product sources" ON product_sources
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM products WHERE products.id = product_sources.product_id AND products.user_id = auth.uid())
    );

CREATE POLICY "Users can insert own product sources" ON product_sources
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM products WHERE products.id = product_sources.product_id AND products.user_id = auth.uid())
    );

CREATE POLICY "Users can update own product sources" ON product_sources
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM products WHERE products.id = product_sources.product_id AND products.user_id = auth.uid())
    );

CREATE POLICY "Users can delete own product sources" ON product_sources
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM products WHERE products.id = product_sources.product_id AND products.user_id = auth.uid())
    );

-- ============================================
-- VIEW: Flattened view for easy querying
-- ============================================
CREATE OR REPLACE VIEW product_deals AS
SELECT 
    ps.id as deal_id,
    p.id as product_id,
    p.user_id,
    p.asin,
    p.title,
    p.image_url,
    p.sell_price,
    p.fees_total,
    p.bsr,
    p.seller_count,
    p.fba_seller_count,
    p.amazon_sells,
    p.status as product_status,
    p.analysis_id,
    ps.supplier_id,
    s.name as supplier_name,
    ps.buy_cost,
    ps.moq,
    ps.pack_size,
    ps.wholesale_cost,
    ps.percent_off,
    ps.promo_qty,
    ps.source,
    ps.source_detail,
    ps.stage,
    ps.notes,
    ps.is_active,
    ps.created_at as deal_created_at,
    ps.updated_at as deal_updated_at,
    -- Calculated fields
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
WHERE ps.is_active = TRUE;

-- ============================================
-- MIGRATE EXISTING DATA (Optional - only if telegram_deals exists)
-- ============================================
-- First, create products from existing telegram_deals
-- Extract data from analysis_data JSONB (since analyses table uses JSONB)
INSERT INTO products (user_id, asin, title, image_url, sell_price, fees_total, bsr, seller_count, fba_seller_count, amazon_sells, analysis_id, status, created_at)
SELECT DISTINCT ON (user_id, asin)
    td.user_id,
    td.asin,
    COALESCE(
        (a.analysis_data->>'product_title')::TEXT,
        (a.analysis_data->>'title')::TEXT,
        td.product_title
    ) as title,
    (a.analysis_data->>'image_url')::TEXT as image_url,
    COALESCE(
        (a.analysis_data->>'sell_price')::DECIMAL,
        (a.analysis_data->>'buy_box_price')::DECIMAL,
        (a.analysis_data->>'new_price')::DECIMAL
    ) as sell_price,
    COALESCE(
        ((a.analysis_data->>'referral_fee')::DECIMAL + (a.analysis_data->>'fba_fee')::DECIMAL),
        (a.analysis_data->>'fees_total')::DECIMAL,
        0
    ) as fees_total,
    COALESCE(
        (a.analysis_data->>'bsr')::INTEGER,
        (a.analysis_data->>'sales_rank')::INTEGER
    ) as bsr,
    (a.analysis_data->>'seller_count')::INTEGER as seller_count,
    (a.analysis_data->>'fba_seller_count')::INTEGER as fba_seller_count,
    COALESCE(
        (a.analysis_data->>'amazon_sells')::BOOLEAN,
        FALSE
    ) as amazon_sells,
    td.analysis_id,
    CASE 
        WHEN td.status = 'analyzed' THEN 'analyzed'
        ELSE 'pending'
    END as status,
    COALESCE(td.extracted_at, NOW())
FROM telegram_deals td
LEFT JOIN analyses a ON a.id = td.analysis_id
WHERE td.asin IS NOT NULL
ON CONFLICT (user_id, asin) DO UPDATE SET
    title = COALESCE(EXCLUDED.title, products.title),
    image_url = COALESCE(EXCLUDED.image_url, products.image_url),
    sell_price = COALESCE(EXCLUDED.sell_price, products.sell_price),
    fees_total = COALESCE(EXCLUDED.fees_total, products.fees_total),
    bsr = COALESCE(EXCLUDED.bsr, products.bsr),
    seller_count = COALESCE(EXCLUDED.seller_count, products.seller_count),
    fba_seller_count = COALESCE(EXCLUDED.fba_seller_count, products.fba_seller_count),
    amazon_sells = COALESCE(EXCLUDED.amazon_sells, products.amazon_sells),
    analysis_id = COALESCE(EXCLUDED.analysis_id, products.analysis_id),
    status = COALESCE(EXCLUDED.status, products.status),
    updated_at = NOW();

-- Then, create product_sources from telegram_deals
-- Get supplier_id from telegram_channels (which links to suppliers)
INSERT INTO product_sources (product_id, supplier_id, buy_cost, moq, source, source_detail, stage, notes, created_at)
SELECT 
    p.id as product_id,
    tc.supplier_id,  -- Get supplier_id from telegram_channels
    td.buy_cost,
    COALESCE(td.moq, 1),
    'telegram' as source,
    tc.channel_name as source_detail,
    CASE 
        WHEN td.status = 'analyzed' THEN 'reviewed' 
        WHEN td.stage IS NOT NULL THEN td.stage
        ELSE 'new' 
    END as stage,
    td.notes,
    COALESCE(td.extracted_at, NOW())
FROM telegram_deals td
JOIN products p ON p.user_id = td.user_id AND p.asin = td.asin
LEFT JOIN telegram_channels tc ON tc.id = td.channel_id
WHERE td.asin IS NOT NULL
ON CONFLICT (product_id, supplier_id) DO UPDATE SET
    buy_cost = COALESCE(EXCLUDED.buy_cost, product_sources.buy_cost),
    moq = COALESCE(EXCLUDED.moq, product_sources.moq),
    source_detail = COALESCE(EXCLUDED.source_detail, product_sources.source_detail),
    notes = COALESCE(EXCLUDED.notes, product_sources.notes),
    updated_at = NOW();

-- Handle NULL supplier conflicts separately (partial index)
-- Note: This is handled by the partial unique index automatically
