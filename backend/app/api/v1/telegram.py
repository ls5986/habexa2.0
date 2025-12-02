from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.api.deps import get_current_user
from app.services.feature_gate import feature_gate, require_limit
from app.services.telegram_service import telegram_service, TelegramServiceError
from app.services.supabase_client import supabase
import uuid

router = APIRouter()


class StartAuthRequest(BaseModel):
    phone_number: str


class VerifyCodeRequest(BaseModel):
    code: str
    password: Optional[str] = None


class AddChannelRequest(BaseModel):
    channel_id: str
    channel_name: str


class AddChannelsRequest(BaseModel):
    channels: List[AddChannelRequest]


class AddTelegramChannelRequest(BaseModel):
    channel_id: int
    channel_name: str
    channel_username: Optional[str] = None
    channel_type: str = "channel"
    # Supplier creation fields
    create_supplier: bool = True
    supplier_name: Optional[str] = None
    supplier_website: Optional[str] = None
    supplier_contact_email: Optional[str] = None
    supplier_notes: Optional[str] = None


# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@router.post("/auth/start")
async def start_telegram_auth(
    request: StartAuthRequest,
    current_user=Depends(get_current_user)
):
    """
    Start Telegram authentication.
    Sends verification code to user's phone.
    """
    
    try:
        return await telegram_service.start_auth(
            user_id=str(current_user.id),  # Ensure string format
            phone_number=request.phone_number
        )
    except TelegramServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Telegram start auth error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to start auth: {str(e)}")


@router.post("/auth/verify")
async def verify_telegram_code(
    request: VerifyCodeRequest,
    current_user=Depends(get_current_user)
):
    """
    Verify the code sent to Telegram.
    Complete authentication.
    """
    
    try:
        return await telegram_service.verify_code(
            user_id=str(current_user.id),  # Ensure string format
            code=request.code,
            password=request.password
        )
    except TelegramServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Telegram verify error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")


@router.delete("/disconnect")
async def disconnect_telegram(current_user=Depends(get_current_user)):
    """Disconnect Telegram account."""
    
    return await telegram_service.disconnect(current_user.id)


@router.get("/status")
async def get_telegram_status(current_user=Depends(get_current_user)):
    """Get Telegram connection and monitoring status."""
    
    status = await telegram_service.get_status(current_user.id)
    
    # Add channel count
    channels = await telegram_service.get_monitored_channels(current_user.id)
    status["channel_count"] = len(channels)
    
    # Add limit info
    limit_check = await feature_gate.check_limit(current_user.id, "telegram_channels")
    status["channel_limit"] = limit_check.get("limit")
    status["channels_remaining"] = limit_check.get("remaining")
    
    return status


# ==========================================
# CHANNEL ENDPOINTS
# ==========================================

@router.get("/channels/available")
async def get_available_channels(current_user=Depends(get_current_user)):
    """
    Get list of Telegram channels/groups the user can monitor.
    Returns channels the user is a member of.
    """
    
    try:
        channels = await telegram_service.get_available_channels(current_user.id)
        
        # Mark which are already being monitored
        monitored = await telegram_service.get_monitored_channels(current_user.id)
        monitored_ids = {c["channel_id"] for c in monitored}
        
        for channel in channels:
            channel["is_monitored"] = channel["id"] in monitored_ids
        
        return {
            "channels": channels,
            "total": len(channels)
        }
    except TelegramServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/channels")
async def get_monitored_channels(current_user=Depends(get_current_user)):
    """Get list of channels currently being monitored."""
    
    channels = await telegram_service.get_monitored_channels(current_user.id)
    
    # Add limit info
    limit_check = await feature_gate.check_limit(current_user.id, "telegram_channels")
    
    return {
        "channels": channels,
        "count": len(channels),
        "limit": limit_check.get("limit"),
        "remaining": limit_check.get("remaining"),
        "unlimited": limit_check.get("unlimited", False)
    }


