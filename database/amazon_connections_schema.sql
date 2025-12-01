-- ============================================
-- AMAZON SELLER CONNECTIONS (Per User)
-- ============================================

CREATE TABLE IF NOT EXISTS public.amazon_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Seller info
    seller_id TEXT,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    
    -- OAuth tokens (encrypted!)
    refresh_token_encrypted TEXT,
    
    -- Connection status
    is_connected BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    
    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, marketplace_id)
);

CREATE INDEX IF NOT EXISTS idx_amazon_connections_user ON public.amazon_connections(user_id);

-- RLS
ALTER TABLE public.amazon_connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own amazon connection" ON public.amazon_connections
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own amazon connection" ON public.amazon_connections
    FOR ALL USING (auth.uid() = user_id);

-- Service role can manage (for webhooks/backend operations)
CREATE POLICY "Service can manage amazon connections" ON public.amazon_connections
    FOR ALL USING (true);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_amazon_connections_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_amazon_connections_updated_at
    BEFORE UPDATE ON public.amazon_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_amazon_connections_updated_at();

