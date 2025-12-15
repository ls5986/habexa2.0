-- ============================================
-- HABEXA - COMPLETE DATABASE MIGRATION
-- ============================================
-- This file contains ALL migrations combined into one
-- Run this entire file in Supabase SQL Editor
-- 
-- Date: December 12, 2024
-- Total Migrations: 11
-- 
-- WARNING: This is a large migration. Run in Supabase SQL Editor.
-- Estimated time: 2-5 minutes depending on database size
-- ============================================

-- ============================================
-- MIGRATION 1: RECOMMENDATION SYSTEM
-- ============================================
-- Intelligent Order Recommendations System
-- AI-powered "What Should I Buy?" recommendation engine

-- 1. RECOMMENDATION CONFIGS
CREATE TABLE IF NOT EXISTS recommendation_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    goal_type TEXT NOT NULL CHECK (goal_type IN (
        'meet_minimum', 'target_profit', 'restock_inventory', 'custom'
    )),
    goal_params JSONB NOT NULL,
    min_roi DECIMAL(5,2) DEFAULT 25.00,
    max_fba_sellers INTEGER DEFAULT 30,
    max_days_to_sell INTEGER DEFAULT 60,
    avoid_hazmat BOOLEAN DEFAULT true,
    pricing_mode TEXT DEFAULT '365d_avg' CHECK (pricing_mode IN ('current', '30d_avg', '90d_avg', '365d_avg')),
    fast_mover_pct INTEGER DEFAULT 60,
    medium_mover_pct INTEGER DEFAULT 30,
    slow_mover_pct INTEGER DEFAULT 10,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, supplier_id, name)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_configs_user ON recommendation_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_configs_supplier ON recommendation_configs(supplier_id);

