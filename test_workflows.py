"""
Workflow Testing Suite - Complete End-to-End User Workflows
Tests real user scenarios, not just individual endpoints.
"""
import requests
import time
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dotenv import load_dotenv

# Load .env.test file if it exists
env_test_path = Path(__file__).parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path)
else:
    load_dotenv()

# Configuration
BASE_URL = os.getenv("BASE_URL", "https://habexa-backend-w5u5.onrender.com/api/v1")
TEST_EMAIL = os.getenv("TEST_EMAIL", "lindsey@letsclink.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
TEST_TOKEN = os.getenv("TEST_TOKEN", "")

# Test Data
TEST_UPC = "689542001425"
TEST_ASIN = "B07VRZ8TK3"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

# Test data cleanup tracker
test_data_to_cleanup = {
    "products": [],
    "deals": [],
    "suppliers": [],
    "favorites": []
}

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def print_step(step_num, total, msg):
    print(f"{CYAN}[{step_num}/{total}] {msg}{RESET}")

def print_workflow_header(name):
    print(f"\n{MAGENTA}{'='*70}{RESET}")
    print(f"{MAGENTA}🔄 WORKFLOW: {name}{RESET}")
    print(f"{MAGENTA}{'='*70}{RESET}\n")

def api_call(method: str, endpoint: str, headers: Dict, json_data: Optional[Dict] = None, files: Optional[Dict] = None, timeout: int = 30) -> Tuple[bool, Any, str, float]:
    """Make API call and return (success, data, error, duration)."""
    try:
        start = time.time()
        response = requests.request(
            method,
            f"{BASE_URL}{endpoint}",
            headers=headers,
            json=json_data,
            files=files,
            timeout=timeout
        )
        duration = (time.time() - start) * 1000
        
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                return (True, data, "", duration)
            except:
                return (True, response.text, "", duration)
        else:
            error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
            return (False, None, error_msg, duration)
    except requests.exceptions.Timeout:
        return (False, None, "Request timeout", 0)
    except Exception as e:
        return (False, None, f"Error: {str(e)}", 0)

# ============================================================================
# WORKFLOW 1: Product Analysis Workflow
# ============================================================================

def workflow_1_product_analysis(headers: Dict) -> Dict:
    """Workflow: Analyze UPC → Get ASIN → Quick Analysis → Add to Products"""
    print_workflow_header("Product Analysis (UPC → ASIN → Analysis → Add)")
    
    workflow_result = {
        "name": "Product Analysis",
        "steps": [],
        "success": False,
        "duration": 0,
        "test_data": {}
    }
    
    start_time = time.time()
    
    # Step 1: Analyze UPC
    print_step(1, 4, "Analyzing UPC to get ASIN...")
    success, data, error, duration = api_call("POST", "/products/analyze-upc", headers, json_data={"upc": TEST_UPC})
    workflow_result["steps"].append({
        "step": 1,
        "action": "Analyze UPC",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if not success:
        print_error(f"Failed to analyze UPC: {error}")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    asin = data.get("asin") if data else None
    if not asin:
        print_error("No ASIN returned from UPC analysis")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    print_success(f"Got ASIN: {asin} ({duration:.0f}ms)")
    workflow_result["test_data"]["asin"] = asin
    
    # Step 2: Quick ASIN Analysis
    print_step(2, 4, "Performing quick ASIN analysis...")
    success, data, error, duration = api_call("POST", "/products/analyze-asin", headers, json_data={"asin": asin, "buy_cost": 10.00})
    workflow_result["steps"].append({
        "step": 2,
        "action": "Quick ASIN Analysis",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if not success:
        print_error(f"Failed to analyze ASIN: {error}")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    sell_price = data.get("sell_price") if data else None
    print_success(f"Analysis complete - Sell Price: ${sell_price} ({duration:.0f}ms)")
    
    # Step 3: Create Supplier (if needed)
    print_step(3, 4, "Creating test supplier...")
    supplier_name = f"Test Supplier {int(time.time())}"
    success, data, error, duration = api_call("POST", "/suppliers", headers, json_data={"name": supplier_name, "website": "http://test.com"})
    
    supplier_id = None
    if success and data:
        supplier_id = data.get("id")
        test_data_to_cleanup["suppliers"].append(supplier_id)
        print_success(f"Supplier created: {supplier_id} ({duration:.0f}ms)")
    else:
        print_warning(f"Could not create supplier: {error} - continuing anyway")
    
    # Step 4: Add Product to Products
    print_step(4, 4, "Adding product to products list...")
    product_data = {
        "asin": asin,
        "title": data.get("title", "Test Product") if data else "Test Product",
        "brand": "Test Brand",
        "upc": TEST_UPC,
        "buy_cost": 10.00,
        "moq": 1
    }
    if supplier_id:
        product_data["supplier_id"] = supplier_id
    
    success, data, error, duration = api_call("POST", "/products", headers, json_data=product_data)
    workflow_result["steps"].append({
        "step": 4,
        "action": "Add Product",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if success and data:
        # FIX: Handle both response formats (product_id/deal_id or product/deal objects)
        product_id = data.get("product_id") or (data.get("product", {}).get("id") if isinstance(data.get("product"), dict) else None)
        deal_id = data.get("deal_id") or (data.get("deal", {}).get("id") if isinstance(data.get("deal"), dict) else None)
        
        if product_id:
            test_data_to_cleanup["products"].append(product_id)
        if deal_id:
            test_data_to_cleanup["deals"].append(deal_id)
        workflow_result["test_data"]["product_id"] = product_id
        workflow_result["test_data"]["deal_id"] = deal_id
        print_success(f"Product added: product_id={product_id}, deal_id={deal_id} ({duration:.0f}ms)")
        workflow_result["success"] = True
    else:
        print_error(f"Failed to add product: {error}")
    
    workflow_result["duration"] = (time.time() - start_time) * 1000
    return workflow_result

# ============================================================================
# WORKFLOW 2: CSV Upload Workflow
# ============================================================================

def workflow_2_csv_upload(headers: Dict) -> Dict:
    """Workflow: Upload CSV → Preview → Map Columns → Confirm Upload"""
    print_workflow_header("CSV Upload (Upload → Preview → Map → Confirm)")
    
    workflow_result = {
        "name": "CSV Upload",
        "steps": [],
        "success": False,
        "duration": 0,
        "test_data": {}
    }
    
    start_time = time.time()
    
    # Step 1: Create CSV content
    print_step(1, 3, "Preparing CSV file...")
    csv_content = f"""UPC,ITEM,WHOLESALE,PACK,BRAND
{TEST_UPC},Test Product CSV,5.71,10,Test Brand
123456789012,Another Test Product,10.00,5,Test Brand"""
    
    # Step 2: Upload Preview
    print_step(2, 3, "Uploading CSV for preview...")
    files = {"file": ("test_workflow.csv", csv_content, "text/csv")}
    success, data, error, duration = api_call("POST", "/products/upload/preview", headers, files=files)
    workflow_result["steps"].append({
        "step": 1,
        "action": "Upload Preview",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if not success:
        print_error(f"Failed to upload preview: {error}")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    total_rows = data.get("total_rows", 0) if data else 0
    print_success(f"Preview successful: {total_rows} rows detected ({duration:.0f}ms)")
    
    # Step 3: Confirm Upload (with mapping)
    print_step(3, 3, "Confirming upload with column mapping...")
    
    # Get suggested mapping from preview
    suggested_mapping = data.get("suggested_mapping", {}) if data else {}
    
    # Confirm upload (use column_mapping as expected by backend)
    # FIX: Encode CSV content as base64 (backend expects base64 encoded file_data)
    import base64
    file_data_base64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    
    confirm_data = {
        "filename": "test_workflow.csv",
        "column_mapping": suggested_mapping,  # Backend expects column_mapping, not mapping
        "file_data": file_data_base64  # Base64 encoded
    }
    
    success, data, error, duration = api_call("POST", "/products/upload/confirm", headers, json_data=confirm_data)
    workflow_result["steps"].append({
        "step": 2,
        "action": "Confirm Upload",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if success and data:
        created = data.get("created", 0)
        print_success(f"Upload confirmed: {created} products created ({duration:.0f}ms)")
        
        # Track created products for cleanup
        if "product_ids" in data:
            test_data_to_cleanup["products"].extend(data["product_ids"])
        workflow_result["success"] = True
    else:
        print_error(f"Failed to confirm upload: {error}")
    
    workflow_result["duration"] = (time.time() - start_time) * 1000
    return workflow_result

# ============================================================================
# WORKFLOW 3: Favorites Workflow
# ============================================================================

def workflow_3_favorites(headers: Dict) -> Dict:
    """Workflow: Add to Favorites → View Favorites → Remove from Favorites"""
    print_workflow_header("Favorites (Add → View → Remove)")
    
    workflow_result = {
        "name": "Favorites",
        "steps": [],
        "success": False,
        "duration": 0,
        "test_data": {}
    }
    
    start_time = time.time()
    
    # Step 1: Get a product/deal to favorite
    print_step(1, 4, "Getting a product to favorite...")
    success, data, error, duration = api_call("GET", "/products?limit=1", headers)
    
    if not success or not data:
        print_error(f"Failed to get products: {error}")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    deals = data.get("deals", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    if not deals:
        print_warning("No products available to favorite - creating one...")
        # Create a product first
        success, data, error, _ = api_call("POST", "/products", headers, json_data={
            "asin": TEST_ASIN,
            "title": "Test Favorite Product",
            "brand": "Test Brand",
            "buy_cost": 10.00
        })
        if success and data:
            deal_id = data.get("deal_id")
            if deal_id:
                test_data_to_cleanup["deals"].append(deal_id)
        else:
            print_error("Could not create test product")
            workflow_result["duration"] = (time.time() - start_time) * 1000
            return workflow_result
        # Get it again
        success, data, error, _ = api_call("GET", "/products?limit=1", headers)
        deals = data.get("deals", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    
    if not deals:
        print_error("No products available for favorites test")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    deal = deals[0]
    deal_id = deal.get("deal_id") or deal.get("id")
    workflow_result["test_data"]["deal_id"] = deal_id
    
    print_success(f"Using deal: {deal_id}")
    
    # Step 2: Add to Favorites
    print_step(2, 4, "Adding product to favorites...")
    success, data, error, duration = api_call("PATCH", f"/products/deal/{deal_id}/favorite", headers)
    workflow_result["steps"].append({
        "step": 1,
        "action": "Add to Favorites",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if not success:
        print_error(f"Failed to add to favorites: {error}")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    is_favorite = data.get("is_favorite") if data else False
    print_success(f"Added to favorites: {is_favorite} ({duration:.0f}ms)")
    test_data_to_cleanup["favorites"].append(deal_id)
    
    # Step 3: View Favorites
    print_step(3, 4, "Viewing favorites list...")
    success, data, error, duration = api_call("GET", "/products?favorite=true", headers)
    workflow_result["steps"].append({
        "step": 2,
        "action": "View Favorites",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if not success:
        print_error(f"Failed to view favorites: {error}")
    else:
        deals = data.get("deals", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        favorite_count = len(deals)
        print_success(f"Found {favorite_count} favorite(s) ({duration:.0f}ms)")
    
    # Step 4: Remove from Favorites
    print_step(4, 4, "Removing from favorites...")
    success, data, error, duration = api_call("PATCH", f"/products/deal/{deal_id}/favorite", headers)
    workflow_result["steps"].append({
        "step": 3,
        "action": "Remove from Favorites",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if success:
        is_favorite = data.get("is_favorite") if data else False
        print_success(f"Removed from favorites: {not is_favorite} ({duration:.0f}ms)")
        workflow_result["success"] = True
    else:
        print_error(f"Failed to remove from favorites: {error}")
    
    workflow_result["duration"] = (time.time() - start_time) * 1000
    return workflow_result

# ============================================================================
# WORKFLOW 4: Bulk Actions Workflow
# ============================================================================

def workflow_4_bulk_actions(headers: Dict) -> Dict:
    """Workflow: Select Products → Bulk Analyze → Bulk Move → Bulk Delete"""
    print_workflow_header("Bulk Actions (Select → Analyze → Move → Delete)")
    
    workflow_result = {
        "name": "Bulk Actions",
        "steps": [],
        "success": False,
        "duration": 0,
        "test_data": {}
    }
    
    start_time = time.time()
    
    # Step 1: Get products to select
    print_step(1, 4, "Getting products for bulk actions...")
    success, data, error, duration = api_call("GET", "/products?limit=3", headers)
    
    if not success or not data:
        print_error(f"Failed to get products: {error}")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    deals = data.get("deals", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    if len(deals) < 2:
        print_warning("Not enough products for bulk actions - creating test products...")
        # Create test products
        for i in range(2):
            success, data, error, _ = api_call("POST", "/products", headers, json_data={
                "asin": f"{TEST_ASIN[:-1]}{i}",
                "title": f"Bulk Test Product {i}",
                "brand": "Test Brand",
                "buy_cost": 10.00 + i
            })
            if success and data:
                deal_id = data.get("deal_id")
                if deal_id:
                    test_data_to_cleanup["deals"].append(deal_id)
        # Get again
        success, data, error, _ = api_call("GET", "/products?limit=3", headers)
        deals = data.get("deals", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    
    if len(deals) < 2:
        print_error("Not enough products for bulk actions test")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    deal_ids = [d.get("deal_id") or d.get("id") for d in deals[:2]]
    workflow_result["test_data"]["deal_ids"] = deal_ids
    print_success(f"Selected {len(deal_ids)} products for bulk actions")
    
    # Step 2: Bulk Analyze
    print_step(2, 4, "Bulk analyzing products...")
    success, data, error, duration = api_call("POST", "/products/bulk-analyze", headers, json_data={"deal_ids": deal_ids})
    workflow_result["steps"].append({
        "step": 1,
        "action": "Bulk Analyze",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if success:
        queued = data.get("queued", 0) if data else 0
        print_success(f"Bulk analyze queued: {queued} products ({duration:.0f}ms)")
    else:
        print_warning(f"Bulk analyze failed: {error} - continuing")
    
    # Step 3: Bulk Move to Buy List (endpoint expects list in body, stage as query param)
    print_step(3, 4, "Bulk moving to buy list...")
    # FIX: bulk-stage expects deal_ids as a list directly in body, not wrapped in object
    success, data, error, duration = api_call("POST", f"/products/bulk-stage?stage=buy_list", headers, json_data=deal_ids)
    workflow_result["steps"].append({
        "step": 2,
        "action": "Bulk Move",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if success:
        print_success(f"Bulk move successful ({duration:.0f}ms)")
    else:
        print_warning(f"Bulk move failed: {error} - continuing")
    
    # Step 4: Bulk Delete (cleanup)
    print_step(4, 4, "Bulk deleting test products...")
    success, data, error, duration = api_call("POST", "/products/bulk-action", headers, json_data={"action": "delete", "product_ids": deal_ids})
    workflow_result["steps"].append({
        "step": 3,
        "action": "Bulk Delete",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if success:
        deleted = data.get("success", 0) if data else 0
        print_success(f"Bulk delete successful: {deleted} products ({duration:.0f}ms)")
        # Remove from cleanup list since we deleted them
        for deal_id in deal_ids:
            if deal_id in test_data_to_cleanup["deals"]:
                test_data_to_cleanup["deals"].remove(deal_id)
        workflow_result["success"] = True
    else:
        print_error(f"Bulk delete failed: {error}")
    
    workflow_result["duration"] = (time.time() - start_time) * 1000
    return workflow_result

# ============================================================================
# WORKFLOW 5: Product Management Workflow
# ============================================================================

def workflow_5_product_management(headers: Dict) -> Dict:
    """Workflow: Create Product → Update MOQ → View Details → Delete"""
    print_workflow_header("Product Management (Create → Update → View → Delete)")
    
    workflow_result = {
        "name": "Product Management",
        "steps": [],
        "success": False,
        "duration": 0,
        "test_data": {}
    }
    
    start_time = time.time()
    
    # Step 1: Create Product
    print_step(1, 4, "Creating product...")
    success, data, error, duration = api_call("POST", "/products", headers, json_data={
        "asin": TEST_ASIN,
        "title": "Workflow Test Product",
        "brand": "Test Brand",
        "upc": TEST_UPC,
        "buy_cost": 15.00,
        "moq": 1
    })
    workflow_result["steps"].append({
        "step": 1,
        "action": "Create Product",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if not success or not data:
        print_error(f"Failed to create product: {error}")
        workflow_result["duration"] = (time.time() - start_time) * 1000
        return workflow_result
    
    # FIX: Handle both response formats (product_id/deal_id or product/deal objects)
    product_id = data.get("product_id") or (data.get("product", {}).get("id") if isinstance(data.get("product"), dict) else None)
    deal_id = data.get("deal_id") or (data.get("deal", {}).get("id") if isinstance(data.get("deal"), dict) else None)
    
    workflow_result["test_data"]["product_id"] = product_id
    workflow_result["test_data"]["deal_id"] = deal_id
    
    if deal_id:
        test_data_to_cleanup["deals"].append(deal_id)
    if product_id:
        test_data_to_cleanup["products"].append(product_id)
    
    print_success(f"Product created: product_id={product_id}, deal_id={deal_id} ({duration:.0f}ms)")
    
    # Step 2: Update MOQ
    print_step(2, 4, "Updating MOQ...")
    if deal_id:
        # FIX: Use PATCH endpoint with UpdateDealRequest format
        success, data, error, duration = api_call("PATCH", f"/products/deal/{deal_id}", headers, json_data={"moq": 5})
        workflow_result["steps"].append({
            "step": 2,
            "action": "Update MOQ",
            "success": success,
            "error": error,
            "duration": duration
        })
        workflow_result["steps"].append({
            "step": 2,
            "action": "Update MOQ",
            "success": success,
            "error": error,
            "duration": duration
        })
        
        if success:
            print_success(f"MOQ updated to 5 ({duration:.0f}ms)")
        else:
            print_warning(f"MOQ update failed: {error} - continuing")
    
    # Step 3: View Product Details
    print_step(3, 4, "Viewing product details...")
    success, data, error, duration = api_call("GET", f"/products?deal_id={deal_id}" if deal_id else "/products", headers)
    workflow_result["steps"].append({
        "step": 3,
        "action": "View Product",
        "success": success,
        "error": error,
        "duration": duration
    })
    
    if success:
        print_success(f"Product details retrieved ({duration:.0f}ms)")
    else:
        print_warning(f"Failed to view product: {error} - continuing")
    
    # Step 4: Delete Product
    print_step(4, 4, "Deleting product...")
    if deal_id:
        # FIX: Use DELETE endpoint for deal
        success, data, error, duration = api_call("DELETE", f"/products/deal/{deal_id}", headers)
        workflow_result["steps"].append({
            "step": 4,
            "action": "Delete Product",
            "success": success,
            "error": error,
            "duration": duration
        })
        
        if success:
            print_success(f"Product deleted ({duration:.0f}ms)")
            if deal_id in test_data_to_cleanup["deals"]:
                test_data_to_cleanup["deals"].remove(deal_id)
            workflow_result["success"] = True
        else:
            print_error(f"Failed to delete product: {error}")
    
    workflow_result["duration"] = (time.time() - start_time) * 1000
    return workflow_result

# ============================================================================
# CLEANUP
# ============================================================================

def cleanup_test_data(headers: Dict):
    """Clean up all test data created during workflows."""
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}🧹 CLEANING UP TEST DATA{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")
    
    cleaned = 0
    
    # Clean up deals (which will cascade to products)
    for deal_id in test_data_to_cleanup["deals"]:
        try:
            api_call("DELETE", f"/products/deal/{deal_id}", headers, timeout=10)
            cleaned += 1
        except:
            pass
    
    # Clean up suppliers
    for supplier_id in test_data_to_cleanup["suppliers"]:
        try:
            api_call("DELETE", f"/suppliers/{supplier_id}", headers, timeout=10)
            cleaned += 1
        except:
            pass
    
    # Clean up favorites (already removed in workflow)
    test_data_to_cleanup["favorites"] = []
    
    if cleaned > 0:
        print_success(f"Cleaned up {cleaned} test items")
    else:
        print_info("No test data to clean up")

# ============================================================================
# MAIN
# ============================================================================

def get_auth_token() -> Optional[str]:
    """Get authentication token using multiple methods (same as production_test.py)."""
    # Method 1: Use TEST_TOKEN if provided
    if TEST_TOKEN and TEST_TOKEN.strip():
        token = TEST_TOKEN.strip()
        try:
            # Check if token is expired (decode without verification)
            try:
                import jwt
                decoded = jwt.decode(token, options={"verify_signature": False})
                import time
                exp = decoded.get("exp", 0)
                now = int(time.time())
                if exp < now:
                    print_warning(f"TEST_TOKEN is EXPIRED (expired {now - exp} seconds ago)")
                else:
                    expires_in = exp - now
                    print_info(f"Token expires in {expires_in // 3600}h {(expires_in % 3600) // 60}m")
            except:
                pass  # Can't decode, try anyway
            
            # Try /products endpoint first (simpler, doesn't require full user object)
            response = requests.get(
                f"{BASE_URL}/products?limit=1",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                return token
        except Exception as e:
            print_warning(f"TEST_TOKEN failed: {e}")
    
    # Method 2: Try Supabase Auth API if credentials provided (and not placeholder)
    if SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_ANON_KEY != "your_anon_key_here" and TEST_EMAIL and TEST_PASSWORD:
        try:
            supabase_url = SUPABASE_URL.rstrip('/')
            if not supabase_url.startswith('http'):
                supabase_url = f"https://{supabase_url}"
            
            auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
            headers = {
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            response = requests.post(auth_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    print_success("Authentication successful via Supabase API")
                    return token
            else:
                print_warning(f"Supabase auth returned {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print_warning(f"Supabase auth API failed: {e}")
    
    # If we have email/password but no Supabase URL, try the known Supabase URL
    if TEST_EMAIL and TEST_PASSWORD:
        known_supabase_urls = [
            "https://fpihznamnwlvkaarnlbc.supabase.co",
            "https://habexa.supabase.co"
        ]
        for supabase_url in known_supabase_urls:
            try:
                auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
                headers = {
                    "apikey": SUPABASE_ANON_KEY if SUPABASE_ANON_KEY != "your_anon_key_here" else "",
                    "Content-Type": "application/json"
                }
                if not headers["apikey"]:
                    continue  # Skip if no anon key
                
                payload = {
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD
                }
                
                response = requests.post(auth_url, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("access_token")
                    if token:
                        print_success(f"Authentication successful via {supabase_url}")
                        return token
            except:
                continue
    
    return None

def main():
    """Run all workflow tests."""
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}🔄 COMPREHENSIVE WORKFLOW TESTING{RESET}")
    print(f"{CYAN}{'='*70}{RESET}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}\n")
    
    # Get auth token
    print_info("Authenticating...")
    token = get_auth_token()
    if not token:
        print_error("Failed to authenticate. Please set TEST_TOKEN or SUPABASE credentials in .env.test")
        return 1
    
    print_success("Authentication successful")
    headers = {"Authorization": f"Bearer {token}"}
    
    workflows = [
        workflow_1_product_analysis,
        workflow_2_csv_upload,
        workflow_3_favorites,
        workflow_4_bulk_actions,
        workflow_5_product_management
    ]
    
    results = []
    
    for workflow_func in workflows:
        try:
            result = workflow_func(headers)
            results.append(result)
        except Exception as e:
            print_error(f"Workflow failed with exception: {e}")
            results.append({
                "name": workflow_func.__name__,
                "success": False,
                "error": str(e)
            })
    
    # Cleanup
    cleanup_test_data(headers)
    
    # Generate report
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}📊 WORKFLOW TEST RESULTS{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")
    
    total_workflows = len(results)
    successful_workflows = sum(1 for r in results if r.get("success", False))
    total_steps = sum(len(r.get("steps", [])) for r in results)
    successful_steps = sum(sum(1 for s in r.get("steps", []) if s.get("success", False)) for r in results)
    
    print(f"{BLUE}Workflow Summary:{RESET}")
    print(f"  Total Workflows: {total_workflows}")
    print(f"  ✅ Successful: {successful_workflows}")
    print(f"  ❌ Failed: {total_workflows - successful_workflows}")
    print(f"  Total Steps: {total_steps}")
    print(f"  ✅ Successful Steps: {successful_steps}")
    print(f"  ❌ Failed Steps: {total_steps - successful_steps}\n")
    
    print(f"{BLUE}Workflow Details:{RESET}\n")
    for result in results:
        name = result.get("name", "Unknown")
        success = result.get("success", False)
        duration = result.get("duration", 0)
        steps = result.get("steps", [])
        
        status_icon = "✅" if success else "❌"
        status_color = GREEN if success else RED
        
        print(f"{status_color}{status_icon} {name}{RESET} ({duration:.0f}ms)")
        for step in steps:
            step_success = step.get("success", False)
            step_icon = "✅" if step_success else "❌"
            step_color = GREEN if step_success else RED
            print(f"  {step_color}{step_icon} {step.get('action', 'Unknown')}{RESET} ({step.get('duration', 0):.0f}ms)")
            if not step_success and step.get("error"):
                print(f"    {RED}Error: {step['error']}{RESET}")
        print()
    
    # Calculate score
    workflow_score = (successful_workflows / total_workflows * 100) if total_workflows > 0 else 0
    step_score = (successful_steps / total_steps * 100) if total_steps > 0 else 0
    overall_score = (workflow_score * 0.6 + step_score * 0.4)  # Weighted average
    
    print(f"{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}🎯 PRODUCTION READINESS ASSESSMENT{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")
    
    print(f"{BLUE}Workflow Score: {workflow_score:.1f}/100{RESET}")
    print(f"{BLUE}Step Score: {step_score:.1f}/100{RESET}")
    print(f"{BLUE}Overall Score: {overall_score:.1f}/100{RESET}\n")
    
    # Recommendation
    if overall_score >= 90:
        print_success("🎉 PRODUCTION READY - Excellent workflow coverage!")
        recommendation = "GO"
    elif overall_score >= 80:
        print_success("✅ PRODUCTION READY - Good workflow coverage")
        recommendation = "GO"
    elif overall_score >= 70:
        print_warning("⚠️  MOSTLY READY - Some workflows need attention")
        recommendation = "CONDITIONAL GO"
    else:
        print_error("❌ NOT READY - Multiple workflow failures")
        recommendation = "NO-GO"
    
    print(f"\n{CYAN}RECOMMENDATION: {recommendation}{RESET}\n")
    
    # Save report
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "workflows": results,
        "summary": {
            "total_workflows": total_workflows,
            "successful_workflows": successful_workflows,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "workflow_score": workflow_score,
            "step_score": step_score,
            "overall_score": overall_score
        },
        "recommendation": recommendation
    }
    
    filename = f"workflow_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"{BLUE}Detailed report saved to: {filename}{RESET}\n")
    
    return 0 if recommendation in ["GO", "CONDITIONAL GO"] else 1

if __name__ == "__main__":
    exit(main())

