-- Add stage, moq, and notes fields to telegram_deals for unified products pipeline
ALTER TABLE telegram_deals ADD COLUMN IF NOT EXISTS stage TEXT DEFAULT 'new';
ALTER TABLE telegram_deals ADD COLUMN IF NOT EXISTS moq INTEGER DEFAULT 1;
ALTER TABLE telegram_deals ADD COLUMN IF NOT EXISTS notes TEXT;

-- Create index for stage filtering
CREATE INDEX IF NOT EXISTS idx_telegram_deals_stage ON telegram_deals(user_id, stage);

-- Update existing analyzed deals to 'reviewed' stage
UPDATE telegram_deals SET stage = 'reviewed' WHERE status = 'analyzed' AND (stage IS NULL OR stage = 'new');

-- Set default stage for any null values
UPDATE telegram_deals SET stage = 'new' WHERE stage IS NULL;

