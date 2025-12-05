"""
Cost Calculator - Inbound shipping and prep cost calculations.
"""

from typing import Optional


# Weight-based inbound rates (typical for SPD/small parcel)
WEIGHT_RATES = {
    (0, 1): 0.50,      # Light items: $0.50/lb
    (1, 3): 0.40,      # 1-3 lb: $0.40/lb
    (3, 5): 0.35,      # 3-5 lb: $0.35/lb
    (5, 10): 0.30,     # 5-10 lb: $0.30/lb
    (10, 25): 0.25,    # 10-25 lb: $0.25/lb
    (25, float('inf')): 0.20,  # Heavy: $0.20/lb
}


def calculate_inbound_shipping(
    weight_lb: Optional[float],
    user_rate: float = 0.35,
    supplier_ships_direct: bool = False,
    rate_override: Optional[float] = None
) -> float:
    """
    Calculate inbound shipping cost per unit.
    
    Args:
        weight_lb: Item weight in pounds (from Keepa/SP-API)
        user_rate: User's default rate (from settings)
        supplier_ships_direct: If True, return 0 (supplier handles shipping)
        rate_override: Per-product rate override
    
    Returns:
        Inbound shipping cost per unit in dollars
    """
    if supplier_ships_direct:
        return 0.0
    
    # Use override if provided
    if rate_override is not None:
        rate = rate_override
    else:
        rate = user_rate
    
    # If no weight, estimate 0.5 lb
    if not weight_lb or weight_lb <= 0:
        weight_lb = 0.5
    
    return round(weight_lb * rate, 2)


def calculate_prep_cost(
    user_default: float = 0.10,
    override: Optional[float] = None
) -> float:
    """
    Calculate prep/labeling cost per unit.
    
    Args:
        user_default: User's default prep cost
        override: Per-product override
    
    Returns:
        Prep cost per unit in dollars
    """
    if override is not None:
        return round(override, 2)
    return round(user_default, 2)


def calculate_landed_cost(
    buy_cost: float,
    inbound_shipping: float,
    prep_cost: float
) -> float:
    """
    Total cost to get product into Amazon FBA.
    
    landed_cost = buy_cost + inbound_shipping + prep_cost
    """
    return round(buy_cost + inbound_shipping + prep_cost, 2)


def calculate_net_profit(
    sell_price: float,
    fees_total: float,
    landed_cost: float
) -> float:
    """
    Calculate net profit after all costs.
    
    net_profit = sell_price - fees_total - landed_cost
    """
    return round(sell_price - fees_total - landed_cost, 2)


def calculate_roi(net_profit: float, landed_cost: float) -> float:
    """
    Calculate ROI based on landed cost (not just buy cost).
    
    roi = (net_profit / landed_cost) × 100
    """
    if landed_cost <= 0:
        return 0.0
    return round((net_profit / landed_cost) * 100, 2)

