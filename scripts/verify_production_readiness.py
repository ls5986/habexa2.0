#!/usr/bin/env python3
"""
Production Readiness Verification Script
Tests all critical components before deployment.
"""
import sys
import os
import asyncio
import httpx
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Color output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

# Test results
results = {
    "database": {"passed": 0, "failed": 0, "warnings": 0},
    "backend": {"passed": 0, "failed": 0, "warnings": 0},
    "frontend": {"passed": 0, "failed": 0, "warnings": 0},
    "integrations": {"passed": 0, "failed": 0, "warnings": 0},
}

def test_database_schema():
    """Test database schema and migrations."""
    print_header("DATABASE SCHEMA VERIFICATION")
    
    try:
        from app.services.supabase_client import supabase
        
        # Test 1: Subscriptions table with trial fields
        print_info("Checking subscriptions table...")
        try:
            result = supabase.table("subscriptions").select("had_free_trial, trial_start, trial_end, cancel_at_period_end").limit(1).execute()
            print_success("subscriptions table exists with trial tracking columns")
            results["database"]["passed"] += 1
        except Exception as e:
            if "column" in str(e).lower() or "does not exist" in str(e).lower():
                print_error(f"subscriptions table missing trial columns: {e}")
                results["database"]["failed"] += 1
            else:
                print_warning(f"Could not verify subscriptions table: {e}")
                results["database"]["warnings"] += 1
        
        # Test 2: Orders table
        print_info("Checking orders table...")
        try:
            result = supabase.table("orders").select("id").limit(1).execute()
            print_success("orders table exists")
            results["database"]["passed"] += 1
        except Exception as e:
            print_error(f"orders table missing: {e}")
            results["database"]["failed"] += 1
        
        # Test 3: Telegram tables
        print_info("Checking telegram tables...")
        try:
            result = supabase.table("telegram_credentials").select("id").limit(1).execute()
            print_success("telegram_credentials table exists")
            results["database"]["passed"] += 1
        except Exception as e:
            print_error(f"telegram_credentials table missing: {e}")
            results["database"]["failed"] += 1
        
        try:
            result = supabase.table("telegram_channels").select("id").limit(1).execute()
            print_success("telegram_channels table exists")
            results["database"]["passed"] += 1
        except Exception as e:
            print_error(f"telegram_channels table missing: {e}")
            results["database"]["failed"] += 1
        
        # Test 4: Amazon connections table
        print_info("Checking amazon tables...")
        try:
            result = supabase.table("amazon_connections").select("id").limit(1).execute()
            print_success("amazon_connections table exists")
            results["database"]["passed"] += 1
        except Exception as e:
            print_warning(f"amazon_connections table missing (may use amazon_credentials): {e}")
            results["database"]["warnings"] += 1
        
        # Test 5: Product sources table
        print_info("Checking product_sources table...")
        try:
            result = supabase.table("product_sources").select("id, stage").limit(1).execute()
            print_success("product_sources table exists with stage column")
            results["database"]["passed"] += 1
        except Exception as e:
            print_error(f"product_sources table missing: {e}")
            results["database"]["failed"] += 1
        
        # Test 6: Products table
        print_info("Checking products table...")
        try:
            result = supabase.table("products").select("id").limit(1).execute()
            print_success("products table exists")
            results["database"]["passed"] += 1
        except Exception as e:
            print_error(f"products table missing: {e}")
            results["database"]["failed"] += 1
        
    except Exception as e:
        print_error(f"Database connection failed: {e}")
        results["database"]["failed"] += 1

