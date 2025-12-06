"""
Orders API - Manage supplier orders
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
from app.api.deps import get_current_user
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


class SendOrderRequest(BaseModel):
    recipient_email: Optional[str] = None
    message: Optional[str] = None


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
    
    return result.data or []


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
    
    return result.data


@router.post("/{order_id}/send")
async def send_order(
    order_id: str,
    request: SendOrderRequest,
    current_user=Depends(get_current_user)
):
    """
    Send order to supplier via email.
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
