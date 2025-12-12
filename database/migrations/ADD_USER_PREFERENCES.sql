-- HABEXA: User Preferences
-- Store user preferences like default pricing mode

-- ============================================
-- 1. ADD USER PREFERENCES COLUMNS TO PROFILES
-- ============================================
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS default_pricing_mode TEXT DEFAULT '365d_avg' CHECK (default_pricing_mode IN ('current', '30d_avg', '90d_avg', '365d_avg')),
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- ============================================
-- 2. COMMENTS
-- ============================================
COMMENT ON COLUMN profiles.default_pricing_mode IS 'Default pricing mode for profitability calculations';
COMMENT ON COLUMN profiles.preferences IS 'JSONB object for storing various user preferences';

