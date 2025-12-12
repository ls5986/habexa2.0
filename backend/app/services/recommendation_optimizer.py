"""
Recommendation Optimizer

Optimization algorithms for different goals:
- Meet budget (select best products for $X)
- Hit profit target (build order to make $X profit)
- Restock inventory (prioritize low inventory)
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
import math

logger = logging.getLogger(__name__)


class RecommendationOptimizer:
    """Optimize product selection for different goals."""
    
    def __init__(self):
        pass
    
    def optimize_for_budget(
        self,
        scored_products: List[Dict[str, Any]],
        budget: float,
        max_days_to_sell: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Select best products to meet budget constraint.
        
        Args:
            scored_products: List of products with scores and cost/profit data
            budget: Maximum budget to spend
            max_days_to_sell: Optional max days constraint
        
        Returns:
            {
                'products': [...],
                'total_cost': 2000.0,
                'total_profit': 8500.0,
                'roi': 425.0,
                'avg_days_to_sell': 35.0
            }
        """
        # Sort by score (highest first)
        sorted_products = sorted(scored_products, key=lambda p: p.get('score', 0), reverse=True)
        
        selected = []
        total_cost = 0.0
        total_profit = 0.0
        total_units = 0
        
        for product in sorted_products:
            # Check if we're close to budget (within 5%)
            if total_cost >= budget * 0.95:
                break
            
            # Get product data
            unit_cost = float(product.get('unit_cost', 0))
            profit_per_unit = float(product.get('profit_per_unit', 0))
            pack_size = int(product.get('pack_size', 1))
            monthly_sales = float(product.get('monthly_sales', 0))
            
            if unit_cost <= 0:
                continue
            
            # Calculate max quantity we can afford
            remaining_budget = budget - total_cost
            max_qty_by_budget = math.floor(remaining_budget / unit_cost)
            
            # Don't buy more than we can sell in reasonable time
            max_qty_by_velocity = float('inf')
            if monthly_sales > 0:
                days_to_sell_100 = (100 / (monthly_sales / 30))
                if max_days_to_sell:
                    max_sellable_units = (monthly_sales / 30) * max_days_to_sell
                    max_qty_by_velocity = math.floor(max_sellable_units)
            
            # Take the minimum
            max_qty = min(max_qty_by_budget, max_qty_by_velocity)
            
            if max_qty <= 0:
                continue
            
            # Round to pack size
            qty = math.floor(max_qty / pack_size) * pack_size
            
            if qty <= 0:
                continue
            
            # Calculate costs and profit
            cost = qty * unit_cost
            profit = qty * profit_per_unit
            days_to_sell = (qty / (monthly_sales / 30)) if monthly_sales > 0 else 999
            
            selected.append({
                **product,
                'recommended_quantity': qty,
                'recommended_cost': cost,
                'expected_profit': profit,
                'days_to_sell': days_to_sell
            })
            
            total_cost += cost
            total_profit += profit
            total_units += qty
            
            # Stop if we hit budget
            if total_cost >= budget:
                break
        
        # Calculate average days to sell (weighted by units)
        total_days_weighted = sum(
            p['days_to_sell'] * p['recommended_quantity'] for p in selected
        )
        avg_days = total_days_weighted / total_units if total_units > 0 else 0
        
        roi = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'products': selected,
            'total_cost': round(total_cost, 2),
            'total_profit': round(total_profit, 2),
            'roi': round(roi, 2),
            'total_units': total_units,
            'avg_days_to_sell': round(avg_days, 1),
            'product_count': len(selected)
        }
    
    def optimize_for_profit(
        self,
        scored_products: List[Dict[str, Any]],
        profit_target: float,
        max_budget: Optional[float] = None,
        fast_pct: float = 0.60,
        medium_pct: float = 0.30,
        slow_pct: float = 0.10
    ) -> Dict[str, Any]:
        """
        Build order to hit profit target.
        
        Args:
            scored_products: List of products with scores
            profit_target: Target profit amount
            max_budget: Optional maximum budget
            fast_pct: % of profit from fast movers
            medium_pct: % of profit from medium movers
            slow_pct: % of profit from slow movers
        """
        # Categorize products by velocity
        fast_movers = []
        medium_movers = []
        slow_movers = []
        
        for product in scored_products:
            monthly_sales = float(product.get('monthly_sales', 0))
            if monthly_sales > 0:
                days_to_sell_100 = (100 / (monthly_sales / 30))
            else:
                days_to_sell_100 = 999
            
            if days_to_sell_100 < 30:
                fast_movers.append({**product, 'mover_category': 'fast', 'days_to_sell_100': days_to_sell_100})
            elif days_to_sell_100 < 60:
                medium_movers.append({**product, 'mover_category': 'medium', 'days_to_sell_100': days_to_sell_100})
            else:
                slow_movers.append({**product, 'mover_category': 'slow', 'days_to_sell_100': days_to_sell_100})
        
        # Sort each category by score
        fast_movers.sort(key=lambda p: p.get('score', 0), reverse=True)
        medium_movers.sort(key=lambda p: p.get('score', 0), reverse=True)
        slow_movers.sort(key=lambda p: p.get('score', 0), reverse=True)
        
        # Allocate profit targets
        fast_target = profit_target * fast_pct
        medium_target = profit_target * medium_pct
        slow_target = profit_target * slow_pct
        
        selected = []
        total_cost = 0.0
        total_profit = 0.0
        total_units = 0
        
        # Fill fast movers first
        for product in fast_movers:
            if total_profit >= fast_target + medium_target + slow_target:
                break
            
            if total_profit >= fast_target:
                break  # Move to medium movers
            
            result = self._add_product_to_selection(
                product, selected, total_cost, total_profit,
                max_budget, max_units_from_velocity=True
            )
            if result:
                selected.append(result['product'])
                total_cost = result['total_cost']
                total_profit = result['total_profit']
                total_units += result['quantity']
        
        # Fill medium movers
        for product in medium_movers:
            if total_profit >= fast_target + medium_target + slow_target:
                break
            
            if total_profit >= fast_target + medium_target:
                break  # Move to slow movers
            
            result = self._add_product_to_selection(
                product, selected, total_cost, total_profit,
                max_budget, max_units_from_velocity=True
            )
            if result:
                selected.append(result['product'])
                total_cost = result['total_cost']
                total_profit = result['total_profit']
                total_units += result['quantity']
        
        # Fill slow movers
        for product in slow_movers:
            if total_profit >= profit_target * 0.98:  # Within 2% of target
                break
            
            result = self._add_product_to_selection(
                product, selected, total_cost, total_profit,
                max_budget, max_units_from_velocity=True
            )
            if result:
                selected.append(result['product'])
                total_cost = result['total_cost']
                total_profit = result['total_profit']
                total_units += result['quantity']
        
        # Calculate metrics
        total_days_weighted = sum(
            p.get('days_to_sell', 0) * p.get('recommended_quantity', 0) for p in selected
        )
        avg_days = total_days_weighted / total_units if total_units > 0 else 0
        
        roi = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'products': selected,
            'total_cost': round(total_cost, 2),
            'total_profit': round(total_profit, 2),
            'roi': round(roi, 2),
            'total_units': total_units,
            'avg_days_to_sell': round(avg_days, 1),
            'product_count': len(selected),
            'fast_movers': len([p for p in selected if p.get('mover_category') == 'fast']),
            'medium_movers': len([p for p in selected if p.get('mover_category') == 'medium']),
            'slow_movers': len([p for p in selected if p.get('mover_category') == 'slow'])
        }
    
    def optimize_for_restock(
        self,
        scored_products: List[Dict[str, Any]],
        current_inventory: Dict[str, int],  # {product_id: current_qty}
        reorder_points: Dict[str, int],  # {product_id: reorder_point}
        max_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Prioritize products below reorder point.
        
        Args:
            scored_products: List of products with scores
            current_inventory: Current FBA inventory levels
            reorder_points: Reorder point for each product
            max_budget: Optional maximum budget
        """
        # Find products below reorder point
        urgent_products = []
        
        for product in scored_products:
            product_id = product.get('product_id')
            current_qty = current_inventory.get(product_id, 0)
            reorder_point = reorder_points.get(product_id, 0)
            
            if current_qty < reorder_point:
                # Calculate urgency (days until stockout)
                monthly_sales = float(product.get('monthly_sales', 0))
                if monthly_sales > 0:
                    daily_sales = monthly_sales / 30
                    days_until_stockout = current_qty / daily_sales if daily_sales > 0 else 0
                    
                    # Calculate suggested order qty
                    # Order enough to get back above reorder point + safety stock
                    suggested_qty = max(reorder_point - current_qty + int(reorder_point * 0.5), 0)
                    
                    urgent_products.append({
                        **product,
                        'days_until_stockout': days_until_stockout,
                        'current_qty': current_qty,
                        'reorder_point': reorder_point,
                        'suggested_qty': suggested_qty,
                        'urgency': 'critical' if days_until_stockout < 7 else 'urgent' if days_until_stockout < 14 else 'low'
                    })
        
        # Sort by urgency and score
        urgent_products.sort(key=lambda p: (
            0 if p['urgency'] == 'critical' else 1 if p['urgency'] == 'urgent' else 2,
            -p.get('score', 0)
        ))
        
        selected = []
        total_cost = 0.0
        total_profit = 0.0
        total_units = 0
        
        for product in urgent_products:
            # Use suggested quantity
            suggested_qty = product.get('suggested_qty', 0)
            pack_size = int(product.get('pack_size', 1))
            
            # Round to pack size
            qty = math.floor(suggested_qty / pack_size) * pack_size
            if qty <= 0:
                qty = pack_size  # At least 1 pack
            
            # Check budget
            unit_cost = float(product.get('unit_cost', 0))
            cost = qty * unit_cost
            
            if max_budget and total_cost + cost > max_budget:
                # Reduce quantity to fit budget
                remaining_budget = max_budget - total_cost
                max_qty = math.floor(remaining_budget / unit_cost)
                qty = math.floor(max_qty / pack_size) * pack_size
                cost = qty * unit_cost
            
            if qty <= 0:
                continue
            
            profit = qty * float(product.get('profit_per_unit', 0))
            
            selected.append({
                **product,
                'recommended_quantity': qty,
                'recommended_cost': cost,
                'expected_profit': profit
            })
            
            total_cost += cost
            total_profit += profit
            total_units += qty
            
            if max_budget and total_cost >= max_budget:
                break
        
        roi = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'products': selected,
            'total_cost': round(total_cost, 2),
            'total_profit': round(total_profit, 2),
            'roi': round(roi, 2),
            'total_units': total_units,
            'product_count': len(selected),
            'critical_count': len([p for p in selected if p.get('urgency') == 'critical']),
            'urgent_count': len([p for p in selected if p.get('urgency') == 'urgent'])
        }
    
    def _add_product_to_selection(
        self,
        product: Dict[str, Any],
        existing_selection: List[Dict[str, Any]],
        current_total_cost: float,
        current_total_profit: float,
        max_budget: Optional[float] = None,
        max_units_from_velocity: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Helper to add a product to selection with constraints."""
        unit_cost = float(product.get('unit_cost', 0))
        profit_per_unit = float(product.get('profit_per_unit', 0))
        pack_size = int(product.get('pack_size', 1))
        monthly_sales = float(product.get('monthly_sales', 0))
        
        if unit_cost <= 0:
            return None
        
        # Determine quantity
        if max_budget:
            remaining_budget = max_budget - current_total_cost
            max_qty_by_budget = math.floor(remaining_budget / unit_cost)
        else:
            max_qty_by_budget = float('inf')
        
        max_qty = max_qty_by_budget
        
        if max_units_from_velocity and monthly_sales > 0:
            # Don't buy more than 1.5 months of sales
            max_sellable = math.floor((monthly_sales / 30) * 45)
            max_qty = min(max_qty, max_sellable)
        
        if max_qty <= 0:
            return None
        
        # Round to pack size
        qty = math.floor(max_qty / pack_size) * pack_size
        if qty <= 0:
            return None
        
        cost = qty * unit_cost
        profit = qty * profit_per_unit
        
        days_to_sell = (qty / (monthly_sales / 30)) if monthly_sales > 0 else 999
        
        return {
            'product': {
                **product,
                'recommended_quantity': qty,
                'recommended_cost': cost,
                'expected_profit': profit,
                'days_to_sell': days_to_sell
            },
            'quantity': qty,
            'total_cost': current_total_cost + cost,
            'total_profit': current_total_profit + profit
        }

