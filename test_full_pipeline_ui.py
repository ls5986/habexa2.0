#!/usr/bin/env python3
"""
Full End-to-End Test - Process Excel file through all stages with UI simulation
Shows what the UI should display at each stage with real data.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.tasks.file_processing import parse_excel, is_kehe_format, parse_supplier_row
from app.services.upc_converter import upc_converter
from app.services.batch_analyzer import batch_analyzer
from app.services.keepa_client import keepa_client
from app.services.keepa_data_extractor import extract_all_keepa_data, calculate_worst_case_profit
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_ui_section(title, data):
    """Print formatted UI section."""
    print("\n" + "=" * 80)
    print(f"📱 UI UPDATE: {title}")
    print("=" * 80)
    for key, value in data.items():
        print(f"  {key}: {value}")
    print()

def print_table(headers, rows):
    """Print formatted table."""
    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print header
    header_row = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        print(row_str)

async def test_full_pipeline_ui(file_path: str):
    """Test full pipeline with UI simulation."""
    
    print("\n" + "=" * 80)
    print("🚀 FULL END-TO-END TEST - UI SIMULATION")
    print("=" * 80)
    print(f"File: {file_path}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # ==========================================
    # STAGE 0: PARSE EXCEL
    # ==========================================
    print_ui_section("STAGE 0: Upload & Parse", {
        "File Name": "test.xlsx",
        "Status": "Uploading...",
        "Progress": "0%"
    })
    
    with open(file_path, 'rb') as f:
        contents = f.read()
    
    rows, headers = parse_excel(contents)
    is_kehe = is_kehe_format(headers)
    
    print_ui_section("STAGE 0: Parse Complete", {
        "Rows Detected": len(rows),
        "Format Detected": "KEHE" if is_kehe else "Standard",
        "Status": "✅ Parsed"
    })
    
    # Parse all rows
    parsed_rows = []
    for row in rows:
        if is_kehe:
            parsed = parse_supplier_row(row)
            if parsed:
                parsed_rows.append(parsed)
    
    # Calculate stats
    valid_upcs = len([p for p in parsed_rows if p.get('upc')])
    products_with_promo = len([p for p in parsed_rows if p.get('has_promo')])
    
    # Pack size distribution
    pack_sizes = {}
    for p in parsed_rows:
        pack = p.get('pack_size', 1)
        pack_sizes[pack] = pack_sizes.get(pack, 0) + 1
    pack_dist = ", ".join([f"{size} units: {count}" for size, count in sorted(pack_sizes.items())])
    
    print_ui_section("STAGE 0: Parsing Summary", {
        "Total Rows": len(rows),
        "Valid UPCs": valid_upcs,
        "Products with Promo": products_with_promo,
        "Pack Sizes Found": pack_dist
    })
    
    # Show parsed data table (first 10 rows)
    print("\n📊 Parsed Data Preview (First 10 rows):")
    print("-" * 80)
    table_headers = ["UPC", "Brand", "Pack Size", "Wholesale", "Buy Cost", "Has Promo", "Promo %"]
    table_rows = []
    for p in parsed_rows[:10]:
        table_rows.append([
            p.get('upc', 'N/A')[:12],
            (p.get('brand', 'N/A') or 'N/A')[:15],
            p.get('pack_size', 1),
            f"${p.get('wholesale_cost', 0):.2f}" if p.get('wholesale_cost') else 'N/A',
            f"${p.get('buy_cost', 0):.4f}" if p.get('buy_cost') else 'N/A',
            "✓" if p.get('has_promo') else "—",
            f"{p.get('promo_percent', 0):.0f}%" if p.get('promo_percent') else "—"
        ])
    print_table(table_headers, table_rows)
    
    # ==========================================
    # STAGE 1: UPC → ASIN CONVERSION
    # ==========================================
    print_ui_section("STAGE 1: UPC → ASIN Conversion", {
        "Status": "Converting...",
        "Progress": "0/35",
        "Batch": "Preparing..."
    })
    
    upcs = [p.get('upc') for p in parsed_rows if p.get('upc')]
    total_upcs = len(upcs)
    
    # Simulate batch conversion
    upc_to_asin_results = await upc_converter.upcs_to_asins_batch(upcs)
    
    asins_found = len([asin for asin in upc_to_asin_results.values() if asin])
    not_found = total_upcs - asins_found
    conversion_rate = (asins_found / total_upcs * 100) if total_upcs > 0 else 0
    
    print_ui_section("STAGE 1: Conversion Complete", {
        "Total UPCs": total_upcs,
        "ASINs Found": f"{asins_found} ✅",
        "Not Found": f"{not_found} ⚠️",
        "Conversion Rate": f"{conversion_rate:.1f}%"
    })
    
    # Update products with ASIN status
    products_with_asin = []
    products_without_asin = []
    for parsed in parsed_rows:
        upc = parsed.get('upc')
        asin = upc_to_asin_results.get(upc) if upc else None
        if asin:
            products_with_asin.append({**parsed, 'asin': asin, 'asin_status': 'found'})
        else:
            products_without_asin.append({**parsed, 'asin': None, 'asin_status': 'not_found', 'upc': upc})
    
    # Show products table with ASIN status
    print("\n📋 Products Table (with ASIN Status):")
    print("-" * 80)
    status_headers = ["UPC", "ASIN", "Status", "Brand", "Buy Cost"]
    status_rows = []
    for p in (products_with_asin[:5] + products_without_asin[:3]):
        status_rows.append([
            (p.get('upc', 'N/A') or 'N/A')[:12],
            p.get('asin', '—')[:10] if p.get('asin') else '—',
            "✓ Found" if p.get('asin') else "⚠️ Not Found",
            (p.get('brand', 'N/A') or 'N/A')[:15],
            f"${p.get('buy_cost', 0):.4f}" if p.get('buy_cost') else 'N/A'
        ])
    print_table(status_headers, status_rows)
    
    # ==========================================
    # STAGE 2: SP-API PRICING + FEES
    # ==========================================
    print_ui_section("STAGE 2: SP-API Pricing & Fees", {
        "Status": "Fetching pricing and fees...",
        "Products to Analyze": len(products_with_asin),
        "Progress": "0%"
    })
    
    # Build buy_costs and promo_costs
    buy_costs = {}
    promo_costs = {}
    for p in products_with_asin:
        asin = p.get('asin')
        if asin:
            if p.get('buy_cost'):
                buy_costs[asin] = float(p.get('buy_cost'))
            if p.get('promo_buy_cost'):
                promo_costs[asin] = float(p.get('promo_buy_cost'))
    
    # Analyze products
    asins = [p.get('asin') for p in products_with_asin if p.get('asin')]
    results = await batch_analyzer.analyze_products(asins, buy_costs=buy_costs, promo_costs=promo_costs)
    
    # Calculate stats
    profitable = [a for a in asins if results.get(a, {}).get('passed_stage2')]
    not_profitable = [a for a in asins if a not in profitable]
    avg_roi = sum(results.get(a, {}).get('roi', 0) for a in asins) / len(asins) if asins else 0
    best_roi = max((results.get(a, {}).get('roi', 0), a) for a in asins) if asins else (0, None)
    
    print_ui_section("STAGE 2: Analysis Complete", {
        "Products Analyzed": len(asins),
        "Profitable (ROI ≥ 30%)": f"{len(profitable)} ✅",
        "Not Profitable": f"{len(not_profitable)} ✗",
        "Average ROI": f"{avg_roi:.1f}%",
        "Best ROI": f"{best_roi[0]:.1f}% (ASIN: {best_roi[1]})" if best_roi[1] else "N/A"
    })
    
    # Show Stage 2 results table
    print("\n💰 Stage 2 Results:")
    print("-" * 80)
    stage2_headers = ["ASIN", "Buy Cost", "Sell Price", "Fees", "Net Profit", "ROI", "Stage"]
    stage2_rows = []
    for asin in asins[:5]:
        r = results.get(asin, {})
        stage2_rows.append([
            asin[:10],
            f"${r.get('buy_cost', 0):.4f}" if r.get('buy_cost') else 'N/A',
            f"${r.get('sell_price', 0):.2f}" if r.get('sell_price') else 'N/A',
            f"${r.get('fees_total', 0):.2f}" if r.get('fees_total') else 'N/A',
            f"${r.get('net_profit', 0):.2f}" if r.get('net_profit') else 'N/A',
            f"{r.get('roi', 0):.0f}% ✓" if r.get('passed_stage2') else f"{r.get('roi', 0):.0f}% ✗",
            "Stage 2 ✓" if r.get('passed_stage2') else "Filtered"
        ])
    print_table(stage2_headers, stage2_rows)
    
    # ==========================================
    # STAGE 3: KEEPA DEEP ANALYSIS
    # ==========================================
    print_ui_section("STAGE 3: Keepa Deep Analysis", {
        "Status": "Fetching Keepa data...",
        "Products to Analyze": len(profitable),
        "Progress": "0%"
    })
    
    # Get Keepa data for profitable products
    keepa_raw = await keepa_client.get_products_raw(profitable, domain=1, days=365)
    
    # Extract Keepa data
    keepa_results = {}
    for asin in profitable:
        if asin in keepa_raw:
            keepa_product = keepa_raw[asin]
            extracted = extract_all_keepa_data(keepa_product)
            
            # Calculate worst case
            buy_cost = buy_costs.get(asin, 0)
            worst_case = calculate_worst_case_profit(
                buy_cost=buy_cost,
                fba_lowest_365d=extracted.get('fba_lowest_365d'),
                fees_total=results.get(asin, {}).get('fees_total', 0),
                current_sell_price=results.get(asin, {}).get('sell_price')
            )
            
            keepa_results[asin] = {
                **extracted,
                **worst_case
            }
    
    # Calculate stats
    still_profitable = sum(1 for a in profitable if keepa_results.get(a, {}).get('still_profitable_at_worst'))
    risky = len(profitable) - still_profitable
    amazon_seller = sum(1 for a in profitable if keepa_results.get(a, {}).get('amazon_was_seller'))
    
    print_ui_section("STAGE 3: Keepa Analysis Complete", {
        "Products Analyzed": len(profitable),
        "Still Profitable at Worst": f"{still_profitable} ✅",
        "Risky (Not Profitable at 365d Low)": f"{risky} ⚠️",
        "Amazon is Seller": f"{amazon_seller} ⚠️"
    })
    
    # Show Stage 3 results table
    print("\n📚 Stage 3 Results:")
    print("-" * 80)
    stage3_headers = ["ASIN", "ROI", "FBA Low 365d", "Worst Profit", "Still Profitable", "FBA Sellers", "Stage"]
    stage3_rows = []
    for asin in profitable[:5]:
        r = results.get(asin, {})
        k = keepa_results.get(asin, {})
        stage3_rows.append([
            asin[:10],
            f"{r.get('roi', 0):.0f}%",
            f"${k.get('fba_lowest_365d', 0):.2f}" if k.get('fba_lowest_365d') else 'N/A',
            f"${k.get('worst_case_profit', 0):.2f}" if k.get('worst_case_profit') else 'N/A',
            "✓ Yes" if k.get('still_profitable_at_worst') else "✗ No",
            k.get('fba_seller_count', 0),
            "Complete ✓"
        ])
    print_table(stage3_headers, stage3_rows)
    
    # ==========================================
    # PRODUCT DETAIL VIEW SIMULATION
    # ==========================================
    print("\n" + "=" * 80)
    print("📱 PRODUCT DETAIL VIEW - Example Product")
    print("=" * 80)
    
    # Pick first product with complete data
    example_product = None
    example_parsed = None
    example_analysis = None
    example_keepa = None
    
    for i, p in enumerate(products_with_asin):
        asin = p.get('asin')
        if asin and asin in results and asin in keepa_results:
            example_product = p
            example_parsed = p
            example_analysis = results.get(asin, {})
            example_keepa = keepa_results.get(asin, {})
            break
    
    if example_product:
        print(f"\n📦 Product: {example_parsed.get('title', 'Unknown')[:50]}")
        print(f"🏷️  Brand: {example_parsed.get('brand', 'N/A')}")
        print(f"🔖 ASIN: {example_product.get('asin')}")
        print(f"📊 UPC: {example_parsed.get('upc', 'N/A')}")
        
        # Pack Size Info
        if example_parsed.get('pack_size', 1) > 1:
            print(f"\n📦 Pack Pricing:")
            print(f"  Case of {example_parsed.get('pack_size')} units @ ${example_parsed.get('wholesale_cost', 0):.2f}/case")
            print(f"  = ${example_parsed.get('buy_cost', 0):.4f}/unit")
        
        # Promo Info
        if example_parsed.get('has_promo'):
            print(f"\n🎉 PROMO: {example_parsed.get('promo_percent', 0):.0f}% OFF")
            print(f"  Regular: ${example_parsed.get('buy_cost', 0):.4f}/unit (ROI: {example_analysis.get('roi', 0):.1f}%)")
            print(f"  With Promo (Min {example_parsed.get('promo_qty', 0)} cases): ${example_parsed.get('promo_buy_cost', 0):.4f}/unit (ROI: {example_analysis.get('promo_roi', 0):.1f}%) 🚀")
            print(f"  Min Investment: ${(example_parsed.get('promo_qty', 0) * example_parsed.get('promo_wholesale_cost', 0)):.2f}")
        
        # Profitability
        print(f"\n💰 Profitability:")
        print(f"  Sell Price: ${example_analysis.get('sell_price', 0):.2f}")
        print(f"  Total Fees: ${example_analysis.get('fees_total', 0):.2f}")
        print(f"  Net Profit: ${example_analysis.get('net_profit', 0):.2f}")
        print(f"  ROI: {example_analysis.get('roi', 0):.1f}%")
        
        # 365-Day Analysis
        if example_keepa.get('fba_lowest_365d'):
            print(f"\n📊 365-Day Price Analysis:")
            print(f"  FBA Lowest (365d): ${example_keepa.get('fba_lowest_365d', 0):.2f}")
            if example_keepa.get('fba_lowest_date'):
                print(f"  Date: {example_keepa.get('fba_lowest_date').strftime('%Y-%m-%d')}")
            print(f"  Worst Case Profit: ${example_keepa.get('worst_case_profit', 0):.2f}")
            if example_keepa.get('still_profitable_at_worst'):
                print(f"  Status: ✓ Still Profitable")
            else:
                print(f"  Status: ⚠️ Would Lose Money")
        
        # Competition
        print(f"\n👥 Competition:")
        print(f"  FBA Sellers: {example_keepa.get('fba_seller_count', 0)}")
        print(f"  FBM Sellers: {example_keepa.get('fbm_seller_count', 0)}")
        if example_keepa.get('amazon_was_seller'):
            print(f"  ⚠️ Amazon was seller")
    
    # ==========================================
    # PRODUCTS LIST PAGE SUMMARY
    # ==========================================
    print("\n" + "=" * 80)
    print("📋 PRODUCTS LIST PAGE - Summary Stats")
    print("=" * 80)
    
    print_ui_section("Header Stats", {
        "Total Products": len(parsed_rows),
        "With ASIN": len(products_with_asin),
        "Needs ASIN": len(products_without_asin),
        "Profitable": len(profitable),
        "Not Profitable": len(not_profitable),
        "Has Promo": products_with_promo
    })
    
    print("\n✅ TEST COMPLETE")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

if __name__ == "__main__":
    file_path = "/Users/lindseystevens/habexa2.0/test.xlsx"
    asyncio.run(test_full_pipeline_ui(file_path))

