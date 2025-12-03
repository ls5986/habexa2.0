# USABILITY ISSUES FOUND

**Date**: 2025-01-XX
**Auditor**: Code Review + Analysis
**Status**: Issues Identified

---

## CRITICAL (Blocks Core Functionality)

### ISSUE-001: Signup Flow Doesn't Create Stripe Customer or Redirect to Checkout

- **Location:** `frontend/src/pages/Register.jsx`, `frontend/src/context/AuthContext.jsx`
- **Description:** 
  - Signup creates Supabase account but doesn't create Stripe customer
  - No redirect to pricing/checkout after signup
  - Landing page links to `/register?trial=true` but query param is ignored
  - User signs up → Goes to dashboard → No subscription → Can't use features
- **Steps to reproduce:**
  1. Go to landing page
  2. Click "Start Free Trial"
  3. Fill signup form
  4. Submit
  5. Observe: Redirects to dashboard, no Stripe customer created, no checkout
- **Expected:** 
  - After signup, create Stripe customer
  - If `?trial=true` in URL, redirect to pricing page with trial option
  - Or automatically start checkout with trial
- **Actual:** 
  - Signup completes, redirects to dashboard
  - No Stripe customer
  - User on free tier with no way to upgrade
- **Fix:** 
  - Update `signUp` in `AuthContext.jsx` to call backend `/auth/register` endpoint
  - Backend should create Stripe customer on registration
  - Frontend should check for `trial=true` query param and redirect to `/pricing` or auto-start checkout
- **Priority:** CRITICAL

---

### ISSUE-002: No Password Reset Flow

- **Location:** `frontend/src/pages/Login.jsx`
- **Description:** 
  - Login page has no "Forgot password" link
  - No password reset page exists
  - Users can't recover accounts if password is forgotten
- **Steps to reproduce:**
  1. Go to `/login`
  2. Look for "Forgot password" link
  3. Observe: Doesn't exist
- **Expected:** 
  - "Forgot password?" link on login page
  - `/forgot-password` page to enter email
  - Email sent with reset link
  - `/reset-password` page to set new password
- **Actual:** 
  - No password reset functionality
- **Fix:** 
  - Add "Forgot password?" link to Login.jsx
  - Create `ForgotPassword.jsx` page
  - Create `ResetPassword.jsx` page
  - Use Supabase `auth.resetPasswordForEmail()` and `auth.updateUser()`
- **Priority:** CRITICAL

---

### ISSUE-003: Register Page Doesn't Handle Trial Query Param

- **Location:** `frontend/src/pages/Register.jsx`
- **Description:** 
  - Landing page links to `/register?trial=true`
  - Register component doesn't read or use this query param
  - User intent (starting trial) is lost
- **Steps to reproduce:**
  1. Click "Start Free Trial" on landing page
  2. Observe URL: `/register?trial=true`
  3. Complete signup
  4. Observe: No trial started, no redirect to pricing
- **Expected:** 
  - Register page reads `trial` query param
  - After signup, redirects to pricing or auto-starts checkout with trial
- **Actual:** 
  - Query param ignored
  - Always redirects to dashboard
- **Fix:** 
  - Use `useSearchParams()` in Register.jsx
  - Check for `trial=true`
  - After signup, redirect to `/pricing` or call checkout with trial
- **Priority:** CRITICAL

---

## HIGH (Major UX Problems)

### ISSUE-004: No Delete Account Functionality

- **Location:** `frontend/src/pages/Settings.jsx`
- **Description:** 
  - Settings page has no "Delete Account" option
  - Users can't remove their account
  - GDPR/compliance issue
- **Steps to reproduce:**
  1. Go to Settings
  2. Look for "Delete Account" or "Danger Zone"
  3. Observe: Doesn't exist
- **Expected:** 
  - Settings → Danger Zone section
  - "Delete Account" button
  - Confirmation modal (type email to confirm)
  - Cancels Stripe subscription
  - Deletes all user data
  - Logs out user
- **Actual:** 
  - No delete account option
- **Fix:** 
  - Add "Danger Zone" section to Settings.jsx
  - Create delete account dialog
  - Backend endpoint: `DELETE /api/v1/auth/account`
  - Cancel Stripe subscription, delete user data, delete Supabase user
- **Priority:** HIGH

---

### ISSUE-005: No Password Change Functionality

- **Location:** `frontend/src/pages/Settings.jsx`
- **Description:** 
  - Settings page has Profile tab but no password change option
  - Users can't update their password
- **Steps to reproduce:**
  1. Go to Settings → Profile
  2. Look for password change form
  3. Observe: Only name and avatar fields
- **Expected:** 
  - Settings → Security tab
  - Password change form with:
    - Current password
    - New password
    - Confirm new password
  - Validation and success message
- **Actual:** 
  - No password change option
