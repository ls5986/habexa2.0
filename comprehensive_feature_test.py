"""
Comprehensive Feature Audit - Test EVERY user-facing feature
Finds all broken features and generates detailed report.
"""
import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Configuration
TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6ImxXc2NWdEdaYVZkbE1pS0UiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZwaWh6bmFtbndsdmthYXJubGJjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY1MzQwMzQwLCJpYXQiOjE3NjUzMzY3NDAsImVtYWlsIjoibGluZHNleUBsZXRzY2xpbmsuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImxpbmRzZXlAbGV0c2NsaW5rLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJsaW5kc2V5IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiJkMzIwOTM1ZC04MGU4LTRiNWYtYWU2OS0wNjMxNWI2YjFiMzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2NTMzNjc0MH1dLCJzZXNzaW9uX2lkIjoiNTk3ZTI0OWUtMjQ4Zi00MWFkLTlhMmMtYjBkMTkyYTFlZjEzIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.YM3ur2DPNc9yI4Av7M5PLiRnLY2I4-GIahenGSbSvPM"
BASE_URL = "https://habexa-backend-w5u5.onrender.com/api/v1"

# Test Data
TEST_UPC = "689542001425"
TEST_ASIN = "B07VRZ8TK3"
TEST_PRODUCT_ID = None  # Will be set after creating a product
TEST_DEAL_ID = None  # Will be set from products list

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Results storage
results: List[Dict] = []
created_resources: List[Dict] = []  # Track created items for cleanup

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

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

def test_category_1_analysis(headers: Dict):
    """CATEGORY 1: Product Analysis"""
    print(f"\n{BLUE}{'='*70}{RESET}")
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"POST /products/analyze-upc: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"POST /products/analyze-upc: SKIP - {error}")
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"POST /products/analyze-asin: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"POST /products/analyze-asin: SKIP - {error}")
    else:
        print_error(f"POST /products/analyze-asin: {error}")
    
    # Test 1.3: Get product details (need product ID first)
    # Will test after creating a product

