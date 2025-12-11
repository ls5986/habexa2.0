"""
Orders API - Manage purchase requests to suppliers
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from app.api.deps import get_current_user
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["orders"])  # FIX: Remove prefix - main.py adds /api/v1/orders


class CreateOrderRequest(BaseModel):
    supplier_id: Optional[str] = None
    product_ids: List[str]  # List of product IDs (deal_ids) to add to order
    notes: Optional[str] = None


class UpdateOrderItemRequest(BaseModel):
    quantity: int
    discount: float = 0.0


class UpdateOrderStatusRequest(BaseModel):
    status: str  # draft, sent, received


class SendOrderRequest(BaseModel):
    recipient_email: Optional[str] = None
    message: Optional[str] = None


class CreateOrdersFromProductsRequest(BaseModel):
    product_ids: List[str]  # List of deal_ids (can be from multiple suppliers)
    notes: Optional[str] = None


@router.post("")
async def create_order(
    request: CreateOrderRequest,
    current_user=Depends(get_current_user)
):
    """
    Create a purchase request for a SINGLE supplier.
    
    For creating orders from mixed suppliers, use:
    POST /orders/create-from-products
    
    This endpoint is useful when you know all products
    are from the same supplier.
    
    Body:
    {
        "supplier_id": "uuid" (optional),
        "product_ids": ["deal_id1", "deal_id2"],
        "notes": "Negotiated 5% discount"
    }
    
    Returns order with items and calculated totals.
    """
    user_id = str(current_user.id)
    
    if not request.product_ids:
        raise HTTPException(400, "At least one product is required")
    
    try:
        # Get deals (product_sources) to get buy_cost and supplier info
        deals_result = supabase.table('product_sources') \
            .select('*, product:products(*), supplier:suppliers(*)') \
            .in_('id', request.product_ids) \
            .execute()
        
        if not deals_result.data or len(deals_result.data) != len(request.product_ids):
            raise HTTPException(404, "Some products not found")
        
        # Verify all products belong to user
        for deal in deals_result.data:
            product = deal.get('product', {})
            if not product or product.get('user_id') != user_id:
                raise HTTPException(403, "Some products don't belong to you")
        
        # Determine supplier_id (use from request or from first deal)
        supplier_id = request.supplier_id
        if not supplier_id:
            # Get supplier from first deal
            first_deal = deals_result.data[0]
            supplier_id = first_deal.get('supplier_id')
            if not supplier_id:
                # Check if all deals have same supplier
                suppliers = set(d.get('supplier_id') for d in deals_result.data if d.get('supplier_id'))
                if len(suppliers) == 1:
                    supplier_id = suppliers.pop()
        
        # Create order
        order_data = {
            'user_id': user_id,
            'supplier_id': supplier_id,
            'status': 'draft',
            'notes': request.notes,
            'total_amount': 0,  # Will calculate
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        order_result = supabase.table('orders').insert(order_data).execute()
        
        if not order_result.data:
            raise HTTPException(500, "Failed to create order")
        
        order = order_result.data[0]
        order_id = order['id']
        
        # Add products to order
        order_items = []
        total_amount = 0.0
        
        for deal in deals_result.data:
            product = deal.get('product', {})
            if not product:
                continue
            
            buy_cost = deal.get('buy_cost', 0) or 0
            quantity = deal.get('moq', 1) or 1
            
            # Calculate item subtotal (quantity * buy_cost - discount)
            # Discount is 0 for now, can be updated later
            discount = 0.0
            item_subtotal = (quantity * float(buy_cost)) - discount
            total_amount += item_subtotal
            
            # Create order item
            item_data = {
                'order_id': order_id,
                'product_id': product['id'],
                'quantity': quantity,
                'unit_cost': float(buy_cost),
                'discount': discount,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            item_result = supabase.table('order_items').insert(item_data).execute()
            
            if item_result.data:
                item = item_result.data[0]
                # Add product details to item
                item['product'] = product
                item['subtotal'] = round(item_subtotal, 2)
                order_items.append(item)
        
        # Update order total
        supabase.table('orders').update({
            'total_amount': round(total_amount, 2),
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', order_id).execute()
        
        # Get supplier info
        supplier = None
        if supplier_id:
            supplier_result = supabase.table('suppliers') \
                .select('*') \
                .eq('id', supplier_id) \
                .eq('user_id', user_id) \
                .single() \
                .execute()
            
            if supplier_result.data:
                supplier = supplier_result.data
        
        order['supplier'] = supplier
        order['items'] = order_items
        order['total_amount'] = round(total_amount, 2)
        order['items_count'] = len(order_items)
        
        logger.info(f"✅ Created order {order_id} with {len(order_items)} items, total: ${total_amount:.2f}")
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create order: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create order: {str(e)}")


@router.get("")
async def get_orders(
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_user=Depends(get_current_user)
):
    """
    Get all orders for user.
    Optionally filter by status or supplier.
    """
    user_id = str(current_user.id)
    
    try:
        # Start with base query
        query = supabase.table('orders') \
            .select('*, supplier:suppliers(id, name, contact_name, contact_email), items:order_items(*, product:products(*))') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(limit)
        
        if status:
            query = query.eq('status', status)
        
        if supplier_id:
            query = query.eq('supplier_id', supplier_id)
        
        result = query.execute()
        
        # Calculate items_count and format response
        orders = result.data or []
        for order in orders:
            items = order.get('items', []) or []
            order['items_count'] = len(items)
            # Calculate subtotals for each item
            for item in items:
                quantity = item.get('quantity', 1) or 1
                unit_cost = item.get('unit_cost', 0) or 0
                discount = item.get('discount', 0) or 0
                item['subtotal'] = round((quantity * float(unit_cost)) - float(discount), 2)
        
        logger.info(f"✅ Retrieved {len(orders)} orders for user {user_id}")
        return orders
        
    except Exception as e:
        logger.error(f"❌ Failed to get orders: {e}", exc_info=True)
        # Try simpler query without nested joins as fallback
        try:
            logger.info("🔄 Retrying with simpler query (no nested joins)...")
            query = supabase.table('orders') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit)
            
            if status:
                query = query.eq('status', status)
            
            if supplier_id:
                query = query.eq('supplier_id', supplier_id)
            
            result = query.execute()
            orders = result.data or []
            
            # Manually fetch supplier and items for each order
            for order in orders:
                order['items_count'] = 0
                order['items'] = []
                
                # Get supplier
                if order.get('supplier_id'):
                    try:
                        supplier_result = supabase.table('suppliers') \
                            .select('id, name, contact_name, contact_email') \
                            .eq('id', order['supplier_id']) \
                            .eq('user_id', user_id) \
                            .single() \
                            .execute()
                        if supplier_result.data:
                            order['supplier'] = supplier_result.data
                    except:
                        order['supplier'] = None
                
                # Get items
                try:
                    items_result = supabase.table('order_items') \
                        .select('*, product:products(*)') \
                        .eq('order_id', order['id']) \
                        .execute()
                    
                    items = items_result.data or []
                    order['items'] = items
                    order['items_count'] = len(items)
                    
                    # Calculate subtotals
                    for item in items:
                        quantity = item.get('quantity', 1) or 1
                        unit_cost = item.get('unit_cost', 0) or 0
                        discount = item.get('discount', 0) or 0
                        item['subtotal'] = round((quantity * float(unit_cost)) - float(discount), 2)
                except Exception as items_error:
                    logger.warning(f"Failed to fetch items for order {order.get('id')}: {items_error}")
                    order['items'] = []
                    order['items_count'] = 0
            
            logger.info(f"✅ Retrieved {len(orders)} orders (fallback query)")
            return orders
            
        except Exception as fallback_error:
            logger.error(f"❌ Fallback query also failed: {fallback_error}", exc_info=True)
            raise HTTPException(500, f"Failed to retrieve orders: {str(fallback_error)}")


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """
    Get order details with items and products.
    """
    user_id = str(current_user.id)
    
    result = supabase.table('orders') \
        .select('*, supplier:suppliers(*), items:order_items(*, product:products(*))') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Order not found")
    
    order = result.data
    
    # Calculate subtotals and totals
    items = order.get('items', [])
    subtotal = 0.0
    total_discount = 0.0
    
    for item in items:
        quantity = item.get('quantity', 1)
        unit_cost = item.get('unit_cost', 0) or 0
        discount = item.get('discount', 0) or 0
        
        item_subtotal = (quantity * float(unit_cost)) - float(discount)
        item['subtotal'] = round(item_subtotal, 2)
        
        subtotal += quantity * float(unit_cost)
        total_discount += float(discount)
    
    order['subtotal'] = round(subtotal, 2)
    order['total_discount'] = round(total_discount, 2)
    order['total_cost'] = round(subtotal - total_discount, 2)
    order['items_count'] = len(items)
    
    return order


@router.put("/{order_id}/items/{product_id}")
async def update_order_item(
    order_id: str,
    product_id: str,
    request: UpdateOrderItemRequest,
    current_user=Depends(get_current_user)
):
    """
    Update quantity or discount for product in order.
    
    Body:
    {
        "quantity": 100,
        "discount": 25.00
    }
    
    Recalculates order total.
    """
    user_id = str(current_user.id)
    
    # Verify order belongs to user
    order_result = supabase.table('orders') \
        .select('*') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    if request.quantity < 1:
        raise HTTPException(400, "Quantity must be at least 1")
    
    if request.discount < 0:
        raise HTTPException(400, "Discount cannot be negative")
    
    try:
        # Get current item
        item_result = supabase.table('order_items') \
            .select('*') \
            .eq('order_id', order_id) \
            .eq('product_id', product_id) \
            .single() \
            .execute()
        
        if not item_result.data:
            raise HTTPException(404, "Product not found in order")
        
        item = item_result.data
        unit_cost = item.get('unit_cost', 0) or 0
        
        # Update item
        supabase.table('order_items').update({
            'quantity': request.quantity,
            'discount': request.discount,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', item['id']).execute()
        
        # Recalculate order total
        items_result = supabase.table('order_items') \
            .select('quantity, unit_cost, discount') \
            .eq('order_id', order_id) \
            .execute()
        
        total_amount = 0.0
        for order_item in (items_result.data or []):
            qty = order_item.get('quantity', 1)
            cost = float(order_item.get('unit_cost', 0) or 0)
            disc = float(order_item.get('discount', 0) or 0)
            total_amount += (qty * cost) - disc
        
        # Update order total
        supabase.table('orders').update({
            'total_amount': round(total_amount, 2),
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', order_id).execute()
        
        # Get updated item with product
        updated_item = supabase.table('order_items') \
            .select('*, product:products(*)') \
            .eq('id', item['id']) \
            .single() \
            .execute()
        
        if updated_item.data:
            item = updated_item.data[0]
            qty = item.get('quantity', 1)
            cost = float(item.get('unit_cost', 0) or 0)
            disc = float(item.get('discount', 0) or 0)
            item['subtotal'] = round((qty * cost) - disc, 2)
        
        logger.info(f"✅ Updated order item: quantity={request.quantity}, discount=${request.discount:.2f}")
        
        return {
            'success': True,
            'item': item,
            'order_total': round(total_amount, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update order item: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update order item: {str(e)}")


@router.patch("/{order_id}")
async def update_order_status(
    order_id: str,
    request: UpdateOrderStatusRequest,
    current_user=Depends(get_current_user)
):
    """
    Update order status.
    
    Body:
    {
        "status": "sent"  // draft, sent, received
    }
    """
    user_id = str(current_user.id)
    
    valid_statuses = ['draft', 'sent', 'received', 'cancelled']
    if request.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Verify order belongs to user
    order_result = supabase.table('orders') \
        .select('*') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    update_data = {
        'status': request.status,
        'updated_at': datetime.utcnow().isoformat()
    }
    
    # Add sent_at timestamp if status is 'sent'
    if request.status == 'sent':
        update_data['sent_at'] = datetime.utcnow().isoformat()
    
    supabase.table('orders').update(update_data).eq('id', order_id).execute()
    
    logger.info(f"✅ Updated order {order_id} status to {request.status}")
    
    return {
        'success': True,
        'order_id': order_id,
        'status': request.status
    }


@router.post("/{order_id}/revert-to-buy-list")
async def revert_order_to_buy_list(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """
    Revert order back to buy list.
    - Moves all products in the order back to buy_list stage
    - Marks order as cancelled
    - Does NOT delete the order (keeps history)
    """
    user_id = str(current_user.id)
    
    # Get order with items
    order_result = supabase.table('orders') \
        .select('*, items:order_items(product_id)') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    order = order_result.data
    items = order.get('items', [])
    
    if not items:
        raise HTTPException(400, "Order has no items to revert")
    
    try:
        # Get all product_sources (deals) for products in this order
        product_ids = [item.get('product_id') for item in items if item.get('product_id')]
        
        if not product_ids:
            raise HTTPException(400, "No products found in order")
        
        # Find product_sources for these products
        deals_result = supabase.table('product_sources') \
            .select('id, product_id') \
            .in_('product_id', product_ids) \
            .eq('is_active', True) \
            .execute()
        
        deal_ids = [deal.get('id') for deal in (deals_result.data or [])]
        
        # Move all deals back to buy_list stage
        if deal_ids:
            supabase.table('product_sources') \
                .update({'stage': 'buy_list'}) \
                .in_('id', deal_ids) \
                .execute()
        
        # Mark order as cancelled (don't delete - keep history)
        supabase.table('orders').update({
            'status': 'cancelled',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', order_id).execute()
        
        logger.info(f"✅ Reverted order {order_id} to buy list: {len(deal_ids)} products moved back")
        
        return {
            'success': True,
            'message': f'Order reverted. {len(deal_ids)} products moved back to buy list.',
            'products_reverted': len(deal_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revert order: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to revert order: {str(e)}")


@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """
    Delete an order (cascades to order_items).
    WARNING: This permanently deletes the order.
    Consider using POST /{order_id}/revert-to-buy-list instead.
    """
    user_id = str(current_user.id)
    
    # Verify order belongs to user
    order_result = supabase.table('orders') \
        .select('*') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    # Delete order (cascades to order_items)
    supabase.table('orders').delete().eq('id', order_id).execute()
    
    logger.info(f"✅ Deleted order {order_id}")
    
    return {
        'success': True,
        'message': 'Order deleted successfully'
    }


@router.post("/{order_id}/send")
async def send_order(
    order_id: str,
    request: SendOrderRequest,
    current_user=Depends(get_current_user)
):
    """
    Send order to supplier.
    - Generates order document (formatted for supplier)
    - Updates status to 'sent'
    - Returns formatted order data for export/email
    """
    user_id = str(current_user.id)
    
    # Get order with full details
    order_result = supabase.table('orders') \
        .select('*, supplier:suppliers(*), items:order_items(*, product:products(*))') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    order = order_result.data
    items = order.get('items', []) or []
    
    if not items:
        raise HTTPException(400, "Order has no items")
    
    # Format order for supplier
    supplier = order.get('supplier', {})
    supplier_name = supplier.get('name', 'Supplier') if supplier else 'Supplier'
    supplier_email = request.recipient_email or (supplier.get('contact_email') if supplier else None)
    
    # Build formatted order document
    formatted_order = {
        'order_id': order.get('id'),
        'order_date': order.get('created_at'),
        'supplier': {
            'name': supplier_name,
            'contact_email': supplier_email,
            'contact_name': supplier.get('contact_name') if supplier else None,
        },
        'items': [],
        'totals': {
            'subtotal': 0.0,
            'total_discount': 0.0,
            'total': 0.0
        },
        'notes': order.get('notes')
    }
    
    # Format items for supplier
    subtotal = 0.0
    total_discount = 0.0
    
    for item in items:
        product = item.get('product', {})
        quantity = item.get('quantity', 1)
        unit_cost = float(item.get('unit_cost', 0) or 0)
        discount = float(item.get('discount', 0) or 0)
        item_subtotal = (quantity * unit_cost) - discount
        
        formatted_item = {
            'asin': product.get('asin', 'N/A'),
            'upc': product.get('upc', 'N/A'),
            'title': product.get('title') or product.get('supplier_title') or 'Product',
            'quantity': quantity,
            'unit_cost': round(unit_cost, 2),
            'discount': round(discount, 2),
            'subtotal': round(item_subtotal, 2)
        }
        
        formatted_order['items'].append(formatted_item)
        subtotal += quantity * unit_cost
        total_discount += discount
    
    formatted_order['totals']['subtotal'] = round(subtotal, 2)
    formatted_order['totals']['total_discount'] = round(total_discount, 2)
    formatted_order['totals']['total'] = round(subtotal - total_discount, 2)
    
    # Update order status
    supabase.table('orders').update({
        'status': 'sent',
        'sent_at': datetime.utcnow().isoformat(),
        'sent_to': supplier_email
    }).eq('id', order_id).execute()
    
    logger.info(f"📧 Order {order_id} sent to {supplier_name} ({supplier_email})")
    
    return {
        'success': True,
        'message': f'Order sent to {supplier_name}',
        'order': formatted_order,
        'export_formats': {
            'csv': f'/api/v1/orders/{order_id}/export/csv',
            'json': f'/api/v1/orders/{order_id}/export/json',
            'pdf': f'/api/v1/orders/{order_id}/export/pdf'  # TODO: Implement PDF export
        }
    }


@router.get("/{order_id}/export/csv")
async def export_order_csv(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """
    Export order as CSV for sending to supplier.
    """
    from fastapi.responses import Response
    import csv
    import io
    
    user_id = str(current_user.id)
    
    # Get order with full details
    order_result = supabase.table('orders') \
        .select('*, supplier:suppliers(*), items:order_items(*, product:products(*))') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    order = order_result.data
    items = order.get('items', []) or []
    supplier = order.get('supplier', {})
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Purchase Order'])
    writer.writerow(['Order ID:', order.get('id')])
    writer.writerow(['Date:', order.get('created_at', '').split('T')[0]])
    writer.writerow(['Supplier:', supplier.get('name', '') if supplier else ''])
    if order.get('notes'):
        writer.writerow(['Notes:', order.get('notes')])
    writer.writerow([])
    
    # Items header
    writer.writerow(['ASIN', 'UPC', 'Product Title', 'Quantity', 'Unit Cost', 'Discount', 'Subtotal'])
    
    # Items
    total = 0.0
    for item in items:
        product = item.get('product', {})
        quantity = item.get('quantity', 1)
        unit_cost = float(item.get('unit_cost', 0) or 0)
        discount = float(item.get('discount', 0) or 0)
        subtotal = (quantity * unit_cost) - discount
        total += subtotal
        
        writer.writerow([
            product.get('asin', ''),
            product.get('upc', ''),
            product.get('title') or product.get('supplier_title') or '',
            quantity,
            f"${unit_cost:.2f}",
            f"${discount:.2f}",
            f"${subtotal:.2f}"
        ])
    
    writer.writerow([])
    writer.writerow(['Total:', f"${total:.2f}"])
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="order_{order_id[:8]}.csv"'
        }
    )


@router.get("/{order_id}/export/json")
async def export_order_json(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """
    Export order as JSON for sending to supplier.
    """
    from fastapi.responses import JSONResponse
    
    user_id = str(current_user.id)
    
    # Get order with full details
    order_result = supabase.table('orders') \
        .select('*, supplier:suppliers(*), items:order_items(*, product:products(*))') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    order = order_result.data
    items = order.get('items', []) or []
    
    # Format for export
    export_data = {
        'order_id': order.get('id'),
        'order_date': order.get('created_at'),
        'supplier': order.get('supplier', {}),
        'items': [],
        'totals': {
            'subtotal': 0.0,
            'total_discount': 0.0,
            'total': 0.0
        },
        'notes': order.get('notes')
    }
    
    subtotal = 0.0
    total_discount = 0.0
    
    for item in items:
        product = item.get('product', {})
        quantity = item.get('quantity', 1)
        unit_cost = float(item.get('unit_cost', 0) or 0)
        discount = float(item.get('discount', 0) or 0)
        item_subtotal = (quantity * unit_cost) - discount
        
        export_data['items'].append({
            'asin': product.get('asin'),
            'upc': product.get('upc'),
            'title': product.get('title') or product.get('supplier_title'),
            'quantity': quantity,
            'unit_cost': round(unit_cost, 2),
            'discount': round(discount, 2),
            'subtotal': round(item_subtotal, 2)
        })
        
        subtotal += quantity * unit_cost
        total_discount += discount
    
    export_data['totals']['subtotal'] = round(subtotal, 2)
    export_data['totals']['total_discount'] = round(total_discount, 2)
    export_data['totals']['total'] = round(subtotal - total_discount, 2)
    
    return JSONResponse(
        content=export_data,
        headers={
            'Content-Disposition': f'attachment; filename="order_{order_id[:8]}.json"'
        }
    )
