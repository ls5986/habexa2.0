# How to Get JWT Token for API Testing

## Quick Method (Browser Console)

1. **Open Production Site:**
   - Go to: https://habexa.onrender.com
   - Login with: lindsey@letsclink.com

2. **Open Browser Console:**
   - Press `F12` (or right-click → Inspect)
   - Go to "Console" tab

3. **Get Token:**
   ```javascript
   // Run this in console:
   localStorage.getItem('auth_token')
   ```

4. **Copy the Token:**
   - It will look like: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Copy the entire string

5. **Use in Test:**
   ```bash
   export HABEXA_TOKEN="paste_token_here"
   python tests/p1_performance_test.py
   ```

---

## Alternative: Get from Network Tab

1. **Open Browser DevTools** (F12)
2. **Go to Network tab**
3. **Make any API request** (e.g., navigate to Products page)
4. **Click on the request**
5. **Go to Headers tab**
6. **Find "Authorization" header**
7. **Copy the token** (after "Bearer ")

---

## Note About the Key You Shared

The JSON you shared is a **JWT Public Key** (JWK format):
- Used by Supabase to **verify** tokens
- Not used to **authenticate** requests
- We need the actual **access token** instead

The access token is what gets generated when you login and stored in `localStorage`.

---

## Test Token Validity

After getting the token, test it:

```bash
# Test if token works
curl https://habexa-backend-w5u5.onrender.com/api/v1/products/stats/asin-status \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

If you get data back (not 403), the token is valid!