- **Fix:** 
  - Add "Security" tab to Settings.jsx
  - Create password change form
  - Use Supabase `auth.updateUser({ password: newPassword })`
- **Priority:** HIGH

---

### ISSUE-006: No API Keys Management (Pro/Enterprise Feature)

- **Location:** `frontend/src/pages/Settings.jsx`
- **Description:** 
  - Pro/Enterprise tiers have `api_access: true`
  - No UI to generate/manage API keys
  - Feature exists in tier but not accessible
- **Steps to reproduce:**
  1. Login as Pro user
  2. Go to Settings
  3. Look for "API Keys" section
  4. Observe: Doesn't exist
- **Expected:** 
  - Settings → API Keys tab (only visible for Pro+)
  - "Generate API Key" button
  - Key displayed once (with copy button)
  - List of active keys
  - Revoke key option
- **Actual:** 
  - No API keys UI
- **Fix:** 
  - Add "API Keys" tab to Settings.jsx (conditionally rendered for Pro+)
  - Backend endpoint: `POST /api/v1/auth/api-keys` (generate)
  - Backend endpoint: `GET /api/v1/auth/api-keys` (list)
  - Backend endpoint: `DELETE /api/v1/auth/api-keys/{id}` (revoke)
- **Priority:** HIGH

---

### ISSUE-007: BillingSuccess Page Doesn't Refresh Subscription

- **Location:** `frontend/src/pages/BillingSuccess.jsx`
- **Description:** 
  - Page calls `refreshSubscription()` but this function doesn't exist in StripeContext
  - Subscription may not update after successful checkout
- **Steps to reproduce:**
  1. Complete Stripe checkout
  2. Redirected to `/billing/success?session_id=xxx`
  3. Check subscription status
  4. Observe: May not be updated
- **Expected:** 
  - `refreshSubscription()` function exists
  - Calls `/billing/subscription` to refresh
  - Updates context state
- **Actual:** 
  - `refreshSubscription()` not defined in StripeContext
- **Fix:** 
  - Add `refreshSubscription` function to StripeContext.jsx
  - Call `fetchSubscription()` internally
- **Priority:** HIGH

---

### ISSUE-008: No Buy List Page

- **Location:** Missing
- **Description:** 
  - Products can be moved to "buy_list" stage
  - No dedicated page to view/manage buy list
  - No way to create orders from buy list
- **Steps to reproduce:**
  1. Move product to "buy_list" stage
  2. Look for "Buy List" page in navigation
  3. Observe: Doesn't exist
- **Expected:** 
  - `/buy-list` route
  - Shows all products in "buy_list" stage
  - Can adjust quantities
  - "Create Order" button
  - Total calculations
- **Actual:** 
  - No buy list page
- **Fix:** 
  - Create `frontend/src/pages/BuyList.jsx`
  - Add route in App.jsx
  - Add to sidebar navigation
  - Backend already has `/orders` endpoints
- **Priority:** HIGH

---

### ISSUE-009: No Orders Page

- **Location:** Missing
- **Description:** 
  - Backend has `/orders` endpoints
  - No frontend page to view order history
  - Users can't see past orders
- **Steps to reproduce:**
  1. Create an order (if possible)
  2. Look for "Orders" page
  3. Observe: Doesn't exist
- **Expected:** 
  - `/orders` route
  - List of all orders
  - Order details (products, quantities, totals)
  - Order status tracking
- **Actual:** 
  - No orders page
- **Fix:** 
  - Create `frontend/src/pages/Orders.jsx`
  - Add route in App.jsx
  - Add to sidebar navigation
  - Use existing `/orders` API endpoints
- **Priority:** HIGH

---

## MEDIUM (Minor UX Issues)

### ISSUE-010: Login Page Uses `href` Instead of React Router `Link`

- **Location:** `frontend/src/pages/Login.jsx` line 90
- **Description:** 
  - "Sign up" link uses `<Link href="/register">` instead of React Router
  - Causes full page reload instead of SPA navigation
- **Steps to reproduce:**
  1. Go to `/login`
  2. Click "Sign up" link
  3. Observe: Full page reload
- **Expected:** 
  - Uses React Router `Link` component
  - Smooth SPA navigation
- **Actual:** 
  - Uses `href` attribute
- **Fix:** 
  - Change `Link` import from `@mui/material` to `react-router-dom`
  - Use `<Link to="/register">` instead of `href`
- **Priority:** MEDIUM

---

### ISSUE-011: Register Page Uses `href` Instead of React Router `Link`

- **Location:** `frontend/src/pages/Register.jsx` line 99
- **Description:** 
  - "Sign in" link uses `href` instead of React Router
  - Same issue as Login page
- **Fix:** 
  - Same as ISSUE-010
- **Priority:** MEDIUM

---

### ISSUE-012: Products Page Empty State Missing `onAction` Callback

