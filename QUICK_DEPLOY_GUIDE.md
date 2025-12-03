# ⚡ QUICK DEPLOY GUIDE

**For when you're ready to deploy RIGHT NOW**

---

## 🚀 3-Step Deploy

### 1. Run Migrations (2 minutes)

```sql
-- In Supabase SQL Editor, paste:
-- (Copy entire contents of database/RUN_BEFORE_DEPLOY.sql)
```

### 2. Verify Environment Variables (1 minute)

Check Render Dashboard → Backend → Environment:
- ✅ `SUPER_ADMIN_EMAILS`
- ✅ `STRIPE_SECRET_KEY`
- ✅ `STRIPE_WEBHOOK_SECRET`
- ✅ All other vars from `.env`

### 3. Deploy (auto)

```bash
git add -A
git commit -m "Production ready"
git push origin main
```

**Render auto-deploys from `main` branch**

---

## ✅ Post-Deploy (2 minutes)

1. **Frontend**: Visit `https://your-frontend.onrender.com/`
2. **Backend**: Check `https://your-backend.onrender.com/health`
3. **Login**: Test with super admin account
4. **Quick Analyze**: Should show "Unlimited ∞"

**Done!** 🎉

---

## 📋 Full Checklist

See `DEPLOYMENT_CHECKLIST_FINAL.md` for complete details.

