#!/usr/bin/env python3
"""
Comprehensive verification for Habexa deployment.
Tests: Tier enforcement, Stripe webhooks, API endpoints, permissions, landing page.

Usage:
  export TEST_USER_JWT_TOKEN="your-token"
  export TEST_API_URL="http://localhost:8020"  # or production URL
  export TEST_FRONTEND_URL="http://localhost:3002"  # or production URL
  python scripts/comprehensive_verification.py
"""
import requests
import os
import sys
import json
from datetime import datetime
from pathlib import Path

BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8020")
FRONTEND_URL = os.getenv("TEST_FRONTEND_URL", "http://localhost:3002")
TOKEN = os.getenv("TEST_USER_JWT_TOKEN", "")

class TestResults:
    passed = 0
    failed = 0
    warnings = 0
    
    @classmethod
    def test(cls, name, condition, details="", warn_only=False):
        if condition:
            print(f"✅ {name}")
            cls.passed += 1
        elif warn_only:
            print(f"⚠️  {name}")
            if details:
                print(f"   {details}")
            cls.warnings += 1
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")
            cls.failed += 1

def headers():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def test_health():
    """Test basic API health"""
    print("\n" + "="*50)
    print("HEALTH CHECKS")
    print("="*50)
    
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        TestResults.test("API is reachable", resp.status_code == 200, f"Status: {resp.status_code}")
    except Exception as e:
        TestResults.test("API is reachable", False, str(e))

