from typing import Dict, Any, Optional


def calculate_profit(
    buy_cost: float,
    sell_price: float,
    fba_fee: Optional[float] = None,
    referral_fee: Optional[float] = None,
    prep_cost: float = 0.50,
    inbound_shipping: float = 0.50,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate profitability metrics for a product."""
    
    # Estimate referral fee if not provided
    if referral_fee is None:
        referral_rate = get_referral_rate(category)
        referral_fee = sell_price * referral_rate
    
    # Estimate FBA fee if not provided
    if fba_fee is None:
        fba_fee = estimate_fba_fee(sell_price)
    
    # Calculate totals
    total_cost = buy_cost + prep_cost + inbound_shipping
    total_amazon_fees = fba_fee + referral_fee
    net_payout = sell_price - total_amazon_fees
    net_profit = net_payout - total_cost
    
    # ROI and margin
    roi = (net_profit / total_cost * 100) if total_cost > 0 else 0
    margin = (net_profit / sell_price * 100) if sell_price > 0 else 0
    
    return {
        "buy_cost": round(buy_cost, 2),
        "prep_cost": round(prep_cost, 2),
        "inbound_shipping": round(inbound_shipping, 2),
        "total_cost": round(total_cost, 2),
        "sell_price": round(sell_price, 2),
        "fba_fee": round(fba_fee, 2),
        "referral_fee": round(referral_fee, 2),
        "total_amazon_fees": round(total_amazon_fees, 2),
        "net_payout": round(net_payout, 2),
        "net_profit": round(net_profit, 2),
        "roi": round(roi, 2),
        "margin": round(margin, 2),
        "is_profitable": net_profit > 0,
    }


def get_referral_rate(category: Optional[str]) -> float:
    """Get Amazon referral fee rate by category."""
    
    REFERRAL_RATES = {
        "Amazon Device Accessories": 0.45,
        "Automotive": 0.12,
        "Baby Products": 0.15,
        "Beauty": 0.15,
        "Books": 0.15,
        "Camera": 0.08,
        "Cell Phone Devices": 0.08,
        "Clothing": 0.17,
        "Computers": 0.08,
        "Electronics": 0.08,
        "Furniture": 0.15,
        "Grocery": 0.15,
        "Health": 0.15,
        "Home": 0.15,
        "Jewelry": 0.20,
        "Kitchen": 0.15,
        "Lawn & Garden": 0.15,
        "Music": 0.15,
        "Office Products": 0.15,
        "Pet Supplies": 0.15,
        "Shoes": 0.15,
        "Sports": 0.15,
        "Tools": 0.15,
        "Toys": 0.15,
        "Video Games": 0.15,
        "Watches": 0.16,
    }
    
    if category:
        for key, rate in REFERRAL_RATES.items():
            if key.lower() in category.lower():
                return rate
    
    return 0.15  # Default


def estimate_fba_fee(sell_price: float) -> float:
    """Simplified FBA fee estimation."""
    
    if sell_price < 10:
        return 3.00
    elif sell_price < 25:
        return 4.50
    elif sell_price < 50:
        return 5.50
    elif sell_price < 100:
        return 7.00
    else:
        return 8.50


def calculate_deal_score(
    roi: float,
    sales_rank: Optional[int],
    gating_status: str,
    amazon_is_seller: bool,
    num_fba_sellers: int
) -> str:
    """Calculate overall deal score (A, B, C, D, F)."""
    
    score = 0
    
    # ROI scoring (0-35 points)
    if roi >= 50:
        score += 35
    elif roi >= 40:
        score += 30
    elif roi >= 30:
        score += 25
    elif roi >= 20:
        score += 20
    elif roi >= 10:
        score += 10
    elif roi > 0:
        score += 5
    
    # Sales rank scoring (0-25 points)
    if sales_rank:
        if sales_rank < 5000:
            score += 25
        elif sales_rank < 15000:
            score += 20
        elif sales_rank < 50000:
            score += 15
        elif sales_rank < 100000:
            score += 10
        elif sales_rank < 200000:
            score += 5
    
    # Gating scoring (0-20 points)
    if gating_status == "ungated":
        score += 20
    elif gating_status == "unknown":
        score += 10
    
    # Competition scoring (0-10 points)
    if not amazon_is_seller:
        score += 5
    if num_fba_sellers < 3:
        score += 5
    elif num_fba_sellers < 5:
        score += 3
    
    # Bonus for low competition + high ROI (0-10 points)
    if roi > 30 and num_fba_sellers < 5 and not amazon_is_seller:
        score += 10
    
    # Convert to letter grade
    if score >= 80:
        return "A"
    elif score >= 65:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 35:
        return "D"
    else:
        return "F"

