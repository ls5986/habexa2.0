# Stripe Integration Setup Instructions

## ✅ What's Been Implemented

1. ✅ Database schema (`database/stripe_schema.sql`)
2. ✅ Backend Stripe service (`backend/app/services/stripe_service.py`)
3. ✅ Billing API endpoints (`backend/app/api/v1/billing.py`)
4. ✅ Frontend Stripe context (`frontend/src/context/StripeContext.jsx`)
5. ✅ Pricing page (`frontend/src/pages/Pricing.jsx`)
6. ✅ Billing settings in Settings page
7. ✅ Success/Cancel pages
8. ✅ Usage tracking in analysis endpoints

## 📋 Setup Steps

### 1. Run Database Schema

Go to Supabase Dashboard → SQL Editor and run:
```sql
-- Copy and paste the contents of database/stripe_schema.sql
```

### 2. Create Products & Prices in Stripe

You need to create products and prices in your Stripe Dashboard:

**Option A: Via Stripe Dashboard**
1. Go to https://dashboard.stripe.com/products
2. Create 3 products:
   - **Habexa Starter** ($29/month, $290/year)
   - **Habexa Pro** ($79/month, $790/year)
   - **Habexa Agency** ($199/month, $1990/year)
3. For each product, create 2 prices (monthly and yearly)
4. Copy the Price IDs (they start with `price_`)

**Option B: Via Stripe CLI** (if you have it installed)
```bash
# Install Stripe CLI first: brew install stripe/stripe-cli/stripe
stripe login

# Create Starter Product
stripe products create --name="Habexa Starter" --description="Perfect for individual sellers"

# Note the product ID (prod_xxxxx), then create prices:
stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=2900 \
  --currency=usd \
  --recurring[interval]=month

stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=29000 \
  --currency=usd \
  --recurring[interval]=year

# Repeat for Pro and Agency products
```

### 3. Update Environment Variables

Add to your `.env` file:
```bash
# Get these from Stripe Dashboard → Developers → API keys
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx  # You already have this
STRIPE_SECRET_KEY=sk_live_xxxxx       # You already have this

# Get webhook secret from Stripe Dashboard → Developers → Webhooks
# Or use: stripe listen --forward-to localhost:8000/api/v1/billing/webhook
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Add the Price IDs you created above
STRIPE_PRICE_STARTER_MONTHLY=price_xxxxx
STRIPE_PRICE_STARTER_YEARLY=price_xxxxx
STRIPE_PRICE_PRO_MONTHLY=price_xxxxx
STRIPE_PRICE_PRO_YEARLY=price_xxxxx
STRIPE_PRICE_AGENCY_MONTHLY=price_xxxxx
STRIPE_PRICE_AGENCY_YEARLY=price_xxxxx
```

### 4. Set Up Webhook (For Production)

**For Local Development:**
```bash
# Install Stripe CLI
stripe listen --forward-to localhost:8000/api/v1/billing/webhook

# This will give you a webhook secret (whsec_xxxxx)
# Use this in your .env for local testing
```

**For Production:**
1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-api-domain.com/api/v1/billing/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
4. Copy the webhook signing secret to your `.env`

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install @stripe/stripe-js
```

### 6. Test the Integration

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to `/pricing` or `/settings?tab=billing`
4. Click "Get Started" on a plan
5. Use Stripe test card: `4242 4242 4242 4242`
6. Complete checkout
7. Verify subscription appears in Settings

## 🎯 Features Implemented

- ✅ Subscription checkout flow
- ✅ Customer Portal integration
- ✅ Subscription management (cancel/reactivate)
- ✅ Usage tracking (analyses per month)
- ✅ Feature access checks
- ✅ Invoice history
- ✅ Webhook handling
- ✅ Tier limits enforcement

## ⚠️ Important Notes

1. **Price IDs Required**: You MUST create products/prices in Stripe and add the Price IDs to `.env` before the checkout will work.

2. **Webhook Secret**: For production, you need to set up webhooks in Stripe Dashboard and add the secret to `.env`.

3. **Test Mode**: If using test keys (`pk_test_`), use test cards. For live keys (`pk_live_`), use real cards.

4. **Usage Tracking**: Analysis endpoints now check limits and increment usage automatically.

5. **Free Tier**: All users start on the free tier with 10 analyses/month.

## 🚀 Next Steps

1. Create products/prices in Stripe Dashboard
2. Add Price IDs to `.env`
3. Set up webhook endpoint
4. Test checkout flow
5. Deploy and configure production webhook

The integration is complete and ready to use once you add the Price IDs!

