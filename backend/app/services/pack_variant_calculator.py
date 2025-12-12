"""
Multi-Pack PPU (Profit Per Unit) Calculator

Calculates profit per unit for each Amazon pack size variant (1-pack, 2-pack, etc.)
and recommends the most profitable pack size.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class PackVariantCalculator:
    """Calculate profit per unit for different pack sizes."""
    
    def __init__(self, profitability_calculator=None):
        """
        Initialize calculator.
        
        Args:
            profitability_calculator: Instance of ProfitabilityCalculator for fee calculations
        """
        self.profitability_calculator = profitability_calculator
    
    def calculate_pack_variants(
        self,
        product_data: Dict[str, Any],
        pack_sizes: List[int],
        pricing_mode: str = 'current'  # 'current', '30d_avg', '90d_avg', '365d_avg'
    ) -> List[Dict[str, Any]]:
        """
        Calculate profit per unit (PPU) for each pack size variant.
        
        Args:
            product_data: Product data including:
                - buy_cost: Cost per unit
                - pack_size: Pack size purchased from supplier
                - wholesale_cost: Wholesale cost
                - fba_fee: FBA fee per unit (or per pack)
                - referral_fee_percentage: Referral fee percentage
                - item_weight: Weight per unit
                - current_price: Current Amazon price
                - buy_box_price_30d_avg: 30-day average
                - buy_box_price_90d_avg: 90-day average
                - buy_box_price_365d_avg: 365-day average
            pack_sizes: List of pack sizes to calculate (e.g., [1, 2, 3, 4])
            pricing_mode: Which price to use ('current', '30d_avg', '90d_avg', '365d_avg')
        
        Returns:
            List of variant dictionaries with:
                - pack_size: Pack size (1, 2, 3, etc.)
                - price: Amazon price for this pack
                - profit_per_unit: PPU (Profit Per Unit)
                - roi: ROI percentage
                - margin: Margin percentage
                - total_profit: Total profit if all units sold as this pack
                - is_recommended: Whether this is the recommended pack size
        """
        variants = []
        
        # Get base cost per unit
        buy_cost_per_unit = self._get_buy_cost_per_unit(product_data)
        if not buy_cost_per_unit or buy_cost_per_unit <= 0:
            logger.warning("Invalid buy_cost_per_unit, cannot calculate variants")
            return variants
        
        # Get base price (current or average based on pricing_mode)
        base_price = self._get_price_for_mode(product_data, pricing_mode)
        if not base_price or base_price <= 0:
            logger.warning(f"No price available for mode {pricing_mode}")
            return variants
        
        # Get fees (per unit)
        fba_fee_per_unit = product_data.get('fba_fee') or 0
        referral_fee_pct = product_data.get('referral_fee_percentage') or 15.0
        item_weight = product_data.get('item_weight') or 1.0
        
        # Calculate for each pack size
        for pack_size in pack_sizes:
            variant = self._calculate_variant(
                pack_size=pack_size,
                base_price=base_price,
                buy_cost_per_unit=buy_cost_per_unit,
                fba_fee_per_unit=fba_fee_per_unit,
                referral_fee_pct=referral_fee_pct,
                item_weight=item_weight,
                product_data=product_data
            )
            
            if variant:
                variants.append(variant)
        
        # Mark recommended variant (highest PPU)
        if variants:
            recommended = max(variants, key=lambda v: v.get('profit_per_unit', 0))
            recommended['is_recommended'] = True
            recommended['recommendation_reason'] = 'Highest PPU'
        
        return variants
    
    def _get_buy_cost_per_unit(self, product_data: Dict[str, Any]) -> Optional[float]:
        """Calculate buy cost per unit from product data."""
        # Try buy_cost first (already per unit)
        buy_cost = product_data.get('buy_cost')
        if buy_cost:
            return float(buy_cost)
        
        # Calculate from wholesale_cost and pack_size
        wholesale_cost = product_data.get('wholesale_cost')
        pack_size = product_data.get('pack_size', 1)
        
        if wholesale_cost and pack_size > 0:
            return float(wholesale_cost) / float(pack_size)
        
        return None
    
    def _get_price_for_mode(self, product_data: Dict[str, Any], pricing_mode: str) -> Optional[float]:
        """Get price based on pricing mode."""
        if pricing_mode == 'current':
            return product_data.get('buy_box_price') or product_data.get('current_price')
        elif pricing_mode == '30d_avg':
            return product_data.get('buy_box_price_30d_avg')
        elif pricing_mode == '90d_avg':
            return product_data.get('buy_box_price_90d_avg')
        elif pricing_mode == '365d_avg':
            return product_data.get('buy_box_price_365d_avg')
        
        return product_data.get('buy_box_price')
    
    def _calculate_variant(
        self,
        pack_size: int,
        base_price: float,
        buy_cost_per_unit: float,
        fba_fee_per_unit: float,
        referral_fee_pct: float,
        item_weight: float,
        product_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate metrics for a single pack size variant.
        
        Logic:
        - Amazon price for N-pack = base_price * N (linear scaling)
        - Cost for N-pack = buy_cost_per_unit * N
        - FBA fee for N-pack = fba_fee_per_unit * N (or recalculated for weight)
        - Referral fee = price * referral_fee_pct
        - PPU = (profit for N-pack) / N
        """
        if pack_size <= 0:
            return None
        
        # Estimate price for this pack size
        # Note: In reality, Amazon prices may not scale linearly
        # This is an approximation - could be enhanced with actual pack variant data
        pack_price = base_price * pack_size
        
        # Cost for this pack
        pack_cost = buy_cost_per_unit * pack_size
        
        # FBA fee for this pack (scale by pack size, or recalculate for weight)
        pack_weight = item_weight * pack_size
        pack_fba_fee = fba_fee_per_unit * pack_size  # Simple scaling for now
        
        # Referral fee
        referral_fee = pack_price * (referral_fee_pct / 100.0)
        
        # Total fees
        total_fees = pack_fba_fee + referral_fee
        
        # Add prep and inbound shipping (per unit, so scale by pack size)
        prep_cost = product_data.get('prep_cost', 0.10) * pack_size
        inbound_shipping = product_data.get('inbound_shipping', 0.35) * pack_weight  # Per pound
        
        total_cost = pack_cost + total_fees + prep_cost + inbound_shipping
        
        # Profit for this pack
        profit = pack_price - total_cost
        
        # Profit Per Unit (PPU) - the key metric!
        profit_per_unit = profit / pack_size if pack_size > 0 else 0
        
        # ROI and Margin
        roi = (profit / total_cost * 100) if total_cost > 0 else 0
        margin = (profit / pack_price * 100) if pack_price > 0 else 0
        
        return {
            'pack_size': pack_size,
            'price': round(pack_price, 2),
            'cost': round(pack_cost, 2),
            'fba_fee': round(pack_fba_fee, 2),
            'referral_fee': round(referral_fee, 2),
            'total_fees': round(total_fees, 2),
            'prep_cost': round(prep_cost, 2),
            'inbound_shipping': round(inbound_shipping, 2),
            'total_cost': round(total_cost, 2),
            'profit': round(profit, 2),
            'profit_per_unit': round(profit_per_unit, 2),  # PPU!
            'roi': round(roi, 2),
            'margin': round(margin, 2),
            'is_recommended': False,
            'recommendation_reason': None
        }
    
    def calculate_packs_to_create(
        self,
        total_units: int,
        target_pack_size: int
    ) -> Dict[str, int]:
        """
        Calculate how many packs to create from total units.
        
        Args:
            total_units: Total units received (e.g., 480)
            target_pack_size: Pack size to create (e.g., 4)
        
        Returns:
            {
                'packs_to_create': 120,
                'leftover_units': 0
            }
        """
        if target_pack_size <= 0:
            return {'packs_to_create': 0, 'leftover_units': total_units}
        
        packs_to_create = total_units // target_pack_size
        leftover_units = total_units % target_pack_size
        
        return {
            'packs_to_create': packs_to_create,
            'leftover_units': leftover_units
        }
    
    def generate_prep_instructions(
        self,
        product_name: str,
        total_units: int,
        target_pack_size: int,
        variant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate prep instructions for 3PL.
        
        Args:
            product_name: Product name
            total_units: Total units to prep
            target_pack_size: Target pack size
            variant_data: Variant data from calculate_pack_variants
        
        Returns:
            Prep instructions dictionary
        """
        pack_calc = self.calculate_packs_to_create(total_units, target_pack_size)
        
        steps = [
            {
                'step': 1,
                'action': 'Receive inventory',
                'quantity': total_units,
                'unit': 'units',
                'notes': f'Verify count matches order: {total_units} units'
            },
            {
                'step': 2,
                'action': 'Bundle into packs',
                'quantity': pack_calc['packs_to_create'],
                'unit': f'{target_pack_size}-packs',
                'notes': f'Create {pack_calc["packs_to_create"]} {target_pack_size}-packs from {total_units} units'
            }
        ]
        
        if pack_calc['leftover_units'] > 0:
            steps.append({
                'step': 3,
                'action': 'Handle leftover units',
                'quantity': pack_calc['leftover_units'],
                'unit': 'units',
                'notes': f'{pack_calc["leftover_units"]} units remain (not enough for full pack)'
            })
        
        steps.append({
            'step': len(steps) + 1,
            'action': 'Apply FNSKU labels',
            'quantity': pack_calc['packs_to_create'],
            'unit': 'labels',
            'notes': 'One label per pack'
        })
        
        steps.append({
            'step': len(steps) + 1,
            'action': 'Quality check',
            'quantity': pack_calc['packs_to_create'],
            'unit': 'packs',
            'notes': 'Verify all packs are complete and labeled correctly'
        })
        
        return {
            'product_name': product_name,
            'expected_units': total_units,
            'target_pack_size': target_pack_size,
            'packs_to_create': pack_calc['packs_to_create'],
            'leftover_units': pack_calc['leftover_units'],
            'profit_per_unit': variant_data.get('profit_per_unit'),
            'total_profit': variant_data.get('profit') * pack_calc['packs_to_create'],
            'prep_steps': steps,
            'status': 'pending'
        }


# Convenience function
def calculate_pack_variants(product_data: Dict[str, Any], pack_sizes: List[int] = None, pricing_mode: str = 'current') -> List[Dict[str, Any]]:
    """
    Convenience function to calculate pack variants.
    
    Args:
        product_data: Product data
        pack_sizes: List of pack sizes (default: [1, 2, 3, 4])
        pricing_mode: Pricing mode ('current', '30d_avg', '90d_avg', '365d_avg')
    
    Returns:
        List of variant dictionaries
    """
    if pack_sizes is None:
        pack_sizes = [1, 2, 3, 4]
    
    calculator = PackVariantCalculator()
    return calculator.calculate_pack_variants(product_data, pack_sizes, pricing_mode)

