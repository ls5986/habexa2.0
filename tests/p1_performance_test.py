#!/usr/bin/env python3
"""
P1 Performance Benchmark Test
Tests API response times and frontend load times.

Usage:
    python tests/p1_performance_test.py

Requirements:
    pip install requests
"""

import time
import statistics
import requests
import json
from typing import Dict, List, Tuple

# Configuration
API_URL = "https://habexa-backend-w5u5.onrender.com"
FRONTEND_URL = "https://habexa.onrender.com"

# Get token from browser localStorage after login
# Or use environment variable
import os
TOKEN = os.getenv("HABEXA_TOKEN", "")

if not TOKEN:
    print("⚠️  WARNING: No token provided!")
    print("   Set HABEXA_TOKEN environment variable or edit this script")
    print("   Get token from browser localStorage after login")
    print()

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
} if TOKEN else {"Content-Type": "application/json"}


def measure_endpoint(
    url: str, 
    method: str = "GET", 
    data: Dict = None, 
    name: str = "",
    iterations: int = 5
) -> Tuple[float, List[float]]:
    """
    Measure endpoint response time.
    
    Returns:
        (average_time_ms, list_of_times_ms)
    """
    times = []
    errors = []
    
    print(f"\n📊 Testing: {name}")
    print(f"   URL: {url}")
    print(f"   Method: {method}")
    print(f"   Iterations: {iterations}")
    
    for i in range(iterations):
        try:
            start = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end = time.time()
            elapsed = (end - start) * 1000  # Convert to ms
            
            times.append(elapsed)
            status_icon = "✅" if response.status_code < 400 else "❌"
            
            print(f"   Request {i+1}: {elapsed:.0f}ms - Status: {response.status_code} {status_icon}")
            
            if response.status_code >= 400:
                errors.append(f"Request {i+1}: {response.status_code} - {response.text[:100]}")
        
        except requests.exceptions.Timeout:
            elapsed = 30000  # 30 seconds timeout
            times.append(elapsed)
            errors.append(f"Request {i+1}: TIMEOUT (>30s)")
            print(f"   Request {i+1}: TIMEOUT (>30s) ❌")
        
        except Exception as e:
            elapsed = 30000
            times.append(elapsed)
            errors.append(f"Request {i+1}: ERROR - {str(e)}")
            print(f"   Request {i+1}: ERROR - {str(e)} ❌")
    
    if times:
        avg = statistics.mean(times)
        median = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n   Results:")
        print(f"   Average: {avg:.0f}ms")
        print(f"   Median: {median:.0f}ms")
        print(f"   Min: {min_time:.0f}ms")
        print(f"   Max: {max_time:.0f}ms")
        
        if errors:
            print(f"\n   ⚠️  Errors:")
            for error in errors:
                print(f"   - {error}")
        
        return avg, times
    else:
        print("   ❌ All requests failed!")
        return 0, []


def test_api_endpoints() -> Dict[str, float]:
    """Test all API endpoints."""
    print("=" * 60)
    print("API PERFORMANCE BENCHMARKS")
    print("=" * 60)
    
    results = {}
    
    # 1. Products endpoint
    avg, _ = measure_endpoint(
        f"{API_URL}/api/v1/products",
        name="GET /products (with filters)",
        iterations=5
    )
    results["products"] = avg
    
    # 2. Stats endpoint
    avg, _ = measure_endpoint(
        f"{API_URL}/api/v1/products/stats/asin-status",
        name="GET /products/stats/asin-status",
        iterations=10  # More iterations for stats (should be very fast)
    )
    results["stats"] = avg
    
    # 3. Single product (need a real product ID)
    # This will fail if no product ID provided, but that's OK
    product_id = os.getenv("TEST_PRODUCT_ID", "")
    if product_id:
        avg, _ = measure_endpoint(
            f"{API_URL}/api/v1/products/{product_id}",
            name=f"GET /products/{product_id}",
            iterations=5
        )
        results["product_detail"] = avg
    else:
        print("\n⚠️  Skipping product detail test (no TEST_PRODUCT_ID)")
        results["product_detail"] = None
    
    # 4. Analysis endpoint (only if token provided)
    if TOKEN:
        avg, _ = measure_endpoint(
            f"{API_URL}/api/v1/analyze/single",
            method="POST",
            data={
                "asin": "B07VRZ8TK3",
                "identifier_type": "asin",
                "buy_cost": 10.00,
                "moq": 1
            },
            name="POST /analyze/single",
            iterations=3  # Fewer iterations (takes longer)
        )
        results["analyze"] = avg
    else:
        print("\n⚠️  Skipping analysis test (no token)")
        results["analyze"] = None
    
    return results


def print_results(results: Dict[str, float]):
    """Print benchmark results with pass/fail indicators."""
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    
    targets = {
        "products": 500,
        "stats": 20,
        "product_detail": 200,
        "analyze": 5000
    }
    
    passed = 0
    total = 0
    
    for endpoint, avg_time in results.items():
        if avg_time is None:
            continue
        
        target = targets.get(endpoint, 1000)
        passed_test = avg_time < target
        status = "✅ PASS" if passed_test else "❌ FAIL"
        
        print(f"\n{endpoint.upper()}:")
        print(f"  Time: {avg_time:.0f}ms")
        print(f"  Target: <{target}ms")
        print(f"  Status: {status}")
        
        if passed_test:
            passed += 1
        total += 1
    
    print("\n" + "=" * 60)
    print(f"Overall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 60)
    
    if passed == total:
        print("\n✅ ALL PERFORMANCE TESTS PASSED!")
    else:
        print(f"\n❌ {total - passed} PERFORMANCE TEST(S) FAILED")
        print("   Review results above and optimize slow endpoints")


def main():
    """Run all performance tests."""
    print("🚀 Starting Performance Benchmarks...")
    print(f"   API URL: {API_URL}")
    print(f"   Frontend URL: {FRONTEND_URL}")
    
    if not TOKEN:
        print("\n⚠️  NOTE: Some tests require authentication")
        print("   Set HABEXA_TOKEN environment variable for full testing")
    
    # Test API endpoints
    results = test_api_endpoints()
    
    # Print results
    print_results(results)
    
    # Save results to file
    with open("tests/performance_results.json", "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }, f, indent=2)
    
    print("\n📄 Results saved to: tests/performance_results.json")


if __name__ == "__main__":
    main()

