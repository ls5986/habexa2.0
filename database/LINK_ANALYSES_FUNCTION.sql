-- Create a function to link analyses to deals
CREATE OR REPLACE FUNCTION link_analyses_to_deals(p_user_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE telegram_deals td
    SET 
        analysis_id = a.id,
        status = 'analyzed'
    FROM analyses a
    WHERE td.user_id = p_user_id
    AND td.user_id = a.user_id
    AND td.asin = a.asin
    AND td.analysis_id IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Run it now to fix existing data (replace with your actual user_id)
-- SELECT link_analyses_to_deals('d320935d-80e8-4b5f-ae69-06315b6b1b36');

-- Also run this direct update now:
UPDATE telegram_deals td
SET analysis_id = a.id, status = 'analyzed'
FROM analyses a
WHERE td.user_id = a.user_id 
AND td.asin = a.asin 
AND td.analysis_id IS NULL;

-- Verify counts match
SELECT 
    (SELECT COUNT(*) FROM telegram_deals WHERE status = 'analyzed') as deals_analyzed,
    (SELECT COUNT(*) FROM analyses) as total_analyses;

