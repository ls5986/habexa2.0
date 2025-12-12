"""
Recommendation Filter Engine

Applies pass/fail filters to products before scoring.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class RecommendationFilter:
    """Filter products for recommendations."""
    
    def __init__(
        self,
        min_roi: float = 25.0,
        max_fba_sellers: int = 30,
        max_days_to_sell: int = 60,
        avoid_hazmat: bool = True,
        pricing_mode: str = '365d_avg'
    ):
        self.min_roi = min_roi
        self.max_fba_sellers = max_fba_sellers
        self.max_days_to_sell = max_days_to_sell
        self.avoid_hazmat = avoid_hazmat
        self.pricing_mode = pricing_mode
    
    def should_include(
        self,
        product: Dict[str, Any],
        product_source: Dict[str, Any],
        brand_status: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if product should be included.
        
        Returns:
            (should_include, failure_reason)
        """
        try:
            # Filter 1: Brand restriction
            if brand_status:
                if brand_status == 'globally_restricted':
                    return False, 'brand_restricted'
                elif brand_status == 'supplier_restricted':
                    return False, 'supplier_restricted'
            
            # Filter 2: Hazmat
            if self.avoid_hazmat and product.get('is_hazmat'):
                return False, 'hazmat'
            
            # Filter 3: Missing ASIN
            if not product.get('asin') or product.get('asin', '').startswith('PENDING_'):
                return False, 'no_asin'
            
            # Filter 4: Missing pricing data
            sell_price = self._get_price_for_mode(product)
            if not sell_price or sell_price <= 0:
                return False, 'no_pricing'
            
            # Filter 5: Calculate ROI and check threshold
            wholesale_cost = float(product_source.get('wholesale_cost', 0))
            pack_size = product_source.get('pack_size', 1) or 1
            unit_cost = wholesale_cost / pack_size if pack_size > 0 else wholesale_cost
            
            if unit_cost <= 0:
                return False, 'no_cost'
            
            # Quick ROI check
            fba_fee = float(product.get('fba_fees') or 0)
            referral_pct = float(product.get('referral_fee_percentage') or 15.0)
            referral_fee = sell_price * (referral_pct / 100)
            total_fees = fba_fee + referral_fee
            total_cost = unit_cost + 0.10 + 0.50 + total_fees  # prep + shipping
            profit = sell_price - total_cost
            roi = (profit / total_cost * 100) if total_cost > 0 else 0
            
            if roi < self.min_roi:
                return False, f'roi_too_low_{roi:.1f}%'
            
            # Filter 6: Too many FBA sellers
            fba_sellers = product.get('fba_seller_count') or product.get('fba_sellers') or 0
            if fba_sellers > self.max_fba_sellers:
                return False, f'too_many_sellers_{fba_sellers}'
            
            # Filter 7: Price volatility (if using 365d avg)
            if self.pricing_mode == '365d_avg':
                current_price = float(product.get('buy_box_price') or 0)
                avg_365d = float(product.get('buy_box_price_365d_avg') or 0)
                if avg_365d > 0 and current_price > 0:
                    volatility = abs(current_price - avg_365d) / avg_365d
                    if volatility > 0.40:  # More than 40% difference
                        return False, f'price_too_volatile_{volatility*100:.0f}%'
            
            # Filter 8: Sales velocity (if max_days set)
            if self.max_days_to_sell:
                monthly_sales = product.get('est_monthly_sales') or 0
                if monthly_sales > 0:
                    days_to_sell_100 = (100 / (monthly_sales / 30))
                    if days_to_sell_100 > self.max_days_to_sell:
                        return False, f'sells_too_slow_{days_to_sell_100:.0f}_days'
                elif monthly_sales == 0:
                    # No sales data = unknown velocity, might be slow
                    # Don't fail, but it's a risk
                    pass
            
            # All filters passed
            return True, None
        
        except Exception as e:
            logger.error(f"Filter check failed: {e}", exc_info=True)
            return False, 'filter_error'
    
    def _get_price_for_mode(self, product: Dict[str, Any]) -> Optional[float]:
        """Get price based on pricing mode."""
        if self.pricing_mode == 'current':
            return float(product.get('buy_box_price') or product.get('current_price') or 0)
        elif self.pricing_mode == '30d_avg':
            return float(product.get('buy_box_price_30d_avg') or 0)
        elif self.pricing_mode == '90d_avg':
            return float(product.get('buy_box_price_90d_avg') or 0)
        elif self.pricing_mode == '365d_avg':
            return float(product.get('buy_box_price_365d_avg') or product.get('avg_buybox_90d') or 0)
        
        return float(product.get('buy_box_price') or 0)

