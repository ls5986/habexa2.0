-- ============================================
-- HYBRID SP-API SCHEMA
-- App credentials for public data, User credentials for seller data
-- ============================================

-- User settings with marketplace preference
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    currency TEXT DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_settings_user ON user_settings(user_id);

ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own settings" ON user_settings 
    FOR ALL USING (auth.uid() = user_id);

-- User's Amazon Seller account connection (optional, for their seller data)
CREATE TABLE IF NOT EXISTS amazon_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    marketplace_id TEXT NOT NULL DEFAULT 'ATVPDKIKX0DER',
    seller_id TEXT,
    refresh_token_encrypted TEXT,
    is_connected BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, marketplace_id)
);

CREATE INDEX idx_amazon_connections_user ON amazon_connections(user_id);
CREATE INDEX idx_amazon_connections_connected ON amazon_connections(user_id, is_connected) WHERE is_connected = TRUE;

ALTER TABLE amazon_connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own connections" ON amazon_connections 
    FOR ALL USING (auth.uid() = user_id);

-- Marketplace reference
CREATE TABLE IF NOT EXISTS marketplaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country_code TEXT,
    currency TEXT,
    domain TEXT,
    region TEXT  -- NA, EU, FE
);

INSERT INTO marketplaces (id, name, country_code, currency, domain, region) VALUES
    ('ATVPDKIKX0DER', 'United States', 'US', 'USD', 'amazon.com', 'NA'),
    ('A2EUQ1WTGCTBG2', 'Canada', 'CA', 'CAD', 'amazon.ca', 'NA'),
    ('A1AM78C64UM0Y8', 'Mexico', 'MX', 'MXN', 'amazon.com.mx', 'NA'),
    ('A1F83G8C2ARO7P', 'United Kingdom', 'UK', 'GBP', 'amazon.co.uk', 'EU'),
    ('A13V1IB3VIYBER', 'France', 'FR', 'EUR', 'amazon.fr', 'EU'),
    ('A1PA6795UKMFR9', 'Germany', 'DE', 'EUR', 'amazon.de', 'EU'),
    ('APJ6JRA9NG5V4', 'Italy', 'IT', 'EUR', 'amazon.it', 'EU'),
    ('A1RKKUPIHCS9HS', 'Spain', 'ES', 'EUR', 'amazon.es', 'EU'),
    ('A1VC38T7YXB528', 'Japan', 'JP', 'JPY', 'amazon.co.jp', 'FE'),
    ('A39IBJ37TRP1C6', 'Australia', 'AU', 'AUD', 'amazon.com.au', 'FE')
ON CONFLICT (id) DO NOTHING;

