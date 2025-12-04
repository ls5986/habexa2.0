# View Your API Keys (Local Only)

**⚠️ SECURITY WARNING:** This file is in `.gitignore`. Never commit your actual API keys to git.

---

## Quick Command to View All Keys

Run this command to see all your API keys (from your local `.env` file):

```bash
cd /Users/lindseystevens/habexa2.0
cat .env | grep -E "API_KEY|API_ID|API_SECRET|TOKEN|AWS_" | grep -v "^#"
```

---

## View Keys by Service

### Keepa API Key
```bash
grep "KEEPA_API_KEY" .env
```

### SP-API Credentials
```bash
grep -E "SP_API|SPAPI" .env | grep -v "^#"
```

### OpenAI API Key
```bash
grep "OPENAI_API_KEY" .env
```

### Telegram Credentials
```bash
grep "TELEGRAM" .env
```

### AWS Credentials
```bash
grep "AWS_" .env
```

---

## Copy Keys to Clipboard (macOS)

### Keepa Key
```bash
grep "KEEPA_API_KEY" .env | cut -d'=' -f2 | pbcopy
echo "Keepa API key copied to clipboard"
```

### SP-API Refresh Token
```bash
grep "SP_API_REFRESH_TOKEN\|SPAPI_REFRESH_TOKEN" .env | cut -d'=' -f2 | pbcopy
echo "SP-API refresh token copied to clipboard"
```

---

## Create Local Reference File (Git-Ignored)

Create a local file with your keys (this won't be committed):

```bash
# Create a git-ignored file for your reference
cat > .env.local-reference << 'EOF'
# My API Keys - LOCAL REFERENCE ONLY
# This file is git-ignored and never committed

EOF

# Append your actual keys (only on your local machine)
cat .env | grep -E "API_KEY|API_ID|API_SECRET|TOKEN|AWS_" >> .env.local-reference

echo "Created .env.local-reference with your keys"
echo "⚠️ This file is git-ignored - safe for local reference"
```

---

## View from Render Dashboard (Production)

1. Go to: https://dashboard.render.com
2. Click your backend service: `habexa-backend`
3. Go to **Environment** tab
4. Click "Show Value" next to each key

---

## Format Reference

Your keys should be in these formats:

| Variable | Format | Example |
|----------|--------|---------|
| `KEEPA_API_KEY` | 40-60 char string | `abc123...xyz789` |
| `SP_API_LWA_APP_ID` | Starts with `amzn1.` | `amzn1.application-oa2-client.xxx` |
| `SP_API_REFRESH_TOKEN` | Starts with `Atzr\|` | `Atzr\|IwEBIJ...` |
| `OPENAI_API_KEY` | Starts with `sk-` | `sk-proj-...` |
| `TELEGRAM_API_ID` | Numeric | `12345678` |
| `TELEGRAM_API_HASH` | 32 char hex | `abcdef1234...` |
| `AWS_ACCESS_KEY_ID` | Starts with `AKIA` | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | Long string | `wJalrXUtnFEMI...` |

---

## Verify Keys Are Set

Run this to check which keys are configured:

```bash
#!/bin/bash
cd /Users/lindseystevens/habexa2.0

echo "=== API Keys Status ==="
echo ""

KEYS=(
  "KEEPA_API_KEY:Keepa"
  "SP_API_LWA_APP_ID:SP-API LWA App ID"
  "SP_API_REFRESH_TOKEN:SP-API Refresh Token"
  "OPENAI_API_KEY:OpenAI"
  "TELEGRAM_API_ID:Telegram API ID"
  "TELEGRAM_API_HASH:Telegram API Hash"
  "AWS_ACCESS_KEY_ID:AWS Access Key"
)

for key_info in "${KEYS[@]}"; do
  IFS=':' read -r key name <<< "$key_info"
  if grep -q "^${key}=" .env 2>/dev/null; then
    value=$(grep "^${key}=" .env | cut -d'=' -f2)
    len=${#value}
    if [ $len -gt 0 ]; then
      preview="${value:0:10}..."
      echo "✅ $name: Set (${len} chars) - $preview"
    else
      echo "❌ $name: Empty"
    fi
  else
    echo "❌ $name: Not found"
  fi
done
```

Save this as `check-keys.sh` and run:
```bash
chmod +x check-keys.sh
./check-keys.sh
```