@router.post("/channels")
async def add_monitored_channel(
    request: AddTelegramChannelRequest,
    auto_backfill: bool = False,
    current_user=Depends(require_limit("telegram_channels"))
):
    """
    Add a channel to monitoring list.
    Enforces channel limit based on subscription tier.
    Optionally creates a linked supplier.
    Optionally backfills last 14 days of messages.
    """
    user_id = str(current_user.id)
    
    try:
        supplier_id = None
        
        # Create supplier if requested
        if request.create_supplier:
            supplier_name = request.supplier_name or request.channel_name
            
            # Check if supplier with this name already exists
            existing = supabase.table("suppliers")\
                .select("id")\
                .eq("user_id", user_id)\
                .ilike("name", supplier_name)\
                .limit(1)\
                .execute()
            
            if existing.data:
                supplier_id = existing.data[0]["id"]
            else:
                # Create new supplier
                supplier_data = {
                    "user_id": user_id,
                    "name": supplier_name,
                    "website": request.supplier_website,
                    "contact_email": request.supplier_contact_email,
                    "notes": request.supplier_notes or f"Auto-created from Telegram channel: {request.channel_username or request.channel_name}",
                    "source": "telegram",
                    "is_active": True,
                }
                
                supplier_result = supabase.table("suppliers")\
                    .insert(supplier_data)\
                    .execute()
                
                if supplier_result.data:
                    supplier_id = supplier_result.data[0]["id"]
        
        # Check if channel already exists
        existing_channel = supabase.table("telegram_channels")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("channel_id", request.channel_id)\
            .limit(1)\
            .execute()
        
        if existing_channel.data:
            # Update existing channel with supplier link
            if supplier_id:
                supabase.table("telegram_channels")\
                    .update({"supplier_id": supplier_id})\
                    .eq("id", existing_channel.data[0]["id"])\
                    .execute()
            
            return {
                "channel": existing_channel.data[0],
                "supplier_id": supplier_id,
                "message": "Channel already exists, updated supplier link"
            }
        
        # Add channel via service (will create in DB)
        channel = await telegram_service.add_channel(
            user_id=user_id,
            channel_id=request.channel_id,
            channel_name=request.channel_name,
            channel_username=request.channel_username,
            channel_type=request.channel_type,
            supplier_id=supplier_id
        )
        
        # Increment usage
        await feature_gate.increment_usage(current_user.id, "telegram_channels")
        
        # Auto backfill if requested
        backfill_result = None
        if auto_backfill:
            try:
                backfill_result = await telegram_service.backfill_channel(
                    user_id=user_id,
                    channel_id=request.channel_id,
                    days=14
                )
            except Exception as e:
                logger = __import__("logging").getLogger(__name__)
                logger.warning(f"Auto-backfill failed for channel {request.channel_id}: {e}")
                # Don't fail the request if backfill fails
        
        return {
            "channel": channel,
            "supplier_id": supplier_id,
            "backfill": backfill_result
        }
    except TelegramServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/channels/bulk")
async def add_channels_bulk(
    data: AddChannelsRequest,
    current_user=Depends(get_current_user)
):
    """
    Add multiple channels at once.
    Checks total limit before adding.
    """
    
    # Check how many we can add
    check = await feature_gate.check_limit(current_user.id, "telegram_channels")
    
    if not check.get("unlimited"):
        remaining = check.get("remaining", 0)
        requested = len(data.channels)
        
        if requested > remaining:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "channel_limit_exceeded",
                    "message": f"You can only add {remaining} more channels. Requested: {requested}.",
                    "remaining": remaining,
                    "requested": requested,
                    "upgrade_url": "/pricing"
                }
            )
    
    # Add channels
    added = []
    for channel in data.channels:
        try:
            result = await add_channel(
                AddChannelRequest(channel_id=channel.channel_id, channel_name=channel.channel_name),
                current_user
            )
            added.append(result)
        except HTTPException:
            break  # Stop if we hit the limit
    
    return {
        "added": len(added),
        "channels": added
    }


@router.delete("/channels/{channel_id}")
async def remove_monitored_channel(
    channel_id: int,
    current_user=Depends(get_current_user)
):
    """Remove a channel from monitoring."""
    
    await telegram_service.remove_channel(current_user.id, channel_id)
    
    # Decrement usage
    await feature_gate.decrement_usage(current_user.id, "telegram_channels")
    
    return {"message": "Channel removed"}


@router.post("/channels/{channel_id}/backfill")
async def backfill_channel(
    channel_id: int,
    days: int = 14,
    current_user=Depends(get_current_user)
):
    """
    Fetch last N days of messages from a channel.
    Useful for syncing historical messages when adding a channel.
    """
    
    if days > 30:
        raise HTTPException(status_code=400, detail="Cannot backfill more than 30 days")
    
    try:
        result = await telegram_service.backfill_channel(
            user_id=current_user.id,
            channel_id=channel_id,
            days=days
        )
        return result
    except TelegramServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


class LinkChannelToSupplierRequest(BaseModel):
    supplier_id: Optional[str] = None  # Link to existing supplier
    create_supplier: bool = False  # Or create new supplier
    supplier_name: Optional[str] = None
    supplier_website: Optional[str] = None
    supplier_contact_email: Optional[str] = None
    supplier_notes: Optional[str] = None


