-- ============================================
-- COMPLETE REMAINING PARTS
-- ============================================
-- Run this AFTER running CREATE_SCHEMA_FIXED.sql (lines 1-661)
-- This completes the functions, triggers, and RLS policies
-- ============================================

-- ============================================
-- PART 8: FUNCTIONS
-- ============================================

-- Update updated_at timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Get tier limits function
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

-- Check user limit function
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

-- Increment usage function
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

-- Decrement usage function
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

-- Increment analyses function
CREATE OR REPLACE FUNCTION increment_analyses(
    p_user_id UUID,
    p_amount INTEGER DEFAULT 1
) RETURNS VOID AS $$
BEGIN
    UPDATE public.subscriptions
    SET analyses_used_this_period = COALESCE(analyses_used_this_period, 0) + p_amount,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- If no subscription exists, create a free one
    IF NOT FOUND THEN
        INSERT INTO public.subscriptions (user_id, tier, status, analyses_used_this_period)
        VALUES (p_user_id, 'free', 'active', p_amount)
        ON CONFLICT (user_id) DO UPDATE
        SET analyses_used_this_period = COALESCE(public.subscriptions.analyses_used_this_period, 0) + p_amount,
            updated_at = NOW();
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Cleanup expired cache function
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.eligibility_cache WHERE expires_at < NOW();
    DELETE FROM public.fee_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update Amazon credentials timestamp function
CREATE OR REPLACE FUNCTION update_amazon_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update channel stats function
CREATE OR REPLACE FUNCTION update_channel_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.telegram_channels
    SET 
        messages_received = messages_received + 1,
        last_message_at = NEW.telegram_date
    WHERE id = NEW.channel_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Increment deals extracted function
CREATE OR REPLACE FUNCTION increment_deals_extracted()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.telegram_channels
    SET deals_extracted = deals_extracted + 1
    WHERE id = NEW.channel_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update Telegram session timestamp function
CREATE OR REPLACE FUNCTION update_telegram_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Cleanup Keepa cache function
CREATE OR REPLACE FUNCTION cleanup_keepa_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.keepa_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Track Keepa usage function
CREATE OR REPLACE FUNCTION track_keepa_usage(p_tokens INTEGER)
RETURNS void AS $$
BEGIN
    INSERT INTO public.keepa_usage (date, tokens_used, requests_made)
    VALUES (CURRENT_DATE, p_tokens, 1)
    ON CONFLICT (date) DO UPDATE
    SET tokens_used = keepa_usage.tokens_used + p_tokens,
        requests_made = keepa_usage.requests_made + 1;
END;
$$ LANGUAGE plpgsql;

-- Update Amazon connections timestamp function
CREATE OR REPLACE FUNCTION update_amazon_connections_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- PART 9: TRIGGERS
-- ============================================

-- Updated_at triggers
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON public.suppliers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deals_updated_at BEFORE UPDATE ON public.deals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_analyses_updated_at BEFORE UPDATE ON public.analyses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON public.user_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_amazon_creds_updated_at BEFORE UPDATE ON public.amazon_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_telegram_creds_updated_at BEFORE UPDATE ON public.telegram_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_amazon_credentials_updated_at BEFORE UPDATE ON public.amazon_credentials FOR EACH ROW EXECUTE FUNCTION update_amazon_credentials_updated_at();
CREATE TRIGGER trigger_telegram_session_updated BEFORE UPDATE ON public.telegram_sessions FOR EACH ROW EXECUTE FUNCTION update_telegram_session_timestamp();
CREATE TRIGGER trigger_update_channel_stats AFTER INSERT ON public.telegram_messages FOR EACH ROW EXECUTE FUNCTION update_channel_stats();
CREATE TRIGGER trigger_increment_deals AFTER INSERT ON public.telegram_deals FOR EACH ROW EXECUTE FUNCTION increment_deals_extracted();
CREATE TRIGGER update_amazon_connections_updated_at BEFORE UPDATE ON public.amazon_connections FOR EACH ROW EXECUTE FUNCTION update_amazon_connections_updated_at();

-- ============================================
-- PART 10: ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amazon_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amazon_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.eligibility_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fee_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monitored_channels ENABLE ROW LEVEL SECURITY;

-- Core policies
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own suppliers" ON public.suppliers FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own messages" ON public.messages FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own deals" ON public.deals FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own analyses" ON public.analyses FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own watchlist" ON public.watchlist FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own orders" ON public.orders FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own settings" ON public.user_settings FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own notifications" ON public.notifications FOR ALL USING (auth.uid() = user_id);

-- Stripe policies
CREATE POLICY "Users can view own subscription" ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own payments" ON public.payments FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own invoices" ON public.invoices FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own usage" ON public.usage_records FOR SELECT USING (auth.uid() = user_id);

-- SP-API policies
CREATE POLICY "Users can view own amazon credentials" ON public.amazon_credentials FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage amazon credentials" ON public.amazon_credentials FOR ALL USING (true);
CREATE POLICY "Users can view own amazon connection" ON public.amazon_connections FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own amazon connection" ON public.amazon_connections FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Service can manage amazon connections" ON public.amazon_connections FOR ALL USING (true);
CREATE POLICY "Users can view own eligibility cache" ON public.eligibility_cache FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own fee cache" ON public.fee_cache FOR SELECT USING (auth.uid() = user_id);

-- Telegram policies
CREATE POLICY "Users can view own telegram session" ON public.telegram_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage telegram sessions" ON public.telegram_sessions FOR ALL USING (true);
CREATE POLICY "Users can view own telegram creds" ON public.telegram_credentials FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own channels" ON public.telegram_channels FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own messages" ON public.telegram_messages FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own telegram deals" ON public.telegram_deals FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own channels" ON public.monitored_channels FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- DONE!
-- ============================================

-- All functions, triggers, and policies have been created.
-- Your database is now complete!

