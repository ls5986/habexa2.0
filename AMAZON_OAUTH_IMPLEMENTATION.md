# Per-User Amazon OAuth Implementation

## ✅ Implementation Complete

This implementation allows each user to connect their own Amazon Seller account and see their own eligibility status and fees.

## What Was Implemented

### 1. Database Schema ✅
- **File**: `database/amazon_connections_schema.sql`
- Created `amazon_connections` table with:
  - Per-user encrypted refresh tokens
  - Connection status tracking
  - Error tracking
  - RLS policies for security

**To apply**: Run the SQL in Supabase SQL Editor

### 2. Backend OAuth Service ✅
- **File**: `backend/app/services/amazon_oauth.py`
- Features:
  - `get_authorization_url(user_id)` - Generate OAuth URL
  - `exchange_code_for_token()` - Exchange auth code for refresh token
  - `get_user_connection()` - Get connection status
  - `get_user_refresh_token()` - Get decrypted token
  - `disconnect()` - Disconnect account
  - Token encryption using Fernet

### 3. Updated SP-API Client ✅
- **File**: `backend/app/services/sp_api_client.py`
- Changes:
  - Now accepts `user_id` parameter for all methods
  - `_get_credentials_for_user()` - Fetches per-user credentials
  - `check_eligibility(user_id, asin)` - Uses user's account
  - `get_fee_estimate(user_id, asin, price)` - Uses user's account
  - `get_competitive_pricing(user_id, asin)` - Uses user's account

### 4. Updated API Endpoints ✅
- **File**: `backend/app/api/v1/amazon.py`
- New OAuth endpoints:
  - `GET /api/v1/integrations/amazon/oauth/authorize` - Get auth URL
  - `GET /api/v1/integrations/amazon/oauth/callback` - Handle callback
  - `GET /api/v1/integrations/amazon/connection` - Check connection status
  - `DELETE /api/v1/integrations/amazon/disconnect` - Disconnect
- Updated SP-API endpoints:
  - All now require `require_amazon_connection` dependency
  - All use per-user credentials

### 5. Frontend Component ✅
- **File**: `frontend/src/components/features/settings/AmazonConnect.jsx`
- Features:
  - Connect/disconnect Amazon account
  - Display connection status
  - Handle OAuth callback
  - Show seller ID and connection date
  - Benefits section when not connected

### 6. Updated ASIN Analyzer ✅
- **File**: `backend/app/services/asin_analyzer.py`
- Changes:
  - Now passes `user_id` to SP-API client methods
  - Uses per-user credentials for eligibility checks
  - Uses per-user credentials for fee estimates

### 7. Settings Page Integration ✅
- **File**: `frontend/src/pages/Settings.jsx`
- Already includes `AmazonConnect` component in Integrations tab

## Setup Instructions

### 1. Database Setup
Run the SQL schema in Supabase:
```sql
-- Run: database/amazon_connections_schema.sql
```

### 2. Amazon Developer Console
Update your Amazon SP-API app redirect URI:
- Go to: Amazon Seller Central → Develop Apps → Your App → Edit
- Set OAuth Redirect URI to:
  - **Production**: `https://your-backend.com/api/v1/integrations/amazon/oauth/callback`
  - **Local Dev**: `http://localhost:8000/api/v1/integrations/amazon/oauth/callback`

### 3. Environment Variables
Ensure these are set in `.env`:
```env
SPAPI_APP_ID=amzn1.sp.solution.xxx
SPAPI_LWA_CLIENT_ID=amzn1.application-oa2-client.xxx
SPAPI_LWA_CLIENT_SECRET=amzn1.oa2-cs.v1.xxx
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Note: `SPAPI_REFRESH_TOKEN` is no longer needed for per-user OAuth (each user has their own).

### 4. Test the Flow

1. **User clicks "Connect Amazon"** in Settings → Integrations
2. **Redirected to Amazon** login page
3. **User authorizes** your app
4. **Amazon redirects back** with auth code
5. **Backend exchanges code** for refresh token
6. **Token encrypted and stored** in `amazon_connections`
7. **User sees "Connected"** status
8. **All eligibility/fee checks** now use their account

## Key Features

✅ **Per-User Isolation**: Each user connects their own account  
✅ **Secure Storage**: Tokens encrypted with Fernet  
✅ **Real Gating Checks**: Uses actual seller account for eligibility  
✅ **Accurate Fees**: Gets exact FBA fees from Amazon  
✅ **Error Handling**: Tracks connection errors  
✅ **Easy Disconnect**: Users can disconnect anytime  

## API Usage Examples

### Check Eligibility (requires connection)
```bash
GET /api/v1/integrations/amazon/eligibility/B08N5WRWNW
Authorization: Bearer <user_jwt>
```

### Get Fees (requires connection)
```bash
GET /api/v1/integrations/amazon/fees/B08N5WRWNW?price=29.99
Authorization: Bearer <user_jwt>
```

### Check Connection Status
```bash
GET /api/v1/integrations/amazon/connection
Authorization: Bearer <user_jwt>
```

## Notes

- The old global `SPAPI_REFRESH_TOKEN` is no longer used for per-user operations
- Each user must connect their own Amazon Seller account
- Eligibility checks are now user-specific (shows THEIR gating status)
- Fee estimates are now user-specific (shows fees for THEIR account)

## Testing Checklist

- [ ] Run database schema in Supabase
- [ ] Update Amazon app redirect URI
- [ ] Test OAuth flow (connect account)
- [ ] Test eligibility check with connected account
- [ ] Test fee estimate with connected account
- [ ] Test disconnect functionality
- [ ] Verify tokens are encrypted in database
- [ ] Test with multiple users (each sees their own status)

