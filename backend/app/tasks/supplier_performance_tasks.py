"""
Supplier Performance Calculation Tasks
- Calculate performance metrics
- Update scorecards
- Track variances
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from decimal import Decimal

from app.celery_app import celery
from app.core.database import supabase

logger = logging.getLogger(__name__)


@celery.task(name="suppliers.calculate_performance")
def calculate_supplier_performance(user_id: str = None, supplier_id: str = None):
    """
    Calculate performance metrics for suppliers.
    Runs periodically (weekly or monthly).
    """
    try:
        logger.info(f"Starting supplier performance calculation for user: {user_id or 'all'}, supplier: {supplier_id or 'all'}")
        
        # Get suppliers to calculate
        query = supabase.table('suppliers').select('id, user_id, name')
        if user_id:
            query = query.eq('user_id', user_id)
        if supplier_id:
            query = query.eq('id', supplier_id)
        
        suppliers = query.execute().data
        
        if not suppliers:
            logger.info("No suppliers found")
            return {"success": True, "suppliers_updated": 0}
        
        suppliers_updated = 0
        
        for supplier in suppliers:
            try:
                uid = supplier['user_id']
                sid = supplier['id']
                
                # Get all orders for this supplier
                orders_result = supabase.table('supplier_orders').select(
                    '''
                    *,
                    order_items:supplier_order_items(*)
                    '''
                ).eq('supplier_id', sid).eq('user_id', uid).execute()
                
                orders = orders_result.data or []
                
                if not orders:
                    continue
                
                # Calculate metrics
                total_orders = len(orders)
                total_spend = sum(float(o.get('total_cost', 0) or 0) for o in orders)
                total_products = sum(len(o.get('order_items', [])) for o in orders)
                total_units = sum(
                    sum(float(item.get('quantity', 0) or 0) for item in o.get('order_items', []))
                    for o in orders
                )
                avg_order_value = total_spend / total_orders if total_orders > 0 else 0
                
                # Delivery performance
                completed_orders = [o for o in orders if o.get('status') in ['received', 'completed']]
                on_time_orders = 0
                late_orders = 0
                early_orders = 0
                total_delivery_days = 0
                delivery_count = 0
                
                for order in completed_orders:
                    expected = order.get('expected_delivery_date')
                    actual = order.get('received_date')
                    
                    if expected and actual:
                        try:
                            expected_date = datetime.fromisoformat(expected.replace('Z', '+00:00')).date()
                            actual_date = datetime.fromisoformat(actual.replace('Z', '+00:00')).date()
                            
                            days_diff = (actual_date - expected_date).days
                            
                            if days_diff <= 0:
                                on_time_orders += 1
                            elif days_diff > 0:
                                late_orders += 1
                            else:
                                early_orders += 1
                            
                            # Calculate delivery time
                            order_date = order.get('created_at')
                            if order_date:
                                order_dt = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                                delivery_days = (actual_date - order_dt.date()).days
                                total_delivery_days += delivery_days
                                delivery_count += 1
                        except:
                            pass
                
                on_time_rate = (on_time_orders / len(completed_orders) * 100) if completed_orders else 0
                avg_delivery_days = total_delivery_days / delivery_count if delivery_count > 0 else 0
                
                # Quality metrics (from order variances)
                variances_result = supabase.table('order_variances').select('*').eq(
                    'user_id', uid
                ).in_('supplier_order_id', [o['id'] for o in orders]).execute()
                
                variances = variances_result.data or []
                total_received = sum(int(v.get('received_quantity', 0) or 0) for v in variances)
                total_damaged = sum(int(v.get('damaged_quantity', 0) or 0) for v in variances)
                total_missing = sum(int(v.get('missing_quantity', 0) or 0) for v in variances)
                
                quality_issue_rate = 0
                if total_received > 0:
                    quality_issue_rate = ((total_damaged + total_missing) / total_received) * 100
                
                # Profitability metrics
                # Get profit data from products linked to this supplier
                products_result = supabase.table('products').select(
                    '''
                    id,
                    product_sources!inner(
                        supplier_id,
                        roi_percentage,
                        margin_percentage,
                        profit_amount
                    )
                    '''
                ).eq('product_sources.supplier_id', sid).eq('user_id', uid).execute()
                
                products = products_result.data or []
                total_profit = 0
                roi_values = []
                margin_values = []
                
                for product in products:
                    sources = product.get('product_sources', [])
                    for source in sources:
                        if source.get('profit_amount'):
                            total_profit += float(source.get('profit_amount', 0))
                        if source.get('roi_percentage'):
                            roi_values.append(float(source.get('roi_percentage', 0)))
                        if source.get('margin_percentage'):
                            margin_values.append(float(source.get('margin_percentage', 0)))
                
                avg_roi = sum(roi_values) / len(roi_values) if roi_values else 0
                avg_margin = sum(margin_values) / len(margin_values) if margin_values else 0
                
                # Calculate ratings (1-5 stars)
                delivery_rating = min(5, max(0, (on_time_rate / 100) * 5))
                quality_rating = max(0, 5 - (quality_issue_rate / 20))  # 0% issues = 5 stars, 100% issues = 0 stars
                profitability_rating = min(5, max(0, (avg_roi / 100)))  # 100% ROI = 5 stars
                
                # Communication rating (placeholder - would need feedback system)
                communication_rating = 4.0
                
                # Overall rating (weighted average)
                overall_rating = (
                    delivery_rating * 0.3 +
                    quality_rating * 0.3 +
                    profitability_rating * 0.25 +
                    communication_rating * 0.15
                )
                
                # Get best selling products
                best_sellers = []
                for product in products[:10]:  # Top 10
                    sources = product.get('product_sources', [])
                    for source in sources:
                        if source.get('profit_amount'):
                            best_sellers.append({
                                'product_id': product['id'],
                                'profit': float(source.get('profit_amount', 0)),
                                'roi': float(source.get('roi_percentage', 0))
                            })
                
                best_sellers.sort(key=lambda x: x['profit'], reverse=True)
                best_sellers = best_sellers[:10]
                
                # Upsert performance record
                period_start = datetime.utcnow().date().replace(day=1)  # First day of current month
                period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)  # Last day of month
                
                performance = {
                    'user_id': uid,
                    'supplier_id': sid,
                    'total_orders': total_orders,
                    'total_spend': float(total_spend),
                    'average_order_value': float(avg_order_value),
                    'total_products_ordered': total_products,
                    'total_units_ordered': int(total_units),
                    'orders_delivered_on_time': on_time_orders,
                    'orders_delivered_late': late_orders,
                    'orders_delivered_early': early_orders,
                    'on_time_delivery_rate': float(on_time_rate),
                    'average_delivery_days': int(avg_delivery_days),
                    'total_units_received': total_received,
                    'damaged_units': total_damaged,
                    'missing_units': total_missing,
                    'quality_issue_rate': float(quality_issue_rate),
                    'total_profit_generated': float(total_profit),
                    'average_roi': float(avg_roi),
                    'average_margin': float(avg_margin),
                    'delivery_rating': float(delivery_rating),
                    'quality_rating': float(quality_rating),
                    'profitability_rating': float(profitability_rating),
                    'communication_rating': float(communication_rating),
                    'overall_rating': float(overall_rating),
                    'best_selling_products': best_sellers,
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'period_type': 'all_time',
                    'calculated_at': datetime.utcnow().isoformat()
                }
                
                supabase.table('supplier_performance').upsert(
                    performance,
                    on_conflict='user_id,supplier_id,period_type,period_start'
                ).execute()
                
                suppliers_updated += 1
            
            except Exception as e:
                logger.error(f"Error calculating performance for supplier {supplier.get('id')}: {e}", exc_info=True)
                continue
        
        logger.info(f"Supplier performance calculation complete. Updated {suppliers_updated} suppliers.")
        
        return {
            "success": True,
            "suppliers_updated": suppliers_updated
        }
    
    except Exception as e:
        logger.error(f"Supplier performance calculation failed: {e}", exc_info=True)
        raise

