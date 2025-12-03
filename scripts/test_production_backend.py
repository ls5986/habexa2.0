#!/usr/bin/env python3
"""
Test ALL endpoints on the PRODUCTION backend.

Run: python scripts/test_production_backend.py
"""
import requests
import json
import sys

PROD_URL = "https://habexa-backend-w5u5.onrender.com"

# Get this from browser localStorage after logging in
# Or pass as environment variable
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6ImxXc2NWdEdaYVZkbE1pS0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZwaWh6bmFtbndsdmthYXJubGJjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY0NzUyMzc0LCJpYXQiOjE3NjQ3NDg3NzQsImVtYWlsIjoibGluZHNleUBsZXRzY2xpbmsuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImxpbmRzZXlAbGV0c2NsaW5rLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJsaW5kc2V5IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2NDc0ODc3NH1dLCJzZXNzaW9uX2lkIjoiMGJhNGU5NjctM2ZiMC00NjE2LWFlYzEtZjAwZWU4YzE3ODZmIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.XIrlCLsCv2-X7j6g8szEg5z4R3TsOoZbCIWURa4z7qk"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def h():
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

results = {"working": [], "broken": [], "errors": []}

def test_endpoint(method, path, expected_codes, auth=True, body=None, name=None):
    url = f"{PROD_URL}{path}"
    display_name = name or f"{method} {path}"
    
    try:
        headers = h() if auth else {"Content-Type": "application/json"}
        
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=body or {}, timeout=10)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=10)
        elif method == "PATCH":
            r = requests.patch(url, headers=headers, json=body or {}, timeout=10)
        elif method == "PUT":
            r = requests.put(url, headers=headers, json=body or {}, timeout=10)
        
        if r.status_code in expected_codes:
            print(f"  {Colors.GREEN}✅{Colors.RESET} {display_name} → {r.status_code}")
            results["working"].append(display_name)
            return True, r
        elif r.status_code == 404:
            print(f"  {Colors.RED}❌ 404{Colors.RESET} {display_name} → ENDPOINT NOT FOUND")
            results["broken"].append(f"{display_name} → 404 NOT FOUND")
            return False, r
        elif r.status_code == 500:
            print(f"  {Colors.RED}❌ 500{Colors.RESET} {display_name} → SERVER ERROR")
            try:
                error_detail = r.json()
            except:
                error_detail = r.text[:200]
            results["broken"].append(f"{display_name} → 500: {error_detail}")
            return False, r
        else:
            print(f"  {Colors.YELLOW}⚠️{Colors.RESET} {display_name} → {r.status_code} (expected {expected_codes})")
            results["errors"].append(f"{display_name} → {r.status_code}")
            return False, r
            
    except requests.exceptions.Timeout:
        print(f"  {Colors.RED}❌ TIMEOUT{Colors.RESET} {display_name}")
        results["broken"].append(f"{display_name} → TIMEOUT")
        return False, None
    except Exception as e:
        print(f"  {Colors.RED}❌ ERROR{Colors.RESET} {display_name} → {str(e)[:50]}")
        results["broken"].append(f"{display_name} → {str(e)[:50]}")
        return False, None

