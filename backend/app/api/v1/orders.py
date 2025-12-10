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


@router.post("/")
async def create_order(
    request: CreateOrderRequest,
    current_user=Depends(get_current_user)
):
    """
    Create a purchase request to supplier.
    
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


@router.get("/")
async def get_orders(
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """
    Get all orders for user.
    Optionally filter by status or supplier.
    """
    user_id = str(current_user.id)
    
    query = supabase.table('orders') \
        .select('*, supplier:suppliers(id, name, contact_name, contact_email), items:order_items(*, product:products(*))') \
        .eq('user_id', user_id) \
        .order('created_at', desc=True)
    
    if status:
        query = query.eq('status', status)
    
    if supplier_id:
        query = query.eq('supplier_id', supplier_id)
    
    result = query.execute()
    
    # Calculate items_count and format response
    orders = result.data or []
    for order in orders:
        items = order.get('items', [])
        order['items_count'] = len(items)
        # Calculate subtotals for each item
        for item in items:
            quantity = item.get('quantity', 1)
            unit_cost = item.get('unit_cost', 0) or 0
            discount = item.get('discount', 0) or 0
            item['subtotal'] = round((quantity * float(unit_cost)) - float(discount), 2)
    
    return orders


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


@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """
    Delete an order (cascades to order_items).
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
    Send order to supplier via email.
    Updates status to 'sent'.
    """
    user_id = str(current_user.id)
    
    # Get order with items
    order_result = supabase.table('orders') \
        .select('*, supplier:suppliers(*)') \
        .eq('id', order_id) \
        .eq('user_id', user_id) \
        .single() \
        .execute()
    
    if not order_result.data:
        raise HTTPException(404, "Order not found")
    
    order = order_result.data
    
    # TODO: Send email to supplier
    # For now, just update status
    
    supabase.table('orders').update({
        'status': 'sent',
        'sent_at': datetime.utcnow().isoformat(),
        'sent_to': request.recipient_email or (order.get('supplier', {}).get('contact_email') if order.get('supplier') else None)
    }).eq('id', order_id).execute()
    
    logger.info(f"📧 Order sent: {order_id}")
    
    return {
        'success': True,
        'message': f'Order sent to {order.get("supplier", {}).get("name", "supplier") if order.get("supplier") else "supplier"}'
    }
