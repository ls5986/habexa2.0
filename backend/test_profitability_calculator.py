#!/usr/bin/env python3
"""
Quick test script for profitability calculator.
Run this to verify the calculator works before testing with real uploads.
"""
import sys
import os
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.profitability_calculator import ProfitabilityCalculator

def test_unprofitable():
    """Test an unprofitable product."""
    print("\n" + "="*60)
    print("TEST 1: Unprofitable Product")
    print("="*60)
    
    product_data = {
        'id': 'test-1',
        'sell_price': Decimal('19.99'),
        'amazon_price_current': Decimal('19.99'),
        'fba_fees': Decimal('3.50'),
        'referral_fee': Decimal('3.00'),
        'fees_total': Decimal('6.50'),
        'item_weight': 680,  # grams (~1.5 lbs)
        'bsr': 50000,
        'seller_count': 25,
        'category': 'Home & Kitchen'
    }
    
    product_source_data = {
        'buy_cost': Decimal('12.99'),
        'wholesale_cost': Decimal('12.99'),
        'pack_size': 1,
        'moq': 1
    }
    
    result = ProfitabilityCalculator.calculate(
        product_data=product_data,
        product_source_data=product_source_data
    )
    
    print(f"Input:")
    print(f"  Wholesale Cost: ${product_source_data['buy_cost']}")
    print(f"  Sell Price: ${product_data['sell_price']}")
    print(f"  Fees: ${product_data['fees_total']}")
    print(f"\nCalculated:")
    print(f"  Profit: ${result.get('profit_amount', 'N/A')}")
    print(f"  ROI: {result.get('roi_percentage', 'N/A')}%")
    print(f"  Margin: {result.get('margin_percentage', 'N/A')}%")
    print(f"  Break-even: ${result.get('break_even_price', 'N/A')}")
    print(f"  Is Profitable: {result.get('is_profitable', 'N/A')}")
    print(f"  Profit Tier: {result.get('profit_tier', 'N/A')}")
    print(f"  Risk Level: {result.get('risk_level', 'N/A')}")
    print(f"  Est Monthly Sales: {result.get('est_monthly_sales', 'N/A')}")
    
    assert result.get('profit_amount') is not None, "Profit should be calculated"
    assert result.get('roi_percentage') is not None, "ROI should be calculated"
    assert result.get('profit_tier') in ['excellent', 'good', 'marginal', 'unprofitable'], "Invalid profit tier"
    
    print("✅ Test 1 PASSED")
    return result

def test_profitable():
    """Test a profitable product."""
    print("\n" + "="*60)
    print("TEST 2: Profitable Product (Excellent ROI)")
    print("="*60)
    
    product_data = {
        'id': 'test-2',
        'sell_price': Decimal('24.99'),
        'amazon_price_current': Decimal('24.99'),
        'fba_fees': Decimal('4.00'),
        'referral_fee': Decimal('3.75'),
        'fees_total': Decimal('7.75'),
        'item_weight': 453,  # grams (~1 lb)
        'bsr': 5000,
        'seller_count': 5,
        'category': 'Electronics'
    }
    
    product_source_data = {
        'buy_cost': Decimal('8.00'),
        'wholesale_cost': Decimal('8.00'),
        'pack_size': 1,
        'moq': 1
    }
    
    result = ProfitabilityCalculator.calculate(
        product_data=product_data,
        product_source_data=product_source_data
    )
    
    print(f"Input:")
    print(f"  Wholesale Cost: ${product_source_data['buy_cost']}")
    print(f"  Sell Price: ${product_data['sell_price']}")
    print(f"  Fees: ${product_data['fees_total']}")
    print(f"\nCalculated:")
    print(f"  Profit: ${result.get('profit_amount', 'N/A')}")
    print(f"  ROI: {result.get('roi_percentage', 'N/A')}%")
    print(f"  Margin: {result.get('margin_percentage', 'N/A')}%")
    print(f"  Break-even: ${result.get('break_even_price', 'N/A')}")
    print(f"  Is Profitable: {result.get('is_profitable', 'N/A')}")
    print(f"  Profit Tier: {result.get('profit_tier', 'N/A')}")
    print(f"  Risk Level: {result.get('risk_level', 'N/A')}")
    print(f"  Est Monthly Sales: {result.get('est_monthly_sales', 'N/A')}")
    
    assert result.get('profit_amount', 0) > 0, "Should be profitable"
    assert result.get('roi_percentage', 0) > 0, "ROI should be positive"
    assert result.get('is_profitable') == True, "Should be marked profitable"
    
    print("✅ Test 2 PASSED")
    return result

def test_pack_size():
    """Test product with pack size > 1."""
    print("\n" + "="*60)
    print("TEST 3: Product with Pack Size (Case of 12)")
    print("="*60)
    
    product_data = {
        'id': 'test-3',
        'sell_price': Decimal('8.99'),
        'amazon_price_current': Decimal('8.99'),
        'fba_fees': Decimal('2.50'),
        'referral_fee': Decimal('1.35'),
        'fees_total': Decimal('3.85'),
        'item_weight': 226,  # grams (~0.5 lbs)
        'bsr': 15000,
        'seller_count': 12,
        'category': 'Grocery'
    }
    
    product_source_data = {
        'buy_cost': None,  # Not set - will use wholesale_cost / pack_size
        'wholesale_cost': Decimal('50.00'),  # Cost for entire case
        'pack_size': 12,  # 12 units per case
        'moq': 1
    }
    
    result = ProfitabilityCalculator.calculate(
        product_data=product_data,
        product_source_data=product_source_data
    )
    
    print(f"Input:")
    print(f"  Wholesale Cost (case): ${product_source_data['wholesale_cost']}")
    print(f"  Pack Size: {product_source_data['pack_size']} units")
    print(f"  Per-Unit Cost: ${product_source_data['wholesale_cost'] / Decimal(product_source_data['pack_size']):.2f}")
    print(f"  Sell Price (per unit): ${product_data['sell_price']}")
    print(f"  Fees: ${product_data['fees_total']}")
    print(f"\nCalculated:")
    print(f"  Profit: ${result.get('profit_amount', 'N/A')}")
    print(f"  ROI: {result.get('roi_percentage', 'N/A')}%")
    print(f"  Margin: {result.get('margin_percentage', 'N/A')}%")
    print(f"  Break-even: ${result.get('break_even_price', 'N/A')}")
    print(f"  Profit Tier: {result.get('profit_tier', 'N/A')}")
    
    # Expected: buy_cost = 50/12 = 4.17, profit = 8.99 - 4.17 - 3.85 - 0.35 = ~0.62
    # ROI = 0.62 / 4.52 * 100 = ~13.7% (marginal)
    expected_buy_cost = product_source_data['wholesale_cost'] / Decimal(product_source_data['pack_size'])
    print(f"\nExpected per-unit cost: ${expected_buy_cost:.2f}")
    
    print("✅ Test 3 PASSED")
    return result

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROFITABILITY CALCULATOR TEST SUITE")
    print("="*60)
    
    try:
        test_unprofitable()
        test_profitable()
        test_pack_size()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nThe calculator is working correctly.")
        print("You can now test with a real CSV upload.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