-- 2. RECOMMENDATION RUNS
CREATE TABLE IF NOT EXISTS recommendation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    config_id UUID REFERENCES recommendation_configs(id) ON DELETE SET NULL,
    goal_type TEXT NOT NULL,
    goal_params JSONB NOT NULL,
    total_products_analyzed INTEGER DEFAULT 0,
    products_passed_filters INTEGER DEFAULT 0,
    products_failed_filters INTEGER DEFAULT 0,
    recommended_product_count INTEGER DEFAULT 0,
    total_investment DECIMAL(10,2) DEFAULT 0,
    expected_profit DECIMAL(10,2) DEFAULT 0,
    expected_roi DECIMAL(5,2) DEFAULT 0,
    avg_days_to_sell DECIMAL(5,1) DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_runs_user ON recommendation_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_runs_supplier ON recommendation_runs(supplier_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_runs_status ON recommendation_runs(status);

-- 3. RECOMMENDATION RESULTS
CREATE TABLE IF NOT EXISTS recommendation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    run_id UUID REFERENCES recommendation_runs(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    product_source_id UUID REFERENCES product_sources(id) ON DELETE CASCADE,
    total_score DECIMAL(5,2) NOT NULL,
    profitability_score DECIMAL(5,2) DEFAULT 0,
    velocity_score DECIMAL(5,2) DEFAULT 0,
    competition_score DECIMAL(5,2) DEFAULT 0,
    risk_score DECIMAL(5,2) DEFAULT 0,
    recommended_quantity INTEGER NOT NULL,
    recommended_cost DECIMAL(10,2) NOT NULL,
    expected_profit DECIMAL(10,2) NOT NULL,
    expected_roi DECIMAL(5,2) NOT NULL,
    days_to_sell DECIMAL(5,1) NOT NULL,
    mover_category TEXT CHECK (mover_category IN ('fast', 'medium', 'slow')),
    why_recommended JSONB DEFAULT '[]',
    warnings JSONB DEFAULT '[]',
    is_selected BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_results_run ON recommendation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_results_product ON recommendation_results(product_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_results_score ON recommendation_results(total_score DESC);

-- 4. FILTER FAILURE LOG
CREATE TABLE IF NOT EXISTS recommendation_filter_failures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES recommendation_runs(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    filter_name TEXT NOT NULL,
    filter_value TEXT,
    threshold_value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_filter_failures_run ON recommendation_filter_failures(run_id);

-- 5. PRODUCT SCORES
ALTER TABLE products
ADD COLUMN IF NOT EXISTS recommendation_score DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS recommendation_score_breakdown JSONB,
ADD COLUMN IF NOT EXISTS recommendation_score_calculated_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_products_recommendation_score ON products(recommendation_score DESC) 
  WHERE recommendation_score IS NOT NULL;

-- ============================================
-- MIGRATION 2: PACK VARIANTS & PREP INSTRUCTIONS
-- ============================================

-- 1. PRODUCT PACK VARIANTS
CREATE TABLE IF NOT EXISTS product_pack_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    asin TEXT NOT NULL,
    pack_size INTEGER NOT NULL CHECK (pack_size > 0),
    current_price DECIMAL(10,2),
    buy_box_price_365d_avg DECIMAL(10,2),
    buy_box_price_90d_avg DECIMAL(10,2),
    buy_box_price_30d_avg DECIMAL(10,2),
    lowest_price_365d DECIMAL(10,2),
    profit_per_unit DECIMAL(10,2),
    roi DECIMAL(10,2),
    margin DECIMAL(10,2),
    total_profit DECIMAL(10,2),
    is_recommended BOOLEAN DEFAULT FALSE,
    recommendation_reason TEXT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(product_id, pack_size),
    CONSTRAINT valid_pack_size CHECK (pack_size BETWEEN 1 AND 100)
);

CREATE INDEX IF NOT EXISTS idx_pack_variants_product_id ON product_pack_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_pack_variants_asin ON product_pack_variants(asin);
CREATE INDEX IF NOT EXISTS idx_pack_variants_recommended ON product_pack_variants(is_recommended) WHERE is_recommended = TRUE;

-- 2. PREP INSTRUCTIONS
CREATE TABLE IF NOT EXISTS prep_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_item_id UUID REFERENCES supplier_order_items(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    expected_units INTEGER NOT NULL,
    target_pack_size INTEGER NOT NULL,
    packs_to_create INTEGER NOT NULL,
    leftover_units INTEGER DEFAULT 0,
    profit_per_unit DECIMAL(10,2),
    total_profit DECIMAL(10,2),
    roi DECIMAL(10,2),
    prep_steps JSONB DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'in_progress', 'completed', 'cancelled')),
    pdf_url TEXT,
    pdf_generated_at TIMESTAMP WITH TIME ZONE,
    email_sent_at TIMESTAMP WITH TIME ZONE,
    email_recipient TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prep_instructions_order_item ON prep_instructions(order_item_id);
CREATE INDEX IF NOT EXISTS idx_prep_instructions_product ON prep_instructions(product_id);

-- 3. ADD PRICING COLUMNS TO PRODUCTS
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS buy_box_price_365d_avg DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS buy_box_price_90d_avg DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS buy_box_price_30d_avg DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS pricing_mode TEXT DEFAULT 'current' CHECK (pricing_mode IN ('current', '30d_avg', '90d_avg', '365d_avg'));

CREATE INDEX IF NOT EXISTS idx_products_pricing_mode ON products(pricing_mode);

-- 4. ADD PACK VARIANT TRACKING TO PRODUCT_SOURCES
ALTER TABLE product_sources
ADD COLUMN IF NOT EXISTS available_pack_sizes INTEGER[] DEFAULT ARRAY[1],
ADD COLUMN IF NOT EXISTS recommended_pack_size INTEGER,
ADD COLUMN IF NOT EXISTS pack_variants_calculated_at TIMESTAMP WITH TIME ZONE;

-- ============================================
-- MIGRATION 3: BRAND RESTRICTIONS
-- ============================================

-- 1. BRAND RESTRICTIONS TABLE
CREATE TABLE IF NOT EXISTS brand_restrictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_name TEXT NOT NULL,
    brand_name_normalized TEXT NOT NULL,
    restriction_type TEXT NOT NULL CHECK (restriction_type IN (
        'globally_gated', 'seller_specific', 'category_gated', 'ungated'
    )),
    category TEXT,
    notes TEXT,
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by TEXT,
    verification_source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(brand_name_normalized)
);

CREATE INDEX IF NOT EXISTS idx_brand_restrictions_name ON brand_restrictions(brand_name_normalized);

-- 2. SUPPLIER BRAND OVERRIDES
CREATE TABLE IF NOT EXISTS supplier_brand_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    brand_name TEXT NOT NULL,
    brand_name_normalized TEXT NOT NULL,
    override_type TEXT NOT NULL CHECK (override_type IN (
        'can_sell', 'cannot_sell', 'requires_approval'
    )),
    approval_status TEXT CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approval_date TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    supplier_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(supplier_id, brand_name_normalized)
);

