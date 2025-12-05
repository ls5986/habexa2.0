#!/usr/bin/env python3
"""
Production Pipeline Test - Upload and process test.xlsx through all stages
Mimics exactly what production does.
"""
import requests
import time
import json
import os
from pathlib import Path

# Configuration
FRONTEND_URL = "https://habexa-frontend.onrender.com"
BACKEND_URL = "https://habexa-backend-w5u5.onrender.com"
EMAIL = "lindsey@letsclink.com"
PASSWORD = "Millie#5986"
EXCEL_FILE = "test.xlsx"

def login():
    """Login and get bearer token."""
    print("🔐 Logging in...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        token = data.get("access_token") or data.get("token")
        
        if not token:
            print(f"❌ No token in response: {data}")
            return None
        
        print(f"✅ Logged in successfully (token length: {len(token)})")
        return token
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def get_or_create_supplier(token):
    """Get or create a test supplier."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to get existing supplier
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/suppliers", headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            suppliers = data.get("suppliers") or data.get("data") or []
            if suppliers:
                supplier_id = suppliers[0]["id"]
                print(f"✅ Using existing supplier: {suppliers[0].get('name', 'Unknown')} ({supplier_id})")
                return supplier_id
    except Exception as e:
        print(f"⚠️  Error getting suppliers: {e}")
    
    # Create new supplier
    print("📦 Creating test supplier...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/suppliers",
            headers=headers,
            json={"name": "KEHE Test Supplier", "contact_email": "test@example.com"},
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            supplier_id = data.get("id") or data.get("supplier", {}).get("id")
            if supplier_id:
                print(f"✅ Created supplier: {supplier_id}")
                return supplier_id
        
        print(f"❌ Failed to create supplier: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error creating supplier: {e}")
    
    return None

def upload_file(token, supplier_id):
    """Upload Excel file."""
    print(f"\n📤 Uploading {EXCEL_FILE}...")
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ File not found: {EXCEL_FILE}")
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with open(EXCEL_FILE, 'rb') as f:
            files = {'file': (EXCEL_FILE, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            data = {'supplier_id': supplier_id}
            
            response = requests.post(
                f"{BACKEND_URL}/api/v1/products/upload",
                headers=headers,
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code not in [200, 201]:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        job_id = result.get("job_id")
        print(f"✅ File uploaded successfully")
        print(f"   Job ID: {job_id}")
        return job_id
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def poll_job_status(token, job_id):
    """Poll job status and show progress."""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n📊 Polling job status...")
    print("=" * 60)
    
    last_status = None
    last_progress = None
    max_polls = 300  # Max 10 minutes (300 * 2 seconds)
    poll_count = 0
    
    while poll_count < max_polls:
        try:
            response = requests.get(
                f"{BACKEND_URL}/api/v1/jobs/{job_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to get job status: {response.status_code} - {response.text}")
                break
        except Exception as e:
            print(f"❌ Error polling job: {e}")
            break
        
        job = response.json()
        status = job.get("status")
        progress = job.get("progress", {})
        current = progress.get("current", 0)
        total = progress.get("total", 0)
        success = progress.get("success", 0)
        errors = progress.get("errors", 0)
        
        # Show status changes
        if status != last_status:
            print(f"\n📌 Status: {status.upper()}")
            last_status = status
        
        # Show progress updates
        if current != last_progress:
            if total > 0:
                pct = (current / total) * 100
                print(f"   Progress: {current}/{total} ({pct:.1f}%) - ✅ {success} | ❌ {errors}")
            last_progress = current
        
        # Show metadata/stage info
        metadata = job.get("metadata", {})
        if metadata:
            if "stage" in metadata:
                print(f"   Stage: {metadata['stage']}")
            if "summary" in metadata:
                summary = metadata["summary"]
                if isinstance(summary, dict):
                    for key, value in summary.items():
                        print(f"   {key}: {value}")
        
        # Check if complete
        if status in ["completed", "failed"]:
            print(f"\n🏁 Job {status.upper()}")
            if status == "completed":
                result = job.get("result", {})
                if result:
                    print(f"   Result: {json.dumps(result, indent=2)}")
            if status == "failed":
                errors_list = job.get("errors", [])
                if errors_list:
                    print(f"   Errors: {errors_list}")
            break
        
        poll_count += 1
        time.sleep(2)  # Poll every 2 seconds
    
    if poll_count >= max_polls:
        print(f"\n⏱️  Timeout: Job still running after {max_polls * 2} seconds")
    
    return job

def check_products(token, supplier_id):
    """Check products created and their analysis status."""
    print(f"\n🔍 Checking products...")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get products for this supplier
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/products?supplier_id={supplier_id}&limit=100",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get products: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Error getting products: {e}")
        return
    
    deals = response.json().get("deals") or response.json().get("data") or []
    print(f"✅ Found {len(deals)} products")
    
    # Analyze products
    stats = {
        "total": len(deals),
        "with_asin": 0,
        "needs_asin": 0,
        "has_pricing": 0,
        "no_pricing": 0,
        "needs_review": 0,
        "manual_price": 0,
        "with_promo": 0,
        "stages": {}
    }
    
    print(f"\n📊 Product Analysis:")
    print("-" * 60)
    
    for deal in deals:
        # ASIN status
        asin_status = deal.get("asin_status", "found")
        if asin_status == "not_found":
            stats["needs_asin"] += 1
        else:
            stats["with_asin"] += 1
        
        # Analysis/pricing status
        analysis = deal.get("analysis") or {}
        pricing_status = analysis.get("pricing_status", "complete")
        
        if pricing_status == "no_pricing":
            stats["no_pricing"] += 1
            stats["needs_review"] += 1
            print(f"⚠️  {deal.get('asin', 'N/A')}: No pricing - {analysis.get('pricing_status_reason', 'unknown')}")
        elif pricing_status == "manual":
            stats["manual_price"] += 1
        else:
            stats["has_pricing"] += 1
        
        # Stage
        stage = deal.get("stage", "new")
        stats["stages"][stage] = stats["stages"].get(stage, 0) + 1
        
        # Promo
        if deal.get("has_promo"):
            stats["with_promo"] += 1
    
    # Print summary
    print(f"\n📈 Summary:")
    print(f"   Total Products: {stats['total']}")
    print(f"   With ASIN: {stats['with_asin']}")
    print(f"   Needs ASIN: {stats['needs_asin']}")
    print(f"   Has Pricing: {stats['has_pricing']}")
    print(f"   No Pricing: {stats['no_pricing']}")
    print(f"   Needs Review: {stats['needs_review']}")
    print(f"   Manual Price: {stats['manual_price']}")
    print(f"   With Promo: {stats['with_promo']}")
    print(f"\n   Stages:")
    for stage, count in stats["stages"].items():
        print(f"      {stage}: {count}")
    
    # Show sample products needing review
    if stats["no_pricing"] > 0:
        print(f"\n⚠️  Products Needing Review ({stats['no_pricing']}):")
        count = 0
        for deal in deals:
            analysis = deal.get("analysis") or {}
            if analysis.get("pricing_status") == "no_pricing":
                count += 1
                print(f"   {count}. ASIN: {deal.get('asin', 'N/A')}")
                print(f"      Title: {deal.get('title', 'N/A')[:50]}")
                print(f"      Reason: {analysis.get('pricing_status_reason', 'unknown')}")
                if analysis.get("fba_lowest_365d"):
                    print(f"      Keepa 365d low: ${analysis.get('fba_lowest_365d'):.2f}")
                if count >= 5:
                    print(f"      ... and {stats['no_pricing'] - 5} more")
                    break

def main():
    try:
        print("=" * 60)
        print("🚀 PRODUCTION PIPELINE TEST")
        print("=" * 60)
        print(f"File: {EXCEL_FILE}")
        print(f"Backend: {BACKEND_URL}")
        print()
        
        # Step 1: Login
        print("Step 1: Login...")
        token = login()
        if not token:
            print("❌ Login failed, exiting")
            return
        print()
        
        # Step 2: Get or create supplier
        print("Step 2: Get or create supplier...")
        supplier_id = get_or_create_supplier(token)
        if not supplier_id:
            print("❌ Failed to get/create supplier, exiting")
            return
        print()
        
        # Step 3: Upload file
        print("Step 3: Upload file...")
        job_id = upload_file(token, supplier_id)
        if not job_id:
            print("❌ Upload failed, exiting")
            return
        print()
        
        # Step 4: Poll job status
        print("Step 4: Poll job status...")
        job = poll_job_status(token, job_id)
        print()
        
        # Step 5: Check products
        if job and job.get("status") == "completed":
            print("Step 5: Check products...")
            time.sleep(3)  # Wait a bit for DB to sync
            check_products(token, supplier_id)
        else:
            print("⚠️  Job not completed, skipping product check")
        
        print("\n" + "=" * 60)
        print("✅ Test complete!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

