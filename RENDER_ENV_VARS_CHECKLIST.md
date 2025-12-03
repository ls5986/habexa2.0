# Render Environment Variables Checklist

## ⚠️ IMPORTANT
Render Blueprints can't hardcode secrets in YAML (security). All API keys must be set manually in the Render Dashboard for each service.

## Required Environment Variables by Service

### 🔧 Backend (`habexa-backend`)
All keys already listed in `render.yaml` - set these in Render Dashboard:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY`
- `KEEPA_API_KEY` ⚠️ REQUIRED
- `SPAPI_LWA_CLIENT_ID` ⚠️ REQUIRED for SP-API
- `SPAPI_LWA_CLIENT_SECRET` ⚠️ REQUIRED for SP-API
- `SPAPI_REFRESH_TOKEN` ⚠️ REQUIRED for SP-API
- `AWS_ACCESS_KEY_ID` ⚠️ REQUIRED for SP-API
- `AWS_SECRET_ACCESS_KEY` ⚠️ REQUIRED for SP-API
- `SP_API_ROLE_ARN` ⚠️ REQUIRED for SP-API
- `OPENAI_API_KEY` (for Telegram extraction if used)

### 🔄 Analysis Worker (`habexa-celery-worker`)
**REQUIRED FOR ANALYSIS TO WORK:**
- `KEEPA_API_KEY` ⚠️ REQUIRED (used by batch_analyzer for catalog data)
- `SPAPI_LWA_CLIENT_ID` ⚠️ REQUIRED (used by batch_analyzer for pricing/fees)
- `SPAPI_LWA_CLIENT_SECRET` ⚠️ REQUIRED
- `SPAPI_REFRESH_TOKEN` ⚠️ REQUIRED
- `AWS_ACCESS_KEY_ID` ⚠️ REQUIRED (for SP-API request signing)
- `AWS_SECRET_ACCESS_KEY` ⚠️ REQUIRED
- `SP_API_ROLE_ARN` ⚠️ REQUIRED

**Also needed:**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY`
- `REDIS_URL` (auto-set from Redis service)

### 📱 Telegram Worker (`habexa-celery-telegram`)
**REQUIRED FOR TELEGRAM PROCESSING:**
- `OPENAI_API_KEY` ⚠️ REQUIRED (for message extraction)
- `TELEGRAM_API_ID` ⚠️ REQUIRED (for channel access)
- `TELEGRAM_API_HASH` ⚠️ REQUIRED

**Also needed:**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY`
- `REDIS_URL` (auto-set from Redis service)

### ⏰ Beat Worker (`habexa-celery-beat`)
**No API keys needed** - just schedules tasks. Needs:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY`
- `REDIS_URL` (auto-set from Redis service)

## How to Set Environment Variables in Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on the service (e.g., `habexa-celery-worker`)
3. Go to **Environment** tab
4. Click **+ Add Environment Variable**
5. Enter the key and value
6. Click **Save Changes**
7. Service will auto-redeploy

## Quick Copy-Paste Checklist

### For Analysis Worker:
```
KEEPA_API_KEY=<your-key>
SPAPI_LWA_CLIENT_ID=<your-id>
SPAPI_LWA_CLIENT_SECRET=<your-secret>
SPAPI_REFRESH_TOKEN=<your-token>
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
SP_API_ROLE_ARN=<your-arn>
```

### For Telegram Worker:
```
OPENAI_API_KEY=<your-key>
TELEGRAM_API_ID=<your-id>
TELEGRAM_API_HASH=<your-hash>
```

## Why Keys are Optional in Config

The API keys are marked as `Optional[str] = None` in `config.py` so workers can **start** without them. However, they will **fail when trying to use** the services that require them:

- Analysis will fail if `KEEPA_API_KEY` or SP-API credentials are missing
- Telegram processing will fail if `OPENAI_API_KEY` is missing

This allows workers to start and report clear errors rather than failing at startup with validation errors.

