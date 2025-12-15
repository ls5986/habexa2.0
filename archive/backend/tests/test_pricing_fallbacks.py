#!/usr/bin/env python3
"""
Test pricing data and fallbacks for specific ASINs.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path.parent / '.env')

from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import get_keepa_client
from app.services.api_field_extractor import SPAPIPricingExtractor, KeepaExtractor

TEST_ASINS = [
    'B0G4NB91XB',
    'B0G4NB29HC',
    'B0G4FC68Z1',
    'B0G4F9DQTW',
    'B0G4C5F4FF'
]

async def test_pricing(asin: str):
    """Test all pricing sources for an ASIN."""
    print(f"\n{'='*80}")
    print(f"🧪 TESTING ASIN: {asin}")
    print(f"{'='*80}")
    
    results = {
        'asin': asin,
        'sp_api_pricing': None,
        'sp_api_offers': None,
        'keepa_pricing': None,
        'final_price': None,
        'fallback_used': None
    }
    
    # ===== SP-API COMPETITIVE PRICING =====
    print("\n📊 SP-API Competitive Pricing:")
    try:
        pricing = await sp_api_client.get_competitive_pricing(asin)
        if pricing:
            results['sp_api_pricing'] = pricing
            print(f"  ✅ Buy Box Price: ${pricing.get('buy_box_price', 'N/A')}")
            print(f"  ✅ Lowest Price: ${pricing.get('lowest_price', 'N/A')}")
            print(f"  ✅ Seller Count: {pricing.get('seller_count', 'N/A')}")
            print(f"  ✅ FBA Seller Count: {pricing.get('fba_seller_count', 'N/A')}")
            print(f"  ✅ Amazon Sells: {pricing.get('amazon_sells', 'N/A')}")
        else:
            print("  ❌ No pricing data")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # ===== SP-API ITEM OFFERS =====
    print("\n💰 SP-API Item Offers:")
    try:
        offers = await sp_api_client.get_item_offers(asin)
        if offers:
            results['sp_api_offers'] = offers
            print(f"  ✅ Buy Box Price: ${offers.get('buy_box_price', 'N/A')}")
            print(f"  ✅ Lowest FBA Price: ${offers.get('lowest_fba_price', 'N/A')}")
            print(f"  ✅ Lowest Merchant Price: ${offers.get('lowest_merchant_price', 'N/A')}")
            print(f"  ✅ Total Offers: {offers.get('offer_count', 'N/A')}")
        else:
            print("  ❌ No offers data")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # ===== KEEPA PRICING =====
    print("\n📈 Keepa Pricing:")
    try:
        keepa_client = get_keepa_client()
        if keepa_client and keepa_client.is_configured():
            keepa_response = await keepa_client.get_products_batch([asin], return_raw=True)
            if keepa_response and keepa_response.get('products'):
                product = keepa_response['products'][0]
                keepa_extracted = KeepaExtractor.extract_all({'products': [product]}, asin=asin)
                results['keepa_pricing'] = keepa_extracted
                
                print(f"  ✅ Amazon Price Current: ${keepa_extracted.get('amazon_price_current', 'N/A')}")
                print(f"  ✅ New Price Current: ${keepa_extracted.get('new_price_current', 'N/A')}")
                print(f"  ✅ Buy Box Price Current: ${keepa_extracted.get('buybox_price_current', 'N/A')}")
                print(f"  ✅ Lowest Price: ${keepa_extracted.get('lowest_price', 'N/A')}")
                
                # Show CSV data if available
                if 'csv' in product:
                    csv = product['csv']
                    if len(csv) > 0 and csv[0]:
                        amazon_prices = csv[0]
                        if amazon_prices and len(amazon_prices) >= 2:
                            last_price = amazon_prices[-1]
                            if last_price >= 0:
                                print(f"  ✅ Amazon Price (from CSV): ${last_price / 100:.2f}")
                    if len(csv) > 1 and csv[1]:
                        new_prices = csv[1]
                        if new_prices and len(new_prices) >= 2:
                            last_price = new_prices[-1]
                            if last_price >= 0:
                                print(f"  ✅ New Price (from CSV): ${last_price / 100:.2f}")
            else:
                print("  ❌ No Keepa data")
        else:
            print("  ⚠️ Keepa not configured")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ===== DETERMINE FINAL PRICE (with fallbacks) =====
    print("\n🎯 FINAL PRICE DETERMINATION:")
    
    # Priority order:
    # 1. SP-API Buy Box Price (from competitive pricing)
    # 2. SP-API Buy Box Price (from item offers)
    # 3. Keepa Buy Box Price
    # 4. SP-API Lowest Price
    # 5. Keepa New Price
    # 6. Keepa Amazon Price
    
    final_price = None
    fallback_used = None
    
    if results['sp_api_pricing'] and results['sp_api_pricing'].get('buy_box_price'):
        final_price = results['sp_api_pricing']['buy_box_price']
        fallback_used = 'SP-API Competitive Pricing (Buy Box)'
    elif results['sp_api_offers'] and results['sp_api_offers'].get('buy_box_price'):
        final_price = results['sp_api_offers']['buy_box_price']
        fallback_used = 'SP-API Item Offers (Buy Box)'
    elif results['keepa_pricing'] and results['keepa_pricing'].get('buybox_price_current'):
        final_price = results['keepa_pricing']['buybox_price_current']
        fallback_used = 'Keepa Buy Box Price'
    elif results['sp_api_pricing'] and results['sp_api_pricing'].get('lowest_price'):
        final_price = results['sp_api_pricing']['lowest_price']
        fallback_used = 'SP-API Lowest Price'
    elif results['keepa_pricing'] and results['keepa_pricing'].get('new_price_current'):
        final_price = results['keepa_pricing']['new_price_current']
        fallback_used = 'Keepa New Price'
    elif results['keepa_pricing'] and results['keepa_pricing'].get('amazon_price_current'):
        final_price = results['keepa_pricing']['amazon_price_current']
        fallback_used = 'Keepa Amazon Price'
    
    results['final_price'] = final_price
    results['fallback_used'] = fallback_used
    
    if final_price:
        print(f"  ✅ Final Price: ${final_price:.2f}")
        print(f"  📍 Source: {fallback_used}")
    else:
        print("  ❌ NO PRICE AVAILABLE from any source")
    
    return results

async def main():
    """Test all ASINs."""
    print("\n" + "="*80)
    print("🧪 PRICING FALLBACK TEST")
    print("="*80)
    print(f"\nTesting {len(TEST_ASINS)} ASINs...")
    
    all_results = []
    
    for asin in TEST_ASINS:
        try:
            result = await test_pricing(asin)
            all_results.append(result)
            # Small delay between ASINs
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"\n❌ Failed to test {asin}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    for result in all_results:
        asin = result['asin']
        price = result['final_price']
        source = result['fallback_used']
        
        if price:
            print(f"  ✅ {asin}: ${price:.2f} ({source})")
        else:
            print(f"  ❌ {asin}: NO PRICE")
    
    # Count success rate
    success_count = sum(1 for r in all_results if r['final_price'])
    print(f"\n📈 Success Rate: {success_count}/{len(all_results)} ({success_count*100//len(all_results)}%)")

if __name__ == '__main__':
    asyncio.run(main())

