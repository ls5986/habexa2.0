# Amazon SP-API Integration Setup Guide

## ✅ What's Been Implemented

1. ✅ Database schema (`database/sp_api_schema.sql`)
2. ✅ Token encryption service (`backend/app/core/encryption.py`)
3. ✅ Amazon OAuth service (`backend/app/services/amazon_oauth.py`)
4. ✅ SP-API client (`backend/app/services/sp_api_client.py`)
5. ✅ API endpoints (`backend/app/api/v1/amazon.py`)
6. ✅ Frontend AmazonConnect component
7. ✅ EligibilityBadge component
8. ✅ useEligibility hook

## 📋 Setup Steps

### 1. Run Database Schema

Go to Supabase Dashboard → SQL Editor and run:
```sql
-- Copy and paste the contents of database/sp_api_schema.sql
```

This creates:
- `amazon_credentials` table (stores encrypted OAuth tokens)
- `eligibility_cache` table (caches eligibility checks for 24 hours)
- `fee_cache` table (caches fee estimates for 7 days)

### 2. Amazon Developer Setup

**Step 2.1: Register as SP-API Developer**
1. Go to https://sellercentral.amazon.com
2. Sign in with your Seller Account
3. Navigate to: **Apps & Services** → **Develop Apps**
4. Click **"Proceed to Developer Central"**
5. Complete Developer Profile
6. Accept the Marketplace Developer Agreement

**Step 2.2: Create SP-API Application**
1. In Developer Central → **Your Apps** → **Add new app client**
2. Fill out:
   - App name: Habexa
   - API Type: SP-API
   - Application Type: Private (for your own account only)
   - OAuth Login URI: `http://localhost:5173/auth/amazon/login`
   - OAuth Redirect URI: `http://localhost:5173/auth/amazon/callback`
3. Select Roles:
   - ✅ Product Listing
   - ✅ Pricing
   - ✅ Inventory and Order Management (optional)
4. Submit and wait for approval (1-2 days for Private apps)

**Step 2.3: Get Credentials**
After approval:
1. Go to your app in Developer Central
2. Click **"View"** next to LWA Credentials
3. Copy:
   - **Client ID**: `amzn1.application-oa2-client.xxxxxxxxxx`
   - **Client Secret**: (click to reveal)
4. Note your **App ID**: `amzn1.sp.solution.xxxxxxxx-xxxx-xxxx-xxxx`

### 3. AWS IAM Setup

**Step 3.1: Create IAM User**
1. Go to AWS Console → **IAM** → **Users** → **Create user**
2. User name: `habexa-sp-api`
3. Access type: ✅ Programmatic access
4. **SAVE THE CREDENTIALS**:
   - Access Key ID: `AKIAxxxxxxxxxxxx`
   - Secret Access Key: `xxxxxxxxxxxxxxxx`

**Step 3.2: Create IAM Role**
1. Go to **IAM** → **Roles** → **Create role**
2. Trusted entity: **AWS account** → **This account**
3. Name: `HabexaSPAPIRole`
4. Add **Inline Policy**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "execute-api:Invoke",
            "Resource": "arn:aws:execute-api:*:*:*"
        }
    ]
}
```
5. Copy the **Role ARN**: `arn:aws:iam::123456789012:role/HabexaSPAPIRole`

**Step 3.3: Update Trust Policy**
1. Go to the role → **Trust relationships** → **Edit trust policy**
2. Replace with (substitute YOUR_ACCOUNT_ID):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:user/habexa-sp-api"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

**Step 3.4: Link IAM ARN to Amazon App**
1. Go back to Amazon Developer Central → Your App
2. Find **IAM ARN** section
3. Enter your role ARN: `arn:aws:iam::123456789012:role/HabexaSPAPIRole`
4. Save

### 4. Update Environment Variables

Add to your `.env`:
```bash
# Amazon SP-API
SPAPI_APP_ID=amzn1.sp.solution.xxxxxxxx-xxxx-xxxx-xxxx
SPAPI_LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxxxxxxx
SPAPI_LWA_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SPAPI_REDIRECT_URI=http://localhost:5173/auth/amazon/callback

# AWS IAM
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
SP_API_ROLE_ARN=arn:aws:iam::123456789012:role/HabexaSPAPIRole

# Marketplace
MARKETPLACE_ID=ATVPDKIKX0DER
```

### 5. Install Backend Dependencies

```bash
cd backend
pip install python-amazon-sp-api boto3 cryptography
```

### 6. Test the Integration

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Go to Settings → Integrations
4. Click "Connect Amazon"
5. Authorize on Amazon
6. Verify redirect back with success
7. Check eligibility for an ASIN: `/api/v1/integrations/amazon/eligibility/B08N5WRWNW`

## 🎯 Features Available

### When Amazon is Connected:
- ✅ **Real Gating Checks** - Know exactly if YOU can list a product
- ✅ **Accurate FBA Fees** - Exact fees from Amazon, not estimates
- ✅ **Seller-Specific Data** - Data tailored to your account
- ✅ **Eligibility Caching** - Results cached for 24 hours
- ✅ **Fee Caching** - Fee estimates cached for 7 days

### API Endpoints:
- `GET /api/v1/integrations/amazon/connect` - Start OAuth flow
- `GET /api/v1/integrations/amazon/callback` - OAuth callback
- `GET /api/v1/integrations/amazon/status` - Connection status
- `DELETE /api/v1/integrations/amazon/disconnect` - Disconnect
- `GET /api/v1/integrations/amazon/eligibility/{asin}` - Check eligibility
- `POST /api/v1/integrations/amazon/eligibility/batch` - Batch check
- `GET /api/v1/integrations/amazon/fees/{asin}?price=29.99` - Get fees
- `GET /api/v1/integrations/amazon/product/{asin}` - Full product data

## ⚠️ Important Notes

1. **OAuth Redirect URI** must match EXACTLY in:
   - Amazon Developer Console
   - Your `.env` file
   - Frontend routes

2. **Token Encryption**: All OAuth tokens are encrypted using your `SECRET_KEY` before storage.

3. **Rate Limits**: SP-API has rate limits. The client includes caching to minimize API calls.

4. **Private Apps**: If you created a Private app, only YOUR seller account can use it.

5. **Production**: Update redirect URIs to your production domain before going live.

## 🚀 Next Steps

1. Complete Amazon Developer setup
2. Complete AWS IAM setup
3. Add credentials to `.env`
4. Run database schema
5. Test OAuth flow
6. Test eligibility checks
7. Integrate into deal analysis flow

The integration is complete and ready to use once you complete the Amazon Developer and AWS setup! 🎉

