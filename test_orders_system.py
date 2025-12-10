"""
Test Orders System - Complete Purchase Request Workflow
"""
import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test
env_test_path = Path(__file__).parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path)
else:
    load_dotenv()

TOKEN = os.getenv("TEST_TOKEN", "").replace("Bearer ", "").strip()
BASE_URL = os.getenv("BASE_URL", "https://habexa-backend-w5u5.onrender.com/api/v1")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def test_endpoint(method, path, data=None, expected_status=200):
    """Test an endpoint and return result"""
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        
        success = response.status_code == expected_status
        return success, response.status_code, response.json() if response.status_code == 200 else response.text
    except Exception as e:
        return False, 0, str(e)

print_section("ORDERS SYSTEM TEST")

# Test 1: List Orders (should work even if empty)
print("1. Testing GET /orders...")
success, status, data = test_endpoint("GET", "/orders")
if success:
    orders = data if isinstance(data, list) else []
    print(f"   ✅ SUCCESS - Found {len(orders)} orders")
else:
    print(f"   ❌ FAILED - Status: {status}")
    print(f"   Response: {str(data)[:200]}")

# Test 2: Get Suppliers
print("\n2. Getting suppliers...")
success, status, data = test_endpoint("GET", "/suppliers")
supplier_id = None
if success and isinstance(data, list) and len(data) > 0:
    supplier_id = data[0].get("id")
    print(f"   ✅ Found supplier: {supplier_id}")
elif success:
    print(f"   ⚠️  No suppliers found")
else:
    print(f"   ❌ Failed: {status}")

# Test 3: Get Products (deals)
print("\n3. Getting products...")
success, status, data = test_endpoint("GET", "/products?limit=2")
deal_ids = []
if success:
    if isinstance(data, dict):
        deals = data.get("deals", [])
    else:
        deals = data if isinstance(data, list) else []
    
    deal_ids = [d.get("deal_id") or d.get("id") for d in deals[:2] if d.get("deal_id") or d.get("id")]
    print(f"   ✅ Found {len(deal_ids)} deals")
else:
    print(f"   ❌ Failed: {status}")

# Test 4: Create Order
if deal_ids:
    print("\n4. Creating order...")
    create_data = {
        "supplier_id": supplier_id,
        "product_ids": deal_ids,
        "notes": "Test order - 5% discount negotiated"
    }
    success, status, data = test_endpoint("POST", "/orders", create_data, expected_status=200)
    order_id = None
    
    if success:
        order_id = data.get("id") if isinstance(data, dict) else None
        print(f"   ✅ Order created: {order_id}")
        print(f"   Items: {data.get('items_count', 0)}")
        print(f"   Total: ${data.get('total_amount', 0):.2f}")
        
        # Test 5: Update Item
        if data.get("items") and len(data["items"]) > 0:
            item = data["items"][0]
            product_id = item.get("product_id")
            
            print("\n5. Updating item quantity and discount...")
            update_data = {"quantity": 100, "discount": 5.00}
            success, status, result = test_endpoint("PUT", f"/orders/{order_id}/items/{product_id}", update_data)
            
            if success:
                print(f"   ✅ Updated: quantity=100, discount=$5.00")
                print(f"   New total: ${result.get('order_total', 0):.2f}")
            else:
                print(f"   ❌ Failed: {status} - {str(result)[:200]}")
        
        # Test 6: Get Order Details
        print(f"\n6. Getting order details...")
        success, status, order_details = test_endpoint("GET", f"/orders/{order_id}")
        
        if success:
            print(f"   ✅ Order details retrieved")
            print(f"   Status: {order_details.get('status')}")
            print(f"   Total cost: ${order_details.get('total_cost', 0):.2f}")
            print(f"   Total discount: ${order_details.get('total_discount', 0):.2f}")
        else:
            print(f"   ❌ Failed: {status}")
        
        # Test 7: Update Status
        print(f"\n7. Updating order status to 'sent'...")
        status_data = {"status": "sent"}
        success, status, result = test_endpoint("PATCH", f"/orders/{order_id}", status_data)
        
        if success:
            print(f"   ✅ Status updated to 'sent'")
        else:
            print(f"   ❌ Failed: {status}")
        
        # Test 8: List Orders Again
        print(f"\n8. Listing all orders...")
        success, status, orders = test_endpoint("GET", "/orders")
        
        if success:
            orders_list = orders if isinstance(orders, list) else []
            print(f"   ✅ Found {len(orders_list)} orders")
        else:
            print(f"   ❌ Failed: {status}")
    else:
        print(f"   ❌ Failed to create order: {status}")
        print(f"   Response: {str(data)[:300]}")
else:
    print("\n⚠️  Cannot test order creation - no products available")

print_section("TEST COMPLETE")

