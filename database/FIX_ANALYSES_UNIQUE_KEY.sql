-- Fix analyses table for multi-user, multi-supplier architecture
-- Unique key: user_id + supplier_id + asin

-- Clear any stuck test data (optional - comment out if you want to keep data)
-- DELETE FROM analyses WHERE user_id = 'd320935d-80e8-4b5f-ae69-06315b6b1b36';

-- Drop old constraints
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_user_asin_unique;
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_supplier_asin_unique;

-- Make sure supplier_id column exists
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL;

-- Add the correct unique constraint: user + supplier + asin
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_user_supplier_asin_unique;
ALTER TABLE analyses ADD CONSTRAINT analyses_user_supplier_asin_unique 
UNIQUE (user_id, supplier_id, asin);

-- Index for performance
DROP INDEX IF EXISTS idx_analyses_user_supplier_asin;
CREATE INDEX IF NOT EXISTS idx_analyses_user_supplier_asin 
ON analyses(user_id, supplier_id, asin);

-- Also add supplier_id to telegram_channels for linking
ALTER TABLE telegram_channels 
ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL;

-- Index for telegram_channels supplier lookup
CREATE INDEX IF NOT EXISTS idx_telegram_channels_supplier 
ON telegram_channels(supplier_id);

