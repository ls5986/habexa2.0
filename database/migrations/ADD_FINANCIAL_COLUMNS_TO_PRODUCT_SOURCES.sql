-- Add missing financial columns to product_sources
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS sell_price NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS profit NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS roi NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS margin NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS fba_fee NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS referral_fee NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS total_fees NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS promo_profit NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS promo_roi NUMERIC(10,2);
ALTER TABLE product_sources ADD COLUMN IF NOT EXISTS promo_margin NUMERIC(10,2);

-- Verify columns were added
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'product_sources' 
-- AND column_name IN ('sell_price', 'profit', 'roi', 'margin', 'fba_fee', 'referral_fee', 'total_fees')
-- ORDER BY column_name;
