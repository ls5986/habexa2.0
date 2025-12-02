-- Add unique constraints for Telegram message and deal deduplication
-- This prevents duplicate messages/deals from being saved

-- Add unique constraint for telegram_messages if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'telegram_messages_unique'
    ) THEN
        ALTER TABLE public.telegram_messages 
        ADD CONSTRAINT telegram_messages_unique 
        UNIQUE (user_id, telegram_channel_id, telegram_message_id);
    END IF;
END $$;

-- Add unique constraint for telegram_deals if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'telegram_deals_unique'
    ) THEN
        ALTER TABLE public.telegram_deals
        ADD CONSTRAINT telegram_deals_unique
        UNIQUE (user_id, channel_id, asin);
    END IF;
END $$;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_telegram_messages_user_channel 
ON public.telegram_messages(user_id, telegram_channel_id, telegram_date DESC);

CREATE INDEX IF NOT EXISTS idx_telegram_deals_user_channel 
ON public.telegram_deals(user_id, channel_id, extracted_at DESC);