def test_category_2_management(headers: Dict):
    """CATEGORY 2: Product Management"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 2: Product Management{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    global TEST_PRODUCT_ID, TEST_DEAL_ID
    
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /products: {duration:.0f}ms")
        # Try to get a product ID and deal ID from response
        try:
            response = requests.get(f"{BASE_URL}/products?limit=5", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                deals = data.get("deals", [])
                if deals and len(deals) > 0:
                    TEST_PRODUCT_ID = deals[0].get("product_id") or deals[0].get("id")
                    TEST_DEAL_ID = deals[0].get("deal_id") or deals[0].get("id")
                    print_info(f"   Found product_id: {TEST_PRODUCT_ID}, deal_id: {TEST_DEAL_ID}")
        except Exception as e:
            print_warning(f"   Could not extract product ID: {e}")
    elif status == "SKIP":
        print_warning(f"GET /products: SKIP - {error}")
    else:
        print_error(f"GET /products: {error}")
    
    # Test 2.2: Create product manually (with buy_cost required field)
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"POST /products: {duration:.0f}ms")
        # Try to get product ID from response
        try:
            response = requests.post(
                f"{BASE_URL}/products",
                headers=headers,
                json={"asin": TEST_ASIN, "title": "Test Product", "brand": "Test Brand", "upc": TEST_UPC, "buy_cost": 10.00},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                TEST_PRODUCT_ID = data.get("id") or data.get("product_id")
                if TEST_PRODUCT_ID:
                    created_resources.append({"type": "product", "id": TEST_PRODUCT_ID})
                    print_info(f"   Created product ID: {TEST_PRODUCT_ID}")
        except:
            pass
    elif status == "SKIP":
        print_warning(f"POST /products: SKIP - {error}")
    else:
        print_error(f"POST /products: {error}")
    
    # Test 2.3: Add to favorites (USER SAYS BROKEN - CRITICAL)
    # Try multiple endpoints: /favorites and /products/deal/{deal_id}/favorite
    
    # Method 1: POST /favorites (if product_id available)
    if TEST_PRODUCT_ID:
        status, success, error, duration = test_endpoint(
            "Management",
            "POST /favorites",
            "POST",
            f"{BASE_URL}/favorites",
            headers=headers,
            json_data={"product_id": TEST_PRODUCT_ID},
            expected_status=200
        )
        results.append({
            "category": "Management",
            "name": "POST /favorites (add to favorites)",
            "status": status,
            "success": success,
            "error": error,
            "duration": duration
        })
        if status == "PASS":
            print_success(f"POST /favorites: {duration:.0f}ms")
        elif status == "SKIP":
            print_warning(f"POST /favorites: SKIP - {error}")
        else:
            print_error(f"POST /favorites: {error} ⚠️ USER REPORTED BROKEN")
    
    # Method 2: PATCH /products/deal/{deal_id}/favorite (if deal_id available)
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
            "duration": duration
        })
        if status == "PASS":
            print_success(f"PATCH /products/deal/{TEST_DEAL_ID}/favorite: {duration:.0f}ms")
        elif status == "SKIP":
            print_warning(f"PATCH /products/deal/{TEST_DEAL_ID}/favorite: SKIP - {error}")
        else:
            print_error(f"PATCH /products/deal/{TEST_DEAL_ID}/favorite: {error} ⚠️ USER REPORTED BROKEN")
    
    if not TEST_PRODUCT_ID and not TEST_DEAL_ID:
        print_warning("Add to favorites: SKIP - No product ID or deal ID available")
        results.append({
            "category": "Management",
            "name": "POST /favorites",
            "status": "SKIP",
            "success": False,
            "error": "No product ID available",
            "duration": 0
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /products?favorite=true: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"GET /products?favorite=true: SKIP - {error}")
    else:
        print_error(f"GET /products?favorite=true: {error}")

def test_category_3_csv_upload(headers: Dict):
    """CATEGORY 3: CSV Upload"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 3: CSV Upload{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test CSV content
    csv_content = f"""UPC,ITEM,WHOLESALE,PACK
{TEST_UPC},Test Product 1,5.71,10
123456789012,Test Product 2,10.00,5"""
    
    # Test 3.1: Preview CSV
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"POST /products/upload/preview: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"POST /products/upload/preview: SKIP - {error}")
    else:
        print_error(f"POST /products/upload/preview: {error}")

def test_category_4_bulk_actions(headers: Dict):
    """CATEGORY 4: Bulk Actions"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 4: Bulk Actions{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test 4.1: Bulk action endpoint
    if TEST_PRODUCT_ID:
        status, success, error, duration = test_endpoint(
            "Bulk Actions",
            "POST /products/bulk-action",
            "POST",
            f"{BASE_URL}/products/bulk-action",
            headers=headers,
            json_data={"action": "favorite", "product_ids": [TEST_PRODUCT_ID]},
            expected_status=200
        )
        results.append({
            "category": "Bulk Actions",
            "name": "POST /products/bulk-action",
            "status": status,
            "success": success,
            "error": error,
            "duration": duration
        })
        if status == "PASS":
            print_success(f"POST /products/bulk-action: {duration:.0f}ms")
        elif status == "SKIP":
            print_warning(f"POST /products/bulk-action: SKIP - {error}")
        else:
            print_error(f"POST /products/bulk-action: {error}")
    else:
        print_warning("POST /products/bulk-action: SKIP - No product ID available")
        results.append({
            "category": "Bulk Actions",
            "name": "POST /products/bulk-action",
            "status": "SKIP",
            "success": False,
            "error": "No product ID available",
            "duration": 0
        })

def test_category_5_filtering(headers: Dict):
    """CATEGORY 5: Filtering & Search"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 5: Filtering & Search{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test 5.1: Filter by ASIN status
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /products?asin_status=needs_asin: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"GET /products?asin_status=needs_asin: SKIP - {error}")
    else:
        print_error(f"GET /products?asin_status=needs_asin: {error}")
    
    # Test 5.2: Search
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /products?search=test: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"GET /products?search=test: SKIP - {error}")
    else:
        print_error(f"GET /products?search=test: {error}")

