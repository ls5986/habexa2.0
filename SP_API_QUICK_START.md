# SP-API Quick Start Checklist

## ✅ Implementation Complete!

All code is ready. You just need to complete the Amazon Developer and AWS setup.

## 📋 Setup Checklist

### 1. Database ✅
- [x] Schema created: `database/sp_api_schema.sql`
- [ ] **Run in Supabase SQL Editor**

### 2. Amazon Developer Setup
- [ ] Register at https://sellercentral.amazon.com
- [ ] Create SP-API app in Developer Central
- [ ] Get App ID, Client ID, Client Secret
- [ ] Set redirect URI: `http://localhost:5173/auth/amazon/callback`

### 3. AWS IAM Setup
- [ ] Create IAM user: `habexa-sp-api`
- [ ] Save Access Key ID and Secret
- [ ] Create IAM role: `HabexaSPAPIRole`
- [ ] Add inline policy for `execute-api:Invoke`
- [ ] Update trust policy to allow user to assume role
- [ ] Link Role ARN to Amazon app

### 4. Environment Variables
- [ ] Add to `.env`:
  - `SPAPI_APP_ID`
  - `SPAPI_LWA_CLIENT_ID`
  - `SPAPI_LWA_CLIENT_SECRET`
  - `SPAPI_REDIRECT_URI`
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `SP_API_ROLE_ARN`

### 5. Install Dependencies
```bash
cd backend
pip install python-amazon-sp-api boto3 cryptography
```

### 6. Test
1. Go to Settings → Integrations
2. Click "Connect Amazon"
3. Authorize on Amazon
4. Check eligibility: `/api/v1/integrations/amazon/eligibility/B08N5WRWNW`

## 🎯 What Works Now

- ✅ OAuth flow (connect/disconnect Amazon)
- ✅ Real eligibility checks (when connected)
- ✅ Accurate FBA fees (when connected)
- ✅ Automatic fee/eligibility caching
- ✅ Analysis uses SP-API data when available
- ✅ Falls back to estimates when not connected

## 📝 Notes

- **Private Apps**: Only work for YOUR seller account
- **Redirect URI**: Must match exactly in all places
- **Token Encryption**: All tokens encrypted before storage
- **Caching**: Eligibility cached 24h, fees cached 7 days

Ready to test once you complete the Amazon Developer setup! 🚀

