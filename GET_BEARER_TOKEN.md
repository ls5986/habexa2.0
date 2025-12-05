# How to Get a Bearer Token for Your Render API

Your backend uses **Supabase** for authentication. The bearer token is a JWT (JSON Web Token) obtained from Supabase.

---

## Method 1: Python Script (Easiest)

I've created a script that will get your token:

```bash
# Install supabase-py if needed
pip install supabase python-dotenv

# Run the script
python3 get_bearer_token.py
```

Or with email as argument:
```bash
python3 get_bearer_token.py lindsey@letsclink.com
```

The script will:
1. Prompt for your password
2. Authenticate with Supabase
3. Get the JWT token
4. Save it to `.bearer_token.txt` for easy use

---

## Method 2: Browser DevTools (Quick)

1. **Open your app in browser:** `https://habexa-frontend.onrender.com`
2. **Login** with your credentials
3. **Open DevTools** (F12 or Cmd+Option+I)
4. **Go to Application tab** (Chrome) or **Storage tab** (Firefox)
5. **Find Local Storage** → `https://habexa-frontend.onrender.com`
6. **Look for key:** `sb-<project-id>-auth-token` or `supabase.auth.token`
7. **Copy the `access_token` value** from the JSON

The token looks like:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzM...
```

---

## Method 3: Supabase API Direct (Advanced)

```bash
# Get token via Supabase REST API
curl -X POST "https://fpihznamnwlvkaarnlbc.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: YOUR_SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "lindsey@letsclink.com",
    "password": "your_password"
  }'
```

Response will contain `access_token` in the JSON.

---

## Using the Token

Once you have the token, use it in curl:

```bash
# Set token as variable
export BEARER_TOKEN="your_token_here"

# Or load from file (if using the script)
export BEARER_TOKEN=$(cat .bearer_token.txt)

# Test the token
curl -X GET "https://habexa-backend-w5u5.onrender.com/api/v1/auth/me" \
  -H "Authorization: Bearer $BEARER_TOKEN"

# Test UPC to ASIN conversion
curl -X POST "https://habexa-backend-w5u5.onrender.com/api/v1/analyze/single" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d '{
    "identifier_type": "upc",
    "upc": "860124000177",
    "buy_cost": 10.00,
    "moq": 1
  }'
```

---

## Token Expiration

**Note:** JWT tokens expire after a period (usually 1 hour). If you get a `401 Unauthorized` error:
1. Re-run the script to get a fresh token
2. Or refresh your browser session and get a new token from DevTools

---

## Quick Test

After getting your token, test it:

```bash
# Test authentication
curl -X GET "https://habexa-backend-w5u5.onrender.com/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Expected response:
```json
{
  "id": "user-uuid",
  "email": "lindsey@letsclink.com",
  "user_metadata": {}
}
```

