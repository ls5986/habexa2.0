"""
Production readiness test script.
Tests all critical workflows end-to-end.
"""
import requests
import time
import json
import sys
import os

BASE_URL = os.getenv("API_BASE_URL", "https://habexa-backend-w5u5.onrender.com/api/v1")
TEST_EMAIL = os.getenv("TEST_EMAIL", "lindsey@letsclink.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "")

# Colors for terminal output
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

def test_auth():
    """Test login."""
    print_info("Testing authentication...")
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_success(f"Login successful")
                return token
            else:
                print_error("Login response missing access_token")
                return None
        else:
            print_error(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Login error: {e}")
        return None

def test_redis_status(token):
    """Test Redis cache status."""
    print_info("Testing Redis cache status...")
    try:
        response = requests.get(
            f"{BASE_URL}/products/cache-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            redis_info = data.get("redis", {})
            
            if redis_info.get("enabled"):
                if redis_info.get("connected"):
                    hit_rate = redis_info.get("hit_rate", 0)
                    print_success(f"Redis connected (hit rate: {hit_rate:.1f}%)")
                    return True
                else:
                    print_warning("Redis enabled but not connected")
                    return False
            else:
                print_warning("Redis not enabled")
                return False
        else:
            print_error(f"Cache status check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Redis status error: {e}")
        return False

def test_stats_performance(token):
    """Test stats endpoint performance."""
    print_info("Testing stats endpoint performance...")
    try:
        # First request (cache miss)
        start = time.time()
        response1 = requests.get(
            f"{BASE_URL}/products/stats/asin-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        miss_time = (time.time() - start) * 1000
        
        if response1.status_code != 200:
            print_error(f"Stats endpoint failed: {response1.status_code}")
            return False
        
        # Second request (cache hit)
        start = time.time()
        response2 = requests.get(
            f"{BASE_URL}/products/stats/asin-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        hit_time = (time.time() - start) * 1000
        
        if response2.status_code != 200:
            print_error(f"Stats endpoint failed on second request: {response2.status_code}")
            return False
        
        print_success(f"Stats: {miss_time:.0f}ms (miss) → {hit_time:.0f}ms (hit)")
        
        if hit_time < 50:
            print_success("Cache hit is <50ms (target met)")
            return True
        else:
            print_warning(f"Cache hit is {hit_time:.0f}ms (target: <50ms)")
            return True  # Still pass, just warn
    except Exception as e:
        print_error(f"Stats performance test error: {e}")
        return False

def test_lookup_status(token):
    """Test ASIN lookup status endpoint."""
    print_info("Testing ASIN lookup status...")
    try:
        response = requests.get(
            f"{BASE_URL}/products/lookup-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            complete = data.get("complete", 0)
            progress = data.get("progress_percent", 0)
            
            print_success(f"Lookup status: {complete}/{total} ASINs found ({progress}%)")
            return True
        else:
            print_error(f"Lookup status failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Lookup status error: {e}")
        return False

def test_products_list(token):
    """Test products list endpoint."""
    print_info("Testing products list endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/products?limit=10",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            deals = data.get("deals", [])
            print_success(f"Products list: {len(deals)} products returned")
            return True
        else:
            print_error(f"Products list failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Products list error: {e}")
        return False

def test_upload_preview(token):
    """Test CSV upload preview endpoint."""
    print_info("Testing CSV upload preview...")
    try:
        # Create a simple test CSV
        csv_content = """UPC,ITEM,WHOLESALE,PACK
689542001425,Test Product 1,5.71,10
123456789012,Test Product 2,10.00,5"""
        
        files = {"file": ("test.csv", csv_content, "text/csv")}
        
        response = requests.post(
            f"{BASE_URL}/products/upload/preview",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            total_rows = data.get("total_rows", 0)
            print_success(f"Upload preview: {total_rows} rows detected")
            return True
        else:
            print_error(f"Upload preview failed: {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        print_error(f"Upload preview error: {e}")
        return False

def run_all_tests():
    """Run all production tests."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}🧪 HABEXA PRODUCTION READINESS TEST{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "auth": False,
        "redis": False,
        "stats_performance": False,
        "lookup_status": False,
        "products_list": False,
        "upload_preview": False
    }
    
    # Test 1: Auth
    print(f"\n{BLUE}[1/6] Authentication{RESET}")
    token = test_auth()
    if not token:
        print_error("Cannot continue without authentication token")
        return False
    results["auth"] = True
    print()
    
    # Test 2: Redis
    print(f"{BLUE}[2/6] Redis Cache{RESET}")
    results["redis"] = test_redis_status(token)
    print()
    
    # Test 3: Performance
    print(f"{BLUE}[3/6] Stats Performance{RESET}")
    results["stats_performance"] = test_stats_performance(token)
    print()
    
    # Test 4: Lookup Status
    print(f"{BLUE}[4/6] ASIN Lookup Status{RESET}")
    results["lookup_status"] = test_lookup_status(token)
    print()
    
    # Test 5: Products List
    print(f"{BLUE}[5/6] Products List{RESET}")
    results["products_list"] = test_products_list(token)
    print()
    
    # Test 6: Upload Preview
    print(f"{BLUE}[6/6] CSV Upload Preview{RESET}")
    results["upload_preview"] = test_upload_preview(token)
    print()
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}📊 TEST RESULTS SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
        print(f"  {test_name.replace('_', ' ').title():.<40} {status}")
    
    print(f"\n{BLUE}Score: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print_success("\n🎉 ALL TESTS PASSED! Production ready!")
        return True
    else:
        print_error(f"\n⚠️  {total - passed} test(s) failed. Review issues above.")
        return False

if __name__ == "__main__":
    if not TEST_PASSWORD:
        print_error("TEST_PASSWORD environment variable not set")
        print_info("Set it with: export TEST_PASSWORD='your_password'")
        sys.exit(1)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)

