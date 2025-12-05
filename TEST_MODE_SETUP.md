# TEST_MODE Setup Guide

## What This Does

Allows you to test Keepa and SP-API endpoints **without Supabase authentication** when:
1. `TEST_MODE=true` is set
2. Your IP is in the `ALLOWED_IPS` whitelist

## Setup in Render

### Step 1: Get Your IP Address

```bash
# Run this to get your current IP
curl -s https://api.ipify.org
```

### Step 2: Add Environment Variables in Render

Go to **Render Dashboard → habexa-backend → Environment**

Add these variables:

```
TEST_MODE=true
ALLOWED_IPS=YOUR_IP_ADDRESS
```

**Example:**
```
TEST_MODE=true
ALLOWED_IPS=123.45.67.89
```

**Multiple IPs (comma-separated):**
```
TEST_MODE=true
ALLOWED_IPS=123.45.67.89,98.76.54.32
```

### Step 3: Redeploy

After adding the env vars, Render will auto-redeploy. Wait ~2-3 minutes.

## Testing

Once deployed, you can test endpoints **without authentication**:

```bash
# Test Keepa
curl "https://habexa-backend-w5u5.onrender.com/api/v1/keepa/product/B0756548HD?days=90"

# Test SP-API
curl "https://habexa-backend-w5u5.onrender.com/api/v1/sp-api/product/B0756548HD"
```

## Security Notes

⚠️ **IMPORTANT:**
- Only enable `TEST_MODE` for testing/development
- Always use IP whitelisting (`ALLOWED_IPS`)
- Don't commit `TEST_MODE=true` to production
- Disable `TEST_MODE` when not testing

## How It Works

1. If `TEST_MODE=true` and your IP is in `ALLOWED_IPS`:
   - Endpoints work **without** Bearer token
   - Returns data normally

2. If `TEST_MODE=false` or IP not whitelisted:
   - Requires Bearer token (normal auth)
   - Returns 401 if no token

3. If token is provided (even in TEST_MODE):
   - Uses the authenticated user
   - Works normally

## Current Status

After deploying with `TEST_MODE=true` and your IP whitelisted:
- ✅ Keepa endpoints: `/api/v1/keepa/product/{asin}`
- ✅ SP-API endpoints: `/api/v1/sp-api/product/{asin}`

Both will work without authentication from your whitelisted IP.

