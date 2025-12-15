#!/usr/bin/env python3
"""
Test ASIN across all Habexa APIs
Tests SP-API, Keepa, and internal endpoints to see what data is returned
"""

import asyncio
import json
import sys
from typing import Dict, Any

# Test ASIN - change this to any ASIN you want to test
TEST_ASIN = "B07VRZ8TK3"  # Change this to your test ASIN

async def test_sp_api_catalog(asin: str) -> Dict[str, Any]:
    """Test SP-API Catalog Items endpoint"""
    print("\n" + "="*80)
    print("📦 TESTING SP-API CATALOG ITEMS")
    print("="*80)
    
    try:
        from app.services.sp_api_client import sp_api_client
        
        result = await sp_api_client.get_catalog_item(asin, marketplace_id="ATVPDKIKX0DER")
        
        if result:
            print(f"✅ SP-API Catalog returned data for {asin}")
            print(f"\n📊 Response Structure:")
            print(f"   Keys: {list(result.keys())}")
            
            # Show key fields
            if 'summaries' in result:
                summary = result['summaries'][0] if result['summaries'] else {}
                print(f"\n📝 Summary Fields:")
                print(f"   - itemName: {summary.get('itemName')}")
                print(f"   - brandName: {summary.get('brandName')}")
                print(f"   - manufacturer: {summary.get('manufacturer')}")
                print(f"   - productGroup: {summary.get('productGroup')}")
                print(f"   - mainImage: {summary.get('mainImage', {}).get('link') if summary.get('mainImage') else None}")
            
            if 'attributes' in result:
                attrs = result['attributes']
                print(f"\n🏷️ Attributes Available:")
                print(f"   Keys: {list(attrs.keys())[:10]}...")  # First 10 keys
            
            if 'salesRanks' in result:
                print(f"\n📈 Sales Ranks:")
                print(f"   {result['salesRanks']}")
            
            return result
        else:
            print(f"❌ SP-API Catalog returned None for {asin}")
            return {}
            
    except Exception as e:
        print(f"❌ SP-API Catalog Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_sp_api_pricing(asin: str) -> Dict[str, Any]:
    """Test SP-API Competitive Pricing endpoint"""
    print("\n" + "="*80)
    print("💰 TESTING SP-API COMPETITIVE PRICING")
    print("="*80)
    
    try:
        from app.services.sp_api_client import sp_api_client
        
        result = await sp_api_client.get_competitive_pricing(asin, marketplace_id="ATVPDKIKX0DER")
        
        if result:
            print(f"✅ SP-API Pricing returned data for {asin}")
            print(f"\n📊 Response Structure:")
            print(f"   Keys: {list(result.keys())}")
            print(f"   - buy_box_price: {result.get('buy_box_price')}")
            print(f"   - lowest_price: {result.get('lowest_price')}")
            print(f"   - seller_count: {result.get('seller_count')}")
            print(f"   - fba_seller_count: {result.get('fba_seller_count')}")
            print(f"   - amazon_sells: {result.get('amazon_sells')}")
            return result
        else:
            print(f"❌ SP-API Pricing returned None for {asin}")
            return {}
            
    except Exception as e:
        print(f"❌ SP-API Pricing Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_keepa(asin: str) -> Dict[str, Any]:
    """Test Keepa API"""
    print("\n" + "="*80)
    print("📊 TESTING KEEPA API")
    print("="*80)
    
    try:
        from app.services.keepa_client import get_keepa_client
        
        client = get_keepa_client()
        if not client or not client.is_configured():
            print("❌ Keepa client not configured")
            return {}
        
        result = await client.get_product(asin, days=90)
        
        if result:
            print(f"✅ Keepa returned data for {asin}")
            print(f"\n📊 Response Structure:")
            print(f"   Keys: {list(result.keys())}")
            
            if 'current' in result:
                current = result['current']
                print(f"\n📝 Current Data:")
                print(f"   - price: {current.get('price')}")
                print(f"   - sales_rank: {current.get('sales_rank')}")
                print(f"   - rating: {current.get('rating')}")
                print(f"   - review_count: {current.get('review_count')}")
            
            if 'stats' in result:
                stats = result['stats']
                print(f"\n📈 Stats Available:")
                print(f"   Keys: {list(stats.keys())[:15]}...")  # First 15 keys
                print(f"   - salesRankDrops30: {stats.get('salesRankDrops30')}")
                print(f"   - offerCountFBA: {stats.get('offerCountFBA')}")
                print(f"   - offerCountFBM: {stats.get('offerCountFBM')}")
            
            return result
        else:
            print(f"❌ Keepa returned None for {asin}")
            return {}
            
    except Exception as e:
        print(f"❌ Keepa Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_keepa_batch(asin: str) -> Dict[str, Any]:
    """Test Keepa Batch API (what we actually use)"""
    print("\n" + "="*80)
    print("📦 TESTING KEEPA BATCH API")
    print("="*80)
    
    try:
        from app.services.keepa_client import get_keepa_client
        
        client = get_keepa_client()
        if not client or not client.is_configured():
            print("❌ Keepa client not configured")
            return {}
        
        result = await client.get_products_batch([asin], days=90, return_raw=True)
        
        if result:
            print(f"✅ Keepa Batch returned data for {asin}")
            print(f"\n📊 Response Structure:")
            print(f"   Keys: {list(result.keys())}")
            
            if 'products' in result and result['products']:
                product = result['products'][0]
                print(f"\n📝 Product Data:")
                print(f"   Keys: {list(product.keys())[:20]}...")  # First 20 keys
                print(f"   - asin: {product.get('asin')}")
                print(f"   - title: {product.get('title')}")
                print(f"   - brand: {product.get('brand')}")
                print(f"   - category: {product.get('category')}")
                print(f"   - productGroup: {product.get('productGroup')}")
                print(f"   - salesRank: {product.get('salesRank')}")
                print(f"   - offerCount: {product.get('offerCount')}")
                print(f"   - fbaOfferCount: {product.get('fbaOfferCount')}")
                print(f"   - rating: {product.get('rating')}")
                print(f"   - reviewCount: {product.get('reviewCount')}")
                print(f"   - hazmatType: {product.get('hazmatType')}")
                print(f"   - parentAsin: {product.get('parentAsin')}")
                
                if 'csv' in product:
                    csv = product['csv']
                    print(f"\n📊 CSV Data (price/rank history):")
                    print(f"   Length: {len(csv)} arrays")
                    if len(csv) > 0:
                        print(f"   csv[0] (Amazon price): {len(csv[0]) if isinstance(csv[0], list) else 'N/A'} data points")
                    if len(csv) > 1:
                        print(f"   csv[1] (New price): {len(csv[1]) if isinstance(csv[1], list) else 'N/A'} data points")
                    if len(csv) > 3:
                        print(f"   csv[3] (Sales rank): {len(csv[3]) if isinstance(csv[3], list) else 'N/A'} data points")
            
            return result
        else:
            print(f"❌ Keepa Batch returned None for {asin}")
            return {}
            
    except Exception as e:
        print(f"❌ Keepa Batch Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_api_batch_fetcher(asin: str) -> Dict[str, Any]:
    """Test the unified API batch fetcher"""
    print("\n" + "="*80)
    print("🔥 TESTING API BATCH FETCHER (Unified Service)")
    print("="*80)
    
    try:
        from app.services.api_batch_fetcher import fetch_api_data_for_asins
        
        # Use a test user ID (you'll need to provide a real one)
        # For testing, we'll just see what the function returns
        print(f"⚠️  Note: This requires a user_id. Testing structure only...")
        
        # Check what the function signature expects
        import inspect
        sig = inspect.signature(fetch_api_data_for_asins)
        print(f"\n📋 Function Signature:")
        print(f"   Parameters: {list(sig.parameters.keys())}")
        
        return {}
            
    except Exception as e:
        print(f"❌ API Batch Fetcher Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_field_extractor(asin: str) -> Dict[str, Any]:
    """Test what fields are extracted by our extractors"""
    print("\n" + "="*80)
    print("🔧 TESTING FIELD EXTRACTORS")
    print("="*80)
    
    try:
        from app.services.api_field_extractor import SPAPIExtractor, KeepaExtractor
        
        # Get SP-API data
        from app.services.sp_api_client import sp_api_client
        sp_data = await sp_api_client.get_catalog_item(asin, marketplace_id="ATVPDKIKX0DER")
        
        if sp_data:
            print(f"\n📦 SP-API Extractor:")
            extracted = SPAPIExtractor.extract_all(sp_data)
            print(f"   Extracted {len(extracted)} fields")
            print(f"   Keys: {list(extracted.keys())[:20]}...")
            print(f"\n   Sample Fields:")
            for key in ['title', 'brand', 'manufacturer', 'image_url', 'bsr', 'current_sales_rank', 'category']:
                if key in extracted:
                    print(f"   - {key}: {extracted[key]}")
        
        # Get Keepa data
        from app.services.keepa_client import get_keepa_client
        keepa_client = get_keepa_client()
        if keepa_client and keepa_client.is_configured():
            keepa_batch = await keepa_client.get_products_batch([asin], days=90, return_raw=True)
            if keepa_batch and 'products' in keepa_batch and keepa_batch['products']:
                product = keepa_batch['products'][0]
                print(f"\n📊 Keepa Extractor:")
                extracted = KeepaExtractor.extract_all({'products': [product]}, asin=asin)
                print(f"   Extracted {len(extracted)} fields")
                print(f"   Keys: {list(extracted.keys())[:20]}...")
                print(f"\n   Sample Fields:")
                for key in ['title', 'brand', 'manufacturer', 'image_url', 'current_sales_rank', 'bsr', 'category', 'fba_seller_count', 'seller_count']:
                    if key in extracted:
                        print(f"   - {key}: {extracted[key]}")
        
        return {}
            
    except Exception as e:
        print(f"❌ Field Extractor Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def main():
    """Run all tests"""
    asin = TEST_ASIN
    
    if len(sys.argv) > 1:
        asin = sys.argv[1]
    
    print("\n" + "="*80)
    print(f"🧪 TESTING ASIN: {asin}")
    print("="*80)
    print(f"\nThis will test all APIs to see what data is returned.")
    print(f"Change TEST_ASIN in the script or pass as argument: python test_asin_apis.py B07VRZ8TK3\n")
    
    # Run all tests
    results = {}
    
    results['sp_api_catalog'] = await test_sp_api_catalog(asin)
    results['sp_api_pricing'] = await test_sp_api_pricing(asin)
    results['keepa'] = await test_keepa(asin)
    results['keepa_batch'] = await test_keepa_batch(asin)
    results['field_extractor'] = await test_field_extractor(asin)
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"\n✅ SP-API Catalog: {'Success' if results['sp_api_catalog'] else 'Failed'}")
    print(f"✅ SP-API Pricing: {'Success' if results['sp_api_pricing'] else 'Failed'}")
    print(f"✅ Keepa: {'Success' if results['keepa'] else 'Failed'}")
    print(f"✅ Keepa Batch: {'Success' if results['keepa_batch'] else 'Failed'}")
    print(f"✅ Field Extractor: {'Success' if results['field_extractor'] else 'Failed'}")
    
    # Save full results to JSON
    output_file = f"test_asin_{asin}_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Full results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

