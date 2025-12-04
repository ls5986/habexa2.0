# API Keys Location & Format Guide

## ⚠️ Security Notice

**DO NOT** commit actual API keys to version control. This document shows you WHERE to find your keys, not the actual values.

---

## 🔍 Where to Find Your API Keys

### Option 1: Local `.env` File (Development)

Your API keys are stored in the `.env` file in the project root:

```bash
# Location
/Users/lindseystevens/habexa2.0/.env
```

**To view your keys:**
```bash
cat .env | grep -E "API_KEY|API_ID|API_SECRET|TOKEN"
```

**Or open in your editor:**
```bash
# Make sure .env is in .gitignore first!
code .env
```

---

### Option 2: Render.com Dashboard (Production)

1. Go to https://dashboard.render.com
2. Select your backend service (`habexa-backend`)
3. Go to **Environment** tab
4. All environment variables are listed there

**Or via CLI:**
```bash
# Install Render CLI first
render env ls --service habexa-backend
```

---

## 📝 API Key Formats (Examples Only)

### Keepa API Key

**Format:** Usually a long alphanumeric string

**Example Format:**
```
KEEPA_API_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

**Length:** Typically 40-60 characters

**Location:**
- Keepa Dashboard: https://keepa.com/#!api
- Click "Access Key" button

---

### Amazon SP-API Credentials

**Format:** Multiple fields required

**Example Format:**
```bash
# LWA (Login with Amazon) Credentials
SP_API_LWA_APP_ID=amzn1.application-oa2-client.1234567890abcdef
SP_API_LWA_CLIENT_SECRET=abcdef1234567890ABCDEF1234567890abcdef12
SP_API_REFRESH_TOKEN=Atzr|IwEBIJxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Legacy names (also supported)
SPAPI_LWA_CLIENT_ID=amzn1.application-oa2-client.1234567890abcdef
SPAPI_LWA_CLIENT_SECRET=abcdef1234567890ABCDEF1234567890abcdef12
SPAPI_REFRESH_TOKEN=Atzr|IwEBIJxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# AWS IAM (if using)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
SP_API_ROLE_ARN=arn:aws:iam::123456789012:role/SP-API-Role
```

**Where to Get:**
1. Amazon Seller Central → Apps & Services → Develop Apps
2. Create new app → Get LWA credentials
3. Self-authorize to get refresh token

---

### OpenAI API Key

**Format:** Starts with `sk-`

**Example Format:**
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Length:** Usually 50+ characters

**Location:**
- OpenAI Dashboard: https://platform.openai.com/api-keys
- Create new secret key

---

### Telegram API Credentials

**Format:** Numeric ID and hash

**Example Format:**
```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
```

**Where to Get:**
1. Go to https://my.telegram.org/apps
2. Create application
3. Get API ID and API Hash

---

### ASIN Data API Key (Optional)

**Format:** Alphanumeric string

**Example Format:**
```
ASIN_DATA_API_KEY=abc123def456ghi789
```

**Status:** ⚠️ Not used in production (we use SP-API + Keepa instead)

---

## 🔐 Viewing Your Actual Keys

### Method 1: Print Specific Key (Safe)

```bash
# View Keepa key (first 10 chars only for safety)
grep "KEEPA_API_KEY" .env | cut -d'=' -f2 | head -c 10
echo "..."

# View all API key variable names (without values)
grep -E "^[A-Z_]*API.*KEY|^[A-Z_]*API.*ID|^[A-Z_]*TOKEN" .env | cut -d'=' -f1
```

### Method 2: Use Environment Variable Display

```bash
# Load .env and show variable names only
source .env 2>/dev/null
echo "Variables set:"
echo "- KEEPA_API_KEY: ${KEEPA_API_KEY:0:10}..."
echo "- SP_API_LWA_APP_ID: ${SP_API_LWA_APP_ID:0:20}..."
```

### Method 3: Render Dashboard

1. Go to Render dashboard
2. Backend service → Environment tab
3. Click "Show Value" next to each key

---

## 📋 Checklist: Verify All Keys Are Set

Run this command to check which keys are configured:

```bash
cd /Users/lindseystevens/habexa2.0

echo "=== Checking API Keys ==="
echo ""
echo "Keepa:"
grep -q "KEEPA_API_KEY=" .env && echo "  ✅ Set" || echo "  ❌ Missing"

echo "SP-API LWA App ID:"
grep -q "SP_API_LWA_APP_ID=" .env && echo "  ✅ Set" || echo "  ❌ Missing"

echo "SP-API Refresh Token:"
grep -q "SP_API_REFRESH_TOKEN=" .env && echo "  ✅ Set" || echo "  ❌ Missing"

echo "OpenAI:"
grep -q "OPENAI_API_KEY=" .env && echo "  ✅ Set" || echo "  ❌ Missing"

echo "Telegram API ID:"
grep -q "TELEGRAM_API_ID=" .env && echo "  ✅ Set" || echo "  ❌ Missing"
```

---

## 🚨 Security Best Practices

1. **Never commit `.env` to git**
   - Check that `.env` is in `.gitignore`
   - Use `.env.example` for templates

2. **Rotate keys regularly**
   - Change keys every 90 days
   - Revoke unused keys

3. **Use different keys for dev/prod**
   - Development: `.env` file
   - Production: Render environment variables

4. **Don't share keys**
   - Never paste keys in chat/Slack
   - Use password managers for team sharing

5. **Monitor usage**
   - Check API usage dashboards
   - Set up alerts for unusual activity

---

## 🔄 Where Keys Are Used

### Keepa API Key
- **Service:** `backend/app/services/keepa_client.py`
- **Environment Variable:** `KEEPA_API_KEY`
- **Used For:** Product catalog, price history, BSR data

### SP-API Credentials
- **Service:** `backend/app/services/sp_api_client.py`
- **Environment Variables:** 
  - `SP_API_LWA_APP_ID`
  - `SP_API_LWA_CLIENT_SECRET`
  - `SP_API_REFRESH_TOKEN`
- **Used For:** Pricing, fees, catalog data

### OpenAI API Key
- **Service:** `backend/app/services/product_extractor.py`
- **Environment Variable:** `OPENAI_API_KEY`
- **Used For:** Telegram message extraction (not product analysis)

---

## 📝 Template for Your Keys

Create a `.env.local` file (git-ignored) with your actual keys:

```bash
# Copy the template
cp .env.example .env.local

# Edit with your actual keys
nano .env.local  # or use your preferred editor
```

---

## 🔍 Quick Reference: Key Locations

| API | Where to Get | Format Example | Required |
|-----|--------------|----------------|----------|
| **Keepa** | https://keepa.com/#!api | 40-60 char string | ✅ Yes |
| **SP-API LWA** | Amazon Seller Central | `amzn1.application-oa2-client.xxx` | ✅ Yes |
| **SP-API Refresh Token** | Self-authorize SP-API app | `Atzr\|...` | ✅ Yes |
| **OpenAI** | https://platform.openai.com/api-keys | `sk-...` | ❌ No (Telegram only) |
| **Telegram** | https://my.telegram.org/apps | Numeric ID + Hash | ❌ No (Telegram only) |

---

## ❓ Need Help Finding a Key?

1. **Check Render Dashboard:**
   - All production keys are there
   - Copy directly from Environment tab

2. **Check Your Email:**
   - API providers send keys via email when you sign up

3. **Regenerate if Lost:**
   - Most APIs allow key regeneration
   - Revoke old key, generate new one

4. **Check Service Logs:**
   - Backend logs show which keys are missing
   - Look for "⚠️ not configured" warnings

