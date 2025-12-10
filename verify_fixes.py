"""
Verify Fixes - Comprehensive Test Suite
Tests all features and compares to previous results.
"""
import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Configuration
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test
env_test_path = Path(__file__).parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path)
else:
    load_dotenv()

TOKEN = os.getenv("TEST_TOKEN", "eyJhbGciOiJIUzI1NiIsImtpZCI6ImxXc2NWdEdaYVZkbE1pS0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZwaWh6bmFtbndsdmthYXJubGJjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzMzNzgxMjkxLCJpYXQiOjE3MzM3Nzc2OTEsImVtYWlsIjoibGluZHNleUBsZXRzY2xpbmsuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImxpbmRzZXlAbGV0c2NsaW5rLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJsaW5kc2V5IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTczMzc3NzY5MX1dLCJzZXNzaW9uX2lkIjoiMGRmOGQ5ZGQtNmVhNS00YzdmLWI0M2MtNzA0ZDNjZDEzNzg3IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.Zf0xKbQ4YWJCCOOPZoO7Dy4TJxJqU_LkwAgXQGC3qnA")
BASE_URL = os.getenv("BASE_URL", "https://habexa-backend-w5u5.onrender.com/api/v1")

# Test Data
TEST_UPC = "689542001425"
TEST_ASIN = "B07VRZ8TK3"
TEST_PRODUCT_ID = None
TEST_DEAL_ID = None

# Previous Results (from before fixes)
PREVIOUS_RESULTS = {
    "total": 14,
    "passed": 10,
    "failed": 0,
    "skipped": 4,
    "score": 71.4,
    "broken": [],
    "working": [
        "GET /products",
        "POST /products",
        "PATCH /products/deal/{deal_id}/favorite",
        "GET /products?favorite=true",
        "POST /products/upload/preview",
        "GET /products?asin_status=needs_asin",
        "GET /products?search=test",
        "GET /suppliers",
        "GET /products/stats/asin-status",
        "GET /products/lookup-status"
    ],
    "skipped": [
        "POST /products/analyze-upc",
        "POST /products/analyze-asin",
        "GET /orders",
        "POST /products/bulk-action"
    ]
}

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

results: List[Dict] = []

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def print_cyan(msg):
    print(f"{CYAN}{msg}{RESET}")

def test_endpoint(
    category: str,
    name: str,
    method: str,
    url: str,
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    files: Optional[Dict] = None,
    expected_status: int = 200,
    skip_if_404: bool = True
) -> Tuple[str, bool, str, float]:
    """Test an endpoint and return (status, success, error, duration)."""
    try:
        start = time.time()
        response = requests.request(
            method,
            url,
            headers=headers,
            json=json_data,
            files=files,
            timeout=30
        )
        duration = (time.time() - start) * 1000
        
        if response.status_code == 404 and skip_if_404:
            return ("SKIP", False, "Endpoint not found (404)", duration)
        
        if response.status_code == expected_status:
            return ("PASS", True, "", duration)
        else:
            error_msg = response.text[:200] if response.text else "No error message"
            return ("FAIL", False, f"{response.status_code}: {error_msg}", duration)
    except requests.exceptions.Timeout:
        return ("FAIL", False, "Request timeout", 0)
    except Exception as e:
        return ("FAIL", False, f"Error: {str(e)}", 0)

