-- Verification query for trial tracking migration
-- Run this in Supabase SQL Editor to verify columns exist

-- Check subscriptions table columns
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'subscriptions' 
AND column_name IN ('had_free_trial', 'trial_start', 'trial_end', 'cancel_at_period_end')
ORDER BY column_name;

-- Expected output:
-- had_free_trial | boolean | false | NO
-- trial_start | timestamp with time zone | NULL | YES
-- trial_end | timestamp with time zone | NULL | YES
-- cancel_at_period_end | boolean | false | NO

-- If any columns are missing, run ADD_TRIAL_TRACKING.sql first

