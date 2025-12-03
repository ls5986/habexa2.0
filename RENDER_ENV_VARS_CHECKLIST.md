# Render Environment Variables Checklist

## ⚠️ IMPORTANT
Render Blueprints can't hardcode secrets in YAML (security). All API keys must be set manually in the Render Dashboard for each service.

**Copy the values from your `.env` file** (see instructions below each section).

---

## Required Environment Variables by Service

### 🔧 Backend (`habexa-backend`)
All keys already listed in `render.yaml` - set these in Render Dashboard.

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
- `SECRET_KEY` ⚠️ REQUIRED
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
- `SECRET_KEY` ⚠️ REQUIRED
- `REDIS_URL` (auto-set from Redis service)

### ⏰ Beat Worker (`habexa-celery-beat`)
**Needs:**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY` ⚠️ REQUIRED
- `REDIS_URL` (auto-set from Redis service)

---

## How to Set Environment Variables in Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on the service (e.g., `habexa-celery-worker`)
3. Go to **Environment** tab
4. Click **+ Add Environment Variable**
5. Enter the key and value (copy from your `.env` file - see variable names below)
6. Click **Save Changes**
7. Service will auto-redeploy

---

## 📋 COPY-PASTE TEMPLATE

### Common Variables (ALL Workers + Backend)

Copy these from your `.env` file:

```
SUPABASE_URL=<from .env line 2>
SUPABASE_ANON_KEY=<from .env line 3>
SUPABASE_SERVICE_ROLE_KEY=<from .env line 4>
SECRET_KEY=<from .env line 41>
```

---

### 🔄 Analysis Worker (`habexa-celery-worker`)

**Required variables** - Copy from your `.env` file:

```
SUPABASE_URL=<from .env line 2>
SUPABASE_ANON_KEY=<from .env line 3>
SUPABASE_SERVICE_ROLE_KEY=<from .env line 4>
SECRET_KEY=<from .env line 41>
KEEPA_API_KEY=<from .env line 15>
SPAPI_LWA_CLIENT_ID=<from .env line 28>
SPAPI_LWA_CLIENT_SECRET=<from .env line 29>
SPAPI_REFRESH_TOKEN=<from .env line 30>
AWS_ACCESS_KEY_ID=<from .env line 35>
AWS_SECRET_ACCESS_KEY=<from .env line 36>
AWS_REGION=us-east-1
SP_API_ROLE_ARN=<from .env line 38>
MARKETPLACE_ID=ATVPDKIKX0DER
```

**Quick reference - Variable names from your .env:**
- Line 2: `SUPABASE_URL`
- Line 3: `SUPABASE_ANON_KEY`
- Line 4: `SUPABASE_SERVICE_ROLE_KEY`
- Line 15: `KEEPA_API_KEY`
- Line 28: `SPAPI_LWA_CLIENT_ID`
- Line 29: `SPAPI_LWA_CLIENT_SECRET`
- Line 30: `SPAPI_REFRESH_TOKEN`
- Line 35: `AWS_ACCESS_KEY_ID`
- Line 36: `AWS_SECRET_ACCESS_KEY`
- Line 38: `SP_API_ROLE_ARN`
- Line 41: `SECRET_KEY`

---

### 📱 Telegram Worker (`habexa-celery-telegram`)

**Required variables** - Copy from your `.env` file:

```
SUPABASE_URL=<from .env line 2>
SUPABASE_ANON_KEY=<from .env line 3>
SUPABASE_SERVICE_ROLE_KEY=<from .env line 4>
SECRET_KEY=<from .env line 41>
OPENAI_API_KEY=<from .env line 12>
TELEGRAM_API_ID=<from .env line 18>
TELEGRAM_API_HASH=<from .env line 19>
```

**Quick reference - Variable names from your .env:**
- Line 2: `SUPABASE_URL`
- Line 3: `SUPABASE_ANON_KEY`
- Line 4: `SUPABASE_SERVICE_ROLE_KEY`
- Line 12: `OPENAI_API_KEY`
- Line 18: `TELEGRAM_API_ID`
- Line 19: `TELEGRAM_API_HASH`
- Line 41: `SECRET_KEY`

---

### ⏰ Beat Worker (`habexa-celery-beat`)

**Required variables** - Copy from your `.env` file:

```
SUPABASE_URL=<from .env line 2>
SUPABASE_ANON_KEY=<from .env line 3>
SUPABASE_SERVICE_ROLE_KEY=<from .env line 4>
SECRET_KEY=<from .env line 41>
```

**Quick reference - Variable names from your .env:**
- Line 2: `SUPABASE_URL`
- Line 3: `SUPABASE_ANON_KEY`
- Line 4: `SUPABASE_SERVICE_ROLE_KEY`
- Line 41: `SECRET_KEY`

---

### 🔧 Backend (`habexa-backend`)

**Core Required:**
```
SUPABASE_URL=<from .env line 2>
SUPABASE_ANON_KEY=<from .env line 3>
SUPABASE_SERVICE_ROLE_KEY=<from .env line 4>
SECRET_KEY=<from .env line 41>
```

**SP-API (if backend uses it directly):**
```
SPAPI_LWA_CLIENT_ID=<from .env line 28>
SPAPI_LWA_CLIENT_SECRET=<from .env line 29>
SPAPI_REFRESH_TOKEN=<from .env line 30>
AWS_ACCESS_KEY_ID=<from .env line 35>
AWS_SECRET_ACCESS_KEY=<from .env line 36>
AWS_REGION=us-east-1
SP_API_ROLE_ARN=<from .env line 38>
MARKETPLACE_ID=ATVPDKIKX0DER
```

**Keepa (if backend uses it directly):**
```
KEEPA_API_KEY=<from .env line 15>
```

**OpenAI (if backend uses it directly):**
```
OPENAI_API_KEY=<from .env line 12>
```

**Stripe (if using billing):**
```
STRIPE_SECRET_KEY=<from .env line 47>
STRIPE_PUBLISHABLE_KEY=<from .env line 46>
STRIPE_WEBHOOK_SECRET=<from .env line 48>
STRIPE_PRICE_STARTER_MONTHLY=<from .env line 50>
STRIPE_PRICE_STARTER_YEARLY=<from .env line 51>
STRIPE_PRICE_PRO_MONTHLY=<from .env line 52>
STRIPE_PRICE_PRO_YEARLY=<from .env line 53>
STRIPE_PRICE_AGENCY_MONTHLY=<from .env line 54>
STRIPE_PRICE_AGENCY_YEARLY=<from .env line 55>
```

---

## Why Keys are Optional in Config

The API keys are marked as `Optional[str] = None` in `config.py` so workers can **start** without them. However, they will **fail when trying to use** the services that require them:

- Analysis will fail if `KEEPA_API_KEY` or SP-API credentials are missing
- Telegram processing will fail if `OPENAI_API_KEY` is missing

**EXCEPTION:** `SECRET_KEY` is **REQUIRED** and cannot be optional - it's needed for JWT token signing and encryption.

---

## 🚨 Current Error Fix

If you're seeing:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
SECRET_KEY
  Field required
```

**Fix:** Add `SECRET_KEY` to the worker's environment variables in Render Dashboard. Copy the value from line 41 of your `.env` file.