def test_category_6_orders(headers: Dict):
    """CATEGORY 6: Orders"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 6: Orders{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test 6.1: List orders (endpoint exists at /api/v1/orders, router prefix is /orders)
    status, success, error, duration = test_endpoint(
        "Orders",
        "GET /orders",
        "GET",
        f"{BASE_URL}/orders",  # Full path: /api/v1/orders
        headers=headers
    )
    results.append({
        "category": "Orders",
        "name": "GET /orders",
        "status": status,
        "success": success,
        "error": error,
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /orders: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"GET /orders: SKIP - {error}")
    else:
        print_error(f"GET /orders: {error}")

def test_category_7_suppliers(headers: Dict):
    """CATEGORY 7: Suppliers"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 7: Suppliers{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test 7.1: List suppliers
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /suppliers: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"GET /suppliers: SKIP - {error}")
    else:
        print_error(f"GET /suppliers: {error}")

def test_category_8_stats(headers: Dict):
    """CATEGORY 8: Stats & Analytics"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CATEGORY 8: Stats & Analytics{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test 8.1: ASIN status stats
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /products/stats/asin-status: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"GET /products/stats/asin-status: SKIP - {error}")
    else:
        print_error(f"GET /products/stats/asin-status: {error}")
    
    # Test 8.2: Lookup status
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
        "duration": duration
    })
    if status == "PASS":
        print_success(f"GET /products/lookup-status: {duration:.0f}ms")
    elif status == "SKIP":
        print_warning(f"GET /products/lookup-status: SKIP - {error}")
    else:
        print_error(f"GET /products/lookup-status: {error}")

def generate_report():
    """Generate comprehensive test report."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}📊 COMPREHENSIVE FEATURE AUDIT REPORT{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    
    print(f"{BLUE}Summary:{RESET}")
    print(f"  Total Features Tested: {total}")
    print(f"  ✅ Working: {passed}")
    print(f"  ❌ Broken: {failed}")
    print(f"  ⚠️  Skipped: {skipped}")
    print(f"  Success Rate: {(passed/total*100):.1f}%\n")
    
    # Broken features
    broken = [r for r in results if r["status"] == "FAIL"]
    if broken:
        print(f"{RED}❌ BROKEN FEATURES ({len(broken)}):{RESET}\n")
        for r in broken:
            print(f"  {r['name']}")
            print(f"    Category: {r['category']}")
            print(f"    Error: {r['error']}")
            print()
    
    # Working features by category
    print(f"{GREEN}✅ WORKING FEATURES BY CATEGORY:{RESET}\n")
    categories = {}
    for r in results:
        if r["status"] == "PASS":
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r["name"])
    
    for cat, features in categories.items():
        print(f"  {cat}: {len(features)} features")
        for feature in features:
            print(f"    ✅ {feature}")
        print()
    
    # Production readiness score
    score = (passed / total * 100) if total > 0 else 0
    print(f"{BLUE}Production Readiness Score: {score:.1f}/100{RESET}\n")
    
    if score >= 90:
        print_success("🎉 PRODUCTION READY - Most features working!")
    elif score >= 70:
        print_warning("⚠️  MOSTLY READY - Some features need fixing")
    else:
        print_error("❌ NOT READY - Multiple features broken")
    
    # Save report to file
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "score": score
        },
        "broken_features": broken,
        "all_results": results
    }
    
    filename = f"feature_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n{BLUE}Detailed report saved to: {filename}{RESET}")

def main():
    """Run comprehensive feature audit."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}🔍 COMPREHENSIVE FEATURE AUDIT{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}\n")
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # Run all category tests
    test_category_1_analysis(headers)
    test_category_2_management(headers)
    test_category_3_csv_upload(headers)
    test_category_4_bulk_actions(headers)
    test_category_5_filtering(headers)
    test_category_6_orders(headers)
    test_category_7_suppliers(headers)
    test_category_8_stats(headers)
    
    # Generate report
    generate_report()
    
    return 0

if __name__ == "__main__":
    exit(main())