CREATE INDEX IF NOT EXISTS idx_supplier_brand_overrides_supplier ON supplier_brand_overrides(supplier_id);

-- 3. PRODUCT BRAND FLAGS
CREATE TABLE IF NOT EXISTS product_brand_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    brand_name TEXT NOT NULL,
    brand_status TEXT NOT NULL CHECK (brand_status IN (
        'unrestricted', 'supplier_restricted', 'globally_restricted', 'requires_approval', 'unknown'
    )),
    restriction_id UUID REFERENCES brand_restrictions(id),
    override_id UUID REFERENCES supplier_brand_overrides(id),
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    detection_method TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(product_id, brand_name)
);

CREATE INDEX IF NOT EXISTS idx_product_brand_flags_product ON product_brand_flags(product_id);
CREATE INDEX IF NOT EXISTS idx_product_brand_flags_status ON product_brand_flags(brand_status);

-- ============================================
-- MIGRATION 4: COST TYPE & CASE SIZE
-- ============================================

ALTER TABLE product_sources
ADD COLUMN IF NOT EXISTS cost_type TEXT DEFAULT 'unit' CHECK (cost_type IN ('unit', 'pack', 'case')),
ADD COLUMN IF NOT EXISTS case_size INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS pack_size_for_cost INTEGER DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_product_sources_cost_type ON product_sources(cost_type);

ALTER TABLE products
ADD COLUMN IF NOT EXISTS amazon_pack_size INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS cost_per_amazon_unit DECIMAL(10,2);

-- ============================================
-- MIGRATION 5: PO EMAIL SYSTEM
-- ============================================

-- 1. EMAIL TEMPLATES
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL,
    body_html TEXT,
    is_default BOOLEAN DEFAULT false,
    cc_emails TEXT[],
    bcc_emails TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, supplier_id, name)
);

CREATE INDEX IF NOT EXISTS idx_email_templates_user ON email_templates(user_id);

