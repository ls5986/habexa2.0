#!/usr/bin/env python3
"""
Test all Supabase-backed endpoints after seeding data.
Verifies that all CRUD operations work correctly.
"""
import sys
import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

BASE_URL = "http://localhost:8020"
API_PREFIX = "/api/v1"

# You'll need a valid JWT token - get it from browser localStorage after logging in
TEST_TOKEN = None  # Set this to test authenticated endpoints

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

async def test_endpoints():
    """Test all Supabase-backed endpoints."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BLUE}TESTING SUPABASE ENDPOINTS{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    if not TEST_TOKEN:
        print(f"{Colors.YELLOW}⚠ No test token provided. Testing public endpoints only.{Colors.RESET}\n")
    
    headers = {}
    if TEST_TOKEN:
        headers["Authorization"] = f"Bearer {TEST_TOKEN}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tests = [
            # Public endpoints
            ("GET", f"{API_PREFIX}/billing/plans", "Get pricing plans"),
            
            # Products endpoints (need auth)
            ("GET", f"{API_PREFIX}/products", "List products"),
            ("GET", f"{API_PREFIX}/products/stats", "Get product stats"),
            
            # Suppliers endpoints (need auth)
            ("GET", f"{API_PREFIX}/suppliers", "List suppliers"),
            
            # Settings endpoints (need auth)
            ("GET", f"{API_PREFIX}/settings/profile", "Get profile"),
            ("GET", f"{API_PREFIX}/settings/alerts", "Get alert settings"),
            ("GET", f"{API_PREFIX}/settings/costs", "Get cost settings"),
            
            # Jobs endpoints (need auth)
            ("GET", f"{API_PREFIX}/jobs", "List jobs"),
            
            # Watchlist endpoints (need auth)
            ("GET", f"{API_PREFIX}/watchlist", "Get watchlist"),
            
            # Orders endpoints (need auth)
            ("GET", f"{API_PREFIX}/orders", "List orders"),
            
            # Notifications endpoints (need auth)
            ("GET", f"{API_PREFIX}/notifications", "List notifications"),
        ]
        
        results = []
        for method, path, description in tests:
            try:
                url = f"{BASE_URL}{path}"
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json={})
                else:
                    continue
                
                success = response.status_code in [200, 201]
                status_icon = f"{Colors.GREEN}✓{Colors.RESET}" if success else f"{Colors.RED}✗{Colors.RESET}"
                status_text = f"{Colors.GREEN}PASS{Colors.RESET}" if success else f"{Colors.RED}FAIL{Colors.RESET}"
                
                print(f"{status_icon} {method:6} {path:50} {status_text} ({response.status_code})")
                
                if success:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            count = len(data.get("suppliers", data.get("products", data.get("deals", []))))
                            if count > 0:
                                print(f"      {Colors.BLUE}→ Found {count} items{Colors.RESET}")
                    except:
                        pass
                
                results.append({
                    "method": method,
                    "path": path,
                    "description": description,
                    "success": success,
                    "status_code": response.status_code
                })
                
            except Exception as e:
                print(f"{Colors.RED}✗{Colors.RESET} {method:6} {path:50} {Colors.RED}ERROR{Colors.RESET}")
                print(f"      {Colors.RED}→ {str(e)[:100]}{Colors.RESET}")
                results.append({
                    "method": method,
                    "path": path,
                    "description": description,
                    "success": False,
                    "error": str(e)
                })
        
        # Summary
        print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
        print(f"{Colors.BLUE}SUMMARY{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
        
        passed = sum(1 for r in results if r.get("success", False))
        failed = sum(1 for r in results if not r.get("success", False))
        
        print(f"{Colors.GREEN}✓ Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}✗ Failed: {failed}{Colors.RESET}")
        print(f"Total:   {len(results)}\n")
        
        if failed > 0:
            print(f"{Colors.RED}FAILURES:{Colors.RESET}")
            for r in results:
                if not r.get("success", False):
                    print(f"  {r['method']} {r['path']}: {r.get('error', f'Status {r.get(\"status_code\")}')}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())

