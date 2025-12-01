# Test User Setup for Local Development

## Quick Setup

### Option 1: Register via UI (Recommended)

1. Go to `http://localhost:5189/register`
2. Create an account with:
   - **Email**: `test@habexa.com` (or any email)
   - **Password**: `Test123!@#` (or any password)
   - **Full Name**: `Test User`

The profile will be automatically created when you register.

### Option 2: Create via Supabase Dashboard

1. Go to your Supabase Dashboard → Authentication → Users
2. Click "Add User" → "Create new user"
3. Enter:
   - **Email**: `test@habexa.com`
   - **Password**: `Test123!@#`
   - Uncheck "Auto Confirm User" if you want email confirmation (or leave checked for instant access)
4. Click "Create User"
5. The profile will be created automatically via database trigger, or run the SQL in `database/create_test_user.sql`

### Option 3: SQL Script

1. Create user in Supabase Dashboard → Authentication → Users
2. Run the SQL in `database/create_test_user.sql` in Supabase SQL Editor

## Test Credentials

**Email**: `test@habexa.com`  
**Password**: `Test123!@#`

## Notes

- The profile is automatically created when you register via the UI
- If you create the user manually in Supabase, you may need to run the profile creation SQL
- Make sure email confirmation is disabled in Supabase Auth settings for instant login, or check your email for confirmation link

## Troubleshooting

If you can't log in:
1. Check Supabase Dashboard → Authentication → Users to see if user exists
2. Check if profile exists: `SELECT * FROM profiles WHERE email = 'test@habexa.com'`
3. If profile doesn't exist, run the SQL script in `database/create_test_user.sql`