-- 2. PO GENERATIONS
CREATE TABLE IF NOT EXISTS po_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE CASCADE NOT NULL,
    po_number TEXT NOT NULL UNIQUE,
    pdf_url TEXT,
    pdf_filename TEXT,
    email_template_id UUID REFERENCES email_templates(id),
    email_sent_at TIMESTAMP WITH TIME ZONE,
    email_subject TEXT,
    email_recipient TEXT,
    email_cc TEXT[],
    email_bcc TEXT[],
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'opened', 'bounced', 'failed')),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_po_generations_order ON po_generations(supplier_order_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_po_generations_po_number ON po_generations(po_number);

-- 3. EMAIL TRACKING
CREATE TABLE IF NOT EXISTS email_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    po_generation_id UUID REFERENCES po_generations(id) ON DELETE CASCADE,
    email_id TEXT,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    opened_count INTEGER DEFAULT 0,
    clicked_at TIMESTAMP WITH TIME ZONE,
    clicked_count INTEGER DEFAULT 0,
    bounced_at TIMESTAMP WITH TIME ZONE,
    bounced_reason TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_tracking_po ON email_tracking(po_generation_id);

-- ============================================
-- MIGRATION 6: INVENTORY FORECASTING
-- ============================================

-- 1. INVENTORY SNAPSHOTS
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    fba_fulfillable_qty INTEGER DEFAULT 0,
    fba_inbound_working_qty INTEGER DEFAULT 0,
    fba_inbound_shipped_qty INTEGER DEFAULT 0,
    fba_reserved_qty INTEGER DEFAULT 0,
    fba_unsellable_qty INTEGER DEFAULT 0,
    fba_total_qty INTEGER DEFAULT 0,
    available_qty INTEGER DEFAULT 0,
    total_inbound_qty INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, product_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_product ON inventory_snapshots(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_date ON inventory_snapshots(snapshot_date DESC);

-- 2. INVENTORY FORECASTS
CREATE TABLE IF NOT EXISTS inventory_forecasts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    avg_daily_sales DECIMAL(10,2) DEFAULT 0,
    sales_velocity_7d DECIMAL(10,2) DEFAULT 0,
    sales_velocity_30d DECIMAL(10,2) DEFAULT 0,
    sales_velocity_90d DECIMAL(10,2) DEFAULT 0,
    lead_time_days INTEGER DEFAULT 14,
    safety_stock_days INTEGER DEFAULT 7,
    reorder_point INTEGER DEFAULT 0,
    months_coverage DECIMAL(3,1) DEFAULT 2.0,
    optimal_order_qty INTEGER DEFAULT 0,
    current_fba_qty INTEGER DEFAULT 0,
    days_of_inventory_remaining DECIMAL(5,1) DEFAULT 0,
    projected_stockout_date DATE,
    status TEXT DEFAULT 'healthy' CHECK (status IN (
        'out_of_stock', 'reorder_now', 'low_stock', 'healthy', 'overstock'
    )),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_forecasts_product ON inventory_forecasts(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_forecasts_status ON inventory_forecasts(status);

-- 3. REORDER ALERTS
CREATE TABLE IF NOT EXISTS reorder_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN (
        'reorder_point', 'out_of_stock', 'overstock', 'slow_moving'
    )),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    message TEXT NOT NULL,
    suggested_order_qty INTEGER,
    estimated_stockout_date DATE,
    is_read BOOLEAN DEFAULT false,
    is_dismissed BOOLEAN DEFAULT false,
    is_actioned BOOLEAN DEFAULT false,
    actioned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    alert_date DATE DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_reorder_alerts_user ON reorder_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_reorder_alerts_unread ON reorder_alerts(user_id, is_read) WHERE is_read = false;
CREATE UNIQUE INDEX IF NOT EXISTS idx_reorder_alerts_unique ON reorder_alerts(user_id, product_id, alert_type, alert_date);

-- ============================================
-- MIGRATION 7: SHIPPING COST PROFILES
-- ============================================

CREATE TABLE IF NOT EXISTS shipping_cost_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    cost_type TEXT NOT NULL CHECK (cost_type IN (
        'flat_rate', 'per_pound', 'per_unit', 'tiered', 'percentage', 'free_above'
    )),
    cost_params JSONB NOT NULL,
    free_shipping_threshold DECIMAL(10,2),
    min_shipping_cost DECIMAL(10,2) DEFAULT 0,
    max_shipping_cost DECIMAL(10,2),
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, supplier_id, name)
);

CREATE INDEX IF NOT EXISTS idx_shipping_profiles_supplier ON shipping_cost_profiles(supplier_id);

ALTER TABLE product_sources
ADD COLUMN IF NOT EXISTS shipping_cost_per_unit DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS shipping_profile_id UUID REFERENCES shipping_cost_profiles(id),
ADD COLUMN IF NOT EXISTS total_landed_cost DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS profit_after_shipping DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS roi_after_shipping DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS margin_after_shipping DECIMAL(5,2);

-- ============================================
-- MIGRATION 8: SUPPLIER PERFORMANCE
-- ============================================

-- 1. SUPPLIER PERFORMANCE
CREATE TABLE IF NOT EXISTS supplier_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_spend DECIMAL(12,2) DEFAULT 0,
    average_order_value DECIMAL(10,2) DEFAULT 0,
    total_products_ordered INTEGER DEFAULT 0,
    total_units_ordered INTEGER DEFAULT 0,
    orders_delivered_on_time INTEGER DEFAULT 0,
    orders_delivered_late INTEGER DEFAULT 0,
    orders_delivered_early INTEGER DEFAULT 0,
    on_time_delivery_rate DECIMAL(5,2) DEFAULT 0,
    average_delivery_days INTEGER DEFAULT 0,
    total_units_received INTEGER DEFAULT 0,
    damaged_units INTEGER DEFAULT 0,
    missing_units INTEGER DEFAULT 0,
    quality_issue_rate DECIMAL(5,2) DEFAULT 0,
    total_profit_generated DECIMAL(12,2) DEFAULT 0,
    average_roi DECIMAL(5,2) DEFAULT 0,
    average_margin DECIMAL(5,2) DEFAULT 0,
    delivery_rating DECIMAL(2,1) DEFAULT 0 CHECK (delivery_rating BETWEEN 0 AND 5),
    quality_rating DECIMAL(2,1) DEFAULT 0 CHECK (quality_rating BETWEEN 0 AND 5),
    profitability_rating DECIMAL(2,1) DEFAULT 0 CHECK (profitability_rating BETWEEN 0 AND 5),
    communication_rating DECIMAL(2,1) DEFAULT 0 CHECK (communication_rating BETWEEN 0 AND 5),
    overall_rating DECIMAL(2,1) DEFAULT 0 CHECK (overall_rating BETWEEN 0 AND 5),
    best_selling_products JSONB DEFAULT '[]',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_type TEXT DEFAULT 'all_time' CHECK (period_type IN ('all_time', 'year', 'quarter', 'month')),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, supplier_id, period_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_supplier_performance_supplier ON supplier_performance(supplier_id);