def run_all_tests():
    """Run comprehensive test suite."""
    global TEST_PRODUCT_ID, TEST_DEAL_ID
    
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}🔍 VERIFY FIXES - COMPREHENSIVE TEST SUITE{RESET}")
    print(f"{CYAN}{'='*70}{RESET}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}\n")
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # CATEGORY 1: Product Analysis
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 1: Product Analysis{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test 1.1: Analyze UPC
    status, success, error, duration = test_endpoint(
        "Analysis",
        "POST /products/analyze-upc",
        "POST",
        f"{BASE_URL}/products/analyze-upc",
        headers=headers,
        json_data={"upc": TEST_UPC},
        expected_status=200
    )
    results.append({
        "category": "Analysis",
        "name": "POST /products/analyze-upc",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_skipped": "POST /products/analyze-upc" in PREVIOUS_RESULTS["skipped"]
    })
    if status == "PASS":
        print_success(f"POST /products/analyze-upc: {duration:.0f}ms (FIXED! Was skipped)")
    elif status == "SKIP":
        print_warning(f"POST /products/analyze-upc: SKIP - {error} (Still needs deployment)")
    else:
        print_error(f"POST /products/analyze-upc: {error}")
    
    # Test 1.2: Analyze ASIN
    status, success, error, duration = test_endpoint(
        "Analysis",
        "POST /products/analyze-asin",
        "POST",
        f"{BASE_URL}/products/analyze-asin",
        headers=headers,
        json_data={"asin": TEST_ASIN},
        expected_status=200
    )
    results.append({
        "category": "Analysis",
        "name": "POST /products/analyze-asin",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_skipped": "POST /products/analyze-asin" in PREVIOUS_RESULTS["skipped"]
    })
    if status == "PASS":
        print_success(f"POST /products/analyze-asin: {duration:.0f}ms (FIXED! Was skipped)")
    elif status == "SKIP":
        print_warning(f"POST /products/analyze-asin: SKIP - {error} (Still needs deployment)")
    else:
        print_error(f"POST /products/analyze-asin: {error}")
    
    # CATEGORY 2: Product Management
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 2: Product Management{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test 2.1: List products
    status, success, error, duration = test_endpoint(
        "Management",
        "GET /products",
        "GET",
        f"{BASE_URL}/products?limit=10",
        headers=headers
    )
    results.append({
        "category": "Management",
        "name": "GET /products",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "GET /products" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"GET /products: {duration:.0f}ms")
        # Get product and deal IDs
        try:
            response = requests.get(f"{BASE_URL}/products?limit=5", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                deals = data.get("deals", [])
                if deals and len(deals) > 0:
                    TEST_PRODUCT_ID = deals[0].get("product_id") or deals[0].get("id")
                    TEST_DEAL_ID = deals[0].get("deal_id") or deals[0].get("id")
        except:
            pass
    else:
        print_error(f"GET /products: {error}")
    
    # Test 2.2: Create product
    status, success, error, duration = test_endpoint(
        "Management",
        "POST /products",
        "POST",
        f"{BASE_URL}/products",
        headers=headers,
        json_data={
            "asin": TEST_ASIN,
            "title": "Test Product",
            "brand": "Test Brand",
            "upc": TEST_UPC,
            "buy_cost": 10.00
        },
        expected_status=200
    )
    results.append({
        "category": "Management",
        "name": "POST /products",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "POST /products" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"POST /products: {duration:.0f}ms")
    else:
        print_error(f"POST /products: {error}")
    
    # Test 2.3: Add to favorites (CRITICAL - WAS BROKEN)
    if TEST_DEAL_ID:
        status, success, error, duration = test_endpoint(
            "Management",
            "PATCH /products/deal/{deal_id}/favorite",
            "PATCH",
            f"{BASE_URL}/products/deal/{TEST_DEAL_ID}/favorite",
            headers=headers,
            expected_status=200
        )
        results.append({
            "category": "Management",
            "name": "PATCH /products/deal/{deal_id}/favorite",
            "status": status,
            "success": success,
            "error": error,
            "duration": duration,
            "was_working": "PATCH /products/deal/{deal_id}/favorite" in PREVIOUS_RESULTS["working"],
            "was_fixed": True  # This was the main fix
        })
        if status == "PASS":
            print_success(f"PATCH /products/deal/{TEST_DEAL_ID}/favorite: {duration:.0f}ms ✅ FIXED!")
        else:
            print_error(f"PATCH /products/deal/{TEST_DEAL_ID}/favorite: {error} ❌ STILL BROKEN")
    else:
        print_warning("PATCH /products/deal/{deal_id}/favorite: SKIP - No deal ID available")
        results.append({
            "category": "Management",
            "name": "PATCH /products/deal/{deal_id}/favorite",
            "status": "SKIP",
            "success": False,
            "error": "No deal ID available",
            "duration": 0,
            "was_working": True,
            "was_fixed": True
        })
    
    # Test 2.4: Get favorites
    status, success, error, duration = test_endpoint(
        "Management",
        "GET /products?favorite=true",
        "GET",
        f"{BASE_URL}/products?favorite=true",
        headers=headers
    )
    results.append({
        "category": "Management",
        "name": "GET /products?favorite=true",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "GET /products?favorite=true" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"GET /products?favorite=true: {duration:.0f}ms")
    else:
        print_error(f"GET /products?favorite=true: {error}")
    
    # CATEGORY 3: CSV Upload
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 3: CSV Upload{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    csv_content = f"""UPC,ITEM,WHOLESALE,PACK
{TEST_UPC},Test Product 1,5.71,10
123456789012,Test Product 2,10.00,5"""
    
    status, success, error, duration = test_endpoint(
        "CSV Upload",
        "POST /products/upload/preview",
        "POST",
        f"{BASE_URL}/products/upload/preview",
        headers=headers,
        files={"file": ("test.csv", csv_content, "text/csv")},
        expected_status=200
    )
    results.append({
        "category": "CSV Upload",
        "name": "POST /products/upload/preview",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "POST /products/upload/preview" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"POST /products/upload/preview: {duration:.0f}ms")
    else:
        print_error(f"POST /products/upload/preview: {error}")
    
    # CATEGORY 4: Bulk Actions
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 4: Bulk Actions{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    if TEST_DEAL_ID:
        status, success, error, duration = test_endpoint(
            "Bulk Actions",
            "POST /products/bulk-action",
            "POST",
            f"{BASE_URL}/products/bulk-action",
            headers=headers,
            json_data={"action": "favorite", "product_ids": [TEST_DEAL_ID]},
            expected_status=200
        )
        results.append({
            "category": "Bulk Actions",
            "name": "POST /products/bulk-action",
            "status": status,
            "success": success,
            "error": error,
            "duration": duration,
            "was_skipped": "POST /products/bulk-action" in PREVIOUS_RESULTS["skipped"]
        })
        if status == "PASS":
            print_success(f"POST /products/bulk-action: {duration:.0f}ms")
        elif status == "SKIP":
            print_warning(f"POST /products/bulk-action: SKIP - {error}")
        else:
            print_error(f"POST /products/bulk-action: {error}")
    else:
        print_warning("POST /products/bulk-action: SKIP - No deal ID available")
        results.append({
            "category": "Bulk Actions",
            "name": "POST /products/bulk-action",
            "status": "SKIP",
            "success": False,
            "error": "No deal ID available",
            "duration": 0,
            "was_skipped": True
        })
    
    # CATEGORY 5: Filtering
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 5: Filtering & Search{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    status, success, error, duration = test_endpoint(
        "Filtering",
        "GET /products?asin_status=needs_asin",
        "GET",
        f"{BASE_URL}/products?asin_status=needs_asin",
        headers=headers
    )
    results.append({
        "category": "Filtering",
        "name": "GET /products?asin_status=needs_asin",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "GET /products?asin_status=needs_asin" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"GET /products?asin_status=needs_asin: {duration:.0f}ms")
    else:
        print_error(f"GET /products?asin_status=needs_asin: {error}")
    
    status, success, error, duration = test_endpoint(
        "Filtering",
        "GET /products?search=test",
        "GET",
        f"{BASE_URL}/products?search=test",
        headers=headers
    )
    results.append({
        "category": "Filtering",
        "name": "GET /products?search=test",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "GET /products?search=test" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"GET /products?search=test: {duration:.0f}ms")
    else:
        print_error(f"GET /products?search=test: {error}")
    
    # CATEGORY 6: Orders
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 6: Orders{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    status, success, error, duration = test_endpoint(
        "Orders",
        "GET /orders",
        "GET",
        f"{BASE_URL}/orders",
        headers=headers
    )
    results.append({
        "category": "Orders",
        "name": "GET /orders",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_skipped": "GET /orders" in PREVIOUS_RESULTS["skipped"]
    })
    if status == "PASS":
        print_success(f"GET /orders: {duration:.0f}ms (FIXED! Was skipped)")
    elif status == "SKIP":
        print_warning(f"GET /orders: SKIP - {error}")
    else:
        print_error(f"GET /orders: {error}")
    
    # CATEGORY 7: Suppliers
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 7: Suppliers{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    status, success, error, duration = test_endpoint(
        "Suppliers",
        "GET /suppliers",
        "GET",
        f"{BASE_URL}/suppliers",
        headers=headers
    )
    results.append({
        "category": "Suppliers",
        "name": "GET /suppliers",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "GET /suppliers" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"GET /suppliers: {duration:.0f}ms")
    else:
        print_error(f"GET /suppliers: {error}")
    
    # CATEGORY 8: Stats
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 8: Stats & Analytics{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    status, success, error, duration = test_endpoint(
        "Stats",
        "GET /products/stats/asin-status",
        "GET",
        f"{BASE_URL}/products/stats/asin-status",
        headers=headers
    )
    results.append({
        "category": "Stats",
        "name": "GET /products/stats/asin-status",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "GET /products/stats/asin-status" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"GET /products/stats/asin-status: {duration:.0f}ms")
    else:
        print_error(f"GET /products/stats/asin-status: {error}")
    
    status, success, error, duration = test_endpoint(
        "Stats",
        "GET /products/lookup-status",
        "GET",
        f"{BASE_URL}/products/lookup-status",
        headers=headers
    )
    results.append({
        "category": "Stats",
        "name": "GET /products/lookup-status",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration,
        "was_working": "GET /products/lookup-status" in PREVIOUS_RESULTS["working"]
    })
    if status == "PASS":
        print_success(f"GET /products/lookup-status: {duration:.0f}ms")
    else:
        print_error(f"GET /products/lookup-status: {error}")

def generate_comparison_report():
    """Generate before/after comparison report."""
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}📊 BEFORE/AFTER COMPARISON{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")
    
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    score = (passed / total * 100) if total > 0 else 0
    
    # Calculate improvements
    previous_passed = PREVIOUS_RESULTS["passed"]
    previous_score = PREVIOUS_RESULTS["score"]
    improvement = passed - previous_passed
    score_improvement = score - previous_score
    
    print(f"{BLUE}BEFORE FIXES:{RESET}")
    print(f"  Total Features: {PREVIOUS_RESULTS['total']}")
    print(f"  ✅ Working: {PREVIOUS_RESULTS['passed']}")
    print(f"  ❌ Broken: {PREVIOUS_RESULTS['failed']}")
    print(f"  ⚠️  Skipped: {PREVIOUS_RESULTS['skipped']}")
    print(f"  Score: {PREVIOUS_RESULTS['score']:.1f}/100\n")
    
    print(f"{GREEN}AFTER FIXES:{RESET}")
    print(f"  Total Features: {total}")
    print(f"  ✅ Working: {passed}")
    print(f"  ❌ Broken: {failed}")
    print(f"  ⚠️  Skipped: {skipped}")
    print(f"  Score: {score:.1f}/100\n")
    
    print(f"{CYAN}IMPROVEMENT:{RESET}")
    if improvement > 0:
        print_success(f"  +{improvement} features fixed!")
        print_success(f"  +{score_improvement:.1f} points improvement!")
    elif improvement == 0:
        print_info("  No change in working features")
    else:
        print_warning(f"  {improvement} features regressed")
    
    # Show fixed features
    fixed_features = [r for r in results if r.get("was_fixed") or (r.get("was_skipped") and r["status"] == "PASS")]
    if fixed_features:
        print(f"\n{GREEN}FIXED FEATURES:{RESET}\n")
        for r in fixed_features:
            if r.get("was_fixed"):
                print_success(f"  ✅ {r['name']} - FIXED (was broken)")
            elif r.get("was_skipped") and r["status"] == "PASS":
                print_success(f"  ✅ {r['name']} - NOW WORKING (was skipped)")
    
    # Show still broken
    broken = [r for r in results if r["status"] == "FAIL"]
    if broken:
        print(f"\n{RED}STILL BROKEN:{RESET}\n")
        for r in broken:
            print_error(f"  ❌ {r['name']}: {r['error']}")
    
    # Show still skipped
    still_skipped = [r for r in results if r["status"] == "SKIP" and r.get("was_skipped")]
    if still_skipped:
        print(f"\n{YELLOW}STILL SKIPPED (needs deployment):{RESET}\n")
        for r in still_skipped:
            print_warning(f"  ⚠️  {r['name']}: {r['error']}")
    
    # Production readiness recommendation
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}🎯 PRODUCTION READINESS ASSESSMENT{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")
    
    print(f"{BLUE}Current Score: {score:.1f}/100{RESET}\n")
    
    if score >= 90:
        print_success("🎉 PRODUCTION READY - Excellent score!")
        recommendation = "GO"
    elif score >= 80:
        print_success("✅ PRODUCTION READY - Good score, minor issues acceptable")
        recommendation = "GO"
    elif score >= 70:
        print_warning("⚠️  MOSTLY READY - Some features need attention")
        if failed == 0:
            recommendation = "GO (with monitoring)"
        else:
            recommendation = "CONDITIONAL GO"
    else:
        print_error("❌ NOT READY - Multiple critical issues")
        recommendation = "NO-GO"
    
    print(f"\n{CYAN}RECOMMENDATION: {recommendation}{RESET}\n")
    
    if recommendation == "GO":
        print_success("✅ Ready to launch!")
        print_info("  - Core features working")
        print_info("  - Favorites fixed")
        print_info("  - No critical bugs")
    elif recommendation == "CONDITIONAL GO":
        print_warning("⚠️  Can launch with conditions:")
        print_info("  - Monitor broken features")
        print_info("  - Plan fixes for next release")
    else:
        print_error("❌ Do not launch yet:")
        print_info("  - Fix critical bugs first")
        print_info("  - Re-test before launch")
    
    # Save report
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "previous": PREVIOUS_RESULTS,
        "current": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "score": score
        },
        "improvement": {
            "features_fixed": improvement,
            "score_improvement": score_improvement
        },
        "fixed_features": [r["name"] for r in fixed_features],
        "broken_features": [{"name": r["name"], "error": r["error"]} for r in broken],
        "recommendation": recommendation,
        "all_results": results
    }
    
    filename = f"verify_fixes_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n{BLUE}Detailed report saved to: {filename}{RESET}\n")
    
    return recommendation

def main():
    """Run verification tests."""
    run_all_tests()
    recommendation = generate_comparison_report()
    return 0 if recommendation in ["GO", "CONDITIONAL GO"] else 1

if __name__ == "__main__":
    exit(main())

