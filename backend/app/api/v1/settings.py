from fastapi import APIRouter, Depends, HTTPException
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
    inbound_rate_per_lb: Optional[float] = None  # New field name


class PreferencesUpdate(BaseModel):
    default_pricing_mode: Optional[str] = None  # current, 30d_avg, 90d_avg, 365d_avg


@router.get("/profile")
async def get_profile(current_user=Depends(get_current_user)):
    """Get user profile settings."""
    try:
        result = supabase.table("profiles").select("*").eq("id", str(current_user.id)).single().execute()
        
        if not result.data:
            # Return empty profile if none exists
            return {
                "id": str(current_user.id),
                "email": getattr(current_user, 'email', None),
                "full_name": None,
                "avatar_url": None,
            }
        
        return result.data
    except Exception as e:
        # Return basic info on error
        import logging
        logging.getLogger(__name__).warning(f"Error fetching profile: {e}")
        return {
            "id": str(current_user.id),
            "email": getattr(current_user, 'email', None),
            "full_name": None,
            "avatar_url": None,
        }


@router.put("/profile")
async def update_profile(data: ProfileUpdate, current_user=Depends(get_current_user)):
    """Update user profile."""
    allowed_fields = ["full_name", "avatar_url"]
    update_data = {k: v for k, v in data.dict().items() if k in allowed_fields and v is not None}
    
    if not update_data:
        return await get_profile(current_user)
    
    try:
        result = supabase.table("profiles").update(update_data).eq("id", str(current_user.id)).execute()
        
        if result.data:
            return result.data[0]
        else:
            # Profile doesn't exist, create it
            profile = {
                "id": str(current_user.id),
                "email": getattr(current_user, 'email', None),
                **update_data
            }
            result = supabase.table("profiles").insert(profile).execute()
            return result.data[0] if result.data else profile
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error updating profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


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
    """Get cost settings. Checks user_cost_settings first, falls back to user_settings."""
    try:
        # Try new user_cost_settings table first
        result = supabase.table("user_cost_settings")\
            .select("inbound_rate_per_lb, default_prep_cost")\
            .eq("user_id", current_user.id)\
            .single()\
            .execute()
        
        if result.data:
            return {
                "inbound_rate_per_lb": result.data.get("inbound_rate_per_lb", 0.35),
                "default_prep_cost": result.data.get("default_prep_cost", 0.10),
                # Also return legacy names for compatibility
                "default_inbound_shipping": result.data.get("inbound_rate_per_lb", 0.35),
            }
    except Exception:
        pass
    
    try:
        # Fall back to user_settings table
        result = supabase.table("user_settings")\
            .select("default_prep_cost, default_inbound_shipping")\
            .eq("user_id", current_user.id)\
            .single()\
            .execute()
        
        if result.data:
            inbound_rate = result.data.get("default_inbound_shipping", 0.35)
            return {
                "inbound_rate_per_lb": inbound_rate,
                "default_prep_cost": result.data.get("default_prep_cost", 0.10),
                "default_inbound_shipping": inbound_rate,
            }
    except Exception:
        pass
    
    # Return defaults
    return {
        "inbound_rate_per_lb": 0.35,
        "default_prep_cost": 0.10,
        "default_inbound_shipping": 0.35,
    }


@router.put("/costs")
async def update_cost_settings(data: CostSettingsUpdate, current_user=Depends(get_current_user)):
    """Update cost settings. Saves to user_cost_settings table (new) or user_settings (fallback)."""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    if not update_data:
        return await get_cost_settings(current_user)
    
    # Normalize field names - convert inbound_rate_per_lb to default_inbound_shipping if needed
    if "inbound_rate_per_lb" in update_data and "default_inbound_shipping" not in update_data:
        update_data["default_inbound_shipping"] = update_data["inbound_rate_per_lb"]
    
    # Try to save to new user_cost_settings table first
    try:
        existing = supabase.table("user_cost_settings")\
            .select("id")\
            .eq("user_id", current_user.id)\
            .single()\
            .execute()
        
        if existing.data:
            # Update existing
            save_data = {
                "inbound_rate_per_lb": update_data.get("inbound_rate_per_lb") or update_data.get("default_inbound_shipping", 0.35),
                "default_prep_cost": update_data.get("default_prep_cost", 0.10),
                "updated_at": "now()",
            }
            result = supabase.table("user_cost_settings")\
                .update(save_data)\
                .eq("user_id", current_user.id)\
                .execute()
        else:
            # Create new
            save_data = {
                "user_id": current_user.id,
                "inbound_rate_per_lb": update_data.get("inbound_rate_per_lb") or update_data.get("default_inbound_shipping", 0.35),
                "default_prep_cost": update_data.get("default_prep_cost", 0.10),
            }
            result = supabase.table("user_cost_settings").insert(save_data).execute()
        
        if result.data:
            return {
                "inbound_rate_per_lb": result.data[0].get("inbound_rate_per_lb", 0.35),
                "default_prep_cost": result.data[0].get("default_prep_cost", 0.10),
                "default_inbound_shipping": result.data[0].get("inbound_rate_per_lb", 0.35),
            }
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not save to user_cost_settings: {e}")
    
    # Fall back to user_settings table
    existing = supabase.table("user_settings").select("id").eq("user_id", current_user.id).execute()
    
    if existing.data:
        result = supabase.table("user_settings").update(update_data).eq("user_id", current_user.id).execute()
    else:
        # Create with defaults + updates
        defaults = {
            "user_id": current_user.id,
            "default_prep_cost": 0.10,
            "default_inbound_shipping": 0.35,
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

