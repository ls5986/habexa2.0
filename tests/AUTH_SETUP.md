# Authentication Setup for Tests

The Habexa backend uses Supabase client-side authentication. To run the production tests, you need to provide authentication credentials.

## Option 1: Supabase Credentials (Recommended)

Add these to your `.env.test` file:

```env
SUPABASE_URL=https://habexa.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

**How to get these:**

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to Settings → API
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon/public key** → `SUPABASE_ANON_KEY`

Or get them from your backend `.env` file.

## Option 2: Direct Token (Alternative)

If you can't access Supabase credentials, get a token from the browser:

1. Log in to https://habexa.onrender.com
2. Open browser console (F12)
3. Run this command:
   ```javascript
   JSON.parse(localStorage.getItem('sb-habexa-auth-token') || '{}').access_token
   ```
4. Copy the token
5. Add to `.env.test`:
   ```env
   TEST_TOKEN=your_token_here
   ```

**Note:** Tokens expire after 1 hour, so you'll need to refresh them periodically.

## Quick Setup

1. **Get Supabase credentials** (easiest):
   - Check your backend `.env` file
   - Or get from Supabase dashboard
   - Add to `.env.test`

2. **Or get a browser token**:
   - Log in to frontend
   - Get token from localStorage
   - Add to `.env.test`

3. **Run tests**:
   ```bash
   python tests/production_test.py
   ```

## Troubleshooting

### "Authentication failed"
- Check `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct
- Or check `TEST_TOKEN` is valid (not expired)

### "Token expired"
- Get a new token from browser localStorage
- Or use Supabase credentials instead

### "Cannot find Supabase project"
- Verify the `SUPABASE_URL` is correct
- Check you have access to the Supabase project

