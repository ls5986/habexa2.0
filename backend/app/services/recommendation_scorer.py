"""
Recommendation Scorer

Calculates 0-100 score for products based on:
- Profitability (40 points)
- Velocity (30 points)
- Competition (15 points)
- Risk (15 points)
"""
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class RecommendationScorer:
    """Score products for recommendations."""
    
    # Score weights
    PROFITABILITY_WEIGHT = 40
    VELOCITY_WEIGHT = 30
    COMPETITION_WEIGHT = 15
    RISK_WEIGHT = 15
    
    def __init__(self, pricing_mode: str = '365d_avg'):
        self.pricing_mode = pricing_mode
    
    def calculate_score(self, product: Dict[str, Any], product_source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate total score (0-100) and breakdown.
        
        Returns:
            {
                'total_score': 87.5,
                'profitability_score': 32.0,
                'velocity_score': 25.0,
                'competition_score': 15.0,
                'risk_score': 15.5,
                'breakdown': {
                    'roi': 160.0,
                    'profit_per_unit': 4.5,
                    'margin': 35.0,
                    'monthly_sales': 520,
                    'days_to_sell': 10,
                    'fba_sellers': 8,
                    'price_volatility': 0.08
                }
            }
        """
        try:
            # Get pricing based on mode
            sell_price = self._get_price_for_mode(product)
            if not sell_price or sell_price <= 0:
                return self._empty_score()
            
            # Get costs
            wholesale_cost = float(product_source.get('wholesale_cost', 0))
            pack_size = product_source.get('pack_size', 1) or 1
            unit_cost = wholesale_cost / pack_size if pack_size > 0 else wholesale_cost
            
            # Calculate profitability
            profit_score, profit_breakdown = self._calculate_profitability_score(
                product, product_source, sell_price, unit_cost
            )
            
            # Calculate velocity
            velocity_score, velocity_breakdown = self._calculate_velocity_score(product)
            
            # Calculate competition
            competition_score, competition_breakdown = self._calculate_competition_score(product)
            
            # Calculate risk
            risk_score, risk_breakdown = self._calculate_risk_score(product, sell_price)
            
            # Total score
            total_score = profit_score + velocity_score + competition_score + risk_score
            
            return {
                'total_score': round(total_score, 2),
                'profitability_score': round(profit_score, 2),
                'velocity_score': round(velocity_score, 2),
                'competition_score': round(competition_score, 2),
                'risk_score': round(risk_score, 2),
                'breakdown': {
                    **profit_breakdown,
                    **velocity_breakdown,
                    **competition_breakdown,
                    **risk_breakdown
                }
            }
        
        except Exception as e:
            logger.error(f"Score calculation failed: {e}", exc_info=True)
            return self._empty_score()
    
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
        
        # Fallback
        return float(product.get('buy_box_price') or product.get('buy_box_price_365d_avg') or 0)
    
    def _calculate_profitability_score(
        self,
        product: Dict[str, Any],
        product_source: Dict[str, Any],
        sell_price: float,
        unit_cost: float
    ) -> tuple[float, Dict[str, Any]]:
        """Calculate profitability score (0-40 points)."""
        # Calculate profit metrics
        fba_fee = float(product.get('fba_fees') or 0)
        referral_pct = float(product.get('referral_fee_percentage') or 15.0)
        referral_fee = sell_price * (referral_pct / 100)
        total_fees = fba_fee + referral_fee
        prep_cost = 0.10  # Default
        inbound_shipping = 0.50  # Default
        
        total_cost = unit_cost + prep_cost + inbound_shipping + total_fees
        profit = sell_price - total_cost
        roi = (profit / total_cost * 100) if total_cost > 0 else 0
        margin = (profit / sell_price * 100) if sell_price > 0 else 0
        
        # Score based on ROI (max 40 points)
        # ROI 200%+ = 40 points
        # ROI 100% = 20 points
        # ROI 50% = 10 points
        # ROI 25% = 5 points
        if roi >= 200:
            score = 40.0
        elif roi >= 150:
            score = 35.0
        elif roi >= 100:
            score = 30.0
        elif roi >= 75:
            score = 25.0
        elif roi >= 50:
            score = 20.0
        elif roi >= 30:
            score = 15.0
        elif roi >= 20:
            score = 10.0
        elif roi >= 10:
            score = 5.0
        else:
            score = max(0, roi / 2)  # Linear below 10%
        
        return score, {
            'roi': round(roi, 2),
            'profit_per_unit': round(profit, 2),
            'margin': round(margin, 2),
            'sell_price': round(sell_price, 2),
            'unit_cost': round(unit_cost, 2)
        }
    
    def _calculate_velocity_score(self, product: Dict[str, Any]) -> tuple[float, Dict[str, Any]]:
        """Calculate velocity score (0-30 points)."""
        monthly_sales = product.get('est_monthly_sales') or 0
        sales_rank = product.get('current_sales_rank') or product.get('bsr') or 999999
        
        # Estimate days to sell (for 100 units, based on monthly sales)
        if monthly_sales > 0:
            days_to_sell_100 = (100 / (monthly_sales / 30))
        else:
            days_to_sell_100 = 999  # Very slow
        
        # Score based on days to sell
        # <10 days = 30 points (very fast)
        # 30 days = 15 points (moderate)
        # 60 days = 0 points (slow)
        if days_to_sell_100 <= 10:
            score = 30.0
        elif days_to_sell_100 <= 20:
            score = 25.0
        elif days_to_sell_100 <= 30:
            score = 20.0
        elif days_to_sell_100 <= 45:
            score = 15.0
        elif days_to_sell_100 <= 60:
            score = 10.0
        else:
            score = max(0, 10 - (days_to_sell_100 - 60) * 0.1)
        
        return score, {
            'monthly_sales': monthly_sales,
            'sales_rank': sales_rank,
            'days_to_sell_100': round(days_to_sell_100, 1)
        }
    
    def _calculate_competition_score(self, product: Dict[str, Any]) -> tuple[float, Dict[str, Any]]:
        """Calculate competition score (0-15 points)."""
        fba_sellers = product.get('fba_seller_count') or product.get('fba_sellers') or 999
        
        # Fewer sellers = better
        if fba_sellers < 5:
            score = 15.0
        elif fba_sellers < 10:
            score = 12.0
        elif fba_sellers < 15:
            score = 10.0
        elif fba_sellers < 20:
            score = 8.0
        elif fba_sellers < 30:
            score = 5.0
        else:
            score = max(0, 5 - (fba_sellers - 30) * 0.1)
        
        total_sellers = product.get('seller_count') or product.get('total_sellers') or 0
        
        return score, {
            'fba_sellers': fba_sellers,
            'total_sellers': total_sellers
        }
    
    def _calculate_risk_score(self, product: Dict[str, Any], sell_price: float) -> tuple[float, Dict[str, Any]]:
        """Calculate risk score (0-15 points)."""
        # Price volatility
        current_price = float(product.get('buy_box_price') or product.get('current_price') or 0)
        avg_365d = float(product.get('buy_box_price_365d_avg') or 0)
        
        if avg_365d > 0 and current_price > 0:
            price_volatility = abs(current_price - avg_365d) / avg_365d
        else:
            price_volatility = 0.5  # High risk if no data
        
        # Score based on volatility
        # <10% variation = 15 points (very stable)
        # 10-25% = 12 points
        # 25-40% = 8 points
        # >40% = 0 points (too volatile)
        if price_volatility < 0.10:
            score = 15.0
        elif price_volatility < 0.25:
            score = 12.0
        elif price_volatility < 0.40:
            score = 8.0
        else:
            score = 0.0
        
        # Additional risk factors
        review_score = float(product.get('rating') or 0)
        if review_score < 4.0:
            score -= 2.0  # Lower reviews = higher risk
        
        return max(0, score), {
            'price_volatility': round(price_volatility * 100, 1),  # As percentage
            'current_price': round(current_price, 2),
            'avg_365d_price': round(avg_365d, 2),
            'review_score': round(review_score, 1)
        }
    
    def _empty_score(self) -> Dict[str, Any]:
        """Return empty score."""
        return {
            'total_score': 0.0,
            'profitability_score': 0.0,
            'velocity_score': 0.0,
            'competition_score': 0.0,
            'risk_score': 0.0,
            'breakdown': {}
        }

