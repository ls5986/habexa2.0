-- Add SP-API specific columns to analyses table
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS seller_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fba_seller_count INTEGER;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS amazon_sells BOOLEAN DEFAULT FALSE;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS price_source TEXT DEFAULT 'unknown';

-- Add index for price_source
CREATE INDEX IF NOT EXISTS idx_analyses_price_source ON analyses(price_source);

-- Add comment
COMMENT ON COLUMN analyses.price_source IS 'Source of sell_price: sp_api_buy_box, keepa_buy_box, keepa_new, keepa_amazon, unknown';

