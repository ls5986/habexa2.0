-- Add fee columns to analyses table
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_total DECIMAL(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_referral DECIMAL(10,2);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS fees_fba DECIMAL(10,2);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_analyses_fees_total ON analyses(fees_total);

-- Add comments
COMMENT ON COLUMN analyses.fees_total IS 'Total Amazon fees (referral + FBA)';
COMMENT ON COLUMN analyses.fees_referral IS 'Amazon referral fee';
COMMENT ON COLUMN analyses.fees_fba IS 'Amazon FBA fulfillment fee';

