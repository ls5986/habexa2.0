# Create LIVE Mode Stripe Prices

Since you want to use **PRODUCTION (live) keys**, you need to create **LIVE mode prices** in Stripe.

## Current Situation

- ✅ Your `.env` has: `STRIPE_SECRET_KEY=sk_live_...` (LIVE mode) - **KEEP THIS**
- ✅ Your `.env` has: `STRIPE_PUBLISHABLE_KEY=pk_live_...` (LIVE mode) - **KEEP THIS**
- ❌ Your price IDs are: TEST mode prices - **NEED TO CREATE LIVE ONES**

## Solution: Create Live Mode Products & Prices

### Option 1: Via Stripe Dashboard (Easiest)

1. **Go to Stripe Dashboard (LIVE mode)**:
   - Make sure you're in **LIVE mode** (toggle in top right)
   - Go to: https://dashboard.stripe.com/products

2. **Create Products** (if they don't exist):
   - Click "Add product"
   - Create 3 products:
     - **Starter** - $29/month, $290/year
     - **Pro** - $79/month, $790/year
     - **Agency** - $199/month, $1990/year

3. **For each product, create 2 prices**:
   - Monthly price (recurring, monthly)
   - Yearly price (recurring, yearly, with 17% discount)

4. **Copy the LIVE price IDs**:
   - They'll start with `price_` but be different from your test prices
   - Example: `price_1ABC123...` (live) vs `price_1SZORR...` (test)

5. **Update `.env`** with the new LIVE price IDs:
   ```bash
   STRIPE_PRICE_STARTER_MONTHLY=price_xxxxx  # Your LIVE price ID
   STRIPE_PRICE_STARTER_YEARLY=price_xxxxx
   STRIPE_PRICE_PRO_MONTHLY=price_xxxxx
   STRIPE_PRICE_PRO_YEARLY=price_xxxxx
   STRIPE_PRICE_AGENCY_MONTHLY=price_xxxxx
   STRIPE_PRICE_AGENCY_YEARLY=price_xxxxx
   ```

### Option 2: Via Stripe CLI

```bash
# Make sure you're using LIVE mode
export STRIPE_API_KEY=sk_live_xxxxx

# Create Starter Monthly
stripe prices create \
  --product=prod_xxxxx \
  --unit-amount=2900 \
  --currency=usd \
  --recurring[interval]=month

# Create Starter Yearly
stripe prices create \
  --product=prod_xxxxx \
  --unit-amount=29000 \
  --currency=usd \
  --recurring[interval]=year

# Repeat for Pro and Agency...
```

### Option 3: Copy from Test to Live

If you want to copy your test products to live:

1. Go to test mode products
2. Use "Copy to live mode" feature (if available)
3. Or manually recreate in live mode

## Verify Your Live Prices

After creating, verify they work:

```bash
cd backend
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv('../.env')

import stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

prices = {
    'starter_monthly': os.getenv('STRIPE_PRICE_STARTER_MONTHLY'),
    'starter_yearly': os.getenv('STRIPE_PRICE_STARTER_YEARLY'),
    'pro_monthly': os.getenv('STRIPE_PRICE_PRO_MONTHLY'),
    'pro_yearly': os.getenv('STRIPE_PRICE_PRO_YEARLY'),
    'agency_monthly': os.getenv('STRIPE_PRICE_AGENCY_MONTHLY'),
    'agency_yearly': os.getenv('STRIPE_PRICE_AGENCY_YEARLY'),
}

for name, price_id in prices.items():
    try:
        price = stripe.Price.retrieve(price_id)
        amount = price.unit_amount / 100
        interval = price.recurring.interval if price.recurring else "one-time"
        mode = "LIVE" if price.livemode else "TEST"
        print(f"✅ {name}: ${amount}/{interval} ({mode})")
    except Exception as e:
        print(f"❌ {name}: {e}")
EOF
```

All should show `(LIVE)` mode.

## After Creating Live Prices

1. Update `.env` with LIVE price IDs
2. Restart backend
3. Run debug endpoint - Stripe should show all ✅

## Important Notes

- **LIVE mode = REAL MONEY** - Be careful when testing!
- Consider using test mode for development, live mode for production
- You can have both test and live keys in different environments

