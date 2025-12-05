#!/usr/bin/env python3
"""
Detailed Keepa structure inspection - find where 365-day lows are stored
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.services.keepa_client import keepa_client

async def test_keepa_detailed():
    """Inspect Keepa response structure in detail."""
    asin = "B0CV4FL9WM"
    
    print("=" * 80)
    print(f"KEEPA DETAILED INSPECTION - {asin}")
    print("=" * 80)
    print()
    
    # Get raw Keepa data
    raw_data = await keepa_client.get_products_raw([asin], domain=1, days=365)
    
    if asin not in raw_data:
        print("❌ ASIN not found in response")
        return
    
    product = raw_data[asin]
    stats = product.get("stats", {})
    
    print("📊 STATS STRUCTURE:")
    print("-" * 80)
    
    # Check min/max fields
    print(f"stats.min type: {type(stats.get('min'))}")
    print(f"stats.min value: {stats.get('min')}")
    print()
    
    print(f"stats.max type: {type(stats.get('max'))}")
    print(f"stats.max value: {stats.get('max')}")
    print()
    
    print(f"stats.minInInterval type: {type(stats.get('minInInterval'))}")
    print(f"stats.minInInterval value: {stats.get('minInInterval')}")
    print()
    
    print(f"stats.maxInInterval type: {type(stats.get('maxInInterval'))}")
    print(f"stats.maxInInterval value: {stats.get('maxInInterval')}")
    print()
    
    # Check stats.365
    stats_365 = stats.get("365", {})
    print(f"stats.365 type: {type(stats_365)}")
    print(f"stats.365 value: {stats_365}")
    print()
    
    # Check if stats.365 is actually a list or different structure
    if isinstance(stats_365, dict):
        print(f"stats.365 is dict with {len(stats_365)} keys")
        if len(stats_365) > 0:
            print(f"First 5 keys: {list(stats_365.keys())[:5]}")
    elif isinstance(stats_365, list):
        print(f"stats.365 is list with {len(stats_365)} items")
        if len(stats_365) > 0:
            print(f"First item: {stats_365[0]}")
    else:
        print(f"stats.365 is {type(stats_365)}: {stats_365}")
    print()
    
    # Check current array
    current = stats.get("current", [])
    print(f"stats.current type: {type(current)}")
    print(f"stats.current length: {len(current) if isinstance(current, list) else 'N/A'}")
    if isinstance(current, list) and len(current) > 0:
        print(f"stats.current[0:5]: {current[:5]}")
    print()
    
    # Check CSV field (might have historical data)
    csv = product.get("csv", [])
    print(f"csv type: {type(csv)}")
    print(f"csv length: {len(csv) if isinstance(csv, list) else 'N/A'}")
    if isinstance(csv, list) and len(csv) > 0:
        print(f"csv[0] type: {type(csv[0])}")
        print(f"csv[0] (first 100 chars): {str(csv[0])[:100] if csv[0] else 'Empty'}")
    print()
    
    # Check buyBoxStats
    buyBoxStats = stats.get("buyBoxStats", {})
    print(f"buyBoxStats type: {type(buyBoxStats)}")
    if isinstance(buyBoxStats, dict):
        print(f"buyBoxStats keys: {list(buyBoxStats.keys())[:10]}")
    print()
    
    # Save full product to file for inspection
    with open("keepa_raw_response.json", "w") as f:
        json.dump(product, f, indent=2, default=str)
    print("💾 Full response saved to keepa_raw_response.json")
    print()
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_keepa_detailed())