def main():
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  PRODUCTION BACKEND TEST{Colors.RESET}")
    print(f"{Colors.BOLD}  {PROD_URL}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    # ========================================
    # HEALTH & BASIC
    # ========================================
    print(f"\n{Colors.BLUE}[HEALTH & BASIC]{Colors.RESET}")
    test_endpoint("GET", "/health", [200], auth=False, name="Health check")
    test_endpoint("GET", "/", [200, 404], auth=False, name="Root")
    test_endpoint("GET", "/docs", [200], auth=False, name="API Docs")
    
    # ========================================
    # AUTH ENDPOINTS
    # ========================================
    print(f"\n{Colors.BLUE}[AUTH]{Colors.RESET}")
    test_endpoint("POST", "/api/v1/auth/login", [200, 400, 401, 422], auth=False, 
                  body={"email": "test@test.com", "password": "wrong"}, name="Login")
    test_endpoint("POST", "/api/v1/auth/register", [200, 400, 422], auth=False,
                  body={"email": "", "password": ""}, name="Register (validation)")
    test_endpoint("GET", "/api/v1/auth/me", [200, 401], name="Get current user")
    test_endpoint("POST", "/api/v1/auth/change-password", [200, 400, 401], 
                  body={"current_password": "wrong", "new_password": "Test1234!"}, name="Change password")
    
    # ========================================
    # BILLING ENDPOINTS (CRITICAL)
    # ========================================
    print(f"\n{Colors.BLUE}[BILLING - CRITICAL]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/billing/user/limits", [200], name="⭐ User limits (CRITICAL)")
    test_endpoint("GET", "/api/v1/billing/subscription", [200, 404], name="Get subscription")
    test_endpoint("POST", "/api/v1/billing/create-checkout-session", [200, 400], 
                  body={"price_id": "test"}, name="Create checkout")
    test_endpoint("POST", "/api/v1/billing/portal-session", [200, 400], name="Billing portal")
    test_endpoint("POST", "/api/v1/billing/cancel-subscription", [200, 400, 404], name="Cancel subscription")
    test_endpoint("POST", "/api/v1/billing/resume-subscription", [200, 400, 404], name="Resume subscription")
    test_endpoint("POST", "/api/v1/billing/initialize-subscription", [200, 400], name="Initialize subscription")
    
    # ========================================
    # PRODUCTS
    # ========================================
    print(f"\n{Colors.BLUE}[PRODUCTS]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/products", [200], name="List products")
    test_endpoint("GET", "/api/v1/products/deals", [200], name="Get deals")
    test_endpoint("POST", "/api/v1/products/analyze", [200, 202, 400, 422],
                  body={"asin": "B007S6Y6VS", "cost": 20, "moq": 100}, name="Analyze product")
    
    # ========================================
    # SUPPLIERS
    # ========================================
    print(f"\n{Colors.BLUE}[SUPPLIERS]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/suppliers", [200], name="List suppliers")
    
    # ========================================
    # BUY LIST
    # ========================================
    print(f"\n{Colors.BLUE}[BUY LIST]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/buy-list", [200], name="Get buy list")
    
    # ========================================
    # ORDERS
    # ========================================
    print(f"\n{Colors.BLUE}[ORDERS]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/orders", [200], name="List orders")
    
    # ========================================
    # NOTIFICATIONS
    # ========================================
    print(f"\n{Colors.BLUE}[NOTIFICATIONS]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/notifications", [200], name="List notifications")
    
    # ========================================
    # TELEGRAM
    # ========================================
    print(f"\n{Colors.BLUE}[TELEGRAM]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/integrations/telegram/status", [200, 404], name="Telegram status")
    
    # ========================================
    # AMAZON
    # ========================================
    print(f"\n{Colors.BLUE}[AMAZON]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/amazon/status", [200, 404], name="Amazon status")
    test_endpoint("GET", "/api/v1/amazon/connection", [200, 404], name="Amazon connection")
    
    # ========================================
    # JOBS
    # ========================================
    print(f"\n{Colors.BLUE}[JOBS]{Colors.RESET}")
    test_endpoint("GET", "/api/v1/jobs", [200], name="List jobs")
    
    # ========================================
    # SUMMARY
    # ========================================
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  RESULTS{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    print(f"\n  {Colors.GREEN}Working:{Colors.RESET} {len(results['working'])}")
    print(f"  {Colors.RED}Broken (404/500):{Colors.RESET} {len(results['broken'])}")
    print(f"  {Colors.YELLOW}Other issues:{Colors.RESET} {len(results['errors'])}")
    
    if results["broken"]:
        print(f"\n  {Colors.RED}{Colors.BOLD}BROKEN ENDPOINTS:{Colors.RESET}")
        for item in results["broken"]:
            print(f"    • {item}")
    
    if results["errors"]:
        print(f"\n  {Colors.YELLOW}OTHER ISSUES:{Colors.RESET}")
        for item in results["errors"]:
            print(f"    • {item}")
    
    # Save results to file
    with open("production_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: production_test_results.json")
    
    if results["broken"]:
        print(f"\n  {Colors.RED}❌ PRODUCTION HAS BROKEN ENDPOINTS{Colors.RESET}")
        sys.exit(1)
    else:
        print(f"\n  {Colors.GREEN}✅ All endpoints responding{Colors.RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()