@router.post("/channels/{channel_id}/link-supplier")
async def link_channel_to_supplier(
    channel_id: int,
    request: LinkChannelToSupplierRequest,
    current_user=Depends(get_current_user)
):
    """
    Link an existing Telegram channel to a supplier.
    Can either link to an existing supplier or create a new one.
    """
    user_id = str(current_user.id)
    
    try:
        # Get the channel
        channel_result = supabase.table("telegram_channels")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("channel_id", channel_id)\
            .limit(1)\
            .execute()
        
        if not channel_result.data:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        channel = channel_result.data[0]
        supplier_id = None
        
        # Link to existing supplier
        if request.supplier_id:
            # Verify supplier exists and belongs to user
            supplier_result = supabase.table("suppliers")\
                .select("id")\
                .eq("id", request.supplier_id)\
                .eq("user_id", user_id)\
                .limit(1)\
                .execute()
            
            if not supplier_result.data:
                raise HTTPException(status_code=404, detail="Supplier not found")
            
            supplier_id = request.supplier_id
        
        # Create new supplier
        elif request.create_supplier:
            supplier_name = request.supplier_name or channel.get("channel_name", "Unknown Supplier")
            
            # Check if supplier with this name already exists
            existing = supabase.table("suppliers")\
                .select("id")\
                .eq("user_id", user_id)\
                .ilike("name", supplier_name)\
                .limit(1)\
                .execute()
            
            if existing.data:
                supplier_id = existing.data[0]["id"]
            else:
                # Create new supplier
                supplier_data = {
                    "user_id": user_id,
                    "name": supplier_name,
                    "website": request.supplier_website,
                    "contact_email": request.supplier_contact_email,
                    "notes": request.supplier_notes or f"Linked from Telegram channel: {channel.get('channel_name')} (@{channel.get('channel_username') or 'no-username'})",
                    "source": "telegram",
                    "telegram_channel_id": channel_id,
                    "telegram_username": channel.get("channel_username"),
                    "is_active": True,
                }
                
                supplier_result = supabase.table("suppliers")\
                    .insert(supplier_data)\
                    .execute()
                
                if supplier_result.data:
                    supplier_id = supplier_result.data[0]["id"]
        
        if not supplier_id:
            raise HTTPException(status_code=400, detail="Must provide supplier_id or set create_supplier=true")
        
        # Update channel with supplier_id
        update_result = supabase.table("telegram_channels")\
            .update({"supplier_id": supplier_id})\
            .eq("user_id", user_id)\
            .eq("channel_id", channel_id)\
            .execute()
        
        # Get updated channel
        updated_channel = supabase.table("telegram_channels")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("channel_id", channel_id)\
            .limit(1)\
            .execute()
        
        # Get supplier info
        supplier_info = supabase.table("suppliers")\
            .select("*")\
            .eq("id", supplier_id)\
            .limit(1)\
            .execute()
        
        return {
            "channel": updated_channel.data[0] if updated_channel.data else channel,
            "supplier": supplier_info.data[0] if supplier_info.data else None,
            "message": "Channel linked to supplier successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Link channel to supplier error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to link channel to supplier: {str(e)}")


# ==========================================
# MONITORING ENDPOINTS
# ==========================================

@router.post("/monitoring/start")
async def start_monitoring(current_user=Depends(get_current_user)):
    """
    Start monitoring all active channels.
    Messages will be processed and products extracted automatically.
    """
    
    try:
        return await telegram_service.start_monitoring(current_user.id)
    except TelegramServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/monitoring/stop")
async def stop_monitoring(current_user=Depends(get_current_user)):
    """Stop monitoring channels."""
    
    return await telegram_service.stop_monitoring(current_user.id)


# ==========================================
# MESSAGES & DEALS ENDPOINTS
# ==========================================

@router.get("/messages")
async def get_messages(
    channel_id: Optional[str] = None,
    limit: int = 50,
    current_user=Depends(get_current_user)
):
    """Get recent messages from monitored channels."""
    
    messages = await telegram_service.get_recent_messages(
        user_id=current_user.id,
        channel_id=channel_id,
        limit=min(limit, 100)
    )
    
    return {
        "messages": messages,
        "count": len(messages)
    }


@router.get("/deals/pending")
async def get_pending_deals(
    limit: int = 50,
    current_user=Depends(get_current_user)
):
    """Get pending deals extracted from messages."""
    
    deals = await telegram_service.get_pending_deals(
        user_id=current_user.id,
        limit=min(limit, 100)
    )
    
    return {
        "deals": deals,
        "count": len(deals)
    }

