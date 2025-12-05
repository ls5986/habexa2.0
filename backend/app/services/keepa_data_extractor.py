"""
Keepa Data Extractor

Extracts key metrics from Keepa API responses.
Uses stats field (pre-calculated by Keepa) instead of parsing 40k line CSV arrays.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Keepa epoch: January 1, 2011
KEEPA_EPOCH = datetime(2011, 1, 1)


def keepa_to_datetime(keepa_time: int) -> Optional[datetime]:
    """Convert Keepa time (minutes since Jan 1, 2011) to datetime."""
    if not keepa_time or keepa_time < 0:
        return None
    try:
        return KEEPA_EPOCH + timedelta(minutes=keepa_time)
    except (ValueError, OverflowError):
        return None


def cents_to_dollars(cents: int) -> Optional[float]:
    """Convert Keepa price (cents) to dollars."""
    if cents is None or cents < 0:
        return None
    return round(cents / 100, 2)


def extract_all_keepa_data(keepa_product: dict) -> Dict[str, Any]:
    """
    Extract all key metrics from a Keepa product response.
    
    Uses:
    - stats.current: Current prices (index: 0=Amazon, 10=FBA, 11=FBM, 18=BuyBox, 3=SalesRank)
    - stats.365 or stats.min: 365-day lowest prices (PRE-CALCULATED by Keepa!)
    - offers: FBA/FBM seller counts
    
    Does NOT parse CSV arrays (saves processing time and avoids 40k lines of JSON).
    """
    if not keepa_product:
        return {}
    
    stats = keepa_product.get("stats", {})
    offers = keepa_product.get("offers", []) or []
    
    # Current prices from stats.current array
    # Index mapping: 0=Amazon, 1=New, 3=SalesRank, 10=FBA, 11=FBM, 18=BuyBox
    current = stats.get("current", []) or []
    
    # 365-day stats (pre-calculated by Keepa!)
    # When stats=365 and history=0, Keepa populates stats.min and stats.max arrays
    # Each element is [keepa_time, price_cents] or None
    # Index mapping: 0=Amazon, 10=FBA, 11=FBM, 18=BuyBox
    stats_min = stats.get("min", []) or []
    stats_max = stats.get("max", []) or []
    
    # Extract min values from arrays (index 10=FBA, 11=FBM, 0=Amazon)
    def safe_min(index):
        """Extract min value from stats.min array at given index."""
        if isinstance(stats_min, list) and len(stats_min) > index:
            min_data = stats_min[index]
            if min_data and isinstance(min_data, (list, tuple)) and len(min_data) >= 2:
                return min_data  # [keepa_time, price_cents]
        return None
    
    fba_min = safe_min(10)  # Index 10 = FBA
    fbm_min = safe_min(11)  # Index 11 = FBM
    amazon_min = safe_min(0)  # Index 0 = Amazon
    
    # Extract FBA/FBM seller counts from offers array
    fba_sellers = [o for o in offers if o.get("isFBA", False)]
    fbm_sellers = [o for o in offers if not o.get("isFBA", False)]
    
    # Safe extraction of min values
    # min_data format: [keepa_time, price_cents]
    def get_min_price(min_data):
        if min_data and isinstance(min_data, (list, tuple)) and len(min_data) >= 2:
            return min_data[1]  # price_cents is at index 1
        return None
    
    def get_min_time(min_data):
        if min_data and isinstance(min_data, (list, tuple)) and len(min_data) >= 2:
            return min_data[0]  # keepa_time is at index 0
        return None
    
    fba_low = get_min_price(fba_min)
    fbm_low = get_min_price(fbm_min)
    
    # Determine who had the lowest price
    lowest_was_fba = None
    if fba_low is not None or fbm_low is not None:
        fba_val = fba_low if fba_low is not None else float('inf')
        fbm_val = fbm_low if fbm_low is not None else float('inf')
        if fba_val != float('inf') or fbm_val != float('inf'):
            lowest_was_fba = fba_val <= fbm_val
    
    # Safe current price extraction
    def safe_current(index):
        if len(current) > index and current[index] is not None and current[index] > 0:
            return current[index]
        return None
    
    return {
        # Current prices
        "current_fba_price": cents_to_dollars(safe_current(10)),
        "current_fbm_price": cents_to_dollars(safe_current(11)),
        "current_amazon_price": cents_to_dollars(safe_current(0)),
        "current_buybox_price": cents_to_dollars(safe_current(18)),
        "current_sales_rank": safe_current(3),
        
        # 365-day lowest prices (from stats - no CSV parsing!)
        "fba_lowest_365d": cents_to_dollars(fba_low),
        "fba_lowest_date": keepa_to_datetime(get_min_time(fba_min)),
        "fbm_lowest_365d": cents_to_dollars(fbm_low),
        "fbm_lowest_date": keepa_to_datetime(get_min_time(fbm_min)),
        "amazon_lowest_365d": cents_to_dollars(get_min_price(amazon_min)),
        
        # Who had lowest?
        "lowest_was_fba": lowest_was_fba,
        
        # Amazon presence
        "amazon_was_seller": get_min_price(amazon_min) is not None and get_min_price(amazon_min) > 0,
        
        # Competition from offers array
        "fba_seller_count": len(fba_sellers),
        "fbm_seller_count": len(fbm_sellers),
        "total_seller_count": len(offers),
        
        # Sales velocity
        "sales_drops_30": stats.get("salesRankDrops30", 0) or 0,
        "sales_drops_90": stats.get("salesRankDrops90", 0) or 0,
        "sales_drops_180": stats.get("salesRankDrops180", 0) or 0,
        
        # BSR and category
        "bsr": keepa_product.get("salesRank") or keepa_product.get("salesRankCurrent") or 0,
        "category": _extract_category(keepa_product),
        
        # Weight and dimensions (for shipping calculation)
        # Keepa stores in grams/mm, convert to lb/inches
        "item_weight_lb": _extract_weight(keepa_product),
        "item_length_in": _extract_dimension(keepa_product, "packageLength"),
        "item_width_in": _extract_dimension(keepa_product, "packageWidth"),
        "item_height_in": _extract_dimension(keepa_product, "packageHeight"),
        "size_tier": _determine_size_tier(keepa_product),
    }


def _extract_category(keepa_product: dict) -> str:
    """Extract category name from Keepa product."""
    category_tree = keepa_product.get("categoryTree") or []
    if category_tree and len(category_tree) > 0:
        return category_tree[0].get("name", "")
    return ""


def _extract_weight(keepa_product: dict) -> Optional[float]:
    """Extract weight in pounds from Keepa product (converts from grams)."""
    package_weight_g = keepa_product.get("packageWeight", 0)
    if package_weight_g and package_weight_g > 0:
        return round(package_weight_g / 453.592, 2)  # Convert grams to pounds
    return None


def _extract_dimension(keepa_product: dict, field: str) -> Optional[float]:
    """Extract dimension in inches from Keepa product (converts from mm)."""
    dimension_mm = keepa_product.get(field, 0)
    if dimension_mm and dimension_mm > 0:
        return round(dimension_mm / 25.4, 2)  # Convert mm to inches
    return None


def _determine_size_tier(keepa_product: dict) -> Optional[str]:
    """Determine Amazon FBA size tier from dimensions and weight."""
    weight_lb = _extract_weight(keepa_product)
    length_in = _extract_dimension(keepa_product, "packageLength")
    width_in = _extract_dimension(keepa_product, "packageWidth")
    height_in = _extract_dimension(keepa_product, "packageHeight")
    
    if not all([weight_lb, length_in, width_in, height_in]):
        return None
    
    # Sort dimensions: longest, median, shortest
    dims = sorted([length_in, width_in, height_in], reverse=True)
    longest = dims[0]
    median = dims[1]
    shortest = dims[2]
    
    # Amazon FBA size tier rules
    if longest <= 15 and median <= 12 and shortest <= 0.75 and weight_lb <= 1:
        return "Small Standard"
    elif longest <= 18 and median <= 14 and shortest <= 8 and weight_lb <= 20:
        return "Large Standard"
    elif longest <= 60 and weight_lb <= 70:
        return "Small Oversize"
    else:
        return "Large Oversize"


def calculate_worst_case_profit(
    buy_cost: float,
    fba_lowest_365d: Optional[float],
    fees_total: float,
    current_sell_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate profitability at the lowest FBA price in the last 365 days.
    
    Args:
        buy_cost: Per-unit cost (wholesale_cost / pack_size)
        fba_lowest_365d: Lowest FBA price in 365 days
        fees_total: Total fees at current price (referral + FBA)
        current_sell_price: Current sell price (used for fee estimation)
    
    Returns:
        Dict with worst_case_profit, still_profitable_at_worst
    """
    if not buy_cost or buy_cost <= 0:
        return {"worst_case_profit": None, "still_profitable_at_worst": None}
    
    # Use lowest FBA price, fall back to current
    worst_price = fba_lowest_365d or current_sell_price
    
    if not worst_price or worst_price <= 0:
        return {"worst_case_profit": None, "still_profitable_at_worst": None}
    
    # Estimate fees at worst price (fees scale roughly with price)
    if current_sell_price and current_sell_price > 0 and fees_total and fees_total > 0:
        fee_ratio = fees_total / current_sell_price
        worst_fees = worst_price * fee_ratio
    else:
        # Estimate 30% fees if we don't have actuals
        worst_fees = worst_price * 0.30
    
    worst_profit = worst_price - worst_fees - buy_cost
    
    return {
        "worst_case_price": round(worst_price, 2),
        "worst_case_fees": round(worst_fees, 2),
        "worst_case_profit": round(worst_profit, 2),
        "still_profitable_at_worst": worst_profit > 0,
    }

