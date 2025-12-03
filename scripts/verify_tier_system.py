#!/usr/bin/env python3
"""
Automated verification script for tier enforcement system.
Run with: python scripts/verify_tier_system.py

Before running:
1. Set SUPER_ADMIN_TOKEN to your JWT token (get from browser devtools)
2. Ensure backend is running on BASE_URL
3. Update BASE_URL if different from default
"""
import requests
import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

BASE_URL = os.getenv("VITE_API_URL", "http://localhost:8020")
API_PREFIX = f"{BASE_URL}/api/v1"

# Get token from environment or prompt
SUPER_ADMIN_TOKEN = os.getenv("TEST_USER_JWT_TOKEN")  # Set this in .env or pass as env var

if not SUPER_ADMIN_TOKEN:
    print("⚠️  TEST_USER_JWT_TOKEN not set. Please set it in .env or as environment variable.")
    print("   Get your JWT token from browser devtools: localStorage.getItem('auth_token')")
    sys.exit(1)

TESTS_PASSED = 0
TESTS_FAILED = 0

def test(name, condition, details=""):
    global TESTS_PASSED, TESTS_FAILED
    if condition:
        print(f"✅ PASS: {name}")
        TESTS_PASSED += 1
    else:
        print(f"❌ FAIL: {name}")
        if details:
            print(f"   Details: {details}")
        TESTS_FAILED += 1

def get_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def run_tests():
    print("\n" + "="*60)
    print("TIER ENFORCEMENT VERIFICATION")
    print("="*60 + "\n")
    
    headers = get_headers(SUPER_ADMIN_TOKEN)
    
    # Test 1: Super admin limits endpoint
    print("--- Testing Super Admin Limits Endpoint ---")
    try:
        resp = requests.get(f"{API_PREFIX}/billing/user/limits", headers=headers, timeout=10)
        test("Super admin endpoint returns 200", resp.status_code == 200, 
             f"Got status: {resp.status_code}, Response: {resp.text[:200]}")
        
        if resp.status_code == 200:
            data = resp.json()
            test("Super admin is_super_admin=True", 
                 data.get("is_super_admin") == True, 
                 f"Got: {data.get('is_super_admin')}")
            test("Super admin unlimited=True", 
                 data.get("unlimited") == True, 
                 f"Got: {data.get('unlimited')}")
            test("Super admin analyses unlimited", 
                 data.get("limits", {}).get("analyses_per_month", {}).get("unlimited") == True,
                 f"Got: {data.get('limits', {}).get('analyses_per_month', {})}")
            
            # Check tier display
            tier_display = data.get("tier_display", "")
            test("Super admin tier_display contains 'Super Admin' or 'Unlimited'",
                 "super admin" in tier_display.lower() or "unlimited" in tier_display.lower(),
                 f"Got: {tier_display}")
    except Exception as e:
        test("Super admin limits endpoint", False, str(e))
    
    # Test 2: Check limit endpoint for super admin
    print("\n--- Testing Check Limit Endpoint (Super Admin) ---")
    try:
        resp = requests.get(f"{API_PREFIX}/billing/limits/analyses_per_month", headers=headers, timeout=10)
        test("Check limit endpoint returns 200", resp.status_code == 200)
        
        if resp.status_code == 200:
            data = resp.json()
            test("Check limit shows unlimited=True", 
                 data.get("unlimited") == True,
                 f"Got: {data}")
            test("Check limit shows is_super_admin=True",
                 data.get("is_super_admin") == True,
                 f"Got: {data}")
    except Exception as e:
        test("Check limit endpoint", False, str(e))
    
    # Test 3: Analysis endpoint returns correct usage info
    print("\n--- Testing Analysis Endpoint Response Format ---")
    try:
        # Just check the endpoint structure, don't actually run analysis
        # (would require valid ASIN and cost)
        resp = requests.post(
            f"{API_PREFIX}/analyze/single",
            json={
                "identifier_type": "asin",
                "asin": "B08N5WRWNW",  # Test ASIN
                "buy_cost": 10.0,
                "moq": 1
            },
            headers=headers,
            timeout=10
        )
        
        # Should either succeed (200/201) or fail with proper error (not 500)
        test("Analysis endpoint responds (not 500)", 
             resp.status_code != 500,
             f"Got status: {resp.status_code}")
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            test("Response includes usage object", 
                 "usage" in data,
                 f"Keys: {list(data.keys())}")
            if "usage" in data:
                usage = data["usage"]
                test("Usage shows unlimited=True for super admin", 
                     usage.get("unlimited") == True,
                     f"Got: {usage}")
    except Exception as e:
        test("Analysis endpoint test", False, str(e))
    
    # Test 4: Verify frontend would get correct data
    print("\n--- Testing Frontend Data Format ---")
    try:
        resp = requests.get(f"{API_PREFIX}/billing/user/limits", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            
            # Check structure matches what frontend expects
            test("Response has 'limits' object", "limits" in data)
            test("Response has 'tier' field", "tier" in data)
            test("Response has 'is_super_admin' field", "is_super_admin" in data)
            test("Response has 'unlimited' field", "unlimited" in data)
            
            if "limits" in data:
                analyses = data["limits"].get("analyses_per_month", {})
                test("Analyses limit has 'limit' field", "limit" in analyses)
                test("Analyses limit has 'used' field", "used" in analyses)
                test("Analyses limit has 'remaining' field", "remaining" in analyses)
                test("Analyses limit has 'unlimited' field", "unlimited" in analyses)
    except Exception as e:
        test("Frontend data format test", False, str(e))
    
    # Summary
    print("\n" + "="*60)
    print(f"RESULTS: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("="*60)
    
    if TESTS_FAILED > 0:
        print("\n⚠️  SOME TESTS FAILED — Continue fixing until all pass")
        print("\nCommon issues:")
        print("  1. Super admin email not in SUPER_ADMIN_EMAILS list")
        print("  2. User object not being passed to check_limit()")
        print("  3. Frontend not calling /billing/user/limits endpoint")
        sys.exit(1)
    else:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNext steps:")
        print("  1. Test manually in browser (Quick Analyze modal)")
        print("  2. Verify super admin sees 'Unlimited ∞'")
        print("  3. Test regular user sees correct limits")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()

