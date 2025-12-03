#!/usr/bin/env python3
"""
Seed test data for Supabase endpoints testing.
Creates test data in all main tables to verify endpoints work.
"""
import sys
import os
import asyncio
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.supabase_client import supabase
from app.core.config import settings

# Test user ID - you'll need to set this to a real user ID from your database
# Or we can create a test user
TEST_USER_ID = None

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_step(msg):
    print(f"{Colors.BLUE}→ {msg}{Colors.RESET}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def get_test_user_id():
    """Get an existing user from the database to use for testing."""
    global TEST_USER_ID
    
    # Try to find any existing user
    try:
        result = supabase.table("profiles")\
            .select("id, email")\
            .limit(1)\
            .execute()
        
        if result.data:
            TEST_USER_ID = result.data[0]["id"]
            print_success(f"Using existing user: {result.data[0].get('email', 'unknown')} ({TEST_USER_ID})")
            return TEST_USER_ID
    except Exception as e:
        print_error(f"Error finding user: {e}")
    
    # If no users found, prompt for user ID
    print(f"{Colors.YELLOW}No users found in database.{Colors.RESET}")
    print(f"{Colors.YELLOW}Please provide a user ID to use for testing, or create a user first.{Colors.RESET}")
    user_input = input(f"{Colors.BLUE}Enter user ID (or press Enter to skip): {Colors.RESET}").strip()
    
    if user_input:
        TEST_USER_ID = user_input
        print_success(f"Using provided user ID: {TEST_USER_ID}")
        return TEST_USER_ID
    
    return None

def seed_data():
    """Seed test data into all tables."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BLUE}SEEDING TEST DATA{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    user_id = get_test_user_id()
    if not user_id:
        print_error("Could not get/create test user. Exiting.")
        return None
    
    seeded_ids = {
        "suppliers": [],
        "products": [],
        "product_sources": [],
        "analyses": [],
        "jobs": [],
        "brands": [],
        "orders": [],
        "watchlist": []
    }
    
    try:
        # 1. Seed Suppliers (use unique names to avoid conflicts)
        print_step("Seeding suppliers...")
        supplier_ids = []
        import time
        timestamp = int(time.time())
        for i in range(3):
            supplier_id = str(uuid.uuid4())
            supplier_name = f"Test Supplier {i+1} - {timestamp}"
            result = supabase.table("suppliers").insert({
                "id": supplier_id,
                "user_id": user_id,
                "name": supplier_name,
                "email": f"supplier{i+1}-{timestamp}@test.com",
                "is_active": True
            }).execute()
            if result.data:
                supplier_ids.append(supplier_id)
                seeded_ids["suppliers"].append(supplier_id)
        print_success(f"Created {len(supplier_ids)} suppliers")
        
        # 2. Seed Brands (use upsert to handle existing)
        print_step("Seeding brands...")
        brand_ids = []
        for brand_name in ["Nike", "Sony", "Apple"]:
            # Check if exists first
            existing = supabase.table("brands")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("name", brand_name)\
                .limit(1)\
                .execute()
            
            if existing.data:
                brand_id = existing.data[0]["id"]
                brand_ids.append(brand_id)
                seeded_ids["brands"].append(brand_id)
            else:
                result = supabase.table("brands").insert({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "name": brand_name,
                    "is_ungated": False
                }).execute()
                if result.data:
                    brand_ids.append(result.data[0]["id"])
                    seeded_ids["brands"].append(result.data[0]["id"])
        print_success(f"Got/created {len(brand_ids)} brands")
        
        # 3. Seed Products (check for existing first)
        print_step("Seeding products...")
        product_ids = []
        test_asins = ["B08N5WRWNW", "B07VRZ8TK3", "B01N81A0SU"]
        import time
        timestamp = int(time.time())
        for i, asin in enumerate(test_asins):
            # Check if product exists
            existing = supabase.table("products")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("asin", asin)\
                .limit(1)\
                .execute()
            
            if existing.data:
                product_id = existing.data[0]["id"]
                product_ids.append(product_id)
                seeded_ids["products"].append(product_id)
            else:
                product_id = str(uuid.uuid4())
                result = supabase.table("products").insert({
                    "id": product_id,
                    "user_id": user_id,
                    "asin": asin,
                    "title": f"Test Product {i+1} - {timestamp}",
                    "status": "pending",
                    "brand_name": ["Nike", "Sony", "Apple"][i] if i < 3 else None
                }).execute()
                if result.data:
                    product_ids.append(product_id)
                    seeded_ids["products"].append(product_id)
        print_success(f"Got/created {len(product_ids)} products")
        
        # 4. Seed Product Sources (deals) - NO user_id column, gets it from product
        print_step("Seeding product sources...")
        source_ids = []
        for i, product_id in enumerate(product_ids):
            if i < len(supplier_ids):
                source_id = str(uuid.uuid4())
                result = supabase.table("product_sources").insert({
                    "id": source_id,
                    "product_id": product_id,
                    "supplier_id": supplier_ids[i],
                    "buy_cost": 10.0 + (i * 5),
                    "moq": 1 + i,
                    "stage": "new",
                    "source": "test_seed",
                    "is_active": True
                }).execute()
                if result.data:
                    source_ids.append(source_id)
                    seeded_ids["product_sources"].append(source_id)
        print_success(f"Created {len(source_ids)} product sources")
        
        # 5. Seed Analyses
        print_step("Seeding analyses...")
        analysis_ids = []
        for i, product_id in enumerate(product_ids):
            if i < len(supplier_ids):
                analysis_id = str(uuid.uuid4())
                result = supabase.table("analyses").insert({
                    "id": analysis_id,
                    "user_id": user_id,
                    "asin": test_asins[i],
                    "supplier_id": supplier_ids[i],
                    "analysis_data": {},
                    "sell_price": 25.0 + (i * 5),
                    "fees_total": 5.0 + i,
                    "fees_referral": 3.0 + i,
                    "fees_fba": 2.0 + i,
                    "title": f"Test Product {i+1}",
                    "brand": ["Nike", "Sony", "Apple"][i] if i < 3 else None
                }).execute()
                if result.data:
                    analysis_ids.append(analysis_id)
                    seeded_ids["analyses"].append(analysis_id)
        print_success(f"Created {len(analysis_ids)} analyses")
        
        # 6. Seed Jobs (check schema - may not have error_items/success_items)
        print_step("Seeding jobs...")
        job_ids = []
        for i in range(2):
            job_id = str(uuid.uuid4())
            job_data = {
                "id": job_id,
                "user_id": user_id,
                "type": "single_analyze",
                "status": "completed",
                "total_items": 1,
                "processed_items": 1
            }
            # Only add if columns exist (will fail gracefully if not)
            result = supabase.table("jobs").insert(job_data).execute()
            if result.data:
                job_ids.append(job_id)
                seeded_ids["jobs"].append(job_id)
        print_success(f"Created {len(job_ids)} jobs")
        
        # 7. Seed Watchlist
        print_step("Seeding watchlist...")
        watchlist_ids = []
        for asin in test_asins[:2]:
            item_id = str(uuid.uuid4())
            result = supabase.table("watchlist").insert({
                "id": item_id,
                "user_id": user_id,
                "asin": asin,
                "target_price": 20.0,
                "notify_on_price_drop": True
            }).execute()
            if result.data:
                watchlist_ids.append(item_id)
                seeded_ids["watchlist"].append(item_id)
        print_success(f"Created {len(watchlist_ids)} watchlist items")
        
        print(f"\n{Colors.GREEN}{'='*80}{Colors.RESET}")
        print(f"{Colors.GREEN}SEEDING COMPLETE!{Colors.RESET}")
        print(f"{Colors.GREEN}{'='*80}{Colors.RESET}\n")
        
        total = sum(len(ids) for ids in seeded_ids.values())
        print(f"Total records created: {total}")
        print(f"  - Suppliers: {len(seeded_ids['suppliers'])}")
        print(f"  - Brands: {len(seeded_ids['brands'])}")
        print(f"  - Products: {len(seeded_ids['products'])}")
        print(f"  - Product Sources: {len(seeded_ids['product_sources'])}")
        print(f"  - Analyses: {len(seeded_ids['analyses'])}")
        print(f"  - Jobs: {len(seeded_ids['jobs'])}")
        print(f"  - Watchlist: {len(seeded_ids['watchlist'])}\n")
        
        return seeded_ids, user_id
        
    except Exception as e:
        print_error(f"Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        return None, user_id

if __name__ == "__main__":
    result = seed_data()
    if result:
        seeded_ids, user_id = result
        print(f"\n{Colors.YELLOW}Test User ID: {user_id}{Colors.RESET}")
        print(f"{Colors.YELLOW}To clean up, run: python3 cleanup_test_data.py{Colors.RESET}\n")
        
        # Save IDs to file for cleanup
        import json
        with open("test_data_ids.json", "w") as f:
            json.dump({"user_id": user_id, "seeded_ids": seeded_ids}, f, indent=2)
        print_success("Saved test data IDs to test_data_ids.json")

