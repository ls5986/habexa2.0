-- Link an existing Telegram channel to a supplier
-- Option 1: Create a new supplier and link it to your channel
-- Option 2: Link channel to an existing supplier

-- ============================================
-- OPTION 1: CREATE NEW SUPPLIER AND LINK
-- ============================================
-- Replace these values:
--   - 'YOUR_USER_ID_HERE' - Your user UUID
--   - YOUR_CHANNEL_ID_HERE - The numeric channel_id from telegram_channels table
--   - 'Supplier Name' - The name for your supplier
--   - 'https://supplier-website.com' - Optional website
--   - 'email@supplier.com' - Optional contact email
--   - 'Notes about this supplier' - Optional notes

-- Step 1: Create the supplier
INSERT INTO suppliers (
    user_id,
    name,
    website,
    contact_email,
    notes,
    source,
    telegram_channel_id,
    telegram_username,
    is_active
)
SELECT 
    'YOUR_USER_ID_HERE'::uuid,
    'Supplier Name',
    'https://supplier-website.com',  -- Optional, can be NULL
    'email@supplier.com',              -- Optional, can be NULL
    'Notes about this supplier',      -- Optional, can be NULL
    'telegram',
    YOUR_CHANNEL_ID_HERE,              -- The numeric channel_id
    tc.channel_username,               -- Get username from channel
    true
FROM telegram_channels tc
WHERE tc.user_id = 'YOUR_USER_ID_HERE'::uuid
  AND tc.channel_id = YOUR_CHANNEL_ID_HERE
RETURNING id, name;

-- Step 2: Link the channel to the supplier (update supplier_id on channel)
UPDATE telegram_channels
SET supplier_id = (
    SELECT id 
    FROM suppliers 
    WHERE telegram_channel_id = YOUR_CHANNEL_ID_HERE
      AND user_id = 'YOUR_USER_ID_HERE'::uuid
    ORDER BY created_at DESC
    LIMIT 1
)
WHERE user_id = 'YOUR_USER_ID_HERE'::uuid
  AND channel_id = YOUR_CHANNEL_ID_HERE;

-- ============================================
-- OPTION 2: LINK TO EXISTING SUPPLIER
-- ============================================
-- If you already have a supplier and just want to link the channel:

-- Replace:
--   - 'YOUR_SUPPLIER_ID_HERE' - The UUID of your existing supplier
--   - YOUR_CHANNEL_ID_HERE - The numeric channel_id from telegram_channels table
--   - 'YOUR_USER_ID_HERE' - Your user UUID

UPDATE telegram_channels
SET supplier_id = 'YOUR_SUPPLIER_ID_HERE'::uuid
WHERE user_id = 'YOUR_USER_ID_HERE'::uuid
  AND channel_id = YOUR_CHANNEL_ID_HERE;

-- Also update the supplier with channel info (optional)
UPDATE suppliers
SET 
    telegram_channel_id = YOUR_CHANNEL_ID_HERE,
    telegram_username = (
        SELECT channel_username 
        FROM telegram_channels 
        WHERE channel_id = YOUR_CHANNEL_ID_HERE
          AND user_id = 'YOUR_USER_ID_HERE'::uuid
    )
WHERE id = 'YOUR_SUPPLIER_ID_HERE'::uuid
  AND user_id = 'YOUR_USER_ID_HERE'::uuid;

-- ============================================
-- VERIFY THE LINK
-- ============================================
-- Run this to check if the link worked:

SELECT 
    tc.channel_id,
    tc.channel_name,
    tc.channel_username,
    tc.supplier_id,
    s.name as supplier_name,
    s.telegram_channel_id,
    s.telegram_username
FROM telegram_channels tc
LEFT JOIN suppliers s ON tc.supplier_id = s.id
WHERE tc.user_id = 'YOUR_USER_ID_HERE'::uuid
  AND tc.channel_id = YOUR_CHANNEL_ID_HERE;

-- ============================================
-- QUICK REFERENCE: FIND YOUR VALUES
-- ============================================
-- To find your user_id:
-- SELECT id, email FROM auth.users WHERE email = 'your-email@example.com';

-- To find your channel_id:
-- SELECT channel_id, channel_name, channel_username, supplier_id 
-- FROM telegram_channels 
-- WHERE user_id = 'YOUR_USER_ID_HERE'::uuid;

-- To find your supplier_id (if you already have one):
-- SELECT id, name, telegram_channel_id 
-- FROM suppliers 
-- WHERE user_id = 'YOUR_USER_ID_HERE'::uuid;

