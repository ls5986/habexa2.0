# Fix Stripe Mode Mismatch

## The Problem
- Your `.env` has: `STRIPE_SECRET_KEY=sk_live_...` (LIVE mode)
- Your prices are: TEST mode prices
- **They can't see each other!**

## The Fix

### Step 1: Get Your Test Keys

1. Go to: https://dashboard.stripe.com/test/apikeys
2. Copy:
   - **Secret key** (starts with `sk_test_`)
   - **Publishable key** (starts with `pk_test_`)

### Step 2: Update `.env`

Replace these lines in your `.env` file:

```bash
# OLD (LIVE mode - replace with YOUR keys):
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx

# NEW (TEST mode - replace with YOUR test keys):
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Keep Your Price IDs (They're Correct!)

Your price IDs are already correct for TEST mode - **don't change them**:

```bash
STRIPE_PRICE_STARTER_MONTHLY=price_1SZORRJNvcs70HLsSDG5Hq0s
STRIPE_PRICE_STARTER_YEARLY=price_1SZORSJNvcs70HLsKJwqAOzG
STRIPE_PRICE_PRO_MONTHLY=price_1SZORSJNvcs70HLsixbu4BSn
STRIPE_PRICE_PRO_YEARLY=price_1SZORTJNvcs70HLsKUcCvTkn
STRIPE_PRICE_AGENCY_MONTHLY=price_1SZORUJNvcs70HLssB33RtdN
STRIPE_PRICE_AGENCY_YEARLY=price_1SZORUJNvcs70HLs4XqrPV3l
```

### Step 4: Restart Backend

After updating `.env`:
```bash
# Kill current backend
lsof -ti:8000 | xargs kill -9

# Restart
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Verify

Run the debug endpoint again - Stripe section should show:
- ✅ `status: "CONNECTED"`
- ✅ All price IDs: `OK - $XX/interval`

## Also Don't Forget!

Run the SQL script to create missing tables:
- `database/FIX_MISSING_TABLES.sql` in Supabase SQL Editor

This will create:
- `feature_usage` table
- `tracked_channels` table

