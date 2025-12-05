#!/usr/bin/env python3
"""
Test Excel parsing through all stages without storing in Supabase.
Shows API responses at each stage and finds errors.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.tasks.file_processing import parse_excel, is_kehe_format, parse_supplier_row
from app.services.upc_converter import upc_converter
from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import keepa_client
from app.services.batch_analyzer import batch_analyzer
from app.services.keepa_data_extractor import extract_all_keepa_data, calculate_worst_case_profit
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_excel_parsing(file_path: str):
    """Test Excel parsing through all stages."""
    
    print("=" * 80)
    print("EXCEL PARSING TEST - Full Pipeline")
    print("=" * 80)
    print()
    
    # ==========================================
    # STAGE 0: PARSE EXCEL
    # ==========================================
    print("📄 STAGE 0: Parsing Excel File")
    print("-" * 80)
    
    with open(file_path, 'rb') as f:
        contents = f.read()
    
    rows, headers = parse_excel(contents)
    print(f"✅ Parsed {len(rows)} rows")
    print(f"📋 Headers: {headers[:10]}...")
    print()
    
    # Check if KEHE format
    is_kehe = is_kehe_format(headers)
    print(f"🔍 Format Detection: {'KEHE Format' if is_kehe else 'Standard Format'}")
    print()
    
    # Parse first 5 rows
    print("📊 Sample Parsed Rows (first 5):")
    print("-" * 80)
    
    parsed_rows = []
    for i, row in enumerate(rows[:5]):
        if is_kehe:
            parsed = parse_supplier_row(row)
        else:
            # For standard format, just show raw row
            parsed = {
                "upc": row.get("UPC") or row.get("upc") or "N/A",
                "raw_row": {k: v for k, v in list(row.items())[:5]}
            }
        
        if parsed:
            parsed_rows.append(parsed)
            print(f"\nRow {i+1}:")
            print(f"  UPC: {parsed.get('upc', 'N/A')}")
            if is_kehe:
                print(f"  Supplier SKU: {parsed.get('supplier_sku', 'N/A')}")
                print(f"  Pack Size: {parsed.get('pack_size', 1)}")
                print(f"  Wholesale Cost: ${parsed.get('wholesale_cost', 'N/A')}")
                print(f"  Buy Cost (per unit): ${parsed.get('buy_cost', 'N/A')}")
                print(f"  MOQ: {parsed.get('moq', 1)}")
                print(f"  Brand: {parsed.get('brand', 'N/A')}")
                print(f"  Title: {parsed.get('title', 'N/A')[:50]}...")
            else:
                print(f"  Raw data: {parsed.get('raw_row', {})}")
        else:
            print(f"\nRow {i+1}: ❌ Failed to parse")
    
    print()
    print("=" * 80)
    
    # ==========================================
    # STAGE 1: UPC → ASIN CONVERSION
    # ==========================================
    print("\n🔄 STAGE 1: UPC → ASIN Conversion")
    print("-" * 80)
    
    # Get UPCs from parsed rows
    upcs = [p.get('upc') for p in parsed_rows if p.get('upc')]
    print(f"📦 Converting {len(upcs)} UPCs to ASINs...")
    print()
    
    products_with_asin = []
    products_without_asin = []
    
    if upcs:
        # Test batch conversion
        upc_to_asin_results = await upc_converter.upcs_to_asins_batch(upcs)
        
        print("✅ Conversion Results:")
        for parsed in parsed_rows:
            upc = parsed.get('upc')
            asin = upc_to_asin_results.get(upc) if upc else None
            if asin:
                print(f"  ✅ {upc} → {asin}")
                products_with_asin.append({**parsed, 'asin': asin, 'asin_status': 'found'})
            else:
                print(f"  ❌ {upc} → NOT FOUND (will be saved with asin_status='not_found')")
                products_without_asin.append({**parsed, 'asin': None, 'asin_status': 'not_found', 'upc': upc})
        
        # Create ASIN list for next stages
        asins = [asin for asin in upc_to_asin_results.values() if asin]
        print(f"\n✅ Successfully converted {len(asins)}/{len(upcs)} UPCs")
        print(f"📝 Products WITH ASIN: {len(products_with_asin)} (ready for analysis)")
        print(f"📝 Products WITHOUT ASIN: {len(products_without_asin)} (saved for manual entry)")
        
        if products_without_asin:
            print("\n📋 Products Saved Without ASIN (for manual entry):")
            for p in products_without_asin:
                print(f"  - UPC: {p.get('upc')}")
                print(f"    Supplier SKU: {p.get('supplier_sku', 'N/A')}")
                print(f"    Pack Size: {p.get('pack_size', 1)}")
                print(f"    Buy Cost: ${p.get('buy_cost', 0):.4f}/unit")
                print(f"    Wholesale Cost: ${p.get('wholesale_cost', 0):.2f}/case")
                print(f"    Status: asin_status='not_found', stage='pending_asin'")
                print()
    else:
        print("⚠️ No UPCs found in parsed rows")
        asins = []
    
    print()
    print("=" * 80)
    
    # ==========================================
    # STAGE 2: SP-API BASIC (Pricing + Fees)
    # ==========================================
    print("\n💰 STAGE 2: SP-API Basic (Pricing + Fees)")
    print("-" * 80)
    
    if not asins:
        print("⚠️ No ASINs to analyze. Skipping Stage 2.")
    else:
        # Build buy_costs dict from parsed rows
        buy_costs = {}
        for parsed, upc in zip(parsed_rows, upcs):
            asin = upc_to_asin_results.get(upc)
            if asin and parsed.get('buy_cost'):
                buy_costs[asin] = float(parsed['buy_cost'])
        
        print(f"📊 Analyzing {len(asins)} products with buy costs...")
        print(f"💵 Buy costs: {buy_costs}")
        print()
        
        # Use batch analyzer (this will do SP-API pricing + fees)
        print("🔄 Calling batch_analyzer.analyze_products()...")
        results = await batch_analyzer.analyze_products(asins, buy_costs=buy_costs)
        
        print("\n✅ Stage 2 Results:")
        for asin in asins:
            result = results.get(asin, {})
            print(f"\n  ASIN: {asin}")
            print(f"    Sell Price: ${result.get('sell_price', 'N/A')}")
            print(f"    Fees Total: ${result.get('fees_total', 'N/A')}")
            print(f"    Buy Cost: ${result.get('buy_cost', 'N/A')}")
            print(f"    Net Profit: ${result.get('net_profit', 'N/A')}")
            print(f"    ROI: {result.get('roi', 'N/A')}%")
            print(f"    Passed Stage 2: {result.get('passed_stage2', False)}")
            print(f"    Analysis Stage: {result.get('analysis_stage', 'N/A')}")
    
    print()
    print("=" * 80)
    
    # ==========================================
    # STAGE 3: KEEPA DEEP ANALYSIS
    # ==========================================
    print("\n📚 STAGE 3: Keepa Deep Analysis (365-day stats)")
    print("-" * 80)
    
    if not asins:
        print("⚠️ No ASINs to analyze. Skipping Stage 3.")
    else:
        # Get products that passed Stage 2
        passed_stage2_asins = [a for a in asins if results.get(a, {}).get('passed_stage2')]
        
        if not passed_stage2_asins:
            print("⚠️ No products passed Stage 2. Skipping Stage 3.")
        else:
            print(f"📊 Fetching Keepa data for {len(passed_stage2_asins)} products...")
            print()
            
            # Get raw Keepa data
            keepa_raw = await keepa_client.get_products_raw(passed_stage2_asins, domain=1, days=365)
            
            print(f"✅ Received Keepa data for {len(keepa_raw)} products")
            print()
            
            # Extract 365-day data
            for asin in passed_stage2_asins:
                if asin in keepa_raw:
                    keepa_product = keepa_raw[asin]
                    extracted = extract_all_keepa_data(keepa_product)
                    
                    print(f"\n  ASIN: {asin}")
                    print(f"    FBA Lowest 365d: ${extracted.get('fba_lowest_365d', 'N/A')}")
                    print(f"    FBA Lowest Date: {extracted.get('fba_lowest_date', 'N/A')}")
                    print(f"    FBM Lowest 365d: ${extracted.get('fbm_lowest_365d', 'N/A')}")
                    print(f"    Lowest Was FBA: {extracted.get('lowest_was_fba', 'N/A')}")
                    print(f"    Amazon Was Seller: {extracted.get('amazon_was_seller', 'N/A')}")
                    print(f"    FBA Seller Count: {extracted.get('fba_seller_count', 'N/A')}")
                    print(f"    FBM Seller Count: {extracted.get('fbm_seller_count', 'N/A')}")
                    print(f"    Sales Drops 30: {extracted.get('sales_drops_30', 'N/A')}")
                    print(f"    Sales Drops 90: {extracted.get('sales_drops_90', 'N/A')}")
                    
                    # Calculate worst case
                    buy_cost = buy_costs.get(asin, 0)
                    worst_case = calculate_worst_case_profit(
                        buy_cost=buy_cost,
                        fba_lowest_365d=extracted.get('fba_lowest_365d'),
                        fees_total=results.get(asin, {}).get('fees_total', 0),
                        current_sell_price=results.get(asin, {}).get('sell_price')
                    )
                    print(f"    Worst Case Profit: ${worst_case.get('worst_case_profit', 'N/A')}")
                    print(f"    Still Profitable: {worst_case.get('still_profitable_at_worst', 'N/A')}")
                else:
                    print(f"\n  ASIN: {asin} - ❌ Not found in Keepa response")
    
    print()
    print("=" * 80)
    print("\n✅ TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    file_path = "/Users/lindseystevens/habexa2.0/test.xlsx"
    asyncio.run(test_excel_parsing(file_path))