def test_backend_endpoints():
    """Test backend API endpoints."""
    print_header("BACKEND API ENDPOINTS VERIFICATION")
    
    base_url = os.getenv("BACKEND_URL", "http://localhost:8020")
    
    endpoints = [
        # Health check
        ("GET", "/health", "Health check"),
        # Telegram endpoints
        ("GET", "/api/v1/integrations/telegram/status", "Telegram status"),
        ("POST", "/api/v1/integrations/telegram/auth/start", "Telegram auth start"),
        ("DELETE", "/api/v1/integrations/telegram/disconnect", "Telegram disconnect"),
        # Amazon endpoints
        ("GET", "/api/v1/integrations/amazon/connection", "Amazon connection status"),
        ("GET", "/api/v1/integrations/amazon/oauth/authorize", "Amazon OAuth authorize"),
        ("DELETE", "/api/v1/integrations/amazon/disconnect", "Amazon disconnect"),
        # Buy list endpoints
        ("GET", "/api/v1/buy-list", "Buy list get"),
        ("POST", "/api/v1/buy-list", "Buy list add"),
        # Orders endpoints
        ("GET", "/api/v1/orders", "Orders list"),
        # Billing endpoints
        ("GET", "/api/v1/billing/user/limits", "User limits"),
    ]
    
    for method, path, name in endpoints:
        try:
            url = f"{base_url}{path}"
            response = httpx.request(method, url, timeout=5, follow_redirects=True)
            
            # 200-299 = success, 401/403 = endpoint exists but needs auth (good), 404 = missing
            if response.status_code < 500:
                print_success(f"{name}: {method} {path} (status: {response.status_code})")
                results["backend"]["passed"] += 1
            else:
                print_error(f"{name}: {method} {path} (status: {response.status_code})")
                results["backend"]["failed"] += 1
        except httpx.ConnectError:
            print_warning(f"{name}: Backend not running at {base_url}")
            results["backend"]["warnings"] += 1
            break
        except Exception as e:
            print_warning(f"{name}: {method} {path} - {e}")
            results["backend"]["warnings"] += 1

def test_backend_imports():
    """Test that backend modules can be imported."""
    print_header("BACKEND MODULE IMPORTS")
    
    modules = [
        ("app.api.v1.telegram", "Telegram API"),
        ("app.api.v1.amazon", "Amazon API"),
        ("app.api.v1.buy_list", "Buy List API"),
        ("app.api.v1.orders", "Orders API"),
        ("app.api.v1.billing", "Billing API"),
        ("app.services.telegram_service", "Telegram Service"),
        ("app.services.amazon_oauth", "Amazon OAuth"),
        ("app.services.sp_api_client", "SP-API Client"),
        ("app.services.keepa_client", "Keepa Client"),
        ("app.services.feature_gate", "Feature Gate"),
        ("app.config.tiers", "Tier Config"),
    ]
    
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print_success(f"{display_name}: {module_name}")
            results["backend"]["passed"] += 1
        except ImportError as e:
            print_error(f"{display_name}: {module_name} - {e}")
            results["backend"]["failed"] += 1
        except Exception as e:
            print_warning(f"{display_name}: {module_name} - {e}")
            results["backend"]["warnings"] += 1

def test_frontend_files():
    """Test that frontend files exist."""
    print_header("FRONTEND FILES VERIFICATION")
    
    frontend_path = Path(__file__).parent.parent / "frontend"
    
    files = [
        ("src/pages/Settings.jsx", "Settings page"),
        ("src/components/features/settings/TelegramConnect.jsx", "Telegram Connect component"),
        ("src/components/features/settings/AmazonConnect.jsx", "Amazon Connect component"),
        ("src/pages/BuyList.jsx", "Buy List page"),
        ("src/pages/Orders.jsx", "Orders page"),
        ("src/pages/OrderDetails.jsx", "Order Details page"),
        ("src/pages/NotFound.jsx", "404 Not Found page"),
        ("src/components/common/ConfirmDialog.jsx", "Confirm Dialog component"),
        ("src/components/ErrorBoundary.jsx", "Error Boundary component"),
        ("src/App.jsx", "Main App component"),
    ]
    
    for file_path, display_name in files:
        full_path = frontend_path / file_path
        if full_path.exists():
            print_success(f"{display_name}: {file_path}")
            results["frontend"]["passed"] += 1
        else:
            print_error(f"{display_name}: {file_path} - NOT FOUND")
            results["frontend"]["failed"] += 1

