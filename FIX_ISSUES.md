# Fix Issues Found by Debug Endpoint

## Issue 1: Missing Database Tables ✅ FIXED

**Problem:**
- `feature_usage_table`: MISSING
- `tracked_channels_table`: MISSING

**Solution:**
Run this SQL in Supabase SQL Editor:
```sql
-- See: database/FIX_MISSING_TABLES.sql
```

The SQL script will create:
- `feature_usage` table (for tracking feature usage)
- `tracked_channels` table (for tracking Telegram channels)
- `telegram_channels` table (if it doesn't exist)

## Issue 2: Stripe Price IDs Mismatch ⚠️ NEEDS FIX

**Problem:**
You're using a **LIVE** Stripe key (`sk_live_...`) but all your price IDs are **TEST** mode prices.

**Error:**
```
No such price: 'price_1SZORRJNvcs70HLsSDG5Hq0s'; 
a similar object exists in test mode, but a live mode key was used
```

**Solution - Choose ONE:**

### Option A: Use Test Mode (Recommended for Development)

1. Get your test key from Stripe Dashboard:
   - Go to: https://dashboard.stripe.com/test/apikeys
   - Copy the **Secret key** (starts with `sk_test_`)

2. Update `.env`:
   ```bash
   STRIPE_SECRET_KEY=sk_test_xxxxx  # Your test key
   STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx  # Your test publishable key
   ```

3. Keep your existing test price IDs (they're already correct for test mode)

### Option B: Create Live Mode Prices

1. Go to Stripe Dashboard (LIVE mode):
   - https://dashboard.stripe.com/products
   - Create products/prices for each tier
   - Copy the LIVE price IDs (they'll be different from test ones)

2. Update `.env` with LIVE price IDs:
   ```bash
   STRIPE_PRICE_STARTER_MONTHLY=price_xxxxx  # Live price ID
   STRIPE_PRICE_STARTER_YEARLY=price_xxxxx
   # ... etc
   ```

### Option C: Get Existing Live Prices

If you already created live prices:

1. Go to Stripe Dashboard → Products (LIVE mode)
2. Click on each product
3. Copy the price ID for each billing interval
4. Update `.env`

## Quick Fix Commands

### Check Current Stripe Key Type:
```bash
cd backend
python3 -c "import os; from dotenv import load_dotenv; load_dotenv('../.env'); print(os.getenv('STRIPE_SECRET_KEY')[:10])"
# Should show: sk_test_ or sk_live_
```

### List Stripe Prices (Test Mode):
```bash
stripe prices list --limit=10 --api-key sk_test_xxxxx
```

### List Stripe Prices (Live Mode):
```bash
stripe prices list --limit=10 --api-key sk_live_xxxxx
```

## After Fixing

1. **Run the SQL** in Supabase: `database/FIX_MISSING_TABLES.sql`
2. **Update .env** with correct Stripe keys/prices
3. **Restart backend** to load new .env values
4. **Run debug endpoint again** to verify:
   - `feature_usage_table`: EXISTS ✅
   - `tracked_channels_table`: EXISTS ✅
   - `stripe.starter_monthly`: OK ✅
   - All other Stripe prices: OK ✅

