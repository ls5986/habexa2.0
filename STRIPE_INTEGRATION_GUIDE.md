# HABEXA STRIPE PAYMENT INTEGRATION
## Complete Billing System Implementation Guide

---

# TABLE OF CONTENTS

1. [Pricing Structure](#1-pricing-structure)
2. [Stripe Setup](#2-stripe-setup)
3. [Environment Variables](#3-environment-variables)
4. [Database Schema](#4-database-schema)
5. [Backend Implementation](#5-backend-implementation)
6. [Frontend Implementation](#6-frontend-implementation)
7. [Webhook Handling](#7-webhook-handling)
8. [Customer Portal](#8-customer-portal)
9. [Stripe CLI Testing](#9-stripe-cli-testing)
10. [Production Checklist](#10-production-checklist)

---

# 1. PRICING STRUCTURE

## Habexa Subscription Tiers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HABEXA PRICING TIERS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │     STARTER     │  │      PRO        │  │    AGENCY       │             │
│  │                 │  │                 │  │                 │             │
│  │    $29/mo       │  │    $79/mo       │  │    $199/mo      │             │
│  │   $290/yr       │  │   $790/yr       │  │   $1990/yr      │             │
│  │  (save 17%)     │  │  (save 17%)     │  │  (save 17%)     │             │
│  │                 │  │                 │  │                 │             │
│  │ • 3 Telegram    │  │ • 10 Telegram   │  │ • Unlimited     │             │
│  │   channels      │  │   channels      │  │   channels      │             │
│  │ • 100 analyses  │  │ • 500 analyses  │  │ • Unlimited     │             │
│  │   /month        │  │   /month        │  │   analyses      │             │
│  │ • Basic alerts  │  │ • Priority      │  │ • White-label   │             │
│  │ • Email support │  │   alerts        │  │ • API access    │             │
│  │                 │  │ • Chat support  │  │ • Team seats    │             │
│  │                 │  │ • Bulk analyze  │  │ • Dedicated     │             │
│  │                 │  │                 │  │   support       │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FREE TRIAL                                   │   │
│  │                    14 days of Pro features                           │   │
│  │                    No credit card required                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Stripe Product IDs (Create These in Stripe Dashboard)

```javascript
// These will be created via Stripe CLI or Dashboard
const STRIPE_PRODUCTS = {
  starter: {
    monthly: 'price_starter_monthly',  // $29/mo
    yearly: 'price_starter_yearly',    // $290/yr
  },
  pro: {
    monthly: 'price_pro_monthly',      // $79/mo
    yearly: 'price_pro_yearly',        // $790/yr
  },
  agency: {
    monthly: 'price_agency_monthly',   // $199/mo
    yearly: 'price_agency_yearly',     // $1990/yr
  }
};

// Feature limits by tier
const TIER_LIMITS = {
  free: {
    telegram_channels: 1,
    analyses_per_month: 10,
    suppliers: 3,
    alerts: false,
    bulk_analyze: false,
    api_access: false,
    team_seats: 1,
  },
  starter: {
    telegram_channels: 3,
    analyses_per_month: 100,
    suppliers: 10,
    alerts: true,
    bulk_analyze: false,
    api_access: false,
    team_seats: 1,
  },
  pro: {
    telegram_channels: 10,
    analyses_per_month: 500,
    suppliers: 50,
    alerts: true,
    bulk_analyze: true,
    api_access: false,
    team_seats: 3,
  },
  agency: {
    telegram_channels: -1,  // unlimited
    analyses_per_month: -1, // unlimited
    suppliers: -1,          // unlimited
    alerts: true,
    bulk_analyze: true,
    api_access: true,
    team_seats: 10,
  }
};
```

---

# 2. STRIPE SETUP

## Step 2.1: Create Stripe Account

1. Go to https://stripe.com
2. Sign up / Sign in
3. Complete account activation (for live payments)

## Step 2.2: Install Stripe CLI

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Windows (using scoop)
scoop install stripe

# Linux
# Download from https://github.com/stripe/stripe-cli/releases

# Login to Stripe CLI
stripe login
```

## Step 2.3: Create Products and Prices via CLI

Run these commands to create your products:

```bash
# Create Starter Product
stripe products create \
  --name="Habexa Starter" \
  --description="Perfect for individual sellers getting started"

# Note the product ID (prod_xxxxx), then create prices:
stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=2900 \
  --currency=usd \
  --recurring[interval]=month \
  --lookup-key="starter_monthly"

stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=29000 \
  --currency=usd \
  --recurring[interval]=year \
  --lookup-key="starter_yearly"

# Create Pro Product
stripe products create \
  --name="Habexa Pro" \
  --description="For serious sellers scaling their business"

stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=7900 \
  --currency=usd \
  --recurring[interval]=month \
  --lookup-key="pro_monthly"

stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=79000 \
  --currency=usd \
  --recurring[interval]=year \
  --lookup-key="pro_yearly"

# Create Agency Product
stripe products create \
  --name="Habexa Agency" \
  --description="For teams and agencies managing multiple accounts"

stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=19900 \
  --currency=usd \
  --recurring[interval]=month \
  --lookup-key="agency_monthly"

stripe prices create \
  --product="prod_xxxxx" \
  --unit-amount=199000 \
  --currency=usd \
  --recurring[interval]=year \
  --lookup-key="agency_yearly"
```

## Step 2.4: Get Your API Keys

From Stripe Dashboard → Developers → API keys:

- **Publishable key**: `pk_test_xxxxx` (frontend)
- **Secret key**: `sk_test_EXAMPLE_KEY_REPLACE_WITH_YOUR_ACTUAL_KEY` (backend)
- **Webhook secret**: `whsec_EXAMPLE_SECRET_REPLACE_WITH_YOUR_ACTUAL_SECRET` (from CLI or Dashboard)

---

# 3. ENVIRONMENT VARIABLES

Add to your `.env`:

```bash
# ============================================
# STRIPE CONFIGURATION
# ============================================

# API Keys (from Stripe Dashboard → Developers → API keys)
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_EXAMPLE_KEY_REPLACE_WITH_YOUR_ACTUAL_KEY

# Webhook Secret (from Stripe CLI or Dashboard)
STRIPE_WEBHOOK_SECRET=whsec_EXAMPLE_SECRET_REPLACE_WITH_YOUR_ACTUAL_SECRET

# Price IDs (from Stripe Dashboard or CLI output)
STRIPE_PRICE_STARTER_MONTHLY=price_xxxxxxxxxxxxxxxx
STRIPE_PRICE_STARTER_YEARLY=price_xxxxxxxxxxxxxxxx
STRIPE_PRICE_PRO_MONTHLY=price_xxxxxxxxxxxxxxxx
STRIPE_PRICE_PRO_YEARLY=price_xxxxxxxxxxxxxxxx
STRIPE_PRICE_AGENCY_MONTHLY=price_xxxxxxxxxxxxxxxx
STRIPE_PRICE_AGENCY_YEARLY=price_xxxxxxxxxxxxxxxx

# URLs
STRIPE_SUCCESS_URL=http://localhost:5173/billing/success
STRIPE_CANCEL_URL=http://localhost:5173/billing/cancel
FRONTEND_URL=http://localhost:5173

# For production, change to:
# STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
# STRIPE_SECRET_KEY=sk_live_EXAMPLE_KEY_REPLACE_WITH_YOUR_ACTUAL_KEY
# STRIPE_SUCCESS_URL=https://app.habexa.com/billing/success
# STRIPE_CANCEL_URL=https://app.habexa.com/billing/cancel
# FRONTEND_URL=https://app.habexa.com
```

Also add to frontend `.env`:

```bash
# frontend/.env
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxx
VITE_API_URL=http://localhost:8000/api/v1
```

---

# 4. DATABASE SCHEMA

Add these tables to your Supabase schema:

```sql
-- Subscriptions table
CREATE TABLE public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    -- Stripe IDs
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    stripe_price_id TEXT,
    
    -- Subscription details
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'pro', 'agency')),
    billing_interval TEXT CHECK (billing_interval IN ('month', 'year')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    
    -- Dates
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    
    -- Usage tracking
    analyses_used_this_period INTEGER DEFAULT 0,
    last_usage_reset TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Payment history
CREATE TABLE public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    subscription_id UUID REFERENCES public.subscriptions(id),
    
    -- Stripe data
    stripe_payment_intent_id TEXT,
    stripe_invoice_id TEXT,
    
    -- Payment details
    amount INTEGER NOT NULL,  -- in cents
    currency TEXT DEFAULT 'usd',
    status TEXT CHECK (status IN ('succeeded', 'failed', 'pending', 'refunded')),
    
    -- Metadata
    description TEXT,
    receipt_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices (for display)
CREATE TABLE public.invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    stripe_invoice_id TEXT UNIQUE,
    stripe_invoice_url TEXT,
    stripe_pdf_url TEXT,
    
    amount_due INTEGER,
    amount_paid INTEGER,
    currency TEXT DEFAULT 'usd',
    status TEXT,
    
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking (for metered features)
CREATE TABLE public.usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    
    feature TEXT NOT NULL,  -- 'analysis', 'channel_add', etc.
    quantity INTEGER DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own subscription" ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own payments" ON public.payments FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own invoices" ON public.invoices FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own usage" ON public.usage_records FOR SELECT USING (auth.uid() = user_id);

-- Service role can do everything (for webhooks)
CREATE POLICY "Service can manage subscriptions" ON public.subscriptions FOR ALL USING (true);
CREATE POLICY "Service can manage payments" ON public.payments FOR ALL USING (true);
CREATE POLICY "Service can manage invoices" ON public.invoices FOR ALL USING (true);
CREATE POLICY "Service can manage usage" ON public.usage_records FOR ALL USING (true);

-- Function to check user's tier limits
CREATE OR REPLACE FUNCTION check_user_limit(
    p_user_id UUID,
    p_feature TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_tier TEXT;
    v_limit INTEGER;
    v_current_usage INTEGER;
BEGIN
    -- Get user's tier
    SELECT tier INTO v_tier FROM public.subscriptions WHERE user_id = p_user_id;
    IF v_tier IS NULL THEN v_tier := 'free'; END IF;
    
    -- Get limit based on tier and feature
    CASE p_feature
        WHEN 'analyses_per_month' THEN
            CASE v_tier
                WHEN 'free' THEN v_limit := 10;
                WHEN 'starter' THEN v_limit := 100;
                WHEN 'pro' THEN v_limit := 500;
                WHEN 'agency' THEN v_limit := -1;  -- unlimited
            END CASE;
        WHEN 'telegram_channels' THEN
            CASE v_tier
                WHEN 'free' THEN v_limit := 1;
                WHEN 'starter' THEN v_limit := 3;
                WHEN 'pro' THEN v_limit := 10;
                WHEN 'agency' THEN v_limit := -1;
            END CASE;
        WHEN 'suppliers' THEN
            CASE v_tier
                WHEN 'free' THEN v_limit := 3;
                WHEN 'starter' THEN v_limit := 10;
                WHEN 'pro' THEN v_limit := 50;
                WHEN 'agency' THEN v_limit := -1;
            END CASE;
        ELSE v_limit := 0;
    END CASE;
    
    -- Unlimited
    IF v_limit = -1 THEN RETURN TRUE; END IF;
    
    -- Check current usage
    IF p_feature = 'analyses_per_month' THEN
        SELECT analyses_used_this_period INTO v_current_usage 
        FROM public.subscriptions WHERE user_id = p_user_id;
        RETURN COALESCE(v_current_usage, 0) < v_limit;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Index for performance
CREATE INDEX idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer ON public.subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_stripe_sub ON public.subscriptions(stripe_subscription_id);
CREATE INDEX idx_payments_user ON public.payments(user_id);
CREATE INDEX idx_usage_user_created ON public.usage_records(user_id, created_at);
```

---

# 5. BACKEND IMPLEMENTATION

## 5.1 Install Dependencies

```bash
pip install stripe
```

Add to `requirements.txt`:
```
stripe==7.0.0
```

## 5.2 Stripe Service

Create: `backend/app/services/stripe_service.py`

```python
import stripe
import os
from typing import Optional, Dict, Any
from datetime import datetime
from app.services.supabase_client import supabase

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Price ID mapping
PRICE_IDS = {
    "starter_monthly": os.getenv("STRIPE_PRICE_STARTER_MONTHLY"),
    "starter_yearly": os.getenv("STRIPE_PRICE_STARTER_YEARLY"),
    "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY"),
    "pro_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY"),
    "agency_monthly": os.getenv("STRIPE_PRICE_AGENCY_MONTHLY"),
    "agency_yearly": os.getenv("STRIPE_PRICE_AGENCY_YEARLY"),
}

PRICE_TO_TIER = {
    os.getenv("STRIPE_PRICE_STARTER_MONTHLY"): "starter",
    os.getenv("STRIPE_PRICE_STARTER_YEARLY"): "starter",
    os.getenv("STRIPE_PRICE_PRO_MONTHLY"): "pro",
    os.getenv("STRIPE_PRICE_PRO_YEARLY"): "pro",
    os.getenv("STRIPE_PRICE_AGENCY_MONTHLY"): "agency",
    os.getenv("STRIPE_PRICE_AGENCY_YEARLY"): "agency",
}

TIER_LIMITS = {
    "free": {
        "telegram_channels": 1,
        "analyses_per_month": 10,
        "suppliers": 3,
        "alerts": False,
        "bulk_analyze": False,
        "api_access": False,
        "team_seats": 1,
    },
    "starter": {
        "telegram_channels": 3,
        "analyses_per_month": 100,
        "suppliers": 10,
        "alerts": True,
        "bulk_analyze": False,
        "api_access": False,
        "team_seats": 1,
    },
    "pro": {
        "telegram_channels": 10,
        "analyses_per_month": 500,
        "suppliers": 50,
        "alerts": True,
        "bulk_analyze": True,
        "api_access": False,
        "team_seats": 3,
    },
    "agency": {
        "telegram_channels": -1,
        "analyses_per_month": -1,
        "suppliers": -1,
        "alerts": True,
        "bulk_analyze": True,
        "api_access": True,
        "team_seats": 10,
    }
}


class StripeService:
    """Handle all Stripe operations."""
    
    @staticmethod
    async def get_or_create_customer(user_id: str, email: str, name: str = None) -> str:
        """Get existing Stripe customer or create new one."""
        
        # Check if customer exists
        result = supabase.table("subscriptions")\
            .select("stripe_customer_id")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if result.data and result.data.get("stripe_customer_id"):
            return result.data["stripe_customer_id"]
        
        # Create new customer
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"user_id": user_id}
        )
        
        # Store in database
        supabase.table("subscriptions").upsert({
            "user_id": user_id,
            "stripe_customer_id": customer.id,
            "tier": "free",
            "status": "active"
        }, on_conflict="user_id").execute()
        
        return customer.id
    
    @staticmethod
    async def create_checkout_session(
        user_id: str,
        email: str,
        price_key: str,  # e.g., "pro_monthly"
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for subscription."""
        
        price_id = PRICE_IDS.get(price_key)
        if not price_id:
            raise ValueError(f"Invalid price key: {price_key}")
        
        # Get or create customer
        customer_id = await StripeService.get_or_create_customer(user_id, email)
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url or os.getenv("STRIPE_SUCCESS_URL") + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url or os.getenv("STRIPE_CANCEL_URL"),
            allow_promotion_codes=True,
            billing_address_collection="auto",
            subscription_data={
                "trial_period_days": 14,  # 14-day free trial
                "metadata": {"user_id": user_id}
            },
            metadata={"user_id": user_id}
        )
        
        return {
            "session_id": session.id,
            "url": session.url
        }
    
    @staticmethod
    async def create_portal_session(user_id: str) -> str:
        """Create a Stripe Customer Portal session."""
        
        result = supabase.table("subscriptions")\
            .select("stripe_customer_id")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data or not result.data.get("stripe_customer_id"):
            raise ValueError("No Stripe customer found")
        
        session = stripe.billing_portal.Session.create(
            customer=result.data["stripe_customer_id"],
            return_url=os.getenv("FRONTEND_URL") + "/settings?tab=billing"
        )
        
        return session.url
    
    @staticmethod
    async def get_subscription(user_id: str) -> Dict[str, Any]:
        """Get user's subscription details."""
        
        result = supabase.table("subscriptions")\
            .select("*")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data:
            return {
                "tier": "free",
                "status": "active",
                "limits": TIER_LIMITS["free"]
            }
        
        sub = result.data
        tier = sub.get("tier", "free")
        
        return {
            "tier": tier,
            "status": sub.get("status", "active"),
            "billing_interval": sub.get("billing_interval"),
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "trial_end": sub.get("trial_end"),
            "analyses_used": sub.get("analyses_used_this_period", 0),
            "limits": TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        }
    
    @staticmethod
    async def cancel_subscription(user_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel a subscription."""
        
        result = supabase.table("subscriptions")\
            .select("stripe_subscription_id")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data or not result.data.get("stripe_subscription_id"):
            raise ValueError("No active subscription found")
        
        if at_period_end:
            # Cancel at end of billing period
            subscription = stripe.Subscription.modify(
                result.data["stripe_subscription_id"],
                cancel_at_period_end=True
            )
        else:
            # Cancel immediately
            subscription = stripe.Subscription.delete(
                result.data["stripe_subscription_id"]
            )
        
        return {"status": "canceled", "cancel_at_period_end": at_period_end}
    
    @staticmethod
    async def reactivate_subscription(user_id: str) -> Dict[str, Any]:
        """Reactivate a subscription that was set to cancel."""
        
        result = supabase.table("subscriptions")\
            .select("stripe_subscription_id")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data or not result.data.get("stripe_subscription_id"):
            raise ValueError("No subscription found")
        
        subscription = stripe.Subscription.modify(
            result.data["stripe_subscription_id"],
            cancel_at_period_end=False
        )
        
        # Update database
        supabase.table("subscriptions")\
            .update({"cancel_at_period_end": False})\
            .eq("user_id", user_id)\
            .execute()
        
        return {"status": "reactivated"}
    
    @staticmethod
    async def change_plan(user_id: str, new_price_key: str) -> Dict[str, Any]:
        """Change subscription plan (upgrade/downgrade)."""
        
        new_price_id = PRICE_IDS.get(new_price_key)
        if not new_price_id:
            raise ValueError(f"Invalid price key: {new_price_key}")
        
        result = supabase.table("subscriptions")\
            .select("stripe_subscription_id")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data or not result.data.get("stripe_subscription_id"):
            raise ValueError("No active subscription found")
        
        subscription = stripe.Subscription.retrieve(
            result.data["stripe_subscription_id"]
        )
        
        # Update subscription with new price
        updated = stripe.Subscription.modify(
            subscription.id,
            items=[{
                "id": subscription["items"]["data"][0].id,
                "price": new_price_id,
            }],
            proration_behavior="create_prorations"
        )
        
        return {"status": "updated", "new_tier": PRICE_TO_TIER.get(new_price_id)}
    
    @staticmethod
    async def get_invoices(user_id: str, limit: int = 10) -> list:
        """Get user's invoice history."""
        
        result = supabase.table("invoices")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data or []
    
    @staticmethod
    async def check_feature_access(user_id: str, feature: str) -> bool:
        """Check if user has access to a feature based on their tier."""
        
        sub = await StripeService.get_subscription(user_id)
        limits = sub.get("limits", TIER_LIMITS["free"])
        
        # Boolean features
        if feature in ["alerts", "bulk_analyze", "api_access"]:
            return limits.get(feature, False)
        
        # Numeric limits
        limit = limits.get(feature, 0)
        if limit == -1:  # unlimited
            return True
        
        # Check usage for analyses
        if feature == "analyses_per_month":
            used = sub.get("analyses_used", 0)
            return used < limit
        
        return True
    
    @staticmethod
    async def increment_usage(user_id: str, feature: str, amount: int = 1):
        """Increment usage counter for a feature."""
        
        if feature == "analyses_per_month":
            # Increment analyses count
            supabase.rpc("increment_analyses", {
                "p_user_id": user_id,
                "p_amount": amount
            }).execute()
        
        # Log usage record
        supabase.table("usage_records").insert({
            "user_id": user_id,
            "feature": feature,
            "quantity": amount
        }).execute()


# Webhook handlers
class StripeWebhookHandler:
    """Handle Stripe webhook events."""
    
    @staticmethod
    async def handle_checkout_completed(session: Dict[str, Any]):
        """Handle successful checkout."""
        
        user_id = session.get("metadata", {}).get("user_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        
        if not user_id or not subscription_id:
            return
        
        # Get subscription details
        subscription = stripe.Subscription.retrieve(subscription_id)
        price_id = subscription["items"]["data"][0]["price"]["id"]
        tier = PRICE_TO_TIER.get(price_id, "starter")
        interval = subscription["items"]["data"][0]["price"]["recurring"]["interval"]
        
        # Update database
        supabase.table("subscriptions").upsert({
            "user_id": user_id,
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "stripe_price_id": price_id,
            "tier": tier,
            "billing_interval": interval,
            "status": subscription["status"],
            "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
            "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
            "trial_start": datetime.fromtimestamp(subscription["trial_start"]).isoformat() if subscription.get("trial_start") else None,
            "trial_end": datetime.fromtimestamp(subscription["trial_end"]).isoformat() if subscription.get("trial_end") else None,
        }, on_conflict="user_id").execute()
    
    @staticmethod
    async def handle_subscription_updated(subscription: Dict[str, Any]):
        """Handle subscription updates."""
        
        subscription_id = subscription["id"]
        price_id = subscription["items"]["data"][0]["price"]["id"]
        tier = PRICE_TO_TIER.get(price_id, "starter")
        interval = subscription["items"]["data"][0]["price"]["recurring"]["interval"]
        
        supabase.table("subscriptions")\
            .update({
                "stripe_price_id": price_id,
                "tier": tier,
                "billing_interval": interval,
                "status": subscription["status"],
                "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
                "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
                "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
                "canceled_at": datetime.fromtimestamp(subscription["canceled_at"]).isoformat() if subscription.get("canceled_at") else None,
            })\
            .eq("stripe_subscription_id", subscription_id)\
            .execute()
    
    @staticmethod
    async def handle_subscription_deleted(subscription: Dict[str, Any]):
        """Handle subscription cancellation."""
        
        subscription_id = subscription["id"]
        
        supabase.table("subscriptions")\
            .update({
                "tier": "free",
                "status": "canceled",
                "stripe_subscription_id": None,
                "stripe_price_id": None,
            })\
            .eq("stripe_subscription_id", subscription_id)\
            .execute()
    
    @staticmethod
    async def handle_invoice_paid(invoice: Dict[str, Any]):
        """Handle successful payment."""
        
        customer_id = invoice["customer"]
        
        # Get user_id from customer
        result = supabase.table("subscriptions")\
            .select("user_id")\
            .eq("stripe_customer_id", customer_id)\
            .single()\
            .execute()
        
        if not result.data:
            return
        
        user_id = result.data["user_id"]
        
        # Store invoice
        supabase.table("invoices").upsert({
            "user_id": user_id,
            "stripe_invoice_id": invoice["id"],
            "stripe_invoice_url": invoice.get("hosted_invoice_url"),
            "stripe_pdf_url": invoice.get("invoice_pdf"),
            "amount_due": invoice["amount_due"],
            "amount_paid": invoice["amount_paid"],
            "currency": invoice["currency"],
            "status": invoice["status"],
            "period_start": datetime.fromtimestamp(invoice["period_start"]).isoformat(),
            "period_end": datetime.fromtimestamp(invoice["period_end"]).isoformat(),
        }, on_conflict="stripe_invoice_id").execute()
        
        # Store payment record
        supabase.table("payments").insert({
            "user_id": user_id,
            "stripe_invoice_id": invoice["id"],
            "stripe_payment_intent_id": invoice.get("payment_intent"),
            "amount": invoice["amount_paid"],
            "currency": invoice["currency"],
            "status": "succeeded",
            "description": f"Payment for {invoice.get('lines', {}).get('data', [{}])[0].get('description', 'subscription')}",
            "receipt_url": invoice.get("hosted_invoice_url")
        }).execute()
        
        # Reset usage counter for new period
        supabase.table("subscriptions")\
            .update({
                "analyses_used_this_period": 0,
                "last_usage_reset": datetime.utcnow().isoformat()
            })\
            .eq("user_id", user_id)\
            .execute()
    
    @staticmethod
    async def handle_invoice_payment_failed(invoice: Dict[str, Any]):
        """Handle failed payment."""
        
        customer_id = invoice["customer"]
        
        result = supabase.table("subscriptions")\
            .select("user_id")\
            .eq("stripe_customer_id", customer_id)\
            .single()\
            .execute()
        
        if not result.data:
            return
        
        # Update subscription status
        supabase.table("subscriptions")\
            .update({"status": "past_due"})\
            .eq("stripe_customer_id", customer_id)\
            .execute()
        
        # TODO: Send email notification about failed payment
```

## 5.3 Billing API Endpoints

Create: `backend/app/api/v1/billing.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import stripe
import os

from app.api.deps import get_current_user
from app.services.stripe_service import StripeService, StripeWebhookHandler, TIER_LIMITS

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class CheckoutRequest(BaseModel):
    price_key: str  # e.g., "pro_monthly"


class ChangePlanRequest(BaseModel):
    new_price_key: str


# ============================================
# SUBSCRIPTION ENDPOINTS
# ============================================

@router.get("/subscription")
async def get_subscription(current_user = Depends(get_current_user)):
    """Get current subscription details."""
    
    return await StripeService.get_subscription(current_user["id"])


@router.get("/plans")
async def get_available_plans():
    """Get available subscription plans."""
    
    return {
        "plans": [
            {
                "tier": "starter",
                "name": "Starter",
                "description": "Perfect for individual sellers getting started",
                "monthly_price": 29,
                "yearly_price": 290,
                "price_keys": {
                    "monthly": "starter_monthly",
                    "yearly": "starter_yearly"
                },
                "features": TIER_LIMITS["starter"]
            },
            {
                "tier": "pro",
                "name": "Pro",
                "description": "For serious sellers scaling their business",
                "monthly_price": 79,
                "yearly_price": 790,
                "price_keys": {
                    "monthly": "pro_monthly",
                    "yearly": "pro_yearly"
                },
                "features": TIER_LIMITS["pro"],
                "popular": True
            },
            {
                "tier": "agency",
                "name": "Agency",
                "description": "For teams and agencies managing multiple accounts",
                "monthly_price": 199,
                "yearly_price": 1990,
                "price_keys": {
                    "monthly": "agency_monthly",
                    "yearly": "agency_yearly"
                },
                "features": TIER_LIMITS["agency"]
            }
        ]
    }


@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user = Depends(get_current_user)
):
    """Create a Stripe Checkout session."""
    
    try:
        session = await StripeService.create_checkout_session(
            user_id=current_user["id"],
            email=current_user["email"],
            price_key=request.price_key
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portal")
async def create_portal_session(current_user = Depends(get_current_user)):
    """Create a Stripe Customer Portal session."""
    
    try:
        url = await StripeService.create_portal_session(current_user["id"])
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(
    at_period_end: bool = True,
    current_user = Depends(get_current_user)
):
    """Cancel subscription."""
    
    try:
        result = await StripeService.cancel_subscription(
            current_user["id"],
            at_period_end=at_period_end
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reactivate")
async def reactivate_subscription(current_user = Depends(get_current_user)):
    """Reactivate a canceled subscription."""
    
    try:
        result = await StripeService.reactivate_subscription(current_user["id"])
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/change-plan")
async def change_plan(
    request: ChangePlanRequest,
    current_user = Depends(get_current_user)
):
    """Change subscription plan."""
    
    try:
        result = await StripeService.change_plan(
            current_user["id"],
            request.new_price_key
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices")
async def get_invoices(
    limit: int = 10,
    current_user = Depends(get_current_user)
):
    """Get invoice history."""
    
    invoices = await StripeService.get_invoices(current_user["id"], limit)
    return {"invoices": invoices}


@router.get("/usage")
async def get_usage(current_user = Depends(get_current_user)):
    """Get current usage stats."""
    
    subscription = await StripeService.get_subscription(current_user["id"])
    
    return {
        "tier": subscription["tier"],
        "analyses": {
            "used": subscription.get("analyses_used", 0),
            "limit": subscription["limits"]["analyses_per_month"],
            "unlimited": subscription["limits"]["analyses_per_month"] == -1
        },
        "period_ends": subscription.get("current_period_end")
    }


# ============================================
# WEBHOOK ENDPOINT
# ============================================

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]
    
    handlers = {
        "checkout.session.completed": StripeWebhookHandler.handle_checkout_completed,
        "customer.subscription.updated": StripeWebhookHandler.handle_subscription_updated,
        "customer.subscription.deleted": StripeWebhookHandler.handle_subscription_deleted,
        "invoice.paid": StripeWebhookHandler.handle_invoice_paid,
        "invoice.payment_failed": StripeWebhookHandler.handle_invoice_payment_failed,
    }
    
    handler = handlers.get(event_type)
    if handler:
        await handler(data)
    
    return {"status": "success"}


# ============================================
# FEATURE ACCESS CHECK (Use in other endpoints)
# ============================================

async def require_feature(feature: str):
    """Dependency to check feature access."""
    
    async def check_access(current_user = Depends(get_current_user)):
        has_access = await StripeService.check_feature_access(
            current_user["id"],
            feature
        )
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature}' not available on your plan. Please upgrade."
            )
        return current_user
    
    return check_access


# Example usage in analysis endpoint:
# @router.post("/analyze")
# async def analyze_asin(
#     data: AnalyzeRequest,
#     current_user = Depends(require_feature("analyses_per_month"))
# ):
#     # ... do analysis
#     await StripeService.increment_usage(current_user["id"], "analyses_per_month")
#     return result
```

## 5.4 Add Helper Function for Usage Increment

Add to Supabase SQL:

```sql
-- Function to increment analysis count
CREATE OR REPLACE FUNCTION increment_analyses(
    p_user_id UUID,
    p_amount INTEGER DEFAULT 1
) RETURNS VOID AS $$
BEGIN
    UPDATE public.subscriptions
    SET analyses_used_this_period = COALESCE(analyses_used_this_period, 0) + p_amount,
        updated_at = NOW()
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## 5.5 Register Router

In `backend/app/main.py`:

```python
from app.api.v1 import billing

app.include_router(billing.router, prefix="/api/v1")
```

---

# 6. FRONTEND IMPLEMENTATION

## 6.1 Install Stripe.js

```bash
cd frontend
npm install @stripe/stripe-js
```

## 6.2 Stripe Context

Create: `frontend/src/context/StripeContext.jsx`

```jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import api from '../services/api';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

const StripeContext = createContext();

export function StripeProvider({ children }) {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const response = await api.get('/billing/subscription');
      setSubscription(response.data);
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
    } finally {
      setLoading(false);
    }
  };

  const createCheckout = async (priceKey) => {
    const response = await api.post('/billing/checkout', { price_key: priceKey });
    const stripe = await stripePromise;
    
    // Redirect to Stripe Checkout
    window.location.href = response.data.url;
  };

  const openPortal = async () => {
    const response = await api.post('/billing/portal');
    window.location.href = response.data.url;
  };

  const cancelSubscription = async (atPeriodEnd = true) => {
    await api.post(`/billing/cancel?at_period_end=${atPeriodEnd}`);
    await fetchSubscription();
  };

  const reactivateSubscription = async () => {
    await api.post('/billing/reactivate');
    await fetchSubscription();
  };

  const changePlan = async (newPriceKey) => {
    await api.post('/billing/change-plan', { new_price_key: newPriceKey });
    await fetchSubscription();
  };

  const checkFeatureAccess = (feature) => {
    if (!subscription) return false;
    const limits = subscription.limits || {};
    
    // Boolean features
    if (typeof limits[feature] === 'boolean') {
      return limits[feature];
    }
    
    // Numeric limits (-1 = unlimited)
    if (limits[feature] === -1) return true;
    
    // Check usage for analyses
    if (feature === 'analyses_per_month') {
      return (subscription.analyses_used || 0) < limits[feature];
    }
    
    return true;
  };

  return (
    <StripeContext.Provider value={{
      subscription,
      loading,
      createCheckout,
      openPortal,
      cancelSubscription,
      reactivateSubscription,
      changePlan,
      checkFeatureAccess,
      refreshSubscription: fetchSubscription,
    }}>
      {children}
    </StripeContext.Provider>
  );
}

export function useStripe() {
  const context = useContext(StripeContext);
  if (!context) {
    throw new Error('useStripe must be used within a StripeProvider');
  }
  return context;
}
```

## 6.3 Pricing Page

Create: `frontend/src/pages/Pricing.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Chip,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
} from '@mui/material';
import { Check, Close, Star } from '@mui/icons-material';
import { useStripe } from '../context/StripeContext';
import api from '../services/api';

export default function Pricing() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [yearly, setYearly] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(null);
  const { subscription, createCheckout } = useStripe();

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await api.get('/billing/plans');
      setPlans(response.data.plans);
    } catch (error) {
      console.error('Failed to fetch plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (plan) => {
    setCheckoutLoading(plan.tier);
    try {
      const priceKey = yearly ? plan.price_keys.yearly : plan.price_keys.monthly;
      await createCheckout(priceKey);
    } catch (error) {
      console.error('Checkout failed:', error);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const formatFeature = (key, value) => {
    if (typeof value === 'boolean') {
      return { text: formatKey(key), included: value };
    }
    if (value === -1) {
      return { text: `Unlimited ${formatKey(key)}`, included: true };
    }
    return { text: `${value} ${formatKey(key)}`, included: true };
  };

  const formatKey = (key) => {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      <Box textAlign="center" mb={6}>
        <Typography variant="h3" fontWeight="bold" gutterBottom>
          Choose Your Plan
        </Typography>
        <Typography variant="h6" color="text.secondary" mb={3}>
          Start with a 14-day free trial. No credit card required.
        </Typography>
        
        <FormControlLabel
          control={
            <Switch
              checked={yearly}
              onChange={(e) => setYearly(e.target.checked)}
              color="primary"
            />
          }
          label={
            <Box display="flex" alignItems="center" gap={1}>
              <span>Annual billing</span>
              <Chip label="Save 17%" size="small" color="success" />
            </Box>
          }
        />
      </Box>

      <Grid container spacing={4} justifyContent="center">
        {plans.map((plan) => (
          <Grid item xs={12} md={4} key={plan.tier}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                border: plan.popular ? '2px solid' : '1px solid',
                borderColor: plan.popular ? 'primary.main' : 'divider',
              }}
            >
              {plan.popular && (
                <Chip
                  icon={<Star />}
                  label="Most Popular"
                  color="primary"
                  sx={{
                    position: 'absolute',
                    top: -12,
                    left: '50%',
                    transform: 'translateX(-50%)',
                  }}
                />
              )}
              
              <CardContent sx={{ flexGrow: 1, pt: plan.popular ? 4 : 2 }}>
                <Typography variant="h5" fontWeight="bold" gutterBottom>
                  {plan.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  {plan.description}
                </Typography>
                
                <Box mb={3}>
                  <Typography variant="h3" fontWeight="bold" display="inline">
                    ${yearly ? Math.round(plan.yearly_price / 12) : plan.monthly_price}
                  </Typography>
                  <Typography variant="body1" color="text.secondary" display="inline">
                    /month
                  </Typography>
                  {yearly && (
                    <Typography variant="body2" color="text.secondary">
                      ${plan.yearly_price} billed annually
                    </Typography>
                  )}
                </Box>

                <List dense>
                  {Object.entries(plan.features).map(([key, value]) => {
                    const feature = formatFeature(key, value);
                    return (
                      <ListItem key={key} sx={{ px: 0 }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          {feature.included ? (
                            <Check color="success" fontSize="small" />
                          ) : (
                            <Close color="disabled" fontSize="small" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={feature.text}
                          primaryTypographyProps={{
                            variant: 'body2',
                            color: feature.included ? 'text.primary' : 'text.disabled',
                          }}
                        />
                      </ListItem>
                    );
                  })}
                </List>
              </CardContent>

              <Box p={2} pt={0}>
                <Button
                  fullWidth
                  variant={plan.popular ? 'contained' : 'outlined'}
                  size="large"
                  onClick={() => handleSubscribe(plan)}
                  disabled={checkoutLoading !== null || subscription?.tier === plan.tier}
                >
                  {checkoutLoading === plan.tier ? (
                    <CircularProgress size={24} />
                  ) : subscription?.tier === plan.tier ? (
                    'Current Plan'
                  ) : (
                    'Start Free Trial'
                  )}
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Box textAlign="center" mt={6}>
        <Typography variant="body2" color="text.secondary">
          All plans include a 14-day free trial. Cancel anytime.
        </Typography>
      </Box>
    </Container>
  );
}
```

## 6.4 Billing Settings Component

Create: `frontend/src/components/features/settings/BillingSettings.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  CreditCard,
  Receipt,
  TrendingUp,
  Warning,
  OpenInNew,
} from '@mui/icons-material';
import { useStripe } from '../../../context/StripeContext';
import api from '../../../services/api';
import { useNavigate } from 'react-router-dom';

export default function BillingSettings() {
  const navigate = useNavigate();
  const {
    subscription,
    loading,
    openPortal,
    cancelSubscription,
    reactivateSubscription,
  } = useStripe();
  
  const [invoices, setInvoices] = useState([]);
  const [usage, setUsage] = useState(null);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchInvoices();
    fetchUsage();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await api.get('/billing/invoices');
      setInvoices(response.data.invoices);
    } catch (error) {
      console.error('Failed to fetch invoices:', error);
    }
  };

  const fetchUsage = async () => {
    try {
      const response = await api.get('/billing/usage');
      setUsage(response.data);
    } catch (error) {
      console.error('Failed to fetch usage:', error);
    }
  };

  const handleCancel = async () => {
    setActionLoading(true);
    try {
      await cancelSubscription(true);
      setCancelDialogOpen(false);
    } catch (error) {
      console.error('Failed to cancel:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReactivate = async () => {
    setActionLoading(true);
    try {
      await reactivateSubscription();
    } catch (error) {
      console.error('Failed to reactivate:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleManageBilling = async () => {
    setActionLoading(true);
    try {
      await openPortal();
    } catch (error) {
      console.error('Failed to open portal:', error);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  const isFreeTier = !subscription || subscription.tier === 'free';
  const usagePercent = usage?.analyses?.unlimited 
    ? 0 
    : (usage?.analyses?.used / usage?.analyses?.limit) * 100;

  return (
    <Box>
      {/* Current Plan */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="flex-start">
            <Box>
              <Typography variant="h6" gutterBottom>
                Current Plan
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Typography variant="h4" fontWeight="bold" color="primary">
                  {subscription?.tier?.charAt(0).toUpperCase() + subscription?.tier?.slice(1) || 'Free'}
                </Typography>
                <Chip
                  label={subscription?.status || 'active'}
                  color={subscription?.status === 'active' ? 'success' : 'warning'}
                  size="small"
                />
                {subscription?.cancel_at_period_end && (
                  <Chip label="Canceling" color="error" size="small" />
                )}
              </Box>
              {subscription?.current_period_end && (
                <Typography variant="body2" color="text.secondary">
                  {subscription.cancel_at_period_end
                    ? `Access until ${new Date(subscription.current_period_end).toLocaleDateString()}`
                    : `Renews ${new Date(subscription.current_period_end).toLocaleDateString()}`
                  }
                </Typography>
              )}
              {subscription?.trial_end && new Date(subscription.trial_end) > new Date() && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Trial ends {new Date(subscription.trial_end).toLocaleDateString()}
                </Alert>
              )}
            </Box>

            <Box display="flex" gap={1}>
              {isFreeTier ? (
                <Button
                  variant="contained"
                  onClick={() => navigate('/pricing')}
                >
                  Upgrade
                </Button>
              ) : (
                <>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/pricing')}
                  >
                    Change Plan
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<CreditCard />}
                    onClick={handleManageBilling}
                    disabled={actionLoading}
                  >
                    Manage Billing
                  </Button>
                </>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Usage */}
      {usage && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Usage This Period
            </Typography>
            
            <Box mb={2}>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">
                  Analyses
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {usage.analyses.unlimited
                    ? `${usage.analyses.used} (Unlimited)`
                    : `${usage.analyses.used} / ${usage.analyses.limit}`
                  }
                </Typography>
              </Box>
              {!usage.analyses.unlimited && (
                <LinearProgress
                  variant="determinate"
                  value={Math.min(usagePercent, 100)}
                  color={usagePercent > 90 ? 'error' : usagePercent > 70 ? 'warning' : 'primary'}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              )}
            </Box>

            {usagePercent > 80 && !usage.analyses.unlimited && (
              <Alert severity="warning" icon={<Warning />}>
                You've used {Math.round(usagePercent)}% of your analyses. 
                <Button size="small" onClick={() => navigate('/pricing')}>
                  Upgrade for more
                </Button>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Invoices */}
      {invoices.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Invoice History
            </Typography>
            
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Invoice</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {invoices.map((invoice) => (
                    <TableRow key={invoice.id}>
                      <TableCell>
                        {new Date(invoice.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        ${(invoice.amount_paid / 100).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={invoice.status}
                          size="small"
                          color={invoice.status === 'paid' ? 'success' : 'default'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        {invoice.stripe_pdf_url && (
                          <Button
                            size="small"
                            startIcon={<Receipt />}
                            href={invoice.stripe_pdf_url}
                            target="_blank"
                          >
                            PDF
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Cancel Subscription */}
      {!isFreeTier && !subscription?.cancel_at_period_end && (
        <Card>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="subtitle1" fontWeight="medium">
                  Cancel Subscription
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  You'll keep access until the end of your billing period.
                </Typography>
              </Box>
              <Button
                variant="outlined"
                color="error"
                onClick={() => setCancelDialogOpen(true)}
              >
                Cancel Plan
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Reactivate */}
      {subscription?.cancel_at_period_end && (
        <Card>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="subtitle1" fontWeight="medium">
                  Subscription Scheduled for Cancellation
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Your plan will be canceled on {new Date(subscription.current_period_end).toLocaleDateString()}.
                </Typography>
              </Box>
              <Button
                variant="contained"
                color="primary"
                onClick={handleReactivate}
                disabled={actionLoading}
              >
                Keep My Plan
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Cancel Dialog */}
      <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)}>
        <DialogTitle>Cancel Subscription?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to cancel? You'll lose access to:
          </Typography>
          <ul>
            <li>Premium analysis features</li>
            <li>Additional Telegram channels</li>
            <li>Priority support</li>
          </ul>
          <Typography variant="body2" color="text.secondary">
            You'll keep access until the end of your current billing period.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialogOpen(false)}>
            Keep Subscription
          </Button>
          <Button
            color="error"
            onClick={handleCancel}
            disabled={actionLoading}
          >
            {actionLoading ? <CircularProgress size={20} /> : 'Yes, Cancel'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
```

## 6.5 Success/Cancel Pages

Create: `frontend/src/pages/BillingSuccess.jsx`

```jsx
import React, { useEffect } from 'react';
import { Box, Container, Typography, Button, Card, CardContent } from '@mui/material';
import { CheckCircle } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useStripe } from '../context/StripeContext';
import confetti from 'canvas-confetti'; // npm install canvas-confetti

export default function BillingSuccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refreshSubscription } = useStripe();

  useEffect(() => {
    // Refresh subscription data
    refreshSubscription();
    
    // Celebration confetti
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });
  }, []);

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Card>
        <CardContent sx={{ textAlign: 'center', py: 6 }}>
          <CheckCircle sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            Welcome to Habexa Pro! 🎉
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={4}>
            Your subscription is now active. You have access to all premium features.
          </Typography>
          <Box display="flex" gap={2} justifyContent="center">
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/dashboard')}
            >
              Go to Dashboard
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/settings?tab=integrations')}
            >
              Connect Telegram
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
}
```

Create: `frontend/src/pages/BillingCancel.jsx`

```jsx
import React from 'react';
import { Box, Container, Typography, Button, Card, CardContent } from '@mui/material';
import { Cancel } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

export default function BillingCancel() {
  const navigate = useNavigate();

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Card>
        <CardContent sx={{ textAlign: 'center', py: 6 }}>
          <Cancel sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            Checkout Canceled
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={4}>
            No worries! Your card hasn't been charged. You can still use the free plan
            or try again when you're ready.
          </Typography>
          <Box display="flex" gap={2} justifyContent="center">
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/pricing')}
            >
              View Plans
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/dashboard')}
            >
              Continue Free
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
}
```

## 6.6 Add Routes

In `App.jsx`:

```jsx
import Pricing from './pages/Pricing';
import BillingSuccess from './pages/BillingSuccess';
import BillingCancel from './pages/BillingCancel';

// In your routes:
<Route path="/pricing" element={<Pricing />} />
<Route path="/billing/success" element={<BillingSuccess />} />
<Route path="/billing/cancel" element={<BillingCancel />} />
```

## 6.7 Add StripeProvider to App

In `App.jsx`:

```jsx
import { StripeProvider } from './context/StripeContext';

function App() {
  return (
    <AuthProvider>
      <StripeProvider>
        <ThemeProvider theme={theme}>
          {/* ... rest of app */}
        </ThemeProvider>
      </StripeProvider>
    </AuthProvider>
  );
}
```

---

# 9. STRIPE CLI TESTING

## Start Webhook Forwarding

```bash
# In a terminal, run:
stripe listen --forward-to localhost:8000/api/v1/billing/webhook

# This will output a webhook signing secret like:
# whsec_EXAMPLE_SECRET_REPLACE_WITH_YOUR_ACTUAL_SECRET
# 
# Copy this and add to your .env:
# STRIPE_WEBHOOK_SECRET=whsec_EXAMPLE_SECRET_REPLACE_WITH_YOUR_ACTUAL_SECRET
```

## Test Events

```bash
# Test checkout complete
stripe trigger checkout.session.completed

# Test subscription update
stripe trigger customer.subscription.updated

# Test payment success
stripe trigger invoice.paid

# Test payment failure
stripe trigger invoice.payment_failed
```

## Test Credit Cards

Use these test cards in Stripe Checkout:

| Card Number | Result |
|-------------|--------|
| 4242 4242 4242 4242 | Success |
| 4000 0000 0000 0002 | Decline |
| 4000 0000 0000 9995 | Insufficient funds |
| 4000 0025 0000 3155 | Requires authentication |

---

# 10. PRODUCTION CHECKLIST

- [ ] Switch to live Stripe keys (pk_live_, sk_live_EXAMPLE_KEY_REPLACE_WITH_YOUR_ACTUAL_KEY)
- [ ] Update webhook endpoint in Stripe Dashboard
- [ ] Set production URLs (SUCCESS_URL, CANCEL_URL, FRONTEND_URL)
- [ ] Enable Stripe Tax (if needed)
- [ ] Set up Stripe Radar for fraud protection
- [ ] Configure email receipts in Stripe Dashboard
- [ ] Set up dunning emails for failed payments
- [ ] Test complete flow with real card
- [ ] Configure Customer Portal in Stripe Dashboard
- [ ] Set up revenue reporting/analytics
- [ ] Implement proper error tracking (Sentry)

---

# QUICK REFERENCE

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /billing/subscription | Get current subscription |
| GET | /billing/plans | Get available plans |
| POST | /billing/checkout | Create checkout session |
| POST | /billing/portal | Create customer portal session |
| POST | /billing/cancel | Cancel subscription |
| POST | /billing/reactivate | Reactivate canceled sub |
| POST | /billing/change-plan | Upgrade/downgrade |
| GET | /billing/invoices | Get invoice history |
| GET | /billing/usage | Get usage stats |
| POST | /billing/webhook | Stripe webhook handler |

## Webhook Events Handled

- checkout.session.completed
- customer.subscription.updated
- customer.subscription.deleted
- invoice.paid
- invoice.payment_failed

---

*Document Version: 1.0*