- **Location:** `frontend/src/pages/Products.jsx` line 515
- **Description:** 
  - Empty state shows "Add Your First ASIN" button
  - Button has `onClick` but EmptyState component expects `onAction` prop
  - May not work correctly
- **Steps to reproduce:**
  1. Go to Products page with no products
  2. Click "Add Your First ASIN" in empty state
  3. Observe: May not open dialog
- **Expected:** 
  - EmptyState receives `onAction` prop
  - Button opens "Add Product" dialog
- **Actual:** 
  - EmptyState component expects `onAction` but Products.jsx doesn't pass it
- **Fix:** 
  - Pass `onAction={() => setShowAddDialog(true)}` to EmptyState
  - Or update EmptyState to accept `onClick` as well
- **Priority:** MEDIUM

---

### ISSUE-013: Suppliers Page Empty State Missing `onAction` Callback

- **Location:** `frontend/src/pages/Suppliers.jsx` line 63
- **Description:** 
  - Same issue as Products page
  - EmptyState doesn't receive `onAction` prop
- **Fix:** 
  - Pass `onAction={handleAddSupplier}` to EmptyState
- **Priority:** MEDIUM

---

### ISSUE-014: No Loading States for Some Actions

- **Location:** Various components
- **Description:** 
  - Some actions don't show loading indicators
  - User doesn't know if action is processing
- **Examples:**
  - Bulk analyze: Shows loading but could be clearer
  - File upload: Has progress but initial upload lacks spinner
  - Export: No loading state
- **Fix:** 
  - Add loading states to all async actions
  - Disable buttons during processing
  - Show spinners or progress bars
- **Priority:** MEDIUM

---

### ISSUE-015: No Error Boundary or Global Error Handling

- **Location:** Missing
- **Description:** 
  - React errors can crash entire app
  - No graceful error recovery
  - Users see blank screen on errors
- **Expected:** 
  - Error boundary component
  - Shows friendly error message
  - Option to retry or go home
- **Actual:** 
  - No error boundary
- **Fix:** 
  - Create `ErrorBoundary.jsx` component
  - Wrap App in ErrorBoundary
  - Show user-friendly error page
- **Priority:** MEDIUM

---

### ISSUE-016: No 404 Page

- **Location:** Missing
- **Description:** 
  - Invalid URLs show blank page or error
  - No friendly 404 page
- **Expected:** 
  - `/404` route or catch-all
  - Shows "Page not found" message
  - Link back to dashboard
- **Actual:** 
  - No 404 handling
- **Fix:** 
  - Add catch-all route in App.jsx
  - Create `NotFound.jsx` page
- **Priority:** MEDIUM

---

## LOW (Polish/Enhancements)

### ISSUE-017: Password Requirements Not Shown

- **Location:** `frontend/src/pages/Register.jsx`
- **Description:** 
  - Password field has no helper text
  - Users don't know requirements (min length, complexity)
- **Expected:** 
  - Helper text: "Minimum 8 characters"
  - Or password strength indicator
- **Fix:** 
  - Add `helperText` to password TextField
  - Or add password strength component
- **Priority:** LOW

---

### ISSUE-018: No Email Verification Flow

- **Location:** Missing
- **Description:** 
  - Supabase sends verification email but no UI to handle it
  - No "Resend verification email" option
- **Expected:** 
  - Banner if email not verified
  - "Resend verification email" button
  - Success message after resend
- **Fix:** 
  - Check `user.email_confirmed_at` in AuthContext
  - Show banner if not verified
  - Add resend button using Supabase `auth.resend()`
- **Priority:** LOW

---

### ISSUE-019: No Mobile Menu/Hamburger

- **Location:** `frontend/src/components/layout/Sidebar.jsx`
- **Description:** 
  - Sidebar always visible on mobile
  - Takes up screen space
  - No hamburger menu to toggle
- **Expected:** 
  - Sidebar hidden on mobile by default
  - Hamburger menu in TopBar
  - Click toggles sidebar
- **Fix:** 
  - Add responsive breakpoint to hide sidebar on mobile
  - Add hamburger icon to TopBar
  - Toggle sidebar visibility
- **Priority:** LOW

---

### ISSUE-020: No Keyboard Shortcuts

- **Location:** Missing
- **Description:** 
  - No keyboard shortcuts for common actions
  - Power users would benefit
- **Expected:** 
  - `Cmd/Ctrl + K` for search
  - `Cmd/Ctrl + N` for new product
  - `Esc` to close modals
- **Fix:** 
  - Add keyboard event listeners
  - Document shortcuts in help menu
- **Priority:** LOW

---

## SUMMARY

**Total Issues Found**: 20
- **Critical**: 3
- **High**: 6
- **Medium**: 7
- **Low**: 4

**Next Steps:**
1. Fix all Critical issues immediately
2. Fix High priority issues
3. Create GitHub issues for Medium/Low
4. Re-test after fixes

---

**Last Updated**: 2025-01-XX

