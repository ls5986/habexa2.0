# Habexa Deployment Checklist

## Before Deploying

### Environment Variables (Set in Render Dashboard)

#### Backend Service (`habexa-backend`)
- [ ] `SUPABASE_URL` — Supabase project URL
- [ ] `SUPABASE_ANON_KEY` — Supabase anonymous key
- [ ] `SUPABASE_SERVICE_ROLE_KEY` — Supabase service role key
- [ ] `SECRET_KEY` — Application secret key for JWT/encryption
- [ ] `FRONTEND_URL` — Production frontend URL (auto-set from service)
- [ ] `BACKEND_URL` — Production backend URL (auto-set from service)
- [ ] `SUPER_ADMIN_EMAILS` — Comma-separated admin emails (e.g., `lindsey@letsclink.com,admin@habexa.com`)
- [ ] `STRIPE_SECRET_KEY` — Stripe secret key (sk_live_...)
- [ ] `STRIPE_WEBHOOK_SECRET` — Webhook signing secret (whsec_...)
- [ ] `STRIPE_PUBLISHABLE_KEY` — Public key (pk_live_...)
- [ ] `STRIPE_PRICE_STARTER_MONTHLY` — Stripe price ID
- [ ] `STRIPE_PRICE_STARTER_YEARLY` — Stripe price ID
- [ ] `STRIPE_PRICE_PRO_MONTHLY` — Stripe price ID
- [ ] `STRIPE_PRICE_PRO_YEARLY` — Stripe price ID
- [ ] `STRIPE_PRICE_AGENCY_MONTHLY` — Stripe price ID
- [ ] `STRIPE_PRICE_AGENCY_YEARLY` — Stripe price ID
- [ ] `KEEPA_API_KEY` — Keepa API key (optional, for analysis)
- [ ] `SP_API_LWA_APP_ID` — SP-API credentials (optional, for analysis)
- [ ] `SP_API_LWA_CLIENT_SECRET` — SP-API credentials (optional)
- [ ] `SPAPI_REFRESH_TOKEN` — SP-API refresh token (optional)
- [ ] `REDIS_URL` — Redis connection string (auto-set from service)

#### Frontend Service (`habexa-frontend`)
- [ ] `VITE_API_URL` — Backend API URL (auto-set from service)
- [ ] `VITE_SUPABASE_URL` — Supabase project URL
- [ ] `VITE_SUPABASE_ANON_KEY` — Supabase anonymous key

#### Celery Worker (`habexa-celery-worker`)
- [ ] `SUPABASE_URL` — Same as backend
- [ ] `SUPABASE_ANON_KEY` — Same as backend
- [ ] `SUPABASE_SERVICE_ROLE_KEY` — Same as backend
- [ ] `SECRET_KEY` — Same as backend
- [ ] `KEEPA_API_KEY` — **REQUIRED** for analysis
- [ ] `SP_API_LWA_APP_ID` — **REQUIRED** for analysis
- [ ] `SP_API_LWA_CLIENT_SECRET` — **REQUIRED** for analysis
- [ ] `SPAPI_REFRESH_TOKEN` — **REQUIRED** for analysis
- [ ] `REDIS_URL` — Auto-set from service

#### Celery Telegram Worker (`habexa-celery-telegram`)
- [ ] `SUPABASE_URL` — Same as backend
- [ ] `SUPABASE_ANON_KEY` — Same as backend
- [ ] `SUPABASE_SERVICE_ROLE_KEY` — Same as backend
- [ ] `SECRET_KEY` — Same as backend
- [ ] `OPENAI_API_KEY` — **REQUIRED** for message extraction
- [ ] `TELEGRAM_API_ID` — **REQUIRED** for channel access
- [ ] `TELEGRAM_API_HASH` — **REQUIRED** for channel access
- [ ] `REDIS_URL` — Auto-set from service

#### Celery Beat (`habexa-celery-beat`)
- [ ] `SUPABASE_URL` — Same as backend
- [ ] `SUPABASE_ANON_KEY` — Same as backend
- [ ] `SUPABASE_SERVICE_ROLE_KEY` — Same as backend
- [ ] `SECRET_KEY` — Same as backend
- [ ] `REDIS_URL` — Auto-set from service

### Stripe Dashboard

- [ ] Webhook endpoint registered: `https://habexa-backend.onrender.com/api/v1/billing/webhook`
- [ ] Events enabled:
  - [ ] `checkout.session.completed`
  - [ ] `invoice.paid`
  - [ ] `customer.subscription.created`
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
  - [ ] `invoice.payment_failed`
- [ ] Test webhook with Stripe CLI or dashboard
- [ ] Verify webhook secret matches `STRIPE_WEBHOOK_SECRET` in Render

### Database

- [ ] All migrations run (check Supabase dashboard)
- [ ] `subscriptions` table exists with correct schema
- [ ] `profiles` table exists
- [ ] RLS policies configured correctly
- [ ] Seed data loaded (if needed)

### Verification

- [ ] Run `python scripts/comprehensive_verification.py` locally
- [ ] Run against staging (if available)
- [ ] Manual test: Sign up → Trial → Checkout → Verify subscription
- [ ] Test super admin bypass (should see "Unlimited ∞")
- [ ] Test regular user limits (should see correct tier limits)

## After Deploying

### Immediate Checks

- [ ] Landing page loads at root URL (`/`)
- [ ] Login/signup works
- [ ] Quick Analyze modal shows correct limits
- [ ] Super admin sees "Unlimited ∞"
- [ ] Regular user sees correct tier limits
- [ ] Stripe checkout redirects work
- [ ] Webhook receives events (check Stripe dashboard logs)
- [ ] Celery workers are running (check Render logs)
- [ ] Analysis jobs complete successfully

### Monitoring

- [ ] Set up error alerting (Sentry, LogRocket, etc.)
- [ ] Monitor Celery queue for stuck tasks
- [ ] Check Stripe webhook delivery rate
- [ ] Monitor API response times
- [ ] Check database connection pool usage

### Post-Deployment Testing

1. **Super Admin Test**:
   - [ ] Login as super admin
   - [ ] Quick Analyze shows "Unlimited ∞"
   - [ ] Run analysis → succeeds
   - [ ] Usage does not increment

2. **Regular User Test**:
   - [ ] Create new account
   - [ ] Quick Analyze shows "0/5" (free tier)
   - [ ] Run 5 analyses → counter increments
   - [ ] 6th analysis → blocked with upgrade prompt

3. **Stripe Integration Test**:
   - [ ] Click "Upgrade" button
   - [ ] Redirects to Stripe checkout
   - [ ] Complete checkout
   - [ ] Webhook receives event
   - [ ] User tier updated in database
   - [ ] User sees new tier limits

4. **Landing Page Test**:
   - [ ] Visit root URL while logged out
   - [ ] See landing page (not redirect)
   - [ ] "Start Free Trial" button works
   - [ ] "View Pricing" scrolls to pricing section
   - [ ] Pricing cards show correct tiers

## Rollback Plan

If deployment fails:

1. **Revert Render Blueprint**: Use previous commit
2. **Check Logs**: Review Render service logs for errors
3. **Verify Env Vars**: Ensure all required vars are set
4. **Database Check**: Verify database is accessible
5. **Stripe Check**: Verify webhook endpoint is correct

## Notes

- Super admin emails are set via `SUPER_ADMIN_EMAILS` env var (comma-separated)
- Default super admin: `lindsey@letsclink.com` (if env var not set)
- Free tier limit: 5 analyses per month
- All tier limits are centralized in `backend/app/config/tiers.py`

