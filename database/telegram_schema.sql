-- Telegram Monitoring Integration Schema
-- Run this in Supabase SQL Editor

-- ============================================
-- TELEGRAM CREDENTIALS & SESSIONS
-- ============================================

CREATE TABLE IF NOT EXISTS public.telegram_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
    
    -- Telethon session string (encrypted)
    session_string_encrypted TEXT,
    
    -- Connection status
    phone_number TEXT,
    is_connected BOOLEAN DEFAULT FALSE,
    is_authorized BOOLEAN DEFAULT FALSE,
    
    -- Monitoring status
    is_monitoring BOOLEAN DEFAULT FALSE,
    monitoring_started_at TIMESTAMPTZ,
    
    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.telegram_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own telegram session" 
    ON public.telegram_sessions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage telegram sessions" 
    ON public.telegram_sessions FOR ALL 
    USING (true);

-- ============================================
-- MONITORED CHANNELS
-- ============================================

CREATE TABLE IF NOT EXISTS public.telegram_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Channel info
    channel_id BIGINT NOT NULL,
    channel_name TEXT,
    channel_username TEXT,
    channel_type TEXT DEFAULT 'channel', -- 'channel', 'group', 'supergroup'
    
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

ALTER TABLE public.telegram_channels ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own channels" 
    ON public.telegram_channels FOR ALL 
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_telegram_channels_user ON public.telegram_channels(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_channels_active ON public.telegram_channels(user_id, is_active);

-- ============================================
-- TELEGRAM MESSAGES
-- ============================================

CREATE TABLE IF NOT EXISTS public.telegram_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    channel_id UUID REFERENCES public.telegram_channels(id) ON DELETE CASCADE,
    
    -- Message details
    telegram_message_id BIGINT NOT NULL,
    telegram_channel_id BIGINT NOT NULL,
    
    -- Content
    content TEXT,
    has_media BOOLEAN DEFAULT FALSE,
    media_type TEXT,
    
    -- Sender info
    sender_id BIGINT,
    sender_name TEXT,
    
    -- Extraction results
    is_processed BOOLEAN DEFAULT FALSE,
    extracted_products JSONB DEFAULT '[]'::JSONB,
    extraction_error TEXT,
    
    -- Timestamps
    telegram_date TIMESTAMPTZ,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

ALTER TABLE public.telegram_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own messages" 
    ON public.telegram_messages FOR SELECT 
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_telegram_messages_user ON public.telegram_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_messages_channel ON public.telegram_messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_telegram_messages_unprocessed ON public.telegram_messages(user_id, is_processed) 
    WHERE is_processed = FALSE;

-- ============================================
-- EXTRACTED DEALS (from Telegram)
-- ============================================

CREATE TABLE IF NOT EXISTS public.telegram_deals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    message_id UUID REFERENCES public.telegram_messages(id) ON DELETE SET NULL,
    channel_id UUID REFERENCES public.telegram_channels(id) ON DELETE SET NULL,
    
    -- Product info
    asin TEXT NOT NULL,
    buy_cost DECIMAL(10,2),
    moq INTEGER DEFAULT 1,
    
    -- Extracted details
    product_title TEXT,
    notes TEXT,
    
    -- Analysis link
    analysis_id UUID REFERENCES public.analyses(id) ON DELETE SET NULL,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'analyzing', 'analyzed', 'error', 'skipped')),
    
    -- Timestamps
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    analyzed_at TIMESTAMPTZ
);

ALTER TABLE public.telegram_deals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own telegram deals" 
    ON public.telegram_deals FOR ALL 
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_telegram_deals_user ON public.telegram_deals(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_deals_asin ON public.telegram_deals(asin);
CREATE INDEX IF NOT EXISTS idx_telegram_deals_pending ON public.telegram_deals(user_id, status) 
    WHERE status = 'pending';

-- ============================================
-- HELPER FUNCTION: Update channel stats
-- ============================================

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

CREATE TRIGGER trigger_update_channel_stats
    AFTER INSERT ON public.telegram_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_channel_stats();

-- ============================================
-- HELPER FUNCTION: Increment deals extracted
-- ============================================

CREATE OR REPLACE FUNCTION increment_deals_extracted()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.telegram_channels
    SET deals_extracted = deals_extracted + 1
    WHERE id = NEW.channel_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_deals
    AFTER INSERT ON public.telegram_deals
    FOR EACH ROW
    EXECUTE FUNCTION increment_deals_extracted();

-- ============================================
-- Updated at trigger
-- ============================================

CREATE OR REPLACE FUNCTION update_telegram_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_telegram_session_updated
    BEFORE UPDATE ON public.telegram_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_telegram_session_timestamp();

