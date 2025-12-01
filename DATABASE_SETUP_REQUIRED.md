# Database Setup Required

## Issue
The backend is throwing 500 errors because some database tables/functions are missing.

## Required Database Setup

### 1. Run Core Schema
```sql
-- Run in Supabase SQL Editor
-- File: database/schema.sql
```

### 2. Run Stripe Schema
```sql
-- Run in Supabase SQL Editor
-- File: database/stripe_schema.sql
```

### 3. Run Feature Gating Schema
```sql
-- Run in Supabase SQL Editor
-- File: database/feature_gating_schema.sql
```

### 4. Run Amazon Connections Schema
```sql
-- Run in Supabase SQL Editor
-- File: database/amazon_connections_schema.sql
```

### 5. Run Telegram Schema
```sql
-- Run in Supabase SQL Editor
-- File: database/telegram_schema.sql
```

### 6. Run Keepa Schema
```sql
-- Run in Supabase SQL Editor
-- File: database/keepa_schema.sql
```

## Quick Check

Run this to see what's missing:

```sql
-- Check if subscriptions table exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'subscriptions' AND table_schema = 'public';

-- Check if check_user_limit function exists
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' AND routine_name = 'check_user_limit';

-- Check if notifications table exists
SELECT * FROM public.notifications LIMIT 1;
```

## Expected Columns in subscriptions table

- `id` (UUID)
- `user_id` (UUID)
- `tier` (TEXT) - **This is the missing column causing errors**
- `status` (TEXT)
- `stripe_customer_id` (TEXT)
- `stripe_subscription_id` (TEXT)
- `stripe_price_id` (TEXT)
- `billing_interval` (TEXT)
- `analyses_used_this_period` (INTEGER)
- `telegram_channels_count` (INTEGER)
- `suppliers_count` (INTEGER)
- `team_members_count` (INTEGER)
- `current_period_start` (TIMESTAMPTZ)
- `current_period_end` (TIMESTAMPTZ)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

## Quick Fix (Temporary)

If you just want to test without setting up the full schema, the backend will now gracefully degrade and allow operations even if the database functions are missing. However, you should still run the schemas for full functionality.

