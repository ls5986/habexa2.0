# CORS Fix Guide

## Issue
Browser shows CORS errors even though backend CORS is configured correctly.

## Root Cause
The CORS middleware is working (verified with curl), but browsers cache CORS responses. The backend was restarted, but your browser may still have the old CORS response cached.

## Solutions

### Solution 1: Hard Refresh Browser (Recommended)
1. **Mac**: Press `Cmd + Shift + R`
2. **Windows/Linux**: Press `Ctrl + Shift + R`
3. This forces the browser to bypass cache and get fresh CORS headers

### Solution 2: Clear Browser Cache
1. Open Chrome DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Solution 3: Use Incognito Mode
1. Open Chrome in Incognito (Cmd+Shift+N / Ctrl+Shift+N)
2. Navigate to `http://localhost:5189`
3. Extensions are disabled and cache is fresh

### Solution 4: Verify Backend is Running
```bash
# Check if backend is running
curl http://localhost:8000/health

# Should return: {"status":"healthy"}

# Test CORS
curl -v -H "Origin: http://localhost:5189" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/v1/deals

# Should see: access-control-allow-origin: http://localhost:5189
```

## Current CORS Configuration

The backend allows these origins:
- `http://localhost:5173` (default Vite port)
- `http://localhost:5189` (your current frontend port)
- `http://localhost:3000` (alternative port)
- Value from `FRONTEND_URL` env variable

## Other Issues Found

### 1. Notifications Table Error
**Error**: `Could not find the table 'public.notifications' in the schema cache`

**Fix**:
1. Go to Supabase Dashboard → SQL Editor
2. Run: `SELECT * FROM public.notifications LIMIT 1;`
3. This refreshes the schema cache
4. Or create the table if it doesn't exist (run `database/schema.sql`)

### 2. Amazon Connection 404
**Error**: `404 Not Found` on `/api/v1/integrations/amazon/connection`

**Fix**:
- This endpoint requires authentication
- Make sure you're logged in
- Check that the JWT token is being sent in the Authorization header

### 3. Telegram Phone Number Error
**Error**: `The phone number is invalid`

**Fix**:
- Phone number must be in international format with `+` prefix
- Example: `+1234567890` (US), `+447700900123` (UK)
- The backend will try to add `+` if missing, but it's better to provide it

## Verification

After applying fixes, you should see:
- ✅ No CORS errors in console
- ✅ API calls return 200/401 (not CORS errors)
- ✅ Data loads on dashboard

## Still Having Issues?

1. **Check backend logs**: `tail -f /tmp/habexa_backend.log`
2. **Check browser network tab**: Look for actual error responses
3. **Verify authentication**: Make sure you're logged in
4. **Check Supabase**: Verify tables exist and RLS policies are set

