-- Feature Gating & Limit Enforcement Schema
-- Run this in Supabase SQL Editor

-- Add usage tracking columns to subscriptions if not exists
ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS telegram_channels_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS suppliers_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS team_members_count INTEGER DEFAULT 1;

-- Create a function to get user's tier limits
CREATE OR REPLACE FUNCTION get_tier_limits(p_tier TEXT)
RETURNS JSONB AS $$
BEGIN
    RETURN CASE p_tier
        WHEN 'free' THEN '{
            "telegram_channels": 1,
            "analyses_per_month": 10,
            "suppliers": 3,
            "alerts": false,
            "bulk_analyze": false,
            "api_access": false,
            "team_seats": 1,
            "export_data": false,
            "priority_support": false
        }'::JSONB
        WHEN 'starter' THEN '{
            "telegram_channels": 3,
            "analyses_per_month": 100,
            "suppliers": 10,
            "alerts": true,
            "bulk_analyze": false,
            "api_access": false,
            "team_seats": 1,
            "export_data": true,
            "priority_support": false
        }'::JSONB
        WHEN 'pro' THEN '{
            "telegram_channels": 10,
            "analyses_per_month": 500,
            "suppliers": 50,
            "alerts": true,
            "bulk_analyze": true,
            "api_access": false,
            "team_seats": 3,
            "export_data": true,
            "priority_support": true
        }'::JSONB
        WHEN 'agency' THEN '{
            "telegram_channels": -1,
            "analyses_per_month": -1,
            "suppliers": -1,
            "alerts": true,
            "bulk_analyze": true,
            "api_access": true,
            "team_seats": 10,
            "export_data": true,
            "priority_support": true
        }'::JSONB
        ELSE '{
            "telegram_channels": 1,
            "analyses_per_month": 10,
            "suppliers": 3,
            "alerts": false,
            "bulk_analyze": false,
            "api_access": false,
            "team_seats": 1,
            "export_data": false,
            "priority_support": false
        }'::JSONB
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to check if user can perform an action
CREATE OR REPLACE FUNCTION check_user_limit(
    p_user_id UUID,
    p_feature TEXT
) RETURNS JSONB AS $$
DECLARE
    v_tier TEXT;
    v_limits JSONB;
    v_limit INTEGER;
    v_current_usage INTEGER;
    v_can_proceed BOOLEAN;
BEGIN
    -- Get user's tier
    SELECT COALESCE(tier, 'free') INTO v_tier 
    FROM public.subscriptions 
    WHERE user_id = p_user_id;
    
    IF v_tier IS NULL THEN 
        v_tier := 'free'; 
    END IF;
    
    -- Get limits for tier
    v_limits := get_tier_limits(v_tier);
    
    -- Handle boolean features
    IF p_feature IN ('alerts', 'bulk_analyze', 'api_access', 'export_data', 'priority_support') THEN
        RETURN jsonb_build_object(
            'allowed', (v_limits->>p_feature)::BOOLEAN,
            'tier', v_tier,
            'feature', p_feature,
            'upgrade_required', NOT (v_limits->>p_feature)::BOOLEAN
        );
    END IF;
    
    -- Get numeric limit
    v_limit := (v_limits->>p_feature)::INTEGER;
    
    -- Unlimited check (-1)
    IF v_limit = -1 THEN
        RETURN jsonb_build_object(
            'allowed', true,
            'tier', v_tier,
            'feature', p_feature,
            'limit', -1,
            'used', 0,
            'remaining', -1,
            'unlimited', true
        );
    END IF;
    
    -- Get current usage based on feature
    CASE p_feature
        WHEN 'analyses_per_month' THEN
            SELECT COALESCE(analyses_used_this_period, 0) INTO v_current_usage
            FROM public.subscriptions WHERE user_id = p_user_id;
        WHEN 'telegram_channels' THEN
            SELECT COALESCE(telegram_channels_count, 0) INTO v_current_usage
            FROM public.subscriptions WHERE user_id = p_user_id;
        WHEN 'suppliers' THEN
            SELECT COUNT(*) INTO v_current_usage
            FROM public.suppliers WHERE user_id = p_user_id;
        WHEN 'team_seats' THEN
            SELECT COALESCE(team_members_count, 1) INTO v_current_usage
            FROM public.subscriptions WHERE user_id = p_user_id;
        ELSE
            v_current_usage := 0;
    END CASE;
    
    v_current_usage := COALESCE(v_current_usage, 0);
    v_can_proceed := v_current_usage < v_limit;
    
    RETURN jsonb_build_object(
        'allowed', v_can_proceed,
        'tier', v_tier,
        'feature', p_feature,
        'limit', v_limit,
        'used', v_current_usage,
        'remaining', GREATEST(0, v_limit - v_current_usage),
        'unlimited', false,
        'upgrade_required', NOT v_can_proceed
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment usage
CREATE OR REPLACE FUNCTION increment_usage(
    p_user_id UUID,
    p_feature TEXT,
    p_amount INTEGER DEFAULT 1
) RETURNS JSONB AS $$
DECLARE
    v_check JSONB;
BEGIN
    -- First check if allowed
    v_check := check_user_limit(p_user_id, p_feature);
    
    IF NOT (v_check->>'allowed')::BOOLEAN THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Limit reached',
            'check', v_check
        );
    END IF;
    
    -- Increment based on feature
    CASE p_feature
        WHEN 'analyses_per_month' THEN
            UPDATE public.subscriptions
            SET analyses_used_this_period = COALESCE(analyses_used_this_period, 0) + p_amount,
                updated_at = NOW()
            WHERE user_id = p_user_id;
        WHEN 'telegram_channels' THEN
            UPDATE public.subscriptions
            SET telegram_channels_count = COALESCE(telegram_channels_count, 0) + p_amount,
                updated_at = NOW()
            WHERE user_id = p_user_id;
        WHEN 'team_seats' THEN
            UPDATE public.subscriptions
            SET team_members_count = COALESCE(team_members_count, 1) + p_amount,
                updated_at = NOW()
            WHERE user_id = p_user_id;
    END CASE;
    
    -- Log usage
    INSERT INTO public.usage_records (user_id, feature, quantity)
    VALUES (p_user_id, p_feature, p_amount);
    
    RETURN jsonb_build_object(
        'success', true,
        'feature', p_feature,
        'incremented_by', p_amount
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to decrement usage (when removing channels/suppliers)
CREATE OR REPLACE FUNCTION decrement_usage(
    p_user_id UUID,
    p_feature TEXT,
    p_amount INTEGER DEFAULT 1
) RETURNS VOID AS $$
BEGIN
    CASE p_feature
        WHEN 'telegram_channels' THEN
            UPDATE public.subscriptions
            SET telegram_channels_count = GREATEST(0, COALESCE(telegram_channels_count, 0) - p_amount),
                updated_at = NOW()
            WHERE user_id = p_user_id;
        WHEN 'team_seats' THEN
            UPDATE public.subscriptions
            SET team_members_count = GREATEST(1, COALESCE(team_members_count, 1) - p_amount),
                updated_at = NOW()
            WHERE user_id = p_user_id;
    END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create monitored_channels table if not exists
CREATE TABLE IF NOT EXISTS public.monitored_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    channel_type TEXT DEFAULT 'telegram',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, channel_id)
);

ALTER TABLE public.monitored_channels ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own channels" ON public.monitored_channels
    FOR ALL USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_monitored_channels_user ON public.monitored_channels(user_id);

