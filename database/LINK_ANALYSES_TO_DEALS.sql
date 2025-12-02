-- Link existing analyses to telegram_deals where they match by asin
-- This fixes deals that were analyzed but analysis_id wasn't saved

UPDATE telegram_deals td
SET 
    analysis_id = a.id,
    status = 'analyzed'
FROM analyses a
WHERE td.user_id = a.user_id
AND td.asin = a.asin
AND td.analysis_id IS NULL;

-- Check the result
SELECT 
    COUNT(*) as total_deals,
    COUNT(analysis_id) as linked_deals,
    COUNT(*) FILTER (WHERE status = 'analyzed') as analyzed_deals,
    COUNT(*) FILTER (WHERE status = 'pending') as pending_deals
FROM telegram_deals;

