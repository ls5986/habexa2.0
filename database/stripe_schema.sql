-- Stripe Integration Schema
-- Add this to your Supabase SQL Editor

-- Subscriptions table
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Stripe IDs
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    stripe_price_id TEXT,
    
    -- Subscription details
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'pro', 'agency')),
    billing_interval TEXT CHECK (billing_interval IN ('month', 'year')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    
    -- Dates
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    
    -- Usage tracking
    analyses_used_this_period INTEGER DEFAULT 0,
    last_usage_reset TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Payment history
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    subscription_id UUID REFERENCES public.subscriptions(id),
    
    -- Stripe data
    stripe_payment_intent_id TEXT,
    stripe_invoice_id TEXT,
    
    -- Payment details
    amount INTEGER NOT NULL,  -- in cents
    currency TEXT DEFAULT 'usd',
    status TEXT CHECK (status IN ('succeeded', 'failed', 'pending', 'refunded')),
    
    -- Metadata
    description TEXT,
    receipt_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices (for display)
CREATE TABLE IF NOT EXISTS public.invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    stripe_invoice_id TEXT UNIQUE,
    stripe_invoice_url TEXT,
    stripe_pdf_url TEXT,
    
    amount_due INTEGER,
    amount_paid INTEGER,
    currency TEXT DEFAULT 'usd',
    status TEXT,
    
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking (for metered features)
CREATE TABLE IF NOT EXISTS public.usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    feature TEXT NOT NULL,  -- 'analysis', 'channel_add', etc.
    quantity INTEGER DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own subscription" ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own payments" ON public.payments FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own invoices" ON public.invoices FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own usage" ON public.usage_records FOR SELECT USING (auth.uid() = user_id);

-- Service role can do everything (for webhooks) - Note: This requires service role key
-- In production, you might want more granular policies

-- Function to check user's tier limits
CREATE OR REPLACE FUNCTION check_user_limit(
    p_user_id UUID,
    p_feature TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_tier TEXT;
    v_limit INTEGER;
    v_current_usage INTEGER;
BEGIN
    -- Get user's tier
    SELECT tier INTO v_tier FROM public.subscriptions WHERE user_id = p_user_id;
    IF v_tier IS NULL THEN v_tier := 'free'; END IF;
    
    -- Get limit based on tier and feature
    CASE p_feature
        WHEN 'analyses_per_month' THEN
            CASE v_tier
                WHEN 'free' THEN v_limit := 10;
                WHEN 'starter' THEN v_limit := 100;
                WHEN 'pro' THEN v_limit := 500;
                WHEN 'agency' THEN v_limit := -1;  -- unlimited
            END CASE;
        WHEN 'telegram_channels' THEN
            CASE v_tier
                WHEN 'free' THEN v_limit := 1;
                WHEN 'starter' THEN v_limit := 3;
                WHEN 'pro' THEN v_limit := 10;
                WHEN 'agency' THEN v_limit := -1;
            END CASE;
        WHEN 'suppliers' THEN
            CASE v_tier
                WHEN 'free' THEN v_limit := 3;
                WHEN 'starter' THEN v_limit := 10;
                WHEN 'pro' THEN v_limit := 50;
                WHEN 'agency' THEN v_limit := -1;
            END CASE;
        ELSE v_limit := 0;
    END CASE;
    
    -- Unlimited
    IF v_limit = -1 THEN RETURN TRUE; END IF;
    
    -- Check current usage
    IF p_feature = 'analyses_per_month' THEN
        SELECT analyses_used_this_period INTO v_current_usage 
        FROM public.subscriptions WHERE user_id = p_user_id;
        RETURN COALESCE(v_current_usage, 0) < v_limit;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment analysis count
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON public.subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_sub ON public.subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_payments_user ON public.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_user_created ON public.usage_records(user_id, created_at);

-- Trigger for updated_at
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

