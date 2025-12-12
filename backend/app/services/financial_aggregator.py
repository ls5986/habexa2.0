"""
Financial Aggregator Service
Aggregates costs and calculates ROI across the entire workflow.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)


class FinancialAggregator:
    """
    Aggregates costs from supplier orders → 3PL → FBA → Amazon
    and calculates ROI across the entire workflow.
    """
    
    @staticmethod
    def calculate_product_costs(product_id: str, user_id: str) -> Dict[str, Any]:
        """
        Calculate total costs for a product across the entire workflow.
        
        Returns:
            {
                'supplier_cost': Decimal,
                'tpl_prep_cost': Decimal,
                'tpl_storage_cost': Decimal,
                'shipping_cost': Decimal,
                'fba_fees': Decimal,
                'referral_fee': Decimal,
                'other_fees': Decimal,
                'total_cost': Decimal,
                'cost_breakdown': List[Dict]  # Detailed cost items
            }
        """
        costs = {
            'supplier_cost': Decimal('0'),
            'tpl_prep_cost': Decimal('0'),
            'tpl_storage_cost': Decimal('0'),
            'shipping_cost': Decimal('0'),
            'fba_fees': Decimal('0'),
            'referral_fee': Decimal('0'),
            'other_fees': Decimal('0'),
            'total_cost': Decimal('0'),
            'cost_breakdown': []
        }
        
        try:
            # Get product with all related entities
            product_res = supabase.table('products')\
                .select('''
                    id,
                    asin,
                    sell_price,
                    fba_fees,
                    referral_fee,
                    product_sources!inner(
                        id,
                        buy_cost,
                        wholesale_cost,
                        pack_size,
                        supplier_id,
                        supplier_orders!inner(
                            id,
                            total_cost,
                            shipping_method,
                            supplier_order_items!inner(
                                id,
                                quantity,
                                unit_cost,
                                total_cost
                            )
                        )
                    ),
                    tpl_inbound_items!inner(
                        id,
                        quantity,
                        tpl_inbound_id,
                        tpl_inbounds!inner(
                            id,
                            tpl_warehouse_id,
                            tpl_warehouses!inner(
                                id,
                                prep_fee_per_unit,
                                storage_fee_per_unit
                            )
                        )
                    ),
                    fba_shipment_items!inner(
                        id,
                        quantity_shipped,
                        fba_shipment_id,
                        fba_shipments!inner(
                            id,
                            estimated_shipping_cost,
                            actual_shipping_cost
                        )
                    )
                ''')\
                .eq('id', product_id)\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            if not product_res.data:
                logger.warning(f"Product {product_id} not found")
                return costs
            
            product = product_res.data
            
            # 1. Supplier Costs (from supplier orders)
            product_sources = product.get('product_sources', [])
            if isinstance(product_sources, dict):
                product_sources = [product_sources]
            
            for ps in product_sources or []:
                supplier_orders = ps.get('supplier_orders', [])
                if isinstance(supplier_orders, dict):
                    supplier_orders = [supplier_orders]
                
                for so in supplier_orders or []:
                    order_items = so.get('supplier_order_items', [])
                    if isinstance(order_items, dict):
                        order_items = [order_items]
                    
                    for item in order_items or []:
                        unit_cost = Decimal(str(item.get('unit_cost', 0)))
                        quantity = int(item.get('quantity', 1))
                        total = unit_cost * quantity
                        
                        costs['supplier_cost'] += total
                        costs['cost_breakdown'].append({
                            'type': 'supplier',
                            'category': 'product_cost',
                            'description': f"Supplier order {so.get('id', '')[:8]}",
                            'amount': float(total),
                            'quantity': quantity,
                            'unit_cost': float(unit_cost),
                            'source_id': so.get('id')
                        })
            
            # 2. 3PL Prep Costs
            tpl_inbound_items = product.get('tpl_inbound_items', [])
            if isinstance(tpl_inbound_items, dict):
                tpl_inbound_items = [tpl_inbound_items]
            
            for item in tpl_inbound_items or []:
                inbound = item.get('tpl_inbounds', {})
                if isinstance(inbound, list) and inbound:
                    inbound = inbound[0]
                
                warehouse = inbound.get('tpl_warehouses', {}) if inbound else {}
                if isinstance(warehouse, list) and warehouse:
                    warehouse = warehouse[0]
                
                prep_fee = Decimal(str(warehouse.get('prep_fee_per_unit', 0))) if warehouse else Decimal('0')
                quantity_prepped = int(item.get('quantity_prepped', item.get('quantity', 0)))
                
                if prep_fee > 0 and quantity_prepped > 0:
                    total_prep = prep_fee * quantity_prepped
                    costs['tpl_prep_cost'] += total_prep
                    costs['cost_breakdown'].append({
                        'type': 'tpl_prep',
                        'category': 'prep_cost',
                        'description': f"3PL prep - {warehouse.get('name', 'Unknown')}",
                        'amount': float(total_prep),
                        'quantity': quantity_prepped,
                        'unit_cost': float(prep_fee),
                        'source_id': inbound.get('id') if inbound else None
                    })
                
                # Storage costs (monthly, pro-rated)
                storage_fee = Decimal(str(warehouse.get('storage_fee_per_unit', 0))) if warehouse else Decimal('0')
                if storage_fee > 0:
                    # For now, calculate for 1 month (can be enhanced with actual storage duration)
                    quantity_received = int(item.get('quantity_received', item.get('quantity', 0)))
                    total_storage = storage_fee * quantity_received
                    costs['tpl_storage_cost'] += total_storage
                    costs['cost_breakdown'].append({
                        'type': 'tpl_storage',
                        'category': 'storage_cost',
                        'description': f"3PL storage (1 month) - {warehouse.get('name', 'Unknown')}",
                        'amount': float(total_storage),
                        'quantity': quantity_received,
                        'unit_cost': float(storage_fee),
                        'source_id': inbound.get('id') if inbound else None
                    })
            
            # 3. Shipping Costs (to 3PL and to Amazon)
            for item in tpl_inbound_items or []:
                inbound = item.get('tpl_inbounds', {})
                if isinstance(inbound, list) and inbound:
                    inbound = inbound[0]
                
                # Shipping to 3PL (if tracked separately, otherwise estimate)
                # For now, we'll use a placeholder - in production, get from supplier order shipping
                quantity = int(item.get('quantity', 0))
                if quantity > 0:
                    # Estimate: $0.50 per unit for shipping to 3PL
                    shipping_to_3pl = Decimal('0.50') * quantity
                    costs['shipping_cost'] += shipping_to_3pl
            
            # 4. FBA Shipping Costs
            fba_shipment_items = product.get('fba_shipment_items', [])
            if isinstance(fba_shipment_items, dict):
                fba_shipment_items = [fba_shipment_items]
            
            for item in fba_shipment_items or []:
                shipment = item.get('fba_shipments', {})
                if isinstance(shipment, list) and shipment:
                    shipment = shipment[0]
                
                # Use actual shipping cost if available, otherwise estimated
                actual_shipping = Decimal(str(shipment.get('actual_shipping_cost', 0))) if shipment else Decimal('0')
                estimated_shipping = Decimal(str(shipment.get('estimated_shipping_cost', 0))) if shipment else Decimal('0')
                
                shipping_cost = actual_shipping if actual_shipping > 0 else estimated_shipping
                
                if shipping_cost > 0:
                    # Pro-rate shipping cost per unit
                    total_units_in_shipment = int(shipment.get('total_units', 1)) if shipment else 1
                    quantity_shipped = int(item.get('quantity_shipped', 0))
                    
                    if total_units_in_shipment > 0:
                        unit_shipping = shipping_cost / Decimal(str(total_units_in_shipment))
                        item_shipping = unit_shipping * quantity_shipped
                        costs['shipping_cost'] += item_shipping
                        costs['cost_breakdown'].append({
                            'type': 'shipping',
                            'category': 'shipping_cost',
                            'description': f"FBA shipment {shipment.get('id', '')[:8]}",
                            'amount': float(item_shipping),
                            'quantity': quantity_shipped,
                            'unit_cost': float(unit_shipping),
                            'source_id': shipment.get('id') if shipment else None
                        })
            
            # 5. FBA Fees (from product data)
            fba_fees = Decimal(str(product.get('fba_fees', 0)))
            if fba_fees > 0:
                # Get total units shipped to calculate total FBA fees
                total_units_shipped = sum(
                    int(item.get('quantity_shipped', 0))
                    for item in fba_shipment_items or []
                )
                
                if total_units_shipped > 0:
                    total_fba_fees = fba_fees * total_units_shipped
                    costs['fba_fees'] = total_fba_fees
                    costs['cost_breakdown'].append({
                        'type': 'fba_fee',
                        'category': 'amazon_fee',
                        'description': 'FBA fulfillment fees',
                        'amount': float(total_fba_fees),
                        'quantity': total_units_shipped,
                        'unit_cost': float(fba_fees),
                        'source_id': None
                    })
            
            # 6. Referral Fee (from product data)
            referral_fee_pct = Decimal(str(product.get('referral_fee', 0)))
            sell_price = Decimal(str(product.get('sell_price', 0)))
            
            if referral_fee_pct > 0 and sell_price > 0:
                # Calculate referral fee per unit
                referral_fee_per_unit = sell_price * (referral_fee_pct / Decimal('100'))
                
                # Get total units for referral fee calculation
                total_units_shipped = sum(
                    int(item.get('quantity_shipped', 0))
                    for item in fba_shipment_items or []
                )
                
                if total_units_shipped > 0:
                    total_referral_fee = referral_fee_per_unit * total_units_shipped
                    costs['referral_fee'] = total_referral_fee
                    costs['cost_breakdown'].append({
                        'type': 'referral_fee',
                        'category': 'amazon_fee',
                        'description': f'Amazon referral fee ({referral_fee_pct}%)',
                        'amount': float(total_referral_fee),
                        'quantity': total_units_shipped,
                        'unit_cost': float(referral_fee_per_unit),
                        'source_id': None
                    })
            
            # Calculate total cost
            costs['total_cost'] = (
                costs['supplier_cost'] +
                costs['tpl_prep_cost'] +
                costs['tpl_storage_cost'] +
                costs['shipping_cost'] +
                costs['fba_fees'] +
                costs['referral_fee'] +
                costs['other_fees']
            )
            
            # Convert Decimal to float for JSON serialization
            for key in ['supplier_cost', 'tpl_prep_cost', 'tpl_storage_cost', 'shipping_cost', 
                       'fba_fees', 'referral_fee', 'other_fees', 'total_cost']:
                costs[key] = float(costs[key])
            
            return costs
            
        except Exception as e:
            logger.error(f"Error calculating product costs: {e}", exc_info=True)
            return costs
    
    @staticmethod
    def calculate_product_roi(
        product_id: str,
        user_id: str,
        revenue: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate ROI for a product including all costs.
        
        Args:
            product_id: Product ID
            user_id: User ID
            revenue: Actual revenue (if None, uses expected sell_price)
        
        Returns:
            {
                'total_cost': float,
                'revenue': float,
                'profit': float,
                'roi_percentage': float,
                'margin_percentage': float,
                'cost_breakdown': Dict
            }
        """
        try:
            # Get costs
            costs = FinancialAggregator.calculate_product_costs(product_id, user_id)
            
            # Get product for sell_price
            product_res = supabase.table('products')\
                .select('sell_price')\
                .eq('id', product_id)\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            sell_price = Decimal('0')
            if product_res.data:
                sell_price = Decimal(str(product_res.data.get('sell_price', 0)))
            
            # Use provided revenue or calculate from sell_price
            if revenue is None:
                # Get total units shipped to calculate expected revenue
                fba_items_res = supabase.table('fba_shipment_items')\
                    .select('quantity_shipped')\
                    .eq('product_id', product_id)\
                    .execute()
                
                total_units = sum(
                    int(item.get('quantity_shipped', 0))
                    for item in fba_items_res.data or []
                )
                
                revenue = float(sell_price * Decimal(str(total_units))) if sell_price > 0 and total_units > 0 else 0.0
            else:
                revenue = float(revenue)
            
            total_cost = costs['total_cost']
            profit = revenue - total_cost
            
            roi_percentage = (profit / total_cost * 100) if total_cost > 0 else 0.0
            margin_percentage = (profit / revenue * 100) if revenue > 0 else 0.0
            
            return {
                'total_cost': total_cost,
                'revenue': revenue,
                'profit': profit,
                'roi_percentage': round(roi_percentage, 2),
                'margin_percentage': round(margin_percentage, 2),
                'cost_breakdown': costs
            }
            
        except Exception as e:
            logger.error(f"Error calculating product ROI: {e}", exc_info=True)
            return {
                'total_cost': 0.0,
                'revenue': 0.0,
                'profit': 0.0,
                'roi_percentage': 0.0,
                'margin_percentage': 0.0,
                'cost_breakdown': {}
            }
    
    @staticmethod
    def aggregate_workflow_costs(
        buy_list_id: Optional[str] = None,
        supplier_order_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate costs for an entire buy list or supplier order.
        
        Returns:
            {
                'total_supplier_cost': float,
                'total_tpl_cost': float,
                'total_shipping_cost': float,
                'total_fba_fees': float,
                'total_referral_fees': float,
                'total_cost': float,
                'product_count': int,
                'unit_count': int,
                'cost_per_unit': float
            }
        """
        aggregation = {
            'total_supplier_cost': Decimal('0'),
            'total_tpl_cost': Decimal('0'),
            'total_shipping_cost': Decimal('0'),
            'total_fba_fees': Decimal('0'),
            'total_referral_fees': Decimal('0'),
            'total_cost': Decimal('0'),
            'product_count': 0,
            'unit_count': 0,
            'cost_per_unit': Decimal('0')
        }
        
        try:
            # Get products from buy list or supplier order
            if buy_list_id:
                items_res = supabase.table('buy_list_items')\
                    .select('product_id')\
                    .eq('buy_list_id', buy_list_id)\
                    .execute()
                
                product_ids = [item.get('product_id') for item in items_res.data or []]
            elif supplier_order_id:
                items_res = supabase.table('supplier_order_items')\
                    .select('product_id')\
                    .eq('supplier_order_id', supplier_order_id)\
                    .execute()
                
                product_ids = [item.get('product_id') for item in items_res.data or []]
            else:
                return aggregation
            
            # Calculate costs for each product
            for product_id in product_ids:
                if not product_id:
                    continue
                
                costs = FinancialAggregator.calculate_product_costs(product_id, user_id)
                
                aggregation['total_supplier_cost'] += Decimal(str(costs['supplier_cost']))
                aggregation['total_tpl_cost'] += (
                    Decimal(str(costs['tpl_prep_cost'])) +
                    Decimal(str(costs['tpl_storage_cost']))
                )
                aggregation['total_shipping_cost'] += Decimal(str(costs['shipping_cost']))
                aggregation['total_fba_fees'] += Decimal(str(costs['fba_fees']))
                aggregation['total_referral_fees'] += Decimal(str(costs['referral_fee']))
                aggregation['product_count'] += 1
            
            # Calculate totals
            aggregation['total_cost'] = (
                aggregation['total_supplier_cost'] +
                aggregation['total_tpl_cost'] +
                aggregation['total_shipping_cost'] +
                aggregation['total_fba_fees'] +
                aggregation['total_referral_fees']
            )
            
            # Get unit count
            if buy_list_id:
                units_res = supabase.table('buy_lists')\
                    .select('total_units')\
                    .eq('id', buy_list_id)\
                    .single()\
                    .execute()
                
                aggregation['unit_count'] = int(units_res.data.get('total_units', 0)) if units_res.data else 0
            elif supplier_order_id:
                units_res = supabase.table('supplier_orders')\
                    .select('total_units')\
                    .eq('id', supplier_order_id)\
                    .single()\
                    .execute()
                
                aggregation['unit_count'] = int(units_res.data.get('total_units', 0)) if units_res.data else 0
            
            # Calculate cost per unit
            if aggregation['unit_count'] > 0:
                aggregation['cost_per_unit'] = aggregation['total_cost'] / Decimal(str(aggregation['unit_count']))
            
            # Convert to float
            for key in ['total_supplier_cost', 'total_tpl_cost', 'total_shipping_cost', 
                       'total_fba_fees', 'total_referral_fees', 'total_cost', 'cost_per_unit']:
                aggregation[key] = float(aggregation[key])
            
            return aggregation
            
        except Exception as e:
            logger.error(f"Error aggregating workflow costs: {e}", exc_info=True)
            return aggregation

