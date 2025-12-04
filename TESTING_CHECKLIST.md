# Testing Checklist - Post-Fix Verification

**Date:** 2025-12-04  
**Purpose:** Verify all fixes are working correctly

---

## Test 1: Signup Flow

### Steps:
1. Navigate to: `https://habexa-frontend.onrender.com/register`
2. Fill in form:
   - Full Name: `Test User`
   - Email: `test-$(date +%s)@example.com` (unique email)
   - Password: `Test123!@#`
3. Click "Sign Up"

### Expected Results:
- ✅ **Success:** Account created, redirected to dashboard
- ⚠️ **Email Confirmation:** If email confirmation required, shows message to check email
- ❌ **Error:** Shows specific error message (not generic "Registration failed")

### Error Messages to Check:
- "An account with this email already exists" (if email exists)
- "Please enter a valid email address" (if invalid email)
- "Password is too weak..." (if password too weak)
- "Registration service temporarily unavailable..." (if Supabase 500)
- "Network error..." (if network issue)

### Browser Console Check:
- Look for any errors
- Check if profile creation succeeded
- Check if subscription initialization was attempted

---

## Test 2: Login Flow

### Steps:
1. Navigate to: `https://habexa-frontend.onrender.com/login`
2. Enter credentials:
   - Email: `lindsey@letsclink.com`
   - Password: `Millie#5986`
3. Click "Sign In"

### Expected Results:
- ✅ **Success:** Logged in, redirected to `/dashboard`
- ❌ **Error:** Shows specific error message if login fails

### Browser Console Check:
After login, check console for:
```
API Request: /billing/subscription
Token exists: true
Token length: [should be 200-300 for Supabase JWT]
Auth header set
```

### Network Tab Check:
1. Open DevTools → Network tab
2. Filter by "subscription"
3. Find request: `GET /api/v1/billing/subscription`
4. Check:
   - **Status:** Should be `200 OK` (not 403)
   - **Request Headers:** Should include `Authorization: Bearer <token>`
   - **Response:** Should return subscription JSON

---

## Test 3: Dashboard Load

### Steps:
1. After successful login, dashboard should load automatically
2. Wait for page to fully load

### Expected Results:
- ✅ Dashboard displays without errors
- ✅ Subscription data loads (or shows error message if fetch fails)
- ✅ No console errors

### Browser Console Check:
Look for:
- `API Request: /billing/subscription`
- `Token exists: true`
- `Auth header set`
- If error: `Subscription fetch failed: [status] [data]`
- If retry: `Retrying subscription fetch...`

### Network Tab Check:
- `/api/v1/billing/subscription` - Should be 200 (or 401 if token invalid)
- `/api/v1/products` - Should be 200 (if called)
- `/api/v1/deals` - Should be 200 (if called)
- `/api/v1/notifications` - Should be 200 (if called)

---

## Test 4: Products Page

### Steps:
1. Navigate to: `/products`
2. Wait for page to load

### Expected Results:
- ✅ Products page loads
- ✅ Product list displays (or empty state if no products)
- ✅ No 403 errors

### Network Tab Check:
- `GET /api/v1/products` - Should be 200 (not 403)
- Request should include `Authorization: Bearer <token>`

---

## Test 5: Quick Analyze

### Steps:
1. Click "Quick Analyze" button (top right)
2. Enter:
   - ASIN: `B07VRZ8TK3`
   - Buy Cost: `10`
3. Click "Analyze"

### Expected Results:
- ✅ Analysis starts
- ✅ Shows loading state
- ✅ Results display or error message shown

### Network Tab Check:
- `POST /api/v1/analyze/single` - Should be 200 (not 403)
- Request should include `Authorization: Bearer <token>`

---

## Test 6: API Endpoint Verification

### Test with curl (from terminal):

```bash
# Get auth token (from browser localStorage after login)
TOKEN="your_token_here"

# Test subscription endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://habexa-backend-w5u5.onrender.com/api/v1/billing/subscription

# Should return 200 with subscription data, not 403
```

---

## Expected Console Logs (After Login)

```
API Request: /billing/subscription
Token exists: true
Token length: 234
Auth header set
```

If subscription fetch fails:
```
Subscription fetch failed: 403 {detail: "Not authenticated"}
Full error: [error object]
Retrying subscription fetch...
```

---

## Expected Network Requests (After Login)

| Endpoint | Method | Expected Status | Headers |
|----------|--------|----------------|---------|
| `/api/v1/billing/subscription` | GET | 200 | `Authorization: Bearer <token>` |
| `/api/v1/products` | GET | 200 | `Authorization: Bearer <token>` |
| `/api/v1/deals` | GET | 200 | `Authorization: Bearer <token>` |
| `/api/v1/notifications` | GET | 200 | `Authorization: Bearer <token>` |

---

## Backend Logs to Check

After testing, check backend logs (Render dashboard) for:

```
INFO: Auth attempt - Token length: 234
INFO: Auth attempt - Token prefix: eyJhbGciOiJIUzI1NiIsInR...
INFO: JWT decode result: True/False
INFO: User ID from JWT: [user_id]
INFO: User found via JWT path: [user_id], email: [email]
```

Or if auth fails:
```
ERROR: JWT decode error: [error]
ERROR: Supabase fallback error: [error]
ERROR: All auth methods failed - returning 401 Unauthorized
```

---

## Issues to Report

If any of these occur, report them:

1. **Signup fails with 500** - Supabase configuration issue
2. **Login succeeds but subscription returns 403** - Auth token validation issue
3. **Token exists: false** - Token not being stored correctly
4. **Auth header not set** - API interceptor issue
5. **All endpoints return 403** - Backend auth validation failing
6. **Network errors** - CORS or connectivity issues

---

## Quick Verification Commands

```bash
# Check if production build has correct URL
grep -r "habexa-backend-w5u5.onrender.com" frontend/dist/ | head -1
# Should find the URL

# Check if localhost is NOT in production build
grep -r "localhost:8020" frontend/dist/ | head -1
# Should return nothing

# Verify .env.production exists
cat frontend/.env.production | grep VITE_API_URL
# Should show: VITE_API_URL=https://habexa-backend-w5u5.onrender.com
```

---

**End of Testing Checklist**

