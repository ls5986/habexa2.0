# PRE-FLIGHT CHECK: VERIFICATION INSTRUCTIONS

Before running the full workflow audit, verify these 5 critical fixes work.

---

## 1. Database Migration ✅

**Run in Supabase SQL Editor:**

```sql
-- First, run the migration
ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS had_free_trial BOOLEAN DEFAULT FALSE;

-- Update existing records
UPDATE public.subscriptions
SET had_free_trial = TRUE
WHERE trial_end IS NOT NULL AND had_free_trial IS NULL;

-- Then verify columns exist
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'subscriptions' 
AND column_name IN ('had_free_trial', 'trial_start', 'trial_end', 'cancel_at_period_end')
ORDER BY column_name;
```

**Expected output:**
- `had_free_trial` (boolean, default: false)
- `trial_start` (timestamptz, nullable)
- `trial_end` (timestamptz, nullable)
- `cancel_at_period_end` (boolean, default: false)

**Or use the verification script:**
```sql
-- Run: database/VERIFY_TRIAL_TRACKING.sql
```

---

## 2. Super Admin Bypass Test ✅

**Start backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Get your JWT token** (from browser DevTools → Application → Local Storage, or login via API)

**Test the endpoint:**
```bash
# Option 1: Use the preflight script
export JWT_TOKEN="your-jwt-token"
python scripts/preflight_check.py

# Option 2: Manual curl
curl -X GET "http://localhost:8000/api/v1/billing/user/limits" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | jq
```

**Expected response for super admin (lindsey@letsclink.com):**
```json
{
  "tier": "super_admin",
  "tier_display": "Super Admin (Unlimited)",
  "is_super_admin": true,
  "unlimited": true,
  "limits": {
    "analyses_per_month": {
      "limit": -1,
      "used": 0,
      "remaining": -1,
      "unlimited": true
    },
    ...
  }
}
```

**If you see `unlimited: false` or `tier: "free"`, the fix didn't work.**

---

## 3. Quick Analyze Modal Test ✅

**Manual browser test:**

1. Open app in browser (logged in as `lindsey@letsclink.com`)
2. Go to Products page
3. Click "Quick Analyze" button
4. Check the "Analyses This Month" display

**Expected:**
- Shows: "Analyses This Month: Unlimited ∞"
- Or: "Analyses This Month: 0 / Unlimited"

**NOT expected:**
- "Analyses This Month: 0/10"
- "Analyses This Month: 0/5"

**Screenshot or describe what you see.**

---

## 4. Environment Variables Check ✅

**Check local .env:**
```bash
cat .env | grep -E "SUPER_ADMIN|STRIPE|EMAIL"
```

**Required:**
- `SUPER_ADMIN_EMAILS=lindsey@letsclink.com`
- `STRIPE_SECRET_KEY=sk_...`
- `STRIPE_WEBHOOK_SECRET=whsec_...`

**Optional (for email service):**
- `EMAIL_PROVIDER=resend` (or sendgrid, postmark, ses)
- `EMAIL_API_KEY=...`
- `EMAIL_FROM=noreply@habexa.com`
- `EMAIL_FROM_NAME=Habexa`

**Or run the preflight script** (it checks these automatically):
```bash
python scripts/preflight_check.py YOUR_JWT_TOKEN
```

---

## 5. Stripe Webhook Configuration ✅

**In Stripe Dashboard → Developers → Webhooks:**

1. **Find your webhook endpoint URL:**
   - Should be: `https://your-backend.onrender.com/api/v1/billing/webhook`
   - Or: `http://localhost:8000/api/v1/billing/webhook` (for local testing)

2. **Verify these 7 events are enabled:**
   - [ ] `checkout.session.completed`
   - [ ] `customer.subscription.created`
   - [ ] `customer.subscription.updated`
   - [ ] `customer.subscription.deleted`
   - [ ] `customer.subscription.trial_will_end` ← **NEW - Make sure this is added**
   - [ ] `invoice.paid`
   - [ ] `invoice.payment_failed`

3. **Test webhook delivery:**
   - Use Stripe CLI: `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`
   - Or trigger a test event in Stripe Dashboard

---

## Automated Preflight Script

**Run the automated checks:**
```bash
# Set your JWT token
export JWT_TOKEN="your-jwt-token-here"
export API_URL="http://localhost:8000"  # or your production URL

# Run the script
python scripts/preflight_check.py
```

**The script checks:**
- ✅ Super admin API endpoint response
- ✅ Environment variables
- ✅ Code files exist
- ⚠️  Database migration (manual verification required)
- ⚠️  Quick Analyze modal (manual browser test required)
- ⚠️  Stripe webhooks (manual dashboard check required)

---

## Report Format

After completing all checks, report:

```
PRE-FLIGHT CHECK RESULTS
========================

1. Database Migration:
   - [ ] Ran migration
   - [ ] Columns verified: had_free_trial, trial_start, trial_end, cancel_at_period_end
   - Output: [paste SQL query results]

2. Super Admin API Test:
   - Response: [paste JSON]
   - [ ] unlimited: true
   - [ ] is_super_admin: true
   - [ ] tier: "super_admin"

3. Quick Analyze Modal:
   - Display shows: [what you see]
   - [ ] Shows "Unlimited ∞" or "0 / Unlimited"

4. Environment Variables:
   - [ ] SUPER_ADMIN_EMAILS set
   - [ ] STRIPE keys set
   - [ ] EMAIL config set (optional)

5. Stripe Webhooks:
   - URL: [your webhook URL]
   - [ ] All 7 events registered
   - Events: [list enabled events]

READY FOR FULL AUDIT: [ YES / NO - fix X first ]
```

---

## If Any Check Fails

**Common issues:**

1. **Super admin still shows limits:**
   - Check `SUPER_ADMIN_EMAILS` in `.env` matches your email exactly
   - Check `backend/app/config/tiers.py` uses `settings.super_admin_list`
   - Verify `PermissionsService.get_effective_limits()` is called

2. **Database columns missing:**
   - Run `database/ADD_TRIAL_TRACKING.sql` in Supabase
   - Verify table name is `subscriptions` not `users`

3. **Webhook events missing:**
   - Add `customer.subscription.trial_will_end` in Stripe Dashboard
   - Verify webhook URL is correct

4. **Quick Analyze shows wrong limits:**
   - Check frontend uses `/api/v1/billing/user/limits` endpoint
   - Verify `useFeatureGate` hook fetches from backend
   - Clear browser cache

---

**Once all 5 checks pass → Ready for full audit!** 🎉

