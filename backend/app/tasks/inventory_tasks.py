"""
Inventory Management Background Tasks
- Daily inventory snapshots
- Sales velocity calculations
- Reorder point calculations
- Alert generation
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from decimal import Decimal

from app.celery_app import celery
from app.core.database import supabase
from app.services.sp_api_client import SPAPIClient

logger = logging.getLogger(__name__)


@celery.task(name="inventory.daily_snapshot")
def daily_inventory_snapshot(user_id: str = None):
    """
    Daily task to snapshot FBA inventory levels for all products.
    Runs once per day, typically at 2 AM.
    """
    try:
        logger.info(f"Starting daily inventory snapshot for user: {user_id or 'all'}")
        
        # Get all products that have ASINs
        query = supabase.table('products').select('id, asin, user_id').not_.is_('asin', 'null')
        if user_id:
            query = query.eq('user_id', user_id)
        
        products = query.execute().data
        
        if not products:
            logger.info("No products found for inventory snapshot")
            return {"success": True, "snapshots_created": 0}
        
        snapshot_date = datetime.utcnow().date()
        snapshots_created = 0
        errors = []
        
        # Group products by user for API efficiency
        user_products = {}
        for product in products:
            uid = product['user_id']
            if uid not in user_products:
                user_products[uid] = []
            user_products[uid].append(product)
        
        # Process each user's products
        for uid, user_prods in user_products.items():
            try:
                sp_api_client = SPAPIClient(user_id=uid)
                
                # Batch fetch inventory (SP-API can handle multiple ASINs)
                asins = [p['asin'] for p in user_prods if p.get('asin') and not p['asin'].startswith('PENDING_')]
                
                if not asins:
                    continue
                
                # Fetch inventory data (in batches of 20 for SP-API)
                batch_size = 20
                for i in range(0, len(asins), batch_size):
                    batch_asins = asins[i:i+batch_size]
                    
                    try:
                        # Get inventory summaries from SP-API (requires user connection)
                        # Note: This will return zeros if user not connected
                        inventory_data = await sp_api_client.get_inventory_summaries(batch_asins, user_id=uid)
                        
                        # Create snapshots for each product
                        for product in user_prods:
                            if product['asin'] not in inventory_data:
                                continue
                            
                            inv = inventory_data[product['asin']]
                            
                            snapshot = {
                                'user_id': uid,
                                'product_id': product['id'],
                                'snapshot_date': snapshot_date.isoformat(),
                                'fba_fulfillable_qty': inv.get('fulfillable_quantity', 0),
                                'fba_inbound_working_qty': inv.get('inbound_working_quantity', 0),
                                'fba_inbound_shipped_qty': inv.get('inbound_shipped_quantity', 0),
                                'fba_reserved_qty': inv.get('reserved_quantity', 0),
                                'fba_unsellable_qty': inv.get('unfulfillable_quantity', 0),
                            }
                            
                            # Calculate totals
                            snapshot['fba_total_qty'] = (
                                snapshot['fba_fulfillable_qty'] +
                                snapshot['fba_inbound_working_qty'] +
                                snapshot['fba_inbound_shipped_qty']
                            )
                            snapshot['available_qty'] = snapshot['fba_fulfillable_qty']
                            snapshot['total_inbound_qty'] = (
                                snapshot['fba_inbound_working_qty'] +
                                snapshot['fba_inbound_shipped_qty']
                            )
                            
                            # Upsert snapshot (unique on user_id, product_id, snapshot_date)
                            supabase.table('inventory_snapshots').upsert(
                                snapshot,
                                on_conflict='user_id,product_id,snapshot_date'
                            ).execute()
                            
                            snapshots_created += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing batch {i}-{i+batch_size}: {e}", exc_info=True)
                        errors.append(str(e))
            
            except Exception as e:
                logger.error(f"Error processing user {uid}: {e}", exc_info=True)
                errors.append(str(e))
        
        logger.info(f"Daily inventory snapshot complete. Created {snapshots_created} snapshots.")
        
        return {
            "success": True,
            "snapshots_created": snapshots_created,
            "errors": errors if errors else None
        }
    
    except Exception as e:
        logger.error(f"Daily inventory snapshot failed: {e}", exc_info=True)
        raise


@celery.task(name="inventory.calculate_forecasts")
def calculate_inventory_forecasts(user_id: str = None):
    """
    Calculate sales velocity, reorder points, and inventory status for all products.
    Runs after daily snapshot.
    """
    try:
        logger.info(f"Starting inventory forecast calculations for user: {user_id or 'all'}")
        
        # Get all products with snapshots
        query = supabase.table('products').select('id, user_id, asin, est_monthly_sales, current_sales_rank')
        if user_id:
            query = query.eq('user_id', user_id)
        
        products = query.execute().data
        
        if not products:
            logger.info("No products found for forecast calculation")
            return {"success": True, "forecasts_updated": 0}
        
        forecasts_updated = 0
        
        for product in products:
            try:
                product_id = product['id']
                uid = product['user_id']
                
                # Get latest snapshot
                snapshot_result = supabase.table('inventory_snapshots').select('*').eq(
                    'product_id', product_id
                ).eq('user_id', uid).order('snapshot_date', desc=True).limit(1).execute()
                
                if not snapshot_result.data:
                    continue
                
                snapshot = snapshot_result.data[0]
                current_qty = snapshot['available_qty'] or 0
                
                # Get estimated monthly sales from product or calculate from sales rank
                monthly_sales = product.get('est_monthly_sales') or 0
                
                # If no monthly sales data, estimate from sales rank
                if monthly_sales == 0 and product.get('current_sales_rank'):
                    # Rough estimation: BSR 1000 = ~100 sales/month, BSR 10000 = ~10 sales/month
                    bsr = product['current_sales_rank']
                    if bsr > 0:
                        monthly_sales = max(1, int(1000 / (bsr / 1000)))
                
                # Calculate average daily sales
                avg_daily_sales = Decimal(monthly_sales) / Decimal('30') if monthly_sales > 0 else Decimal('0')
                
                # Calculate sales velocity from snapshots (last 7, 30, 90 days)
                velocity_7d = _calculate_sales_velocity(product_id, uid, days=7)
                velocity_30d = _calculate_sales_velocity(product_id, uid, days=30)
                velocity_90d = _calculate_sales_velocity(product_id, uid, days=90) if avg_daily_sales > 0 else avg_daily_sales
                
                # Use best available velocity
                if velocity_30d > 0:
                    avg_daily_sales = velocity_30d
                elif velocity_7d > 0:
                    avg_daily_sales = velocity_7d
                elif avg_daily_sales == 0:
                    avg_daily_sales = velocity_90d
                
                # Calculate reorder point
                lead_time_days = 14  # Default
                safety_stock_days = 7  # Default
                reorder_point = int((avg_daily_sales * lead_time_days) + (avg_daily_sales * safety_stock_days))
                
                # Calculate optimal order quantity (2 months coverage)
                months_coverage = Decimal('2.0')
                optimal_order_qty = max(0, int((monthly_sales * months_coverage) - current_qty - snapshot.get('total_inbound_qty', 0)))
                
                # Calculate days remaining
                if avg_daily_sales > 0:
                    days_remaining = float(current_qty) / float(avg_daily_sales)
                else:
                    days_remaining = 999  # Infinite if no sales
                
                projected_stockout_date = (datetime.utcnow().date() + timedelta(days=int(days_remaining))) if days_remaining < 999 else None
                
                # Calculate status
                status = _calculate_inventory_status(current_qty, days_remaining, reorder_point)
                
                # Upsert forecast
                forecast = {
                    'user_id': uid,
                    'product_id': product_id,
                    'avg_daily_sales': float(avg_daily_sales),
                    'sales_velocity_7d': float(velocity_7d),
                    'sales_velocity_30d': float(velocity_30d),
                    'sales_velocity_90d': float(velocity_90d),
                    'lead_time_days': lead_time_days,
                    'safety_stock_days': safety_stock_days,
                    'reorder_point': reorder_point,
                    'months_coverage': float(months_coverage),
                    'optimal_order_qty': optimal_order_qty,
                    'current_fba_qty': current_qty,
                    'days_of_inventory_remaining': round(days_remaining, 1),
                    'projected_stockout_date': projected_stockout_date.isoformat() if projected_stockout_date else None,
                    'status': status,
                    'calculated_at': datetime.utcnow().isoformat()
                }
                
                supabase.table('inventory_forecasts').upsert(
                    forecast,
                    on_conflict='user_id,product_id'
                ).execute()
                
                forecasts_updated += 1
                
                # Generate alerts if needed
                _generate_reorder_alerts(uid, product_id, status, days_remaining, reorder_point, current_qty, optimal_order_qty, projected_stockout_date)
            
            except Exception as e:
                logger.error(f"Error calculating forecast for product {product.get('id')}: {e}", exc_info=True)
                continue
        
        logger.info(f"Inventory forecast calculation complete. Updated {forecasts_updated} forecasts.")
        
        return {
            "success": True,
            "forecasts_updated": forecasts_updated
        }
    
    except Exception as e:
        logger.error(f"Inventory forecast calculation failed: {e}", exc_info=True)
        raise


def _calculate_sales_velocity(product_id: str, user_id: str, days: int) -> Decimal:
    """Calculate sales velocity from inventory snapshots."""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        snapshots = supabase.table('inventory_snapshots').select('snapshot_date, available_qty').eq(
            'product_id', product_id
        ).eq('user_id', user_id).gte('snapshot_date', start_date.isoformat()).lte(
            'snapshot_date', end_date.isoformat()
        ).order('snapshot_date').execute().data
        
        if len(snapshots) < 2:
            return Decimal('0')
        
        # Calculate average daily change in inventory
        total_change = 0
        days_counted = 0
        
        for i in range(1, len(snapshots)):
            prev_qty = snapshots[i-1]['available_qty'] or 0
            curr_qty = snapshots[i]['available_qty'] or 0
            
            # Decrease in inventory = sales (assuming no new stock)
            if curr_qty < prev_qty:
                total_change += (prev_qty - curr_qty)
                days_counted += 1
        
        if days_counted == 0:
            return Decimal('0')
        
        # Average daily sales
        return Decimal(str(total_change / days_counted))
    
    except Exception as e:
        logger.error(f"Error calculating sales velocity: {e}", exc_info=True)
        return Decimal('0')


def _calculate_inventory_status(current_qty: int, days_remaining: float, reorder_point: int) -> str:
    """Calculate inventory status."""
    if current_qty == 0:
        return 'out_of_stock'
    elif current_qty < reorder_point:
        return 'reorder_now'
    elif days_remaining < 10:
        return 'low_stock'
    elif days_remaining > 90:
        return 'overstock'
    else:
        return 'healthy'


def _generate_reorder_alerts(
    user_id: str,
    product_id: str,
    status: str,
    days_remaining: float,
    reorder_point: int,
    current_qty: int,
    optimal_order_qty: int,
    projected_stockout_date: datetime.date
):
    """Generate reorder alerts for products needing attention."""
    try:
        alert_type = None
        severity = 'medium'
        message = ""
        
        if status == 'out_of_stock':
            alert_type = 'out_of_stock'
            severity = 'critical'
            message = f"Product is out of stock. Order {optimal_order_qty} units to restock."
        
        elif status == 'reorder_now':
            alert_type = 'reorder_point'
            severity = 'high'
            message = f"Product below reorder point ({current_qty}/{reorder_point} units). Suggested order: {optimal_order_qty} units."
        
        elif days_remaining > 90:
            alert_type = 'overstock'
            severity = 'low'
            message = f"Product overstocked ({days_remaining:.0f} days inventory). Consider reducing order size."
        
        elif days_remaining < 30 and status != 'reorder_now':
            alert_type = 'reorder_point'
            severity = 'medium'
            message = f"Product running low ({days_remaining:.0f} days remaining). Suggested order: {optimal_order_qty} units."
        
        if alert_type:
            # Check if alert already exists today
            existing = supabase.table('reorder_alerts').select('id').eq(
                'user_id', user_id
            ).eq('product_id', product_id).eq('alert_type', alert_type).eq(
                'created_at::date', datetime.utcnow().date().isoformat()
            ).limit(1).execute()
            
            if not existing.data:
                alert = {
                    'user_id': user_id,
                    'product_id': product_id,
                    'alert_type': alert_type,
                    'severity': severity,
                    'message': message,
                    'suggested_order_qty': optimal_order_qty,
                    'estimated_stockout_date': projected_stockout_date.isoformat() if projected_stockout_date else None
                }
                
                supabase.table('reorder_alerts').insert(alert).execute()
    
    except Exception as e:
        logger.error(f"Error generating alert: {e}", exc_info=True)

