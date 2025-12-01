from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.core.exceptions import NotFoundError

router = APIRouter()


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class AlertSettingsUpdate(BaseModel):
    min_roi: Optional[float] = None
    min_profit: Optional[float] = None
    max_rank: Optional[int] = None
    alerts_enabled: Optional[bool] = None
    alert_min_roi: Optional[float] = None
    alert_channels: Optional[list] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    preferred_categories: Optional[list] = None
    excluded_categories: Optional[list] = None


class CostSettingsUpdate(BaseModel):
    default_prep_cost: Optional[float] = None
    default_inbound_shipping: Optional[float] = None


@router.get("/profile")
async def get_profile(current_user=Depends(get_current_user)):
    """Get user profile."""
    result = supabase.table("profiles").select("*").eq("id", current_user.id).single().execute()
    
    if not result.data:
        # Create default profile
        profile = {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.user_metadata.get("full_name") if hasattr(current_user, 'user_metadata') else None,
        }
        supabase.table("profiles").insert(profile).execute()
        return profile
    
    return result.data


@router.put("/profile")
async def update_profile(data: ProfileUpdate, current_user=Depends(get_current_user)):
    """Update user profile."""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if not update_data:
        return await get_profile(current_user)
    
    result = supabase.table("profiles").update(update_data).eq("id", current_user.id).execute()
    
    if not result.data:
        raise NotFoundError("Profile")
    
    return result.data[0]


@router.get("/alerts")
async def get_alert_settings(current_user=Depends(get_current_user)):
    """Get alert settings."""
    try:
        result = supabase.table("user_settings").select("*").eq("user_id", current_user.id).single().execute()
        
        if not result.data:
            # Create default settings
            defaults = {
                "user_id": current_user.id,
                "min_roi": 20.0,
                "min_profit": 3.0,
                "max_rank": 100000,
                "default_prep_cost": 0.50,
                "default_inbound_shipping": 0.50,
                "alerts_enabled": True,
                "alert_min_roi": 30.0,
                "alert_channels": ["push", "email"],
                "preferred_categories": [],
                "excluded_categories": [],
            }
            try:
                supabase.table("user_settings").insert(defaults).execute()
            except:
                pass  # Table might not exist
            return defaults
        
        return result.data
    except Exception as e:
        # Table doesn't exist yet - return defaults
        import logging
        logging.getLogger(__name__).warning(f"User settings table not found: {e}")
        return {
            "user_id": current_user.id,
            "min_roi": 20.0,
            "min_profit": 3.0,
            "max_rank": 100000,
            "default_prep_cost": 0.50,
            "default_inbound_shipping": 0.50,
            "alerts_enabled": True,
            "alert_min_roi": 30.0,
            "alert_channels": ["push", "email"],
            "preferred_categories": [],
            "excluded_categories": [],
        }


@router.put("/alerts")
async def update_alert_settings(data: AlertSettingsUpdate, current_user=Depends(get_current_user)):
    """Update alert settings."""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if not update_data:
        return await get_alert_settings(current_user)
    
    # Check if settings exist
    existing = supabase.table("user_settings").select("id").eq("user_id", current_user.id).execute()
    
    if existing.data:
        result = supabase.table("user_settings").update(update_data).eq("user_id", current_user.id).execute()
    else:
        # Create with defaults + updates
        defaults = {
            "user_id": current_user.id,
            "min_roi": 20.0,
            "min_profit": 3.0,
            "max_rank": 100000,
            "default_prep_cost": 0.50,
            "default_inbound_shipping": 0.50,
            "alerts_enabled": True,
            "alert_min_roi": 30.0,
            "alert_channels": ["push", "email"],
            "preferred_categories": [],
            "excluded_categories": [],
        }
        defaults.update(update_data)
        result = supabase.table("user_settings").insert(defaults).execute()
    
    return result.data[0] if result.data else {}


@router.get("/costs")
async def get_cost_settings(current_user=Depends(get_current_user)):
    """Get cost settings."""
    try:
        result = supabase.table("user_settings").select("default_prep_cost, default_inbound_shipping").eq("user_id", current_user.id).single().execute()
        
        if result.data:
            return result.data
        
        return {
            "default_prep_cost": 0.50,
            "default_inbound_shipping": 0.50,
        }
    except Exception as e:
        # Table doesn't exist yet - return defaults
        import logging
        logging.getLogger(__name__).warning(f"User settings table not found: {e}")
        return {
            "default_prep_cost": 0.50,
            "default_inbound_shipping": 0.50,
        }


@router.put("/costs")
async def update_cost_settings(data: CostSettingsUpdate, current_user=Depends(get_current_user)):
    """Update cost settings."""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if not update_data:
        return await get_cost_settings(current_user)
    
    # Check if settings exist
    existing = supabase.table("user_settings").select("id").eq("user_id", current_user.id).execute()
    
    if existing.data:
        result = supabase.table("user_settings").update(update_data).eq("user_id", current_user.id).execute()
    else:
        # Create with defaults + updates
        defaults = {
            "user_id": current_user.id,
            "default_prep_cost": 0.50,
            "default_inbound_shipping": 0.50,
        }
        defaults.update(update_data)
        result = supabase.table("user_settings").insert(defaults).execute()
    
    return result.data[0] if result.data else {}


@router.get("/profit-rules")
async def get_profit_rules(current_user=Depends(get_current_user)):
    """Get profit rules (min ROI, min profit, max rank)."""
    result = supabase.table("user_settings").select("min_roi, min_profit, max_rank").eq("user_id", current_user.id).single().execute()
    
    if result.data:
        return result.data
    
    return {
        "min_roi": 20.0,
        "min_profit": 3.0,
        "max_rank": 100000,
    }


@router.put("/profit-rules")
async def update_profit_rules(data: dict, current_user=Depends(get_current_user)):
    """Update profit rules."""
    update_data = {k: v for k, v in data.items() if v is not None}
    
    if not update_data:
        return await get_profit_rules(current_user)
    
    # Check if settings exist
    existing = supabase.table("user_settings").select("id").eq("user_id", current_user.id).execute()
    
    if existing.data:
        result = supabase.table("user_settings").update(update_data).eq("user_id", current_user.id).execute()
    else:
        # Create with defaults + updates
        defaults = {
            "user_id": current_user.id,
            "min_roi": 20.0,
            "min_profit": 3.0,
            "max_rank": 100000,
        }
        defaults.update(update_data)
        result = supabase.table("user_settings").insert(defaults).execute()
    
    return result.data[0] if result.data else {}