-- 2. ORDER VARIANCES
CREATE TABLE IF NOT EXISTS order_variances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE CASCADE NOT NULL,
    supplier_order_item_id UUID REFERENCES supplier_order_items(id) ON DELETE CASCADE NOT NULL,
    ordered_quantity INTEGER NOT NULL,
    received_quantity INTEGER DEFAULT 0,
    variance_quantity INTEGER DEFAULT 0,
    damaged_quantity INTEGER DEFAULT 0,
    missing_quantity INTEGER DEFAULT 0,
    defective_quantity INTEGER DEFAULT 0,
    variance_amount DECIMAL(10,2) DEFAULT 0,
    refund_amount DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_variances_order ON order_variances(supplier_order_id);

-- ============================================
-- MIGRATION 9: FINANCIAL TRACKING
-- ============================================

-- 1. FINANCIAL TRANSACTIONS
CREATE TABLE IF NOT EXISTS financial_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN (
        'purchase', 'sale', 'fee', 'shipping', 'tpl_fee', 'refund', 'reimbursement', 'adjustment'
    )),
    amount DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE SET NULL,
    sale_id TEXT,
    description TEXT,
    category TEXT,
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    posted_date DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_financial_transactions_user ON financial_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_type ON financial_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_financial_transactions_date ON financial_transactions(transaction_date DESC);

-- 2. P&L SUMMARIES
CREATE TABLE IF NOT EXISTS pl_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_type TEXT DEFAULT 'month' CHECK (period_type IN ('month', 'quarter', 'year')),
    total_revenue DECIMAL(12,2) DEFAULT 0,
    total_sales_count INTEGER DEFAULT 0,
    total_cogs DECIMAL(12,2) DEFAULT 0,
    total_purchases DECIMAL(12,2) DEFAULT 0,
    total_amazon_fees DECIMAL(12,2) DEFAULT 0,
    total_shipping_costs DECIMAL(12,2) DEFAULT 0,
    total_tpl_fees DECIMAL(12,2) DEFAULT 0,
    total_other_expenses DECIMAL(12,2) DEFAULT 0,
    total_refunds DECIMAL(12,2) DEFAULT 0,
    total_reimbursements DECIMAL(12,2) DEFAULT 0,
    net_profit DECIMAL(12,2) DEFAULT 0,
    profit_margin DECIMAL(5,2) DEFAULT 0,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, period_start, period_end, period_type)
);

CREATE INDEX IF NOT EXISTS idx_pl_summaries_user ON pl_summaries(user_id);

-- ============================================
-- MIGRATION 10: USER PREFERENCES
-- ============================================

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS default_pricing_mode TEXT DEFAULT '365d_avg' CHECK (default_pricing_mode IN ('current', '30d_avg', '90d_avg', '365d_avg')),
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- ============================================
-- MIGRATION 11: UPLOAD TEMPLATES
-- ============================================

CREATE TABLE IF NOT EXISTS upload_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    column_mappings JSONB NOT NULL,
    default_values JSONB DEFAULT '{}'::jsonb,
    validation_rules JSONB DEFAULT '[]'::jsonb,
    transformations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, supplier_id, name)
);

CREATE INDEX IF NOT EXISTS idx_upload_templates_user ON upload_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_upload_templates_supplier ON upload_templates(supplier_id);

-- ============================================
-- ✅ MIGRATION COMPLETE
-- ============================================
-- All 11 migrations have been applied
-- 
-- Next steps:
-- 1. Verify all tables were created
-- 2. Test backend services
-- 3. Test frontend components
-- ============================================

