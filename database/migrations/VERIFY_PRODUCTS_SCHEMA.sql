-- Verify products table has all required columns
-- Run this in Supabase SQL Editor to check schema

SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'products'
ORDER BY ordinal_position;

-- Required columns checklist:
-- ✅ id (uuid)
-- ✅ user_id (uuid)
-- ✅ asin (varchar/text)
-- ✅ title (text)
-- ✅ brand (text)
-- ✅ category (text)
-- ✅ image_url (text)
-- ✅ sell_price (numeric/decimal)
-- ✅ fees_total (numeric/decimal)
-- ✅ bsr (integer)
-- ✅ seller_count (integer)
-- ✅ fba_seller_count (integer)
-- ✅ amazon_sells (boolean)
-- ✅ status (varchar/text)
-- ✅ analysis_id (uuid)
-- ✅ upc (text/varchar)
-- ✅ lookup_status (varchar) - Added by ADD_ASIN_LOOKUP_TRACKING.sql
-- ✅ lookup_attempts (integer) - Added by ADD_ASIN_LOOKUP_TRACKING.sql
-- ✅ asin_found_at (timestamp) - Added by ADD_ASIN_LOOKUP_TRACKING.sql
-- ✅ potential_asins (jsonb) - Added by ADD_ASIN_LOOKUP_TRACKING.sql
-- ✅ created_at (timestamp)
-- ✅ updated_at (timestamp)

-- If any columns are missing, run the appropriate migration:
-- - ADD_ASIN_LOOKUP_TRACKING.sql for lookup_status, lookup_attempts, asin_found_at, potential_asins
-- - ADD_UPC_SUPPORT.sql for upc
-- - Other migrations as needed