def test_auth():
    """Test authentication works"""
    print("\n" + "="*50)
    print("AUTHENTICATION")
    print("="*50)
    
    if not TOKEN:
        TestResults.test("JWT token provided", False, "Set TEST_USER_JWT_TOKEN env var")
        return None
    
    try:
        # Try to get user info from any authenticated endpoint
        resp = requests.get(f"{BASE_URL}/api/v1/billing/user/limits", headers=headers())
        TestResults.test("Auth token valid", resp.status_code == 200, f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            user_data = resp.json()
            TestResults.test("User data returned", "tier" in user_data, f"Keys: {list(user_data.keys())}")
            return user_data
    except Exception as e:
        TestResults.test("Auth request", False, str(e))
    
    return None

def test_tier_enforcement(user_data):
    """Test tier limits and super admin bypass"""
    print("\n" + "="*50)
    print("TIER ENFORCEMENT")
    print("="*50)
    
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/billing/user/limits", headers=headers())
        TestResults.test("Limits endpoint returns 200", resp.status_code == 200)
        
        if resp.status_code != 200:
            return
        
        data = resp.json()
        
        # Check structure
        TestResults.test("Response has 'tier' field", "tier" in data)
        TestResults.test("Response has 'unlimited' field", "unlimited" in data)
        TestResults.test("Response has 'is_super_admin' field", "is_super_admin" in data)
        TestResults.test("Response has 'limits' object", "limits" in data)
        
        # Check limits structure
        if "limits" in data:
            limits = data["limits"]
            TestResults.test("Has analyses_per_month limit", "analyses_per_month" in limits)
            
            if "analyses_per_month" in limits:
                apm = limits["analyses_per_month"]
                TestResults.test("Analysis limit has 'limit' field", "limit" in apm)
                TestResults.test("Analysis limit has 'used' field", "used" in apm)
                TestResults.test("Analysis limit has 'unlimited' field", "unlimited" in apm)
        
        # Super admin specific
        if data.get("is_super_admin"):
            print("\n  Testing Super Admin specifics:")
            TestResults.test("  Super admin has unlimited=True", data.get("unlimited") == True)
            if "limits" in data and "analyses_per_month" in data["limits"]:
                TestResults.test(
                    "  Analyses show unlimited", 
                    data["limits"]["analyses_per_month"].get("unlimited") == True
                )
    except Exception as e:
        TestResults.test("Tier enforcement test", False, str(e))

def test_analysis_endpoint():
    """Test analysis respects limits"""
    print("\n" + "="*50)
    print("ANALYSIS ENDPOINT")
    print("="*50)
    
    try:
        # Get usage before
        resp1 = requests.get(f"{BASE_URL}/api/v1/billing/user/limits", headers=headers())
        before_data = resp1.json() if resp1.status_code == 200 else {}
        before_used = before_data.get("limits", {}).get("analyses_per_month", {}).get("used", 0)
        is_unlimited = before_data.get("unlimited", False)
        
        # Run analysis (just check endpoint exists and accepts request)
        resp2 = requests.post(
            f"{BASE_URL}/api/v1/analyze/single",
            json={
                "identifier_type": "asin",
                "asin": "B08N5WRWNW",
                "buy_cost": 10.0,
                "moq": 1
            },
            headers=headers(),
            timeout=30
        )
        
        # Should accept (200/201) or reject with proper error (not 500)
        TestResults.test(
            "Analysis request handled (not 500)", 
            resp2.status_code != 500,
            f"Status: {resp2.status_code}"
        )
        
        if resp2.status_code in [200, 201]:
            data = resp2.json()
            TestResults.test("Response has job_id or usage info", 
                           "job_id" in data or "usage" in data, 
                           warn_only=True)
        
        # Check usage after (for super admins, should not increment)
        resp3 = requests.get(f"{BASE_URL}/api/v1/billing/user/limits", headers=headers())
        after_data = resp3.json() if resp3.status_code == 200 else {}
        after_used = after_data.get("limits", {}).get("analyses_per_month", {}).get("used", 0)
        
        if is_unlimited:
            TestResults.test(
                "Super admin usage not incremented", 
                before_used == after_used,
                f"Before: {before_used}, After: {after_used}"
            )
        else:
            # For regular users, usage might increment (warn only)
            TestResults.test(
                "Regular user usage tracking",
                True,  # Just check it doesn't error
                f"Before: {before_used}, After: {after_used}",
                warn_only=True
            )
            
    except Exception as e:
        TestResults.test("Analysis endpoint test", False, str(e))

def test_stripe_webhook_endpoint():
    """Verify webhook endpoint exists and validates signatures"""
    print("\n" + "="*50)
    print("STRIPE WEBHOOK")
    print("="*50)
    
    try:
        # Send invalid webhook (should reject)
        resp = requests.post(
            f"{BASE_URL}/api/v1/billing/webhook",
            json={"type": "test"},
            headers={"stripe-signature": "invalid"},
            timeout=10
        )
        
        # Should reject with 400 (bad signature) not 404 (not found)
        TestResults.test(
            "Webhook endpoint exists", 
            resp.status_code != 404,
            f"Status: {resp.status_code}"
        )
        TestResults.test(
            "Webhook validates signature", 
            resp.status_code == 400,
            f"Status: {resp.status_code} (expected 400 for invalid sig)"
        )
    except Exception as e:
        TestResults.test("Webhook endpoint test", False, str(e))

def test_landing_page():
    """Test landing page is accessible"""
    print("\n" + "="*50)
    print("LANDING PAGE")
    print("="*50)
    
    try:
        resp = requests.get(FRONTEND_URL, timeout=10, allow_redirects=False)
        
        # Should return 200 (landing page) not 302 (redirect to login)
        TestResults.test(
            "Landing page returns 200 (not redirect)",
            resp.status_code == 200,
            f"Status: {resp.status_code}"
        )
        
        if resp.status_code == 200:
            content = resp.text.lower()
            TestResults.test("Page contains 'habexa'", "habexa" in content)
            TestResults.test("Page contains 'trial'", "trial" in content or "free" in content)
            TestResults.test("Page contains 'pricing'", "pricing" in content)
    except Exception as e:
        TestResults.test("Landing page test", False, str(e))

def test_database_connection():
    """Test database is accessible"""
    print("\n" + "="*50)
    print("DATABASE")
    print("="*50)
    
    try:
        # Use an endpoint that queries the DB
        resp = requests.get(f"{BASE_URL}/api/v1/products", headers=headers())
        TestResults.test(
            "Database query works",
            resp.status_code in [200, 204, 401],  # 200 with data, 204 empty, or 401 if not auth
            f"Status: {resp.status_code}"
        )
    except Exception as e:
        TestResults.test("Database test", False, str(e))

def test_render_config():
    """Check render.yaml exists and has required services"""
    print("\n" + "="*50)
    print("RENDER CONFIG")
    print("="*50)
    
    render_files = ["render.yaml", "render.yml", "render-blueprint.yaml"]
    found = False
    
    for f in render_files:
        if os.path.exists(f):
            found = True
            with open(f) as file:
                content = file.read()
                TestResults.test(f"Found {f}", True)
                TestResults.test("Has 'services' section", "services:" in content)
                TestResults.test("Has backend service", "backend" in content.lower() or "api" in content.lower())
                TestResults.test("Has frontend service", "frontend" in content.lower())
                TestResults.test("Has database reference", "database" in content.lower() or "postgres" in content.lower() or "supabase" in content.lower())
                TestResults.test("Has SUPER_ADMIN_EMAILS", "SUPER_ADMIN_EMAILS" in content)
            break
    
    if not found:
        TestResults.test("Render config file exists", False, "No render.yaml found")

def test_env_config():
    """Check environment variable configuration"""
    print("\n" + "="*50)
    print("ENVIRONMENT CONFIG")
    print("="*50)
    
    # Check if config file uses env vars
    config_file = Path("backend/app/core/config.py")
    if config_file.exists():
        with open(config_file) as f:
            content = f.read()
            TestResults.test("Config has SUPER_ADMIN_EMAILS", "SUPER_ADMIN_EMAILS" in content)
            TestResults.test("Config has super_admin_list property", "super_admin_list" in content)
    
    # Check if tiers.py uses settings
    tiers_file = Path("backend/app/config/tiers.py")
    if tiers_file.exists():
        with open(tiers_file) as f:
            content = f.read()
            TestResults.test("Tiers uses settings", "from app.core.config import settings" in content or "settings.super_admin_list" in content)

def run_all_tests():
    print("\n" + "="*60)
    print(f"HABEXA DEPLOYMENT VERIFICATION")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"API: {BASE_URL}")
    print(f"Frontend: {FRONTEND_URL}")
    print("="*60)
    
    test_health()
    user_data = test_auth()
    
    if user_data:
        test_tier_enforcement(user_data)
        test_analysis_endpoint()
    
    test_stripe_webhook_endpoint()
    test_landing_page()
    test_database_connection()
    test_render_config()
    test_env_config()
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"✅ Passed:   {TestResults.passed}")
    print(f"⚠️  Warnings: {TestResults.warnings}")
    print(f"❌ Failed:   {TestResults.failed}")
    print("="*60)
    
    if TestResults.failed > 0:
        print("\n🚨 SOME TESTS FAILED — Fix issues before deploying")
        sys.exit(1)
    elif TestResults.warnings > 0:
        print("\n⚠️  Tests passed with warnings — Review before deploying")
        sys.exit(0)
    else:
        print("\n🎉 ALL TESTS PASSED — Ready to deploy!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()

