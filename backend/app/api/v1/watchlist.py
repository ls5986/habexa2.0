from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
import uuid

router = APIRouter()


class WatchlistItemCreate(BaseModel):
    asin: str
    target_price: Optional[float] = None
    notes: Optional[str] = None
    notify_on_price_drop: bool = True


@router.get("")
async def get_watchlist(current_user=Depends(get_current_user)):
    """Get user's watchlist."""
    try:
        result = supabase.table("watchlist").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        # Table doesn't exist yet - return empty array
        import logging
        logging.getLogger(__name__).warning(f"Watchlist table not found: {e}")
        return []


@router.post("")
async def add_to_watchlist(data: WatchlistItemCreate, current_user=Depends(get_current_user)):
    """Add item to watchlist."""
    # Check if already in watchlist
    existing = supabase.table("watchlist").select("id").eq("user_id", current_user.id).eq("asin", data.asin).execute()
    
    if existing.data:
        # Update existing
        update_data = {}
        if data.target_price is not None:
            update_data["target_price"] = data.target_price
        if data.notes is not None:
            update_data["notes"] = data.notes
        if "notify_on_price_drop" in data.dict():
            update_data["notify_on_price_drop"] = data.notify_on_price_drop
        
        result = supabase.table("watchlist").update(update_data).eq("id", existing.data[0]["id"]).execute()
        return result.data[0] if result.data else {}
    
    # Create new
    item = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "asin": data.asin,
        "target_price": data.target_price,
        "notes": data.notes,
        "notify_on_price_drop": data.notify_on_price_drop,
    }
    
    result = supabase.table("watchlist").insert(item).execute()
    return result.data[0] if result.data else {}


@router.delete("/{item_id}")
async def remove_from_watchlist(item_id: str, current_user=Depends(get_current_user)):
    """Remove item from watchlist."""
    supabase.table("watchlist").delete().eq("id", item_id).eq("user_id", current_user.id).execute()
    return {"success": True, "message": "Removed from watchlist"}


@router.get("/{asin}/check")
async def check_watchlist(asin: str, current_user=Depends(get_current_user)):
    """Check if ASIN is in watchlist."""
    result = supabase.table("watchlist").select("id").eq("user_id", current_user.id).eq("asin", asin).execute()
    return {
        "in_watchlist": len(result.data) > 0,
        "item_id": result.data[0]["id"] if result.data else None,
    }

