#!/usr/bin/env python3
"""
Diagnostic script to check file upload data storage.

Run this to see:
1. What products were created from your upload
2. Which ones have API data stored
3. What's missing
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def check_upload_data(user_id: str = None, limit: int = 50):
    """
    Check what data is stored for recent uploads.
    """
    print("=" * 80)
    print("FILE UPLOAD DATA DIAGNOSTIC")
    print("=" * 80)
    print()
    
    # Get recent products
    query = supabase.table("products").select(
        "id, asin, upc, title, supplier_title, "
        "sp_api_raw_response, keepa_raw_response, "
        "sp_api_last_fetched, keepa_last_fetched, "
        "asin_status, created_at, user_id"
    ).order("created_at", desc=True).limit(limit)
    
    if user_id:
        query = query.eq("user_id", user_id)
    
    result = query.execute()
    
    if not result.data:
        print("❌ No products found")
        return
    
    products = result.data
    print(f"📦 Found {len(products)} recent products\n")
    
    # Analyze data
    stats = {
        "total": len(products),
        "with_asin": 0,
        "with_sp_api": 0,
        "with_keepa": 0,
        "with_both": 0,
        "missing_all": 0,
        "pending_asin": 0,
    }
    
    missing_data = []
    
    for p in products:
        asin = p.get("asin")
        has_sp = bool(p.get("sp_api_raw_response"))
        has_keepa = bool(p.get("keepa_raw_response"))
        asin_status = p.get("asin_status", "unknown")
        
        if asin and asin not in ["PENDING_", "Unknown"] and not str(asin).startswith("PENDING_"):
            stats["with_asin"] += 1
            
            if has_sp:
                stats["with_sp_api"] += 1
            if has_keepa:
                stats["with_keepa"] += 1
            if has_sp and has_keepa:
                stats["with_both"] += 1
            if not has_sp and not has_keepa:
                stats["missing_all"] += 1
                missing_data.append({
                    "asin": asin,
                    "upc": p.get("upc"),
                    "title": p.get("title") or p.get("supplier_title"),
                    "created_at": p.get("created_at"),
                    "sp_fetched": p.get("sp_api_last_fetched"),
                    "keepa_fetched": p.get("keepa_last_fetched"),
                })
        else:
            stats["pending_asin"] += 1
    
    # Print stats
    print("📊 STATISTICS:")
    print(f"   Total products: {stats['total']}")
    print(f"   With ASIN: {stats['with_asin']}")
    print(f"   Pending ASIN: {stats['pending_asin']}")
    print()
    print("📡 API DATA STORAGE:")
    print(f"   With SP-API data: {stats['with_sp_api']}")
    print(f"   With Keepa data: {stats['with_keepa']}")
    print(f"   With BOTH: {stats['with_both']}")
    print(f"   Missing ALL API data: {stats['missing_all']}")
    print()
    
    # Show missing data
    if missing_data:
        print(f"❌ {len(missing_data)} products with ASINs but NO API data:")
        print()
        for item in missing_data[:10]:  # Show first 10
            print(f"   ASIN: {item['asin']}")
            print(f"   UPC: {item['upc']}")
            print(f"   Title: {item['title']}")
            print(f"   Created: {item['created_at']}")
            print(f"   SP-API fetched: {item['sp_fetched'] or 'NEVER'}")
            print(f"   Keepa fetched: {item['keepa_fetched'] or 'NEVER'}")
            print()
        
        if len(missing_data) > 10:
            print(f"   ... and {len(missing_data) - 10} more")
        print()
    
    # Check recent uploads
    print("📁 RECENT UPLOADS:")
    jobs = supabase.table("jobs").select(
        "id, type, status, total_items, processed_items, "
        "created_at, metadata"
    ).eq("type", "upload").order("created_at", desc=True).limit(5).execute()
    
    if jobs.data:
        for job in jobs.data:
            print(f"   Job {job['id'][:8]}...")
            print(f"   Status: {job['status']}")
            print(f"   Items: {job.get('processed_items', 0)}/{job.get('total_items', 0)}")
            print(f"   Created: {job['created_at']}")
            print()
    else:
        print("   No upload jobs found")
    
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print("1. Check Celery logs for API call errors")
    print("2. Verify user_id is being passed to fetch_and_store_all_api_data")
    print("3. Check if API keys are configured correctly")
    print("4. Look for 'Failed to fetch' errors in logs")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnose file upload data storage")
    parser.add_argument("--user-id", help="Filter by user ID")
    parser.add_argument("--limit", type=int, default=50, help="Number of products to check")
    
    args = parser.parse_args()
    
    check_upload_data(user_id=args.user_id, limit=args.limit)

