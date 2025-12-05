#!/usr/bin/env python3
"""
Debug Keepa 365-day extraction - see actual API response structure
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.services.keepa_client import keepa_client

async def test_keepa_extraction():
    """Test Keepa raw data extraction."""
    asins = ["B0CV4FL9WM", "B0CV4FN2DN"]
    
    print("=" * 80)
    print("KEEPA RAW DATA INSPECTION")
    print("=" * 80)
    print()
    
    # Get raw Keepa data
    raw_data = await keepa_client.get_products_raw(asins, domain=1, days=365)
    
    for asin in asins:
        if asin in raw_data:
            product = raw_data[asin]
            
            print(f"ASIN: {asin}")
            print("-" * 80)
            
            # Check top-level keys
            print(f"Top-level keys: {list(product.keys())[:20]}")
            print()
            
            # Check stats structure
            stats = product.get("stats", {})
            print(f"Stats keys: {list(stats.keys()) if isinstance(stats, dict) else 'Not a dict'}")
            print()
            
            # Check stats.365
            stats_365 = stats.get("365", {}) if isinstance(stats, dict) else {}
            print(f"stats.365 type: {type(stats_365)}")
            print(f"stats.365 keys: {list(stats_365.keys())[:20] if isinstance(stats_365, dict) else 'Not a dict'}")
            print()
            
            # Check for min fields
            if isinstance(stats_365, dict):
                print("Looking for min fields:")
                for key in stats_365.keys():
                    if 'MIN' in str(key).upper() or 'min' in str(key).lower():
                        print(f"  Found: {key} = {stats_365[key]}")
                print()
            
            # Check offers
            offers = product.get("offers", [])
            print(f"Offers count: {len(offers) if isinstance(offers, list) else 'Not a list'}")
            if offers and len(offers) > 0:
                print(f"First offer keys: {list(offers[0].keys())[:10] if isinstance(offers[0], dict) else 'Not a dict'}")
                print(f"First offer isFBA: {offers[0].get('isFBA', 'N/A')}")
            print()
            
            # Show full stats.365 structure (truncated)
            if isinstance(stats_365, dict):
                print("Full stats.365 structure (first 10 keys):")
                for i, (key, value) in enumerate(list(stats_365.items())[:10]):
                    print(f"  {key}: {type(value).__name__} = {str(value)[:100]}")
            print()
            
            print("=" * 80)
            print()

if __name__ == "__main__":
    asyncio.run(test_keepa_extraction())

