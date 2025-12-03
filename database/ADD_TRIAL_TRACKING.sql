-- Add trial tracking fields to subscriptions table
-- Run this in Supabase SQL Editor

ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS had_free_trial BOOLEAN DEFAULT FALSE;

-- Update existing records: if they have trial_end set, they had a trial
UPDATE public.subscriptions
SET had_free_trial = TRUE
WHERE trial_end IS NOT NULL AND had_free_trial IS NULL;

-- Add comment
COMMENT ON COLUMN public.subscriptions.had_free_trial IS 'Prevents users from getting multiple free trials';

