# PHASE 1.5: TIER ENFORCEMENT SYSTEM AUDIT

## 🔴 CRITICAL ISSUES FOUND

### Issue #1: Super Admin Check NOT Being Called
**Location**: `backend/app/api/v1/analysis.py:49`

```python
limit_check = await feature_gate.check_limit(current_user.id, "analyses_per_month")
```

**Problem**: `check_limit()` has a `user_email` parameter for super admin detection, but it's **NEVER PASSED**!

**Expected**:
```python
limit_check = await feature_gate.check_limit(
    current_user.id, 
    "analyses_per_month",
    user_email=getattr(current_user, 'email', None)  # ← MISSING!
)
```

**Impact**: Super admin bypass logic (lines 137-147 in `feature_gate.py`) never executes.

---

### Issue #2: Frontend Doesn't Know About Super Admin
**Location**: `frontend/src/hooks/useFeatureGate.js:55`

```javascript
const tier = subscription?.tier || 'free';
const limits = TIER_LIMITS[tier] || TIER_LIMITS.free;
```

**Problem**: Frontend uses hardcoded `TIER_LIMITS` based on `subscription.tier`. It has **NO WAY** to know if user is super admin.

**Impact**: Even if backend returns unlimited, frontend shows "0/10" because it doesn't check super admin status.

---

### Issue #3: Usage Being Tracked for Super Admins
**Location**: `backend/app/services/feature_gate.py:243-297`

The `increment_usage()` method does NOT check if user is super admin before incrementing.

**Problem**: Super admins' usage is being counted, which is wrong.

**Expected**: Should check `should_track_usage()` before incrementing.

---

### Issue #4: Duplicate Tier Limits Configuration
**Found in 2 places**:
1. `backend/app/services/feature_gate.py:17-62` (TIER_LIMITS)
2. `backend/app/services/stripe_service.py:33-70` (TIER_LIMITS)

**Problem**: Two sources of truth. If one changes, the other doesn't.

---

## 📊 CURRENT SYSTEM ARCHITECTURE

### Backend Tier System
**File**: `backend/app/services/feature_gate.py`

**Super Admin Detection**:
- ✅ Defined: `SUPER_ADMIN_EMAILS = ["lindsey@letsclink.com"]`
- ✅ Logic exists: Lines 137-147 check email and return unlimited
- ❌ **NOT CALLED**: `user_email` parameter never passed in API calls

**Tier Limits**:
- ✅ Defined: `TIER_LIMITS` dict with free/starter/pro/agency
- ✅ Limits: `analyses_per_month: 10` (free), `100` (starter), `500` (pro), `-1` (agency/unlimited)

**Usage Tracking**:
- ✅ Reads from: `subscriptions.analyses_used_this_period`
- ✅ Increments via: `feature_gate.increment_usage()`
- ❌ **NO SUPER ADMIN BYPASS**: Always increments, even for super admins

**Where Limits Are Checked**:
1. `backend/app/api/v1/analysis.py:49` - Single analysis (❌ no user_email)
2. `backend/app/api/v1/analysis.py:156` - After analysis (❌ no user_email)
3. `backend/app/api/v1/analysis.py:192` - Batch analysis (❌ no user_email)
4. `backend/app/api/v1/suppliers.py:44` - Supplier limit (❌ no user_email)
5. `backend/app/api/v1/telegram.py:113` - Telegram channels (❌ no user_email)

---

### Frontend Tier System
**File**: `frontend/src/hooks/useFeatureGate.js`

**Tier Detection**:
- Reads from: `subscription.tier` (from StripeContext)
- ❌ **NO SUPER ADMIN CHECK**: Hardcoded `TIER_LIMITS` lookup

**Usage Display**:
- Reads from: `subscription.analyses_used` (from StripeContext)
- ❌ **NO BACKEND CALL**: Doesn't fetch from `/billing/usage` endpoint

**Where Limits Are Displayed**:
1. `frontend/src/components/features/analyze/QuickAnalyzeModal.jsx:29-30`
   ```javascript
   const analysesUsed = subscription?.analyses_used || 0;
   const analysesLimit = getLimit('analyses_per_month');
   ```
   ❌ Uses frontend hardcoded limits, not backend

---

## 🔍 CODE TRACE: Why Super Admin Sees "0/10"

### Flow 1: Quick Analyze Modal
```
1. User opens Quick Analyze modal
2. Component calls: `useFeatureGate()` hook
3. Hook reads: `subscription.tier` from StripeContext
4. Hook looks up: `TIER_LIMITS[subscription.tier]` (hardcoded frontend)
5. Returns: `analyses_per_month: 10` (because tier is "free" or not set)
6. Displays: "0/10" ❌
```

