#!/usr/bin/env python3
"""
Debug script to check ASIN lookup status after CSV upload.

Run this after uploading a CSV to see:
1. Product records from database
2. Job records created
3. What the upload response should look like
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("ASIN LOOKUP DEBUG - Product Records")
print("=" * 80)

# 1. Get recent products with UPCs (last 10)
print("\n1️⃣ RECENT PRODUCTS WITH UPCs (last 10):")
print("-" * 80)

products = supabase.table("products")\
    .select("id, asin, upc, title, lookup_status, asin_status, status, created_at, user_id")\
    .not_.is_("upc", "null")\
    .neq("upc", "")\
    .order("created_at", desc=True)\
    .limit(10)\
    .execute()

if products.data:
    for p in products.data:
        print(f"""
Product ID: {p.get('id')}
  ASIN: {p.get('asin') or 'NULL'}
  UPC: {p.get('upc')}
  Title: {p.get('title') or 'N/A'}
  lookup_status: {p.get('lookup_status') or 'NULL'}
  asin_status: {p.get('asin_status') or 'NULL'}
  status: {p.get('status') or 'NULL'}
  Created: {p.get('created_at')}
  User ID: {p.get('user_id')}
""")
else:
    print("❌ No products found with UPCs")

# 2. Get products stuck in pending
print("\n2️⃣ PRODUCTS STUCK IN 'pending' LOOKUP STATUS:")
print("-" * 80)

pending = supabase.table("products")\
    .select("id, asin, upc, lookup_status, lookup_attempts, created_at")\
    .eq("lookup_status", "pending")\
    .not_.is_("upc", "null")\
    .neq("upc", "")\
    .limit(10)\
    .execute()

if pending.data:
    print(f"Found {len(pending.data)} products stuck in 'pending':")
    for p in pending.data:
        print(f"  - {p.get('id')}: UPC={p.get('upc')}, ASIN={p.get('asin')}, attempts={p.get('lookup_attempts', 0)}")
else:
    print("✅ No products stuck in pending")

# 3. Get recent ASIN lookup jobs
print("\n3️⃣ RECENT ASIN LOOKUP JOBS:")
print("-" * 80)

jobs = supabase.table("jobs")\
    .select("id, type, status, total_items, processed_items, progress, created_at, metadata, errors")\
    .eq("type", "asin_lookup")\
    .order("created_at", desc=True)\
    .limit(5)\
    .execute()

if jobs.data:
    for job in jobs.data:
        print(f"""
Job ID: {job.get('id')}
  Type: {job.get('type')}
  Status: {job.get('status')}
  Progress: {job.get('progress', 0)}% ({job.get('processed_items', 0)}/{job.get('total_items', 0)})
  Created: {job.get('created_at')}
  Metadata: {job.get('metadata')}
  Errors: {job.get('errors')}
""")
else:
    print("❌ No ASIN lookup jobs found")

# 4. Check for PENDING_ ASINs
print("\n4️⃣ PRODUCTS WITH PENDING_ ASINs:")
print("-" * 80)

pending_asins = supabase.table("products")\
    .select("id, asin, upc, lookup_status, created_at")\
    .like("asin", "PENDING_%")\
    .limit(10)\
    .execute()

if pending_asins.data:
    print(f"Found {len(pending_asins.data)} products with PENDING_ ASINs:")
    for p in pending_asins.data:
        print(f"  - {p.get('id')}: ASIN={p.get('asin')}, UPC={p.get('upc')}, lookup_status={p.get('lookup_status')}")
else:
    print("✅ No products with PENDING_ ASINs")

print("\n" + "=" * 80)
print("✅ Debug complete!")
print("=" * 80)
print("\nNext steps:")
print("1. Check Celery worker logs on Render (see instructions below)")
print("2. Check if job_id is returned in upload response")
print("3. Verify SP-API credentials are configured")

