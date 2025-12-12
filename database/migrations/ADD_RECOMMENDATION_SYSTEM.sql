-- HABEXA: Intelligent Order Recommendations System
-- AI-powered "What Should I Buy?" recommendation engine

-- ============================================
-- 1. RECOMMENDATION CONFIGS
-- ============================================
-- User preferences and saved recommendation configurations
CREATE TABLE IF NOT EXISTS recommendation_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    
    -- Config Name
    name TEXT NOT NULL, -- e.g., "KEHE Monthly Order"
    
    -- Goal Type
    goal_type TEXT NOT NULL CHECK (goal_type IN (
        'meet_minimum',      -- Meet supplier minimum order
        'target_profit',     -- Hit specific profit target
        'restock_inventory', -- Restock low inventory
        'custom'             -- Custom rules
    )),
    
    -- Goal Parameters (JSONB for flexibility)
    goal_params JSONB NOT NULL, -- {
    --   "budget": 2000,
    --   "profit_target": 10000,
    --   "days": 30,
    --   "urgency": "critical"
    -- }
    
    -- Constraints
    min_roi DECIMAL(5,2) DEFAULT 25.00,
    max_fba_sellers INTEGER DEFAULT 30,
    max_days_to_sell INTEGER DEFAULT 60,
    avoid_hazmat BOOLEAN DEFAULT true,
    pricing_mode TEXT DEFAULT '365d_avg' CHECK (pricing_mode IN ('current', '30d_avg', '90d_avg', '365d_avg')),
    
    -- Portfolio Balance (for profit target goal)
    fast_mover_pct INTEGER DEFAULT 60, -- % of order in fast movers
    medium_mover_pct INTEGER DEFAULT 30,
    slow_mover_pct INTEGER DEFAULT 10,
    
    -- Metadata
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, supplier_id, name)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_configs_user ON recommendation_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_configs_supplier ON recommendation_configs(supplier_id);

-- ============================================
-- 2. RECOMMENDATION RUNS
-- ============================================
-- Track each recommendation generation
CREATE TABLE IF NOT EXISTS recommendation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    config_id UUID REFERENCES recommendation_configs(id) ON DELETE SET NULL,
    
    -- Goal
    goal_type TEXT NOT NULL,
    goal_params JSONB NOT NULL,
    
    -- Input Stats
    total_products_analyzed INTEGER DEFAULT 0,
    products_passed_filters INTEGER DEFAULT 0,
    products_failed_filters INTEGER DEFAULT 0,
    
    -- Results Summary
    recommended_product_count INTEGER DEFAULT 0,
    total_investment DECIMAL(10,2) DEFAULT 0,
    expected_profit DECIMAL(10,2) DEFAULT 0,
    expected_roi DECIMAL(5,2) DEFAULT 0,
    avg_days_to_sell DECIMAL(5,1) DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    
    -- Metadata
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_runs_user ON recommendation_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_runs_supplier ON recommendation_runs(supplier_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_runs_status ON recommendation_runs(status);
CREATE INDEX IF NOT EXISTS idx_recommendation_runs_created ON recommendation_runs(created_at DESC);

-- ============================================
-- 3. RECOMMENDATION RESULTS
-- ============================================
-- Individual product recommendations in a run
CREATE TABLE IF NOT EXISTS recommendation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    run_id UUID REFERENCES recommendation_runs(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    product_source_id UUID REFERENCES product_sources(id) ON DELETE CASCADE,
    
    -- Scoring
    total_score DECIMAL(5,2) NOT NULL, -- 0-100
    profitability_score DECIMAL(5,2) DEFAULT 0, -- 0-40
    velocity_score DECIMAL(5,2) DEFAULT 0, -- 0-30
    competition_score DECIMAL(5,2) DEFAULT 0, -- 0-15
    risk_score DECIMAL(5,2) DEFAULT 0, -- 0-15
    
    -- Recommendation
    recommended_quantity INTEGER NOT NULL,
    recommended_cost DECIMAL(10,2) NOT NULL,
    expected_profit DECIMAL(10,2) NOT NULL,
    expected_roi DECIMAL(5,2) NOT NULL,
    days_to_sell DECIMAL(5,1) NOT NULL,
    
    -- Category (for portfolio balance)
    mover_category TEXT CHECK (mover_category IN ('fast', 'medium', 'slow')),
    
    -- Reasoning (JSONB array of strings)
    why_recommended JSONB DEFAULT '[]', -- ["High ROI", "Fast mover", "Low competition"]
    warnings JSONB DEFAULT '[]', -- ["Price spike", "Volatile"]
    
    -- Status
    is_selected BOOLEAN DEFAULT true, -- User can deselect
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_results_run ON recommendation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_results_product ON recommendation_results(product_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_results_score ON recommendation_results(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_recommendation_results_user ON recommendation_results(user_id);

-- ============================================
-- 4. FILTER FAILURE LOG
-- ============================================
-- Track why products were excluded (for transparency)
CREATE TABLE IF NOT EXISTS recommendation_filter_failures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES recommendation_runs(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    
    -- Failure Reason
    filter_name TEXT NOT NULL, -- 'brand_restricted', 'roi_too_low', 'too_many_sellers', etc.
    filter_value TEXT, -- Actual value that caused failure
    threshold_value TEXT, -- Threshold that was exceeded
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_filter_failures_run ON recommendation_filter_failures(run_id);
CREATE INDEX IF NOT EXISTS idx_filter_failures_product ON recommendation_filter_failures(product_id);

-- ============================================
-- 5. PRODUCT SCORES (Cached)
-- ============================================
-- Cache calculated scores for performance
ALTER TABLE products
ADD COLUMN IF NOT EXISTS recommendation_score DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS recommendation_score_breakdown JSONB,
ADD COLUMN IF NOT EXISTS recommendation_score_calculated_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_products_recommendation_score ON products(recommendation_score DESC) 
  WHERE recommendation_score IS NOT NULL;

-- ============================================
-- 6. COMMENTS
-- ============================================
COMMENT ON TABLE recommendation_configs IS 'Saved recommendation configurations (goals, constraints, preferences)';
COMMENT ON TABLE recommendation_runs IS 'Track each recommendation generation session';
COMMENT ON TABLE recommendation_results IS 'Individual product recommendations with scores and reasoning';
COMMENT ON TABLE recommendation_filter_failures IS 'Why products were excluded (transparency)';
COMMENT ON COLUMN recommendation_configs.goal_params IS 'JSON with goal-specific parameters (budget, profit_target, etc.)';
COMMENT ON COLUMN recommendation_results.why_recommended IS 'JSON array of reasons: ["High ROI", "Fast mover"]';
COMMENT ON COLUMN recommendation_results.warnings IS 'JSON array of warnings: ["Price spike", "Volatile"]';

