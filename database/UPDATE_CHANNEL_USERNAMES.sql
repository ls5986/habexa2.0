-- Update existing telegram_channels that might be missing usernames
-- This is a helper script - you'll need to manually update channels that don't have usernames
-- by looking them up in Telegram and adding the username

-- Check which channels are missing usernames
SELECT 
    channel_id,
    channel_name,
    channel_username,
    user_id
FROM telegram_channels
WHERE channel_username IS NULL OR channel_username = '';

-- Example: Update a specific channel with its username
-- Replace the values below with actual channel info
-- UPDATE telegram_channels
-- SET channel_username = '@drachmadistribution'  -- without @ is also fine
-- WHERE channel_id = 123456789  -- replace with actual channel_id
--   AND user_id = 'user-uuid-here';  -- replace with actual user_id

-- Note: Channels without usernames will still work for backfill
-- but using the username is more reliable. The backfill will try:
-- 1. Username (if available)
-- 2. Numeric ID
-- 3. PeerChannel wrapper

