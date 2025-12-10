"""
Production test script for Habexa application.
Tests critical endpoints with authentication.
"""
import requests
import time
import json
from datetime import datetime

# Configuration
TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6ImxXc2NWdEdaYVZkbE1pS0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZwaWh6bmFtbndsdmthYXJubGJjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY1MzQwMzQwLCJpYXQiOjE3NjUzMzY3NDAsImVtYWlsIjoibGluZHNleUBsZXRzY2xpbmsuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImxpbmRzZXlAbGV0c2NsaW5rLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJsaW5kc2V5IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2NTMzNjc0MH1dLCJzZXNzaW9uX2lkIjoiNTk3ZTI0OWUtMjQ4Zi00MWFkLTlhMmMtYjBkMTkyYTFlZjEzIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.YM3ur2DPNc9yI4Av7M5PLiRnLY2I4-GIahenGSbSvPM"
BASE_URL = "https://habexa-backend-w5u5.onrender.com/api/v1"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def test_endpoint(name, method, url, headers=None, expected_status=200):
    """Test an endpoint and return result."""
    try:
        start = time.time()
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            response = requests.post(url, headers=headers, timeout=15)
        else:
            response = requests.request(method, url, headers=headers, timeout=15)
        
        duration = (time.time() - start) * 1000
        
        if response.status_code == expected_status:
            print_success(f"{name}: {response.status_code} ({duration:.0f}ms)")
            return True, duration, response
        else:
            print_error(f"{name}: {response.status_code} ({duration:.0f}ms) - {response.text[:100]}")
            return False, duration, response
    except Exception as e:
        print_error(f"{name}: Error - {str(e)}")
        return False, 0, None

def main():
    """Run all production tests."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}🧪 HABEXA PRODUCTION TESTS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}\n")
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    results = []
    
    # Test 1: Health Check
    print(f"{BLUE}[1/5] Health Check{RESET}")
    success, duration, _ = test_endpoint(
        "GET /health",
        "GET",
        f"{BASE_URL.replace('/api/v1', '')}/health"
    )
    results.append(("Health Check", success, duration))
    print()
    
    # Test 2: Cache Status
    print(f"{BLUE}[2/5] Redis Cache Status{RESET}")
    success, duration, response = test_endpoint(
        "GET /products/cache-status",
        "GET",
        f"{BASE_URL}/products/cache-status",
        headers=headers
    )
    if success and response:
        try:
            data = response.json()
            redis_info = data.get("redis", {})
            if redis_info.get("connected"):
                hit_rate = redis_info.get("hit_rate", 0) or 0
                print_info(f"   Redis hit rate: {hit_rate:.1f}%")
                print_info(f"   Memory: {redis_info.get('memory_usage', {}).get('used_memory_human', 'N/A')}")
            else:
                print_warning("   Redis not connected")
        except:
            pass
    results.append(("Cache Status", success, duration))
    print()
    
    # Test 3: Stats Endpoint (Cache Test)
    print(f"{BLUE}[3/5] Stats Endpoint (Cache Test){RESET}")
    
    # First request (cache miss)
    print_info("   First request (cache miss)...")
    success1, duration1, _ = test_endpoint(
        "GET /products/stats/asin-status (miss)",
        "GET",
        f"{BASE_URL}/products/stats/asin-status",
        headers=headers
    )
    
    # Second request (cache hit)
    print_info("   Second request (cache hit)...")
    success2, duration2, _ = test_endpoint(
        "GET /products/stats/asin-status (hit)",
        "GET",
        f"{BASE_URL}/products/stats/asin-status",
        headers=headers
    )
    
    if success1 and success2:
        speedup = duration1 / duration2 if duration2 > 0 else 0
        print_info(f"   Performance: {duration1:.0f}ms → {duration2:.0f}ms ({speedup:.1f}x faster)")
        if duration2 < 50:
            print_success(f"   Cache hit <50ms target met")
        else:
            print_warning(f"   Cache hit {duration2:.0f}ms (target: <50ms)")
    
    results.append(("Stats (miss)", success1, duration1))
    results.append(("Stats (hit)", success2, duration2))
    print()
    
    # Test 4: Lookup Status
    print(f"{BLUE}[4/5] ASIN Lookup Status{RESET}")
    success, duration, response = test_endpoint(
        "GET /products/lookup-status",
        "GET",
        f"{BASE_URL}/products/lookup-status",
        headers=headers
    )
    if success and response:
        try:
            data = response.json()
            total = data.get("total", 0)
            complete = data.get("complete", 0)
            progress = data.get("progress_percent", 0)
            print_info(f"   Status: {complete}/{total} ASINs found ({progress}%)")
        except:
            pass
    results.append(("Lookup Status", success, duration))
    print()
    
    # Test 5: Products List
    print(f"{BLUE}[5/5] Products List{RESET}")
    success, duration, response = test_endpoint(
        "GET /products",
        "GET",
        f"{BASE_URL}/products?limit=10",
        headers=headers
    )
    if success and response:
        try:
            data = response.json()
            deals = data.get("deals", [])
            print_info(f"   Products returned: {len(deals)}")
        except:
            pass
    results.append(("Products List", success, duration))
    print()
    
    # Summary
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}📊 TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    avg_duration = sum(d for _, _, d in results) / total if total > 0 else 0
    
    for name, success, duration in results:
        status = f"{GREEN}✅ PASS{RESET}" if success else f"{RED}❌ FAIL{RESET}"
        print(f"  {name:.<50} {status} ({duration:.0f}ms)")
    
    print(f"\n{BLUE}Results:{RESET}")
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}")
    print(f"  Average response time: {avg_duration:.0f}ms")
    
    if passed == total:
        print_success(f"\n🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print_error(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())

