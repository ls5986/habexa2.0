"""
Profitability Calculator Service

Calculates profit, ROI, margin, break-even, and classifies products into tiers.
Used by analyzer dashboard and auto-calculated after file upload.
"""
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class ProfitabilityCalculator:
    """
    Calculates profitability metrics for Amazon products.
    
    Formulas:
    - Profit = sell_price - (buy_cost + prep_cost + inbound_shipping + fba_fee + referral_fee)
    - ROI = (profit / total_cost) * 100
    - Margin = (profit / sell_price) * 100
    - Break-even = buy_cost + prep_cost + inbound_shipping + fba_fee + referral_fee
    """
    
    # Default cost assumptions (can be overridden per user)
    DEFAULT_PREP_COST = Decimal('0.10')  # $0.10 per unit
    DEFAULT_INBOUND_SHIPPING_PER_LB = Decimal('0.35')  # $0.35 per pound
    DEFAULT_PACK_SIZE = 1
    
    # Profit tier thresholds
    EXCELLENT_ROI_THRESHOLD = 50.0  # 50%+ ROI
    GOOD_ROI_THRESHOLD = 30.0  # 30-50% ROI
    MARGINAL_ROI_THRESHOLD = 15.0  # 15-30% ROI
    
    # Risk level thresholds
    LOW_RISK_MARGIN = 40.0  # Margin > 40%
    LOW_RISK_SELLERS = 10  # Seller count < 10
    LOW_RISK_BSR = 10000  # BSR < 10,000
    
    HIGH_RISK_MARGIN = 20.0  # Margin < 20%
    HIGH_RISK_SELLERS = 50  # Seller count > 50
    HIGH_RISK_BSR = 100000  # BSR > 100,000
    
    @classmethod
    def calculate(
        cls,
        product_data: Dict[str, Any],
        product_source_data: Dict[str, Any],
        user_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate all profitability metrics for a product.
        
        Args:
            product_data: Product record from database (sell_price, fba_fees, referral_fee, etc.)
            product_source_data: Product source record (buy_cost, wholesale_cost, pack_size, moq)
            user_settings: Optional user-specific cost settings (prep_cost, inbound_shipping)
            
        Returns:
            Dictionary with calculated metrics:
            {
                'profit_amount': 3.25,
                'roi_percentage': 42.3,
                'margin_percentage': 34.5,
                'break_even_price': 9.50,
                'is_profitable': True,
                'profit_tier': 'good',
                'risk_level': 'medium',
                'est_monthly_sales': 48
            }
        """
        try:
            # Extract values with defaults
            sell_price = cls._safe_decimal(product_data.get('sell_price') or product_data.get('amazon_price_current'))
            buy_cost = cls._safe_decimal(product_source_data.get('buy_cost') or product_source_data.get('wholesale_cost'))
            pack_size = product_source_data.get('pack_size', cls.DEFAULT_PACK_SIZE) or cls.DEFAULT_PACK_SIZE
            
            # If wholesale_cost is for entire pack, calculate per-unit cost
            if product_source_data.get('wholesale_cost') and pack_size > 1:
                buy_cost = cls._safe_decimal(product_source_data.get('wholesale_cost')) / Decimal(pack_size)
            
            # Fees (from product data or defaults)
            fba_fee = cls._safe_decimal(product_data.get('fba_fees') or product_data.get('fba_fee') or 0)
            referral_fee = cls._safe_decimal(product_data.get('referral_fee') or 0)
            total_fees = cls._safe_decimal(product_data.get('fees_total') or 0)
            
            # If total_fees exists, use it; otherwise sum individual fees
            if total_fees == 0:
                total_fees = fba_fee + referral_fee
            
            # Cost assumptions (from user settings or defaults)
            prep_cost = cls._safe_decimal(
                (user_settings or {}).get('prep_cost') or cls.DEFAULT_PREP_COST
            )
            
            # Inbound shipping (estimate based on weight if available)
            item_weight = product_data.get('item_weight') or product_data.get('package_weight')
            if item_weight:
                # Convert to pounds (assuming grams if > 100, otherwise already pounds)
                weight_lbs = Decimal(item_weight) if item_weight < 100 else Decimal(item_weight) / Decimal('453.592')
                inbound_shipping = weight_lbs * cls._safe_decimal(
                    (user_settings or {}).get('inbound_shipping_per_lb') or cls.DEFAULT_INBOUND_SHIPPING_PER_LB
                )
            else:
                # Default estimate: $0.35 for average product
                inbound_shipping = cls.DEFAULT_INBOUND_SHIPPING_PER_LB
            
            # Validate we have required data
            if not sell_price or sell_price <= 0:
                logger.warning(f"Missing sell_price for product {product_data.get('id')}")
                return cls._empty_result()
            
            if not buy_cost or buy_cost <= 0:
                logger.warning(f"Missing buy_cost for product {product_data.get('id')}")
                return cls._empty_result()
            
            # ===== CALCULATE PROFIT =====
            total_cost = buy_cost + prep_cost + inbound_shipping + total_fees
            profit_amount = sell_price - total_cost
            
            # ===== CALCULATE ROI =====
            if total_cost > 0:
                roi_percentage = (profit_amount / total_cost) * Decimal('100')
            else:
                roi_percentage = Decimal('0')
            
            # ===== CALCULATE MARGIN =====
            if sell_price > 0:
                margin_percentage = (profit_amount / sell_price) * Decimal('100')
            else:
                margin_percentage = Decimal('0')
            
            # ===== BREAK-EVEN PRICE =====
            break_even_price = total_cost
            
            # ===== IS PROFITABLE =====
            is_profitable = profit_amount > 0 and roi_percentage >= Decimal(str(cls.MARGINAL_ROI_THRESHOLD))
            
            # ===== PROFIT TIER =====
            roi_float = float(roi_percentage)
            if roi_float >= cls.EXCELLENT_ROI_THRESHOLD:
                profit_tier = 'excellent'
            elif roi_float >= cls.GOOD_ROI_THRESHOLD:
                profit_tier = 'good'
            elif roi_float >= cls.MARGINAL_ROI_THRESHOLD:
                profit_tier = 'marginal'
            else:
                profit_tier = 'unprofitable'
            
            # ===== RISK LEVEL =====
            margin_float = float(margin_percentage)
            seller_count = product_data.get('seller_count') or product_data.get('fba_seller_count') or 0
            bsr = product_data.get('bsr') or product_data.get('current_sales_rank') or 999999
            
            if (margin_float > cls.LOW_RISK_MARGIN and 
                seller_count < cls.LOW_RISK_SELLERS and 
                bsr < cls.LOW_RISK_BSR):
                risk_level = 'low'
            elif (margin_float < cls.HIGH_RISK_MARGIN or 
                  seller_count > cls.HIGH_RISK_SELLERS or 
                  bsr > cls.HIGH_RISK_BSR):
                risk_level = 'high'
            else:
                risk_level = 'medium'
            
            # ===== ESTIMATED MONTHLY SALES =====
            est_monthly_sales = cls._estimate_monthly_sales(
                bsr=bsr,
                category=product_data.get('category'),
                sales_rank_30d=product_data.get('sales_rank_30_day_avg') or bsr
            )
            
            # Round all decimals to 2 places
            return {
                'profit_amount': float(profit_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'roi_percentage': float(roi_percentage.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)),
                'margin_percentage': float(margin_percentage.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)),
                'break_even_price': float(break_even_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'is_profitable': is_profitable,
                'profit_tier': profit_tier,
                'risk_level': risk_level,
                'est_monthly_sales': est_monthly_sales
            }
            
        except Exception as e:
            logger.error(f"Error calculating profitability: {e}", exc_info=True)
            return cls._empty_result()
    
    @staticmethod
    def _safe_decimal(value: Any) -> Decimal:
        """Convert value to Decimal safely."""
        if value is None:
            return Decimal('0')
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return Decimal('0')
    
    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        """Return empty result when calculation fails."""
        return {
            'profit_amount': None,
            'roi_percentage': None,
            'margin_percentage': None,
            'break_even_price': None,
            'is_profitable': False,
            'profit_tier': 'unprofitable',
            'risk_level': 'high',
            'est_monthly_sales': None
        }
    
    @staticmethod
    def _estimate_monthly_sales(
        bsr: Optional[int],
        category: Optional[str],
        sales_rank_30d: Optional[int] = None
    ) -> Optional[int]:
        """
        Estimate monthly sales based on BSR and category.
        
        Uses rough estimates based on Amazon BSR ranges:
        - BSR 1-1,000: ~500-1000 units/month
        - BSR 1,000-10,000: ~100-500 units/month
        - BSR 10,000-50,000: ~50-100 units/month
        - BSR 50,000-100,000: ~20-50 units/month
        - BSR 100,000-500,000: ~5-20 units/month
        - BSR 500,000+: ~1-5 units/month
        
        This is a rough estimate - actual sales vary by category and season.
        """
        if not bsr or bsr <= 0:
            return None
        
        # Use 30-day average if available (more accurate)
        rank = sales_rank_30d or bsr
        
        if rank <= 1000:
            return 750  # High volume
        elif rank <= 10000:
            return 300  # Good volume
        elif rank <= 50000:
            return 75  # Moderate volume
        elif rank <= 100000:
            return 35  # Low-moderate volume
        elif rank <= 500000:
            return 12  # Low volume
        else:
            return 3  # Very low volume
    
    @classmethod
    def calculate_batch(
        cls,
        products: List[Dict[str, Any]],
        product_sources: List[Dict[str, Any]],
        user_settings: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate profitability for multiple products at once.
        
        Args:
            products: List of product records
            product_sources: List of product_source records (matched by product_id)
            user_settings: Optional user-specific cost settings
            
        Returns:
            List of calculated metrics dictionaries
        """
        # Create lookup for product_sources by product_id
        sources_by_product = {ps.get('product_id'): ps for ps in product_sources}
        
        results = []
        for product in products:
            product_id = product.get('id')
            source_data = sources_by_product.get(product_id, {})
            
            calculated = cls.calculate(
                product_data=product,
                product_source_data=source_data,
                user_settings=user_settings
            )
            
            results.append({
                'product_id': product_id,
                **calculated
            })
        
        return results

