#!/usr/bin/env python3
"""
Pre-flight check script to verify critical fixes before full audit.

Run this before the comprehensive workflow audit.
"""
import os
import sys
import requests
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
JWT_TOKEN = os.getenv("JWT_TOKEN", "")

print("=" * 60)
print("PRE-FLIGHT CHECK: CRITICAL FIXES VERIFICATION")
print("=" * 60)
print()

# 1. Database Migration Check
print("1. DATABASE MIGRATION CHECK")
print("-" * 60)
print("⚠️  MANUAL STEP REQUIRED:")
print("   Run this SQL in Supabase SQL Editor:")
print()
print("   SELECT column_name, data_type, column_default")
print("   FROM information_schema.columns")
print("   WHERE table_name = 'subscriptions'")
print("   AND column_name IN ('had_free_trial', 'trial_start', 'trial_end', 'cancel_at_period_end');")
print()
print("   Expected columns:")
print("   - had_free_trial (boolean)")
print("   - trial_start (timestamptz)")
print("   - trial_end (timestamptz)")
print("   - cancel_at_period_end (boolean)")
print()
migration_status = input("   Did you run the migration? (y/n): ").lower()
if migration_status != 'y':
    print("   ❌ Migration not run. Run database/ADD_TRIAL_TRACKING.sql first!")
    sys.exit(1)
print("   ✅ Migration check passed (manual verification required)")
print()

# 2. Super Admin Bypass Test
print("2. SUPER ADMIN BYPASS TEST")
print("-" * 60)
if not JWT_TOKEN:
    print("   ⚠️  JWT_TOKEN not set. Set it in environment:")
    print("      export JWT_TOKEN='your-jwt-token'")
    print("   Or pass it as argument: python preflight_check.py YOUR_TOKEN")
    if len(sys.argv) > 1:
        JWT_TOKEN = sys.argv[1]
    else:
        print("   ❌ Cannot test without JWT token")
        sys.exit(1)

try:
    response = requests.get(
        f"{BASE_URL}/api/v1/billing/user/limits",
        headers={
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Content-Type": "application/json"
        },
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"   ❌ API returned {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)
    
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)}")
    print()
    
    # Check critical fields
    is_super_admin = data.get("is_super_admin", False)
    unlimited = data.get("unlimited", False)
    tier = data.get("tier", "")
    
    if is_super_admin and unlimited and tier == "super_admin":
        print("   ✅ Super admin bypass working correctly!")
        print(f"      - is_super_admin: {is_super_admin}")
        print(f"      - unlimited: {unlimited}")
        print(f"      - tier: {tier}")
    else:
        print("   ❌ Super admin bypass NOT working!")
        print(f"      - is_super_admin: {is_super_admin} (expected: True)")
        print(f"      - unlimited: {unlimited} (expected: True)")
        print(f"      - tier: {tier} (expected: 'super_admin')")
        sys.exit(1)
    
    # Check limits structure
    limits = data.get("limits", {})
    apm = limits.get("analyses_per_month", {})
    if apm.get("unlimited") and apm.get("limit") == -1:
        print("   ✅ Analyses limit shows unlimited correctly")
    else:
        print("   ❌ Analyses limit not showing unlimited!")
        print(f"      - limit: {apm.get('limit')} (expected: -1)")
        print(f"      - unlimited: {apm.get('unlimited')} (expected: True)")
        sys.exit(1)
        
except requests.exceptions.ConnectionError:
    print(f"   ❌ Cannot connect to {BASE_URL}")
    print("   Make sure backend is running: uvicorn app.main:app --reload --port 8000")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()

# 3. Environment Variables Check
print("3. ENVIRONMENT VARIABLES CHECK")
print("-" * 60)
env_vars = {
    "SUPER_ADMIN_EMAILS": settings.SUPER_ADMIN_EMAILS,
    "STRIPE_SECRET_KEY": "✅ Set" if settings.STRIPE_SECRET_KEY else "❌ Missing",
    "STRIPE_WEBHOOK_SECRET": "✅ Set" if settings.STRIPE_WEBHOOK_SECRET else "❌ Missing",
    "EMAIL_PROVIDER": settings.EMAIL_PROVIDER or "⚠️  Optional (not set)",
    "EMAIL_API_KEY": "✅ Set" if settings.EMAIL_API_KEY else "⚠️  Optional (not set)",
}

all_critical = True
for key, value in env_vars.items():
    status = "✅" if "✅" in str(value) or (key == "SUPER_ADMIN_EMAILS" and value) else "❌"
    print(f"   {status} {key}: {value}")
    if key in ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"] and "❌" in str(value):
        all_critical = False

if not all_critical:
    print("   ❌ Critical environment variables missing!")
    sys.exit(1)

print("   ✅ All critical environment variables set")
print()

# 4. Code Verification
print("4. CODE VERIFICATION")
print("-" * 60)

# Check if email service exists
email_service_path = Path(__file__).parent.parent / "backend" / "app" / "services" / "email_service.py"
if email_service_path.exists():
    print("   ✅ Email service exists: backend/app/services/email_service.py")
else:
    print("   ❌ Email service missing!")
    sys.exit(1)

# Check if webhook handlers are integrated
stripe_service_path = Path(__file__).parent.parent / "backend" / "app" / "services" / "stripe_service.py"
if stripe_service_path.exists():
    content = stripe_service_path.read_text()
    if "EmailService" in content and "send_trial_ending_email" in content:
        print("   ✅ Email service integrated in webhook handlers")
    else:
        print("   ⚠️  Email service not fully integrated (check webhook handlers)")

print()

# 5. Summary
print("=" * 60)
print("PRE-FLIGHT CHECK SUMMARY")
print("=" * 60)
print()
print("✅ All automated checks passed!")
print()
print("⚠️  MANUAL CHECKS REQUIRED:")
print("   1. Database migration: Run ADD_TRIAL_TRACKING.sql in Supabase")
print("   2. Quick Analyze Modal: Open app and verify 'Unlimited ∞' shows")
print("   3. Stripe Webhooks: Verify all 7 events registered in Stripe Dashboard")
print()
print("Required Stripe Webhook Events:")
print("   - checkout.session.completed")
print("   - customer.subscription.created")
print("   - customer.subscription.updated")
print("   - customer.subscription.deleted")
print("   - customer.subscription.trial_will_end")
print("   - invoice.paid")
print("   - invoice.payment_failed")
print()
print("=" * 60)
print("READY FOR FULL AUDIT: YES (after manual checks)")
print("=" * 60)

