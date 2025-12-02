-- Add unique constraint for analyses table to prevent duplicate analyses per user/ASIN
-- This ensures one analysis per ASIN per user

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'analyses_user_asin_unique'
    ) THEN
        ALTER TABLE public.analyses 
        ADD CONSTRAINT analyses_user_asin_unique 
        UNIQUE (user_id, asin);
    END IF;
END $$;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_analyses_user_asin ON public.analyses(user_id, asin);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON public.analyses(created_at DESC);

