# Feature Gating & Limit Enforcement - Setup Guide

## ✅ What's Been Implemented

1. ✅ Database schema with limit checking functions
2. ✅ Backend FeatureGate service
3. ✅ API endpoints with limit enforcement
4. ✅ Frontend hooks and components
5. ✅ Usage tracking and display

## 📋 Setup Steps

### 1. Run Database Schema

Go to Supabase Dashboard → SQL Editor and run:
```sql
-- Copy and paste the contents of database/feature_gating_schema.sql
```

This creates:
- Usage tracking columns on subscriptions table
- `get_tier_limits()` function
- `check_user_limit()` function
- `increment_usage()` function
- `decrement_usage()` function
- `monitored_channels` table

### 2. Backend is Ready

The backend endpoints now enforce limits:
- ✅ `/api/v1/analysis/single` - checks analyses_per_month
- ✅ `/api/v1/analysis/batch` - requires bulk_analyze feature
- ✅ `/api/v1/suppliers` - checks suppliers limit
- ✅ `/api/v1/integrations/telegram/channels` - checks telegram_channels limit
- ✅ `/api/v1/billing/limits` - get all limits
- ✅ `/api/v1/billing/limits/{feature}` - check specific feature

### 3. Frontend Components

All frontend components are ready:
- ✅ `useFeatureGate` hook
- ✅ `UpgradePrompt` component
- ✅ `UsageDisplay` component
- ✅ `UsageWidget` for dashboard
- ✅ Updated Suppliers page with limits
- ✅ Updated Quick Analyze modal with usage display

## 🎯 Features Enforced

### Free Tier
- 1 Telegram channel
- 10 analyses/month
- 3 suppliers
- No alerts
- No bulk analyze
- No API access

### Starter ($29/mo)
- 3 Telegram channels
- 100 analyses/month
- 10 suppliers
- ✅ Alerts
- ✅ Export data
- No bulk analyze

### Pro ($79/mo)
- 10 Telegram channels
- 500 analyses/month
- 50 suppliers
- ✅ Alerts
- ✅ Bulk analyze
- ✅ Export data
- ✅ Priority support

### Agency ($199/mo)
- Unlimited channels
- Unlimited analyses
- Unlimited suppliers
- ✅ All features
- ✅ API access

## 🧪 Testing

### Test Free User Limits
1. Create a free account
2. Try to add 4th supplier → Should see upgrade prompt
3. Try to run 11th analysis → Should be blocked
4. Try bulk analyze → Should be blocked (Pro+ only)

### Test Upgrade Flow
1. Hit a limit
2. See upgrade prompt
3. Click "View Plans"
4. Complete checkout
5. Limits should increase immediately

## 📝 API Examples

### Check Limit
```bash
GET /api/v1/billing/limits/analyses_per_month
Authorization: Bearer YOUR_TOKEN

Response:
{
  "allowed": true,
  "tier": "free",
  "feature": "analyses_per_month",
  "limit": 10,
  "used": 3,
  "remaining": 7,
  "unlimited": false
}
```

### Get All Limits
```bash
GET /api/v1/billing/limits
Authorization: Bearer YOUR_TOKEN

Response:
{
  "tier": "free",
  "usage": {
    "analyses_per_month": {...},
    "telegram_channels": {...},
    "suppliers": {...}
  }
}
```

## 🚀 Next Steps

1. Run the database schema
2. Test with a free account
3. Verify limits are enforced
4. Test upgrade flow
5. Monitor usage tracking

Everything is ready to go! 🎉

