-- ============================================
-- FIX MISSING TABLES
-- Run this in Supabase SQL Editor
-- ============================================

-- ============================================
-- 1. CREATE feature_usage TABLE
-- ============================================
-- Note: The schema uses 'usage_records' but the debug endpoint looks for 'feature_usage'
-- Creating both for compatibility

CREATE TABLE IF NOT EXISTS public.feature_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    feature TEXT NOT NULL,  -- 'analyses_per_month', 'telegram_channels', etc.
    quantity INTEGER DEFAULT 1,
    period_start TIMESTAMPTZ DEFAULT DATE_TRUNC('month', NOW()),
    period_end TIMESTAMPTZ DEFAULT (DATE_TRUNC('month', NOW()) + INTERVAL '1 month'),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, feature, period_start)
);

CREATE INDEX IF NOT EXISTS idx_feature_usage_user ON public.feature_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_feature_usage_feature ON public.feature_usage(feature);
CREATE INDEX IF NOT EXISTS idx_feature_usage_period ON public.feature_usage(period_start, period_end);

ALTER TABLE public.feature_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own feature usage" 
    ON public.feature_usage FOR SELECT 
    USING (auth.uid() = user_id);

-- ============================================
-- 2. CREATE tracked_channels TABLE
-- ============================================
-- Note: The debug endpoint looks for 'tracked_channels' but schema uses 'telegram_channels'
-- Creating 'tracked_channels' as an alias/view or separate table

-- Option 1: Create as separate table (if you want to track differently)
CREATE TABLE IF NOT EXISTS public.tracked_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Channel info
    channel_id BIGINT NOT NULL,
    channel_name TEXT,
    channel_username TEXT,
    channel_type TEXT DEFAULT 'channel',
    
    -- Tracking settings
    is_active BOOLEAN DEFAULT TRUE,
    auto_analyze BOOLEAN DEFAULT TRUE,
    
    -- Stats
    messages_received INTEGER DEFAULT 0,
    deals_extracted INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, channel_id)
);

CREATE INDEX IF NOT EXISTS idx_tracked_channels_user ON public.tracked_channels(user_id);
CREATE INDEX IF NOT EXISTS idx_tracked_channels_active ON public.tracked_channels(user_id, is_active);

ALTER TABLE public.tracked_channels ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own tracked channels" 
    ON public.tracked_channels FOR ALL 
    USING (auth.uid() = user_id);

-- ============================================
-- 3. VERIFY telegram_channels EXISTS
-- ============================================
-- If telegram_channels doesn't exist, create it too

CREATE TABLE IF NOT EXISTS public.telegram_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Channel info
    channel_id BIGINT NOT NULL,
    channel_name TEXT,
    channel_username TEXT,
    channel_type TEXT DEFAULT 'channel',
    
    -- Monitoring settings
    is_active BOOLEAN DEFAULT TRUE,
    auto_analyze BOOLEAN DEFAULT TRUE,
    
    -- Stats
    messages_received INTEGER DEFAULT 0,
    deals_extracted INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, channel_id)
);

CREATE INDEX IF NOT EXISTS idx_telegram_channels_user ON public.telegram_channels(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_channels_active ON public.telegram_channels(user_id, is_active);

ALTER TABLE public.telegram_channels ENABLE ROW LEVEL SECURITY;

-- Drop policy if exists, then create
DROP POLICY IF EXISTS "Users can manage own channels" ON public.telegram_channels;
CREATE POLICY "Users can manage own channels" 
    ON public.telegram_channels FOR ALL 
    USING (auth.uid() = user_id);

-- ============================================
-- DONE
-- ============================================
-- After running this, the debug endpoint should show:
-- - feature_usage_table: EXISTS
-- - tracked_channels_table: EXISTS
-- - telegram_channels_table: EXISTS

