# Debug Endpoint Setup

## ✅ What Was Created

1. **Backend Debug Endpoint**: `backend/app/api/v1/debug.py`
   - `/api/v1/debug/test-all` - Tests all integrations
   - `/api/v1/debug/test-stripe-checkout` - Tests Stripe checkout creation
   - `/api/v1/debug/test-keepa/{asin}` - Tests Keepa API for an ASIN
   - `/api/v1/debug/test-amazon/{asin}` - Tests Amazon SP-API for an ASIN

2. **Frontend Debug Page**: `frontend/src/pages/Debug.jsx`
   - Accessible at `/debug` route
   - Shows detailed test results for all integrations

3. **Router Registration**: Added to `backend/app/main.py`

## 🚀 How to Use

### Step 1: Start Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Access Debug Page
1. Open frontend: `http://localhost:5189`
2. Login with your account
3. Navigate to: `http://localhost:5189/debug`
4. Click "Run All Tests"

### Step 3: Or Use cURL
```bash
# Get your auth token from browser localStorage or Supabase
curl http://localhost:8000/api/v1/debug/test-all \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📊 What Gets Tested

### 1. Environment Variables
Checks for:
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- `STRIPE_SECRET_KEY`, `STRIPE_PRICE_*` (all 6 price IDs)
- `SPAPI_LWA_CLIENT_ID`, `SPAPI_LWA_CLIENT_SECRET`, `SPAPI_REFRESH_TOKEN`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SP_API_ROLE_ARN`
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`
- `KEEPA_API_KEY`
- `OPENAI_API_KEY`
- `SECRET_KEY`

### 2. Database
- Connection test
- Table existence check:
  - `profiles`, `suppliers`, `analyses`, `subscriptions`
  - `feature_usage`, `amazon_connections`, `telegram_sessions`
  - `tracked_channels`, `keepa_cache`, `eligibility_cache`

### 3. Stripe
- API connection
- Price ID validation (all 6 prices)
- Checkout session creation test

### 4. Amazon SP-API
- Credentials check
- Client creation
- API call test

### 5. Telegram
- Credentials check
- Telethon library check

### 6. Keepa
- API key check
- Token status endpoint
- Product data fetch test

### 7. OpenAI
- API key check
- Chat completion test

## 🔍 Interpreting Results

### Status Colors (in frontend):
- 🟢 **Green (success)**: OK, CONNECTED, EXISTS, SET
- 🔴 **Red (error)**: MISSING, ERROR, FAILED
- 🟡 **Yellow (warning)**: NOT INSTALLED

### Common Issues:

#### "MISSING" env vars
- Check `.env` file exists
- Verify variable names match exactly
- No quotes around values
- No trailing spaces

#### "NOT INSTALLED" packages
```bash
pip install python-amazon-sp-api boto3 telethon httpx openai stripe supabase
```

#### "MISSING" database tables
- Run `database/CREATE_SCHEMA_FIXED.sql` in Supabase SQL Editor
- Or run `database/create_profile_trigger.sql` for profiles

#### "INVALID PRICE ID" (Stripe)
- Go to Stripe Dashboard → Products
- Click on each product → Copy the Price ID (starts with `price_`)
- Update `.env` with correct price IDs

#### "API ERROR" (Keepa/Amazon)
- Check API keys are valid
- Verify API quotas/limits
- Check network connectivity

## 📝 Next Steps After Running Tests

1. **Fix Missing Env Vars**: Add to `.env` file
2. **Install Missing Packages**: Run `pip install` commands
3. **Create Missing Tables**: Run SQL migrations
4. **Fix Invalid Credentials**: Update API keys
5. **Re-run Tests**: Verify all issues resolved

## 🎯 Priority Order

1. Environment variables (nothing works without these)
2. Database tables (run migration SQL)
3. Supabase connection (foundation)
4. Stripe (billing)
5. OpenAI (product extraction)
6. Amazon SP-API (eligibility)
7. Keepa (price charts)
8. Telegram (optional)

## 🔒 Security Note

The debug endpoint:
- Requires authentication (`get_current_user`)
- Masks sensitive values (shows first/last 4 chars only)
- Should be disabled in production or restricted to admin users

