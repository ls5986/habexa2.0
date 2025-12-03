#!/usr/bin/env python3
"""
Comprehensive endpoint testing script.
Tests all critical API endpoints for correctness.
"""
import asyncio
import httpx
import json
import sys
from typing import Dict, List, Tuple

# Test configuration
BASE_URL = "http://localhost:8020"
API_PREFIX = "/api/v1"

# You'll need to set this to a valid JWT token for authenticated endpoints
TEST_TOKEN = None  # Set this if you want to test auth endpoints

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class EndpointTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[Dict] = []
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def test_endpoint(
        self,
        method: str,
        path: str,
        expected_status: int = 200,
        requires_auth: bool = False,
        json_data: dict = None,
        params: dict = None,
        description: str = None
    ) -> Dict:
        """Test a single endpoint."""
        url = f"{self.base_url}{path}"
        headers = {}
        
        if requires_auth and TEST_TOKEN:
            headers["Authorization"] = f"Bearer {TEST_TOKEN}"
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=json_data, params=params)
            elif method.upper() == "PUT":
                response = await self.client.put(url, headers=headers, json=json_data)
            elif method.upper() == "PATCH":
                response = await self.client.patch(url, headers=headers, json=json_data)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, headers=headers)
            else:
                return {
                    "method": method,
                    "path": path,
                    "status": "SKIP",
                    "error": f"Unsupported method: {method}"
                }
            
            success = response.status_code == expected_status
            result = {
                "method": method,
                "path": path,
                "description": description or path,
                "status_code": response.status_code,
                "expected": expected_status,
                "success": success,
                "response_size": len(response.content),
            }
            
            # Try to parse JSON response
            try:
                result["response"] = response.json()
            except:
                result["response"] = response.text[:200]
            
            if not success:
                result["error"] = f"Expected {expected_status}, got {response.status_code}"
            
            return result
            
        except httpx.ConnectError:
            return {
                "method": method,
                "path": path,
                "description": description or path,
                "status": "ERROR",
                "error": "Connection refused - is backend running?"
            }
        except Exception as e:
            return {
                "method": method,
                "path": path,
                "description": description or path,
                "status": "ERROR",
                "error": str(e)
            }
    
    def print_result(self, result: Dict):
        """Print a test result with color coding."""
        method = result.get("method", "?")
        path = result.get("path", "?")
        desc = result.get("description", path)
        
        if result.get("status") == "ERROR":
            status_icon = f"{Colors.RED}✗{Colors.RESET}"
            status_text = f"{Colors.RED}ERROR{Colors.RESET}"
        elif result.get("status") == "SKIP":
            status_icon = f"{Colors.YELLOW}⊘{Colors.RESET}"
            status_text = f"{Colors.YELLOW}SKIP{Colors.RESET}"
        elif result.get("success", False):
            status_icon = f"{Colors.GREEN}✓{Colors.RESET}"
            status_text = f"{Colors.GREEN}PASS{Colors.RESET}"
        else:
            status_icon = f"{Colors.RED}✗{Colors.RESET}"
            status_text = f"{Colors.RED}FAIL{Colors.RESET}"
        
        print(f"{status_icon} {method:6} {path:50} {status_text}")
        
        if result.get("error"):
            print(f"      {Colors.RED}→ {result['error']}{Colors.RESET}")
        elif result.get("status_code"):
            print(f"      {Colors.BLUE}→ Status: {result['status_code']}{Colors.RESET}")

async def test_all_endpoints():
    """Test all critical endpoints."""
    
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BLUE}COMPREHENSIVE ENDPOINT TEST{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    async with EndpointTester(BASE_URL) as tester:
        tests = [
            # Health & Root
            ("GET", "/health", 200, False, None, None, "Health check"),
            ("GET", "/", 200, False, None, None, "Root endpoint"),
            
            # Billing (Public - no auth needed for plans)
            ("GET", f"{API_PREFIX}/billing/plans", 200, False, None, None, "Get pricing plans"),
            
            # Analysis endpoints (will fail without auth, but test structure)
            ("POST", f"{API_PREFIX}/analyze/single", 401, False, {
                "identifier_type": "asin",
                "asin": "B08N5WRWNW",
                "buy_cost": 10.0
            }, None, "Analyze single product (should 401 without auth)"),
            
            # Products (will fail without auth)
            ("GET", f"{API_PREFIX}/products", 401, False, None, None, "Get products (should 401 without auth)"),
            ("GET", f"{API_PREFIX}/products/stats", 401, False, None, None, "Get product stats (should 401 without auth)"),
            
            # Jobs (will fail without auth)
            ("GET", f"{API_PREFIX}/jobs", 401, False, None, None, "List jobs (should 401 without auth)"),
            
            # Suppliers (will fail without auth)
            ("GET", f"{API_PREFIX}/suppliers", 401, False, None, None, "List suppliers (should 401 without auth)"),
            
            # Settings (will fail without auth)
            ("GET", f"{API_PREFIX}/settings/profile", 401, False, None, None, "Get profile (should 401 without auth)"),
            
            # Keepa (will fail without auth)
            ("GET", f"{API_PREFIX}/product/B08N5WRWNW", 401, False, None, None, "Get Keepa product (should 401 without auth)"),
            
            # SP-API (will fail without auth)
            ("GET", f"{API_PREFIX}/sp-api/product/B08N5WRWNW/offers", 401, False, None, None, "Get SP-API offers (should 401 without auth)"),
            
            # Invalid endpoints (should 404)
            ("GET", f"{API_PREFIX}/nonexistent", 404, False, None, None, "Non-existent endpoint (should 404)"),
            ("GET", "/invalid-path", 404, False, None, None, "Invalid root path (should 404)"),
        ]
        
        print(f"{Colors.YELLOW}Testing {len(tests)} endpoints...{Colors.RESET}\n")
        
        results = []
        for test in tests:
            result = await tester.test_endpoint(*test)
            results.append(result)
            tester.print_result(result)
        
        # Summary
        print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
        print(f"{Colors.BLUE}SUMMARY{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
        
        passed = sum(1 for r in results if r.get("success", False))
        failed = sum(1 for r in results if not r.get("success", False) and r.get("status") != "SKIP")
        errors = sum(1 for r in results if r.get("status") == "ERROR")
        skipped = sum(1 for r in results if r.get("status") == "SKIP")
        
        print(f"{Colors.GREEN}✓ Passed:  {passed}{Colors.RESET}")
        print(f"{Colors.RED}✗ Failed:  {failed}{Colors.RESET}")
        print(f"{Colors.RED}✗ Errors:  {errors}{Colors.RESET}")
        print(f"{Colors.YELLOW}⊘ Skipped: {skipped}{Colors.RESET}")
        print(f"Total:    {len(results)}\n")
        
        # Show failures
        if failed > 0 or errors > 0:
            print(f"{Colors.RED}FAILURES:{Colors.RESET}")
            for r in results:
                if not r.get("success", False) and r.get("status") != "SKIP":
                    print(f"  {r['method']} {r['path']}: {r.get('error', 'Unknown error')}")
        
        return passed, failed, errors

if __name__ == "__main__":
    try:
        passed, failed, errors = asyncio.run(test_all_endpoints())
        sys.exit(0 if failed == 0 and errors == 0 else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Test script error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

