from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.services.supabase_client import supabase

router = APIRouter()


@router.get("")
async def list_notifications(current_user=Depends(get_current_user)):
    """List notifications."""
    
    try:
        result = supabase.table("notifications").select("*").eq("user_id", str(current_user.id)).order("created_at", desc=True).limit(50).execute()
        return result.data or []
    except Exception as e:
        # If notifications table doesn't exist, return empty array
        import logging
        logging.getLogger(__name__).warning(f"Failed to fetch notifications: {e}")
        return []


@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: str, current_user=Depends(get_current_user)):
    """Mark notification as read."""
    
    try:
        supabase.table("notifications").update({"is_read": True, "read_at": "now()"}).eq("id", notification_id).eq("user_id", str(current_user.id)).execute()
        return {"success": True}
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to mark notification as read: {e}")
        return {"success": False}


@router.post("/read-all")
async def mark_all_as_read(current_user=Depends(get_current_user)):
    """Mark all notifications as read."""
    
    try:
        supabase.table("notifications").update({"is_read": True, "read_at": "now()"}).eq("user_id", str(current_user.id)).eq("is_read", False).execute()
        return {"success": True}
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to mark all as read: {e}")
        return {"success": False}