**Root Cause**: Frontend doesn't know about super admin status.

---

### Flow 2: Backend Analysis Check
```
1. User clicks "Analyze"
2. Frontend calls: `POST /api/v1/analyze/single`
3. Backend calls: `feature_gate.check_limit(user_id, "analyses_per_month")`
4. check_limit() method:
   - Line 137: Checks `if user_email in SUPER_ADMIN_EMAILS`
   - ❌ BUT user_email is None (not passed!)
   - Falls through to line 162: `tier = await get_user_tier(user_id)`
   - Gets tier from database (probably "free")
   - Returns limit: 10 ❌
```

**Root Cause**: `user_email` parameter not passed in API calls.

---

## 📋 DATABASE SCHEMA

### User Model Fields
**Table**: `profiles` (Supabase auth.users)
- ✅ `id` (UUID)
- ✅ `email` (TEXT)
- ❌ **NO `role` field** - Super admin is determined by email list
- ❌ **NO `subscription_tier` field** - Stored in separate `subscriptions` table

### Subscription Model Fields
**Table**: `subscriptions`
- ✅ `user_id` (UUID, FK to profiles)
- ✅ `tier` (TEXT: 'free', 'starter', 'pro', 'agency')
- ✅ `status` (TEXT: 'active', 'trialing', 'canceled', etc.)
- ✅ `analyses_used_this_period` (INTEGER)
- ✅ `stripe_customer_id` (TEXT)
- ✅ `stripe_subscription_id` (TEXT)

**Issue**: No `role` field. Super admin is email-based only.

---

## 🎯 SUMMARY OF FINDINGS

### What Works
- ✅ Tier limits are defined (in 2 places, but defined)
- ✅ Super admin bypass logic exists (just not called)
- ✅ Usage tracking infrastructure exists
- ✅ Database schema supports tier storage

### What's Broken
1. ❌ **Super admin check never executes** - `user_email` not passed
2. ❌ **Frontend doesn't know about super admin** - uses hardcoded limits
3. ❌ **Usage tracked for super admins** - should be skipped
4. ❌ **Duplicate tier configs** - `feature_gate.py` and `stripe_service.py`
5. ❌ **Frontend doesn't call backend for limits** - uses local `TIER_LIMITS`

### Missing
- ❌ No centralized tier configuration
- ❌ No permissions service
- ❌ No usage service with super admin bypass
- ❌ No frontend API call to get accurate limits

---

## 🔧 FIXES NEEDED

### Immediate Fixes (Phase 2)
1. **Pass `user_email` to all `check_limit()` calls**
2. **Add super admin check to `increment_usage()`**
3. **Create centralized tier config** (remove duplicates)
4. **Create `/billing/usage` endpoint** that returns accurate limits
5. **Update frontend to call backend for limits** (not hardcoded)

### Architecture Improvements (Phase 2)
1. **Create `PermissionsService`** - centralized permission checks
2. **Create `UsageService`** - usage tracking with super admin bypass
3. **Create `subscription_tiers.py`** - single source of truth for limits
4. **Update frontend `useFeatureGate`** - call backend API instead of hardcoded

---

## 📝 FILES TO MODIFY

### Backend
1. `backend/app/api/v1/analysis.py` - Pass `user_email` to `check_limit()`
2. `backend/app/api/v1/suppliers.py` - Pass `user_email` to `check_limit()`
3. `backend/app/api/v1/telegram.py` - Pass `user_email` to `check_limit()`
4. `backend/app/services/feature_gate.py` - Add super admin check to `increment_usage()`
5. `backend/app/services/stripe_service.py` - Remove duplicate `TIER_LIMITS`

### Frontend
1. `frontend/src/hooks/useFeatureGate.js` - Call backend API for limits
2. `frontend/src/components/features/analyze/QuickAnalyzeModal.jsx` - Use backend limits
3. `frontend/src/context/StripeContext.jsx` - Fetch usage from backend

### New Files to Create
1. `backend/app/config/subscription_tiers.py` - Centralized tier config
2. `backend/app/services/permissions_service.py` - Permission checks
3. `backend/app/services/usage_service.py` - Usage tracking

---

## ✅ READY FOR PHASE 2

The foundation exists but has critical bugs:
- Super admin bypass exists but isn't called
- Frontend uses hardcoded limits instead of backend
- Usage tracking doesn't respect super admin status

**Proceed to Phase 2: Implement Centralized Tier System?**

