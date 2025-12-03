#!/usr/bin/env python3
"""
Cleanup test data created by seed_test_data.py
Deletes all test data to restore database to clean state.
"""
import sys
import os
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.supabase_client import supabase

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

def cleanup_test_data():
    """Delete all test data."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BLUE}CLEANING UP TEST DATA{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    # Load test data IDs
    try:
        with open("test_data_ids.json", "r") as f:
            data = json.load(f)
            user_id = data.get("user_id")
            seeded_ids = data.get("seeded_ids", {})
    except FileNotFoundError:
        print_error("test_data_ids.json not found. Cleaning up by email instead...")
        user_id = None
        seeded_ids = {}
        
        # Find test user by email
        try:
            result = supabase.table("profiles")\
                .select("id")\
                .eq("email", "test@habexa.com")\
                .limit(1)\
                .execute()
            if result.data:
                user_id = result.data[0]["id"]
        except:
            pass
    
    if not user_id:
        print_error("Could not find test user. Nothing to clean up.")
        return
    
    deleted_counts = {}
    
    try:
        # Delete in reverse order (child tables first)
        tables = [
            ("watchlist", "watchlist"),
            ("jobs", "jobs"),
            ("analyses", "analyses"),
            ("product_sources", "product_sources"),
            ("products", "products"),
            ("brands", "brands"),
            ("suppliers", "suppliers"),
        ]
        
        for key, table_name in tables:
            print_step(f"Deleting {table_name}...")
            try:
                if key in seeded_ids and seeded_ids[key]:
                    # Delete specific IDs
                    result = supabase.table(table_name)\
                        .delete()\
                        .in_("id", seeded_ids[key])\
                        .execute()
                    deleted_counts[key] = len(seeded_ids[key])
                else:
                    # Delete by user_id
                    result = supabase.table(table_name)\
                        .delete()\
                        .eq("user_id", user_id)\
                        .execute()
                    deleted_counts[key] = "all"
                print_success(f"Deleted {table_name}")
            except Exception as e:
                print_error(f"Error deleting {table_name}: {e}")
        
        # Delete test user profile
        print_step("Deleting test user profile...")
        try:
            supabase.table("profiles")\
                .delete()\
                .eq("id", user_id)\
                .execute()
            print_success("Deleted test user profile")
        except Exception as e:
            print_error(f"Error deleting test user: {e}")
        
        # Clean up the IDs file
        try:
            os.remove("test_data_ids.json")
            print_success("Removed test_data_ids.json")
        except:
            pass
        
        print(f"\n{Colors.GREEN}{'='*80}{Colors.RESET}")
        print(f"{Colors.GREEN}CLEANUP COMPLETE!{Colors.RESET}")
        print(f"{Colors.GREEN}{'='*80}{Colors.RESET}\n")
        
        total = sum(1 for v in deleted_counts.values() if isinstance(v, int))
        print(f"Total records deleted: {total}")
        for key, count in deleted_counts.items():
            print(f"  - {key}: {count}")
        
    except Exception as e:
        print_error(f"Error during cleanup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_test_data()

