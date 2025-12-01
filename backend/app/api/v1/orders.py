from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.core.exceptions import NotFoundError
import uuid

router = APIRouter()


class OrderCreate(BaseModel):
    supplier_id: Optional[str] = None
    deal_id: Optional[str] = None
    asin: str
    quantity: int
    unit_cost: float
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    expected_delivery: Optional[str] = None
    actual_delivery: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
async def get_orders(
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user)
):
    """Get user's orders."""
    query = supabase.table("orders").select("*, suppliers(name)").eq("user_id", current_user.id)
    
    if status:
        query = query.eq("status", status)
    if supplier_id:
        query = query.eq("supplier_id", supplier_id)
    
    try:
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data
    except Exception as e:
        # Table doesn't exist yet - return empty array
        import logging
        logging.getLogger(__name__).warning(f"Orders table not found: {e}")
        return []


@router.get("/{order_id}")
async def get_order(order_id: str, current_user=Depends(get_current_user)):
    """Get single order."""
    result = supabase.table("orders").select("*, suppliers(name)").eq("id", order_id).eq("user_id", current_user.id).single().execute()
    
    if not result.data:
        raise NotFoundError("Order")
    
    return result.data


@router.post("")
async def create_order(data: OrderCreate, current_user=Depends(get_current_user)):
    """Create a new order."""
    order = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "supplier_id": data.supplier_id,
        "deal_id": data.deal_id,
        "asin": data.asin,
        "quantity": data.quantity,
        "unit_cost": data.unit_cost,
        "total_cost": data.quantity * data.unit_cost,
        "status": "pending",
        "notes": data.notes,
    }
    
    result = supabase.table("orders").insert(order).execute()
    
    # Update deal status to "ordered" if deal_id provided
    if data.deal_id:
        supabase.table("deals").update({"status": "ordered"}).eq("id", data.deal_id).eq("user_id", current_user.id).execute()
    
    return result.data[0] if result.data else {}


@router.put("/{order_id}")
async def update_order(order_id: str, data: OrderUpdate, current_user=Depends(get_current_user)):
    """Update order."""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if not update_data:
        return await get_order(order_id, current_user)
    
    result = supabase.table("orders").update(update_data).eq("id", order_id).eq("user_id", current_user.id).execute()
    
    if not result.data:
        raise NotFoundError("Order")
    
    return result.data[0]


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: str,
    status: str,
    current_user=Depends(get_current_user)
):
    """Update order status."""
    valid_statuses = ["pending", "confirmed", "shipped", "received", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    result = supabase.table("orders").update({"status": status}).eq("id", order_id).eq("user_id", current_user.id).execute()
    
    if not result.data:
        raise NotFoundError("Order")
    
    return result.data[0]

