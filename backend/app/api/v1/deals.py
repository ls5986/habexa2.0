from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("")
async def list_deals(
    status: Optional[str] = Query(None),
    min_roi: Optional[float] = Query(None),
    supplier_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    gating_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user)
):
    """List deals with filters."""
    
    query = supabase.table("deals").select("*").eq("user_id", current_user.id)
    
    if status:
        query = query.eq("status", status)
    if min_roi:
        query = query.gte("roi", min_roi)
    if supplier_id:
        query = query.eq("supplier_id", supplier_id)
    if category:
        query = query.eq("category", category)
    if gating_status:
        query = query.eq("gating_status", gating_status)
    
    query = query.order("created_at", desc=True).limit(limit).offset(offset)
    
    try:
        result = query.execute()
        return result.data
    except Exception as e:
        # Table doesn't exist yet - return empty array
        import logging
        logging.getLogger(__name__).warning(f"Deals table not found: {e}")
        return []


@router.get("/{deal_id}")
async def get_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Get single deal."""
    
    result = supabase.table("deals").select("*").eq("id", deal_id).eq("user_id", current_user.id).single().execute()
    
    if not result.data:
        raise NotFoundError("Deal")
    
    return result.data


@router.post("/{deal_id}/save")
async def save_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Save deal to watchlist."""
    
    # Update deal status
    supabase.table("deals").update({"status": "saved"}).eq("id", deal_id).eq("user_id", current_user.id).execute()
    
    # Get deal to add to watchlist
    deal_result = supabase.table("deals").select("asin").eq("id", deal_id).single().execute()
    if deal_result.data:
        supabase.table("watchlist").upsert({
            "user_id": current_user.id,
            "asin": deal_result.data["asin"]
        }).execute()
    
    return {"success": True}


@router.post("/{deal_id}/dismiss")
async def dismiss_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Dismiss deal."""
    
    supabase.table("deals").update({"status": "dismissed"}).eq("id", deal_id).eq("user_id", current_user.id).execute()
    
    return {"success": True}


@router.post("/{deal_id}/order")
async def order_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Mark deal as ordered."""
    
    supabase.table("deals").update({"status": "ordered"}).eq("id", deal_id).eq("user_id", current_user.id).execute()
    
    return {"success": True}

