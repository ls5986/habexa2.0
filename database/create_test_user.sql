-- Create a test user in Supabase
-- Run this in Supabase SQL Editor after creating the user in Auth

-- First, create the user in Supabase Dashboard > Authentication > Users
-- Email: test@habexa.com
-- Password: Test123!@#
-- Then run this SQL to create the profile

-- Insert profile for test user (replace USER_ID with actual user ID from auth.users)
-- You can get the user ID from: SELECT id FROM auth.users WHERE email = 'test@habexa.com';

-- Example (replace the UUID with your actual user ID):
/*
INSERT INTO public.profiles (id, email, full_name, created_at, updated_at)
VALUES (
    (SELECT id FROM auth.users WHERE email = 'test@habexa.com'),
    'test@habexa.com',
    'Test User',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    updated_at = NOW();
*/

-- Or use this simpler version that works if user already exists:
DO $$
DECLARE
    user_id UUID;
BEGIN
    -- Get user ID
    SELECT id INTO user_id FROM auth.users WHERE email = 'test@habexa.com' LIMIT 1;
    
    IF user_id IS NOT NULL THEN
        -- Insert or update profile
        INSERT INTO public.profiles (id, email, full_name, created_at, updated_at)
        VALUES (user_id, 'test@habexa.com', 'Test User', NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET
            email = EXCLUDED.email,
            full_name = EXCLUDED.full_name,
            updated_at = NOW();
        
        RAISE NOTICE 'Profile created/updated for user: %', user_id;
    ELSE
        RAISE NOTICE 'User test@habexa.com not found. Please create the user in Authentication first.';
    END IF;
END $$;

