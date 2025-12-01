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
    channel_type: str = "channel"


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
    current_user=Depends(require_limit("telegram_channels"))
):
    """
    Add a channel to monitoring list.
    Enforces channel limit based on subscription tier.
    """
    
    try:
        channel = await telegram_service.add_channel(
            user_id=current_user.id,
            channel_id=request.channel_id,
            channel_name=request.channel_name,
            channel_type=request.channel_type
        )
        
        # Increment usage
        await feature_gate.increment_usage(current_user.id, "telegram_channels")
        
        return channel
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