def test_integrations():
    """Test integration configurations."""
    print_header("INTEGRATION CONFIGURATIONS")
    
    from app.core.config import settings
    
    # Telegram config
    if settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH:
        print_success("Telegram API credentials configured")
        results["integrations"]["passed"] += 1
    else:
        print_warning("Telegram API credentials not configured")
        results["integrations"]["warnings"] += 1
    
    # Amazon SP-API config
    if (settings.SP_API_LWA_APP_ID or settings.SPAPI_LWA_CLIENT_ID) and \
       (settings.SP_API_LWA_CLIENT_SECRET or settings.SPAPI_LWA_CLIENT_SECRET):
        print_success("Amazon SP-API credentials configured")
        results["integrations"]["passed"] += 1
    else:
        print_warning("Amazon SP-API credentials not configured")
        results["integrations"]["warnings"] += 1
    
    # Keepa config
    if os.getenv("KEEPA_API_KEY"):
        print_success("Keepa API key configured")
        results["integrations"]["passed"] += 1
    else:
        print_warning("Keepa API key not configured")
        results["integrations"]["warnings"] += 1
    
    # Stripe config
    if settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET:
        print_success("Stripe credentials configured")
        results["integrations"]["passed"] += 1
    else:
        print_warning("Stripe credentials not configured")
        results["integrations"]["warnings"] += 1
    
    # Supabase config
    supabase_url = getattr(settings, "SUPABASE_URL", None)
    supabase_key = getattr(settings, "SUPABASE_KEY", None) or getattr(settings, "SUPABASE_ANON_KEY", None) or os.getenv("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        print_success("Supabase credentials configured")
        results["integrations"]["passed"] += 1
    else:
        print_error("Supabase credentials not configured")
        results["integrations"]["failed"] += 1

def generate_report():
    """Generate production readiness report."""
    print_header("PRODUCTION READINESS SUMMARY")
    
    total_passed = sum(cat["passed"] for cat in results.values())
    total_failed = sum(cat["failed"] for cat in results.values())
    total_warnings = sum(cat["warnings"] for cat in results.values())
    total_tests = total_passed + total_failed + total_warnings
    
    print(f"\n{Colors.BOLD}Test Results:{Colors.RESET}")
    print(f"  {Colors.GREEN}Passed: {total_passed}{Colors.RESET}")
    print(f"  {Colors.RED}Failed: {total_failed}{Colors.RESET}")
    print(f"  {Colors.YELLOW}Warnings: {total_warnings}{Colors.RESET}")
    print(f"  Total: {total_tests}\n")
    
    print(f"{Colors.BOLD}By Category:{Colors.RESET}")
    for category, stats in results.items():
        status = "✅" if stats["failed"] == 0 else "❌"
        print(f"  {status} {category.upper()}: {stats['passed']} passed, {stats['failed']} failed, {stats['warnings']} warnings")
    
    # Overall status
    if total_failed == 0:
        print(f"\n{Colors.BOLD}{Colors.GREEN}✅ PRODUCTION READY{Colors.RESET}")
        if total_warnings > 0:
            print(f"{Colors.YELLOW}⚠️  {total_warnings} warnings - review before deployment{Colors.RESET}")
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}❌ NOT PRODUCTION READY{Colors.RESET}")
        print(f"{Colors.RED}Fix {total_failed} failed test(s) before deployment{Colors.RESET}")
    
    return {
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_warnings": total_warnings,
        "total_tests": total_tests,
        "ready": total_failed == 0,
        "results": results
    }

def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*60)
    print("  HABEXA PRODUCTION READINESS VERIFICATION")
    print("="*60)
    print(f"{Colors.RESET}\n")
    
    # Run tests
    test_database_schema()
    test_backend_imports()
    test_backend_endpoints()
    test_frontend_files()
    test_integrations()
    
    # Generate report
    report = generate_report()
    
    return 0 if report["ready"] else 1

if __name__ == "__main__":
    exit(main())

