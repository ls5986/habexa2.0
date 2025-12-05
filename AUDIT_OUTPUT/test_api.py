#!/usr/bin/env python3
"""
API Test Script for Habexa Backend
Run this after getting a fresh auth token from the browser.
"""
import urllib.request
import urllib.error
import json
import ssl
from datetime import datetime

BASE_URL = "https://habexa-backend-w5u5.onrender.com"

# GET A FRESH TOKEN:
# 1. Go to https://habexa-frontend.onrender.com
# 2. Login
# 3. Open DevTools > Network
# 4. Copy Authorization header from any API call
TOKEN = "PASTE_YOUR_TOKEN_HERE"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

ENDPOINTS = [
    # Health
    ("GET", "/health", 200),
    
    # Auth
    ("GET", "/api/v1/auth/me", 200),
    
    # Products
    ("GET", "/api/v1/products", 200),
    ("GET", "/api/v1/products/stats", 200),
    
    # Deals
    ("GET", "/api/v1/deals", 200),
    ("GET", "/api/v1/deals/stats", 200),
    
    # Suppliers
    ("GET", "/api/v1/suppliers", 200),
    
    # Keepa
    ("GET", "/api/v1/keepa/product/B07Y93SMRV", 200),
    ("GET", "/api/v1/keepa/tokens", 200),
    
    # Favorites
    ("GET", "/api/v1/favorites", 200),
    ("GET", "/api/v1/favorites/count", 200),
    
    # Billing
    ("GET", "/api/v1/billing/subscription", 200),
    ("GET", "/api/v1/billing/usage", 200),
    ("GET", "/api/v1/billing/user/limits", 200),
    
    # Jobs
    ("GET", "/api/v1/jobs", 200),
    
    # SP-API
    ("GET", "/api/v1/sp-api/product/B07Y93SMRV/offers", 200),
    ("GET", "/api/v1/sp-api/product/B07Y93SMRV/fees?price=19.99", 200),
    ("GET", "/api/v1/sp-api/product/B07Y93SMRV/eligibility", 200),
    ("GET", "/api/v1/sp-api/product/B07Y93SMRV/sales-estimate", 200),
]

def test(method, path, expected):
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, headers=headers, method=method)
        start = datetime.now()
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as resp:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            status = "✅" if resp.status == expected else "⚠️"
            return status, resp.status, round(elapsed), None
    except urllib.error.HTTPError as e:
        status = "✅" if e.code == expected else "❌"
        return status, e.code, 0, str(e)
    except Exception as e:
        return "❌", "ERR", 0, str(e)

def main():
    print("=" * 60)
    print("HABEXA API TESTS")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Token: {'SET' if TOKEN != 'PASTE_YOUR_TOKEN_HERE' else 'NOT SET - UPDATE TOKEN!'}")
    print("=" * 60)
    print()
    
    if TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("⚠️  WARNING: Token not set. Update TOKEN variable in script.")
        print()
    
    results = []
    for method, path, expected in ENDPOINTS:
        status, code, ms, err = test(method, path, expected)
        results.append((method, path, expected, status, code, ms, err))
        print(f"{status} {method:4} {path:50} -> {code:3} ({ms:5}ms)")
        if err:
            print(f"   Error: {err[:80]}")
    
    passed = sum(1 for r in results if r[3] == "✅")
    print()
    print(f"RESULTS: {passed}/{len(results)} passed")
    
    # Write report
    with open("/Users/lindseystevens/habexa2.0/AUDIT_OUTPUT/09_TEST_RESULTS.md", "w") as f:
        f.write("# API Test Results\n\n")
        f.write(f"**Date:** {datetime.now()}\n")
        f.write(f"**Base URL:** {BASE_URL}\n")
        f.write(f"**Passed:** {passed}/{len(results)}\n\n")
        f.write("| Status | Method | Path | Expected | Actual | Time |\n")
        f.write("|--------|--------|------|----------|--------|------|\n")
        for method, path, expected, status, code, ms, err in results:
            f.write(f"| {status} | {method} | `{path}` | {expected} | {code} | {ms}ms |\n")
        
        f.write("\n## Failures\n\n")
        for method, path, expected, status, code, ms, err in results:
            if status != "✅":
                f.write(f"### {method} {path}\n")
                f.write(f"- Expected: {expected}, Got: {code}\n")
                if err:
                    f.write(f"- Error: {err}\n")
                f.write("\n")

if __name__ == "__main__":
    main()

