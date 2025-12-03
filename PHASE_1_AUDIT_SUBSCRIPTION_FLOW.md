# PHASE 1: AUDIT CURRENT SIGNUP/CHECKOUT FLOW

## CURRENT STATE ANALYSIS

### 1. User Registration Flow

**Status**: ❌ **NOT FOUND**
- No dedicated `/auth/register` endpoint found
- Registration likely handled by Supabase Auth (frontend)
- **Gap**: No backend endpoint that creates Stripe customer on signup

**Location**: Frontend handles signup via Supabase Auth
- `frontend/src/pages/Register.jsx` likely uses Supabase client
- No backend registration endpoint found

**Action Needed**: 
- Create backend registration endpoint OR
- Hook into Supabase Auth webhook to create Stripe customer

---

### 2. Checkout Session Creation

**Status**: ✅ **EXISTS BUT INCOMPLETE**

**Location**: `backend/app/services/stripe_service.py` → `create_checkout_session()`

**Current Implementation** (lines 71-160):
```python
async def create_checkout_session(
    user_id: str,
    email: str,
    price_key: str,
    success_url: str = None,
    cancel_url: str = None
) -> Dict[str, Any]:
    # Creates Stripe customer if needed
    # Checks for existing subscriptions
    # Creates checkout session
    # ❌ NO TRIAL PERIOD CONFIGURATION
```

**Gaps**:
- ❌ No `subscription_data.trial_period_days` parameter
- ❌ No check for `had_free_trial` flag
- ❌ No `include_trial` parameter in request
- ❌ Trial tracking fields not checked

**Endpoint**: `POST /api/v1/billing/checkout` (in `billing.py` line ~160)

---

### 3. Webhook Handling

**Status**: ✅ **EXISTS BUT INCOMPLETE**

**Location**: `backend/app/services/stripe_service.py` → `StripeWebhookHandler`

**Current Events Handled**:
- ✅ `checkout.session.completed` → `handle_checkout_completed()`
- ✅ `customer.subscription.updated` → `handle_subscription_updated()`
- ✅ `customer.subscription.deleted` → `handle_subscription_deleted()`
- ✅ `invoice.paid` → `handle_invoice_paid()`
- ✅ `invoice.payment_failed` → `handle_invoice_payment_failed()`

**Missing Events**:
- ❌ `customer.subscription.trial_will_end` (3 days before trial ends)
- ❌ `customer.subscription.created` (separate from checkout)

**Current Implementation Issues**:
- ✅ Stores `trial_start` and `trial_end` in database
- ❌ Does NOT set `had_free_trial` flag
- ❌ Does NOT track trial status separately

**Location**: `backend/app/api/v1/billing.py` → `/webhook` endpoint (line ~359)

---

### 4. Database Schema

**Status**: ✅ **EXISTS**

**Location**: `database/stripe_schema.sql`

**Current Fields in `subscriptions` table**:
- ✅ `stripe_customer_id`
- ✅ `stripe_subscription_id`
- ✅ `tier`
- ✅ `status`
- ✅ `current_period_start`
- ✅ `current_period_end`
- ✅ `trial_start`
- ✅ `trial_end`
- ❌ **MISSING**: `had_free_trial` (Boolean)
- ❌ **MISSING**: `cancel_at_period_end` (Boolean)
- ❌ **MISSING**: `trial_start_date` (separate from trial_start timestamp)

**Action Needed**: Add missing fields to schema

---

### 5. Subscription Management Endpoints

**Status**: ⚠️ **PARTIAL**

**Existing Endpoints** (in `billing.py`):
- ✅ `GET /billing/subscription` - Get subscription status
- ✅ `POST /billing/sync` - Sync from Stripe
- ✅ `POST /billing/reactivate` - Reactivate subscription
- ✅ `POST /billing/change-plan` - Change plan
- ✅ `POST /billing/set-tier` - Super admin set tier

**Missing Endpoints**:
- ❌ `POST /billing/cancel-subscription` - Cancel at period end
- ❌ `POST /billing/cancel-immediately` - Cancel immediately
- ❌ `POST /billing/resume-subscription` - Resume cancelled subscription
- ❌ `POST /billing/resubscribe` - Resubscribe after cancellation
- ❌ `POST /billing/portal-session` - Stripe billing portal

---

### 6. Frontend Subscription Management

**Status**: ❌ **MISSING**

**Current State**:
- ✅ Pricing page exists (`frontend/src/pages/Pricing.jsx`)
- ✅ Landing page has CTAs
- ❌ No billing settings page
- ❌ No subscription management UI
- ❌ No cancel/resume buttons

**Action Needed**: Create `BillingSettings.jsx` component

---

## SUMMARY OF GAPS

### Critical Gaps:
1. ❌ **No trial period in checkout** - Checkout doesn't include `trial_period_days`
2. ❌ **No trial tracking** - `had_free_trial` flag not set
3. ❌ **No cancel endpoints** - Can't cancel subscription
4. ❌ **No billing portal** - No Stripe portal access
5. ❌ **Missing webhook events** - `trial_will_end` not handled

### Medium Priority:
6. ⚠️ **No registration hook** - Stripe customer not created on signup
7. ⚠️ **No frontend management UI** - Users can't manage subscription

### Low Priority:
8. ⚠️ **Database schema gaps** - Missing `had_free_trial`, `cancel_at_period_end` fields

---

## IMPLEMENTATION ORDER

1. **Phase 2**: Add trial support to checkout + database fields
2. **Phase 3**: Add cancel/resume endpoints
3. **Phase 4**: Add billing portal endpoint
4. **Phase 5**: Update webhook handlers for full lifecycle
5. **Phase 6**: Create frontend billing settings page
6. **Phase 7**: Add registration hook (optional - can use webhook)

---

## FILES TO MODIFY

1. `database/stripe_schema.sql` - Add missing fields
2. `backend/app/services/stripe_service.py` - Add trial to checkout, update webhooks
3. `backend/app/api/v1/billing.py` - Add cancel/resume/portal endpoints
4. `frontend/src/pages/BillingSettings.jsx` - Create new component
5. `frontend/src/App.jsx` - Add billing settings route

---

**Ready to proceed with implementation!**

