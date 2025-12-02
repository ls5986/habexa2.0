from typing import Dict, Any, Optional
from functools import wraps
from fastapi import HTTPException, Depends
import logging

from app.services.supabase_client import supabase
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

# Super admin emails - get unlimited access to everything
SUPER_ADMIN_EMAILS = [
    "lindsey@letsclink.com"
]

# Tier limits configuration
TIER_LIMITS = {
    "free": {
        "telegram_channels": 1,
        "analyses_per_month": 10,
        "suppliers": 3,
        "alerts": False,
        "bulk_analyze": False,
        "api_access": False,
        "team_seats": 1,
        "export_data": False,
        "priority_support": False,
    },
    "starter": {
        "telegram_channels": 3,
        "analyses_per_month": 100,
        "suppliers": 10,
        "alerts": True,
        "bulk_analyze": False,
        "api_access": False,
        "team_seats": 1,
        "export_data": True,
        "priority_support": False,
    },
    "pro": {
        "telegram_channels": 10,
        "analyses_per_month": 500,
        "suppliers": 50,
        "alerts": True,
        "bulk_analyze": True,
        "api_access": False,
        "team_seats": 3,
        "export_data": True,
        "priority_support": True,
    },
    "agency": {
        "telegram_channels": -1,
        "analyses_per_month": -1,
        "suppliers": -1,
        "alerts": True,
        "bulk_analyze": True,
        "api_access": True,
        "team_seats": 10,
        "export_data": True,
        "priority_support": True,
    }
}


class FeatureGate:
    """Feature gating service to enforce subscription limits."""
    
    @staticmethod
    async def get_user_tier(user_id: str, user_email: Optional[str] = None) -> str:
        """Get user's current subscription tier. Uses Redis cache if available."""
        from app.services.redis_client import cache_service
        
        # Check if user is super admin
        if user_email and user_email.lower() in [email.lower() for email in SUPER_ADMIN_EMAILS]:
            return "agency"  # Super admins get agency tier (unlimited)
        
        # Try cache first
        cache_key = f"tier:{user_id}"
        cached_tier = cache_service.get(cache_key)
        if cached_tier:
            return cached_tier
        
        try:
            result = supabase.table("subscriptions")\
                .select("tier, status")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            
            if not result.data:
                tier = "free"
            else:
                sub = result.data
                # Check if subscription is active
                if sub.get("status") not in ["active", "trialing"]:
                    tier = "free"
                else:
                    tier = sub.get("tier", "free")
            
            # Cache for 5 minutes
            cache_service.set(cache_key, tier, ttl=300)
            return tier
        except Exception as e:
            # If subscriptions table doesn't exist or has issues, default to free
            logger.warning(f"Error getting user tier: {e}, defaulting to free")
            return "free"
    
    @staticmethod
    async def get_user_limits(user_id: str) -> Dict[str, Any]:
        """Get all limits for user's tier."""
        
        tier = await FeatureGate.get_user_tier(user_id)
        return {
            "tier": tier,
            "limits": TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        }
    
    @staticmethod
    async def check_limit(user_id: str, feature: str, user_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if user can use a feature.
        
        Returns:
            {
                "allowed": bool,
                "tier": str,
                "feature": str,
                "limit": int (or -1 for unlimited),
                "used": int,
                "remaining": int (or -1 for unlimited),
                "unlimited": bool,
                "upgrade_required": bool
            }
        """
        
        # Check if user is super admin - grant unlimited access
        if user_email and user_email.lower() in [email.lower() for email in SUPER_ADMIN_EMAILS]:
            return {
                "allowed": True,
                "tier": "agency",
                "feature": feature,
                "limit": -1,
                "used": 0,
                "remaining": -1,
                "unlimited": True,
                "upgrade_required": False
            }
        
        # Use database function for accurate count
        try:
            result = supabase.rpc("check_user_limit", {
                "p_user_id": user_id,
                "p_feature": feature
            }).execute()
            
            if result.data:
                return result.data
        except Exception as e:
            logger.debug(f"Error calling check_user_limit function: {e}, using fallback")
        
        # Fallback to Python calculation
        tier = await FeatureGate.get_user_tier(user_id, user_email)
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        
        # Boolean features
        if feature in ["alerts", "bulk_analyze", "api_access", "export_data", "priority_support"]:
            allowed = limits.get(feature, False)
            return {
                "allowed": allowed,
                "tier": tier,
                "feature": feature,
                "upgrade_required": not allowed
            }
        
        # Numeric limits
        limit = limits.get(feature, 0)
        
        # Unlimited
        if limit == -1:
            return {
                "allowed": True,
                "tier": tier,
                "feature": feature,
                "limit": -1,
                "used": 0,
                "remaining": -1,
                "unlimited": True,
                "upgrade_required": False
            }
        
        # Get current usage
        used = await FeatureGate._get_usage(user_id, feature)
        remaining = max(0, limit - used)
        allowed = used < limit
        
        return {
            "allowed": allowed,
            "tier": tier,
            "feature": feature,
            "limit": limit,
            "used": used,
            "remaining": remaining,
            "unlimited": False,
            "upgrade_required": not allowed
        }
    
    @staticmethod
    async def _get_usage(user_id: str, feature: str) -> int:
        """Get current usage for a feature."""
        
        if feature == "analyses_per_month":
            result = supabase.table("subscriptions")\
                .select("analyses_used_this_period")\
                .eq("user_id", user_id)\
                .execute()
            return result.data[0].get("analyses_used_this_period", 0) if result.data else 0
        
        elif feature == "telegram_channels":
            result = supabase.table("telegram_channels")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            return result.count or 0
        
        elif feature == "suppliers":
            result = supabase.table("suppliers")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            return result.count or 0
        
        elif feature == "team_seats":
            result = supabase.table("subscriptions")\
                .select("team_members_count")\
                .eq("user_id", user_id)\
                .execute()
            return result.data[0].get("team_members_count", 1) if result.data else 1
        
        return 0
    
    @staticmethod
    async def increment_usage(user_id: str, feature: str, amount: int = 1) -> Dict[str, Any]:
        """
        Increment usage for a feature.
        First checks if allowed, then increments.
        """
        
        # Check limit first
        check = await FeatureGate.check_limit(user_id, feature)
        
        if not check.get("allowed"):
            return {
                "success": False,
                "error": "limit_reached",
                "message": f"You've reached your {feature.replace('_', ' ')} limit. Please upgrade.",
                "check": check
            }
        
        # Use database function to increment
        try:
            result = supabase.rpc("increment_usage", {
                "p_user_id": user_id,
                "p_feature": feature,
                "p_amount": amount
            }).execute()
            
            if result.data and result.data.get("success"):
                return result.data
        except Exception as e:
            print(f"Error calling increment_usage: {e}")
        
        # Fallback manual increment
        if feature == "analyses_per_month":
            result = supabase.table("subscriptions")\
                .select("analyses_used_this_period")\
                .eq("user_id", user_id)\
                .execute()
            
            current = result.data[0].get("analyses_used_this_period", 0) if result.data else 0
            supabase.table("subscriptions")\
                .update({"analyses_used_this_period": current + amount})\
                .eq("user_id", user_id)\
                .execute()
        
        # Log usage record
        supabase.table("usage_records").insert({
            "user_id": user_id,
            "feature": feature,
            "quantity": amount
        }).execute()
        
        return {
            "success": True,
            "feature": feature,
            "incremented_by": amount
        }
    
    @staticmethod
    async def decrement_usage(user_id: str, feature: str, amount: int = 1):
        """Decrement usage (when removing channels, etc.)."""
        
        try:
            supabase.rpc("decrement_usage", {
                "p_user_id": user_id,
                "p_feature": feature,
                "p_amount": amount
            }).execute()
        except Exception as e:
            print(f"Error calling decrement_usage: {e}")
    
    @staticmethod
    async def can_use_feature(user_id: str, feature: str) -> bool:
        """Simple boolean check if user can use a feature."""
        
        check = await FeatureGate.check_limit(user_id, feature)
        return check.get("allowed", False)
    
    @staticmethod
    async def get_all_usage(user_id: str) -> Dict[str, Any]:
        """Get all usage stats for a user."""
        
        tier = await FeatureGate.get_user_tier(user_id)
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        
        usage = {}
        for feature in ["analyses_per_month", "telegram_channels", "suppliers", "team_seats"]:
            check = await FeatureGate.check_limit(user_id, feature)
            usage[feature] = check
        
        # Add boolean features
        for feature in ["alerts", "bulk_analyze", "api_access", "export_data"]:
            usage[feature] = {
                "allowed": limits.get(feature, False),
                "feature": feature
            }
        
        return {
            "tier": tier,
            "usage": usage
        }


# Dependency for requiring a feature
def require_feature(feature: str):
    """
    FastAPI dependency that checks if user has access to a feature.
    Raises 403 if not allowed.
    """
    
    async def check_feature(current_user = Depends(get_current_user)):
        user_email = getattr(current_user, 'email', None)
        check = await FeatureGate.check_limit(current_user.id, feature, user_email)
        
        if not check.get("allowed"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "feature_limited",
                    "message": f"This feature requires an upgrade. {check.get('feature')} limit reached.",
                    "feature": feature,
                    "tier": check.get("tier"),
                    "limit": check.get("limit"),
                    "used": check.get("used"),
                    "upgrade_url": "/pricing"
                }
            )
        
        return current_user
    
    return check_feature


# Dependency for checking numeric limits
def require_limit(feature: str):
    """
    FastAPI dependency that checks numeric limits before allowing action.
    """
    
    async def check_limit(current_user = Depends(get_current_user)):
        user_email = getattr(current_user, 'email', None)
        check = await FeatureGate.check_limit(current_user.id, feature, user_email)
        
        if not check.get("allowed"):
            limit = check.get("limit", 0)
            used = check.get("used", 0)
            
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "limit_reached",
                    "message": f"You've used {used}/{limit} {feature.replace('_', ' ')}. Please upgrade for more.",
                    "feature": feature,
                    "tier": check.get("tier"),
                    "limit": limit,
                    "used": used,
                    "remaining": 0,
                    "upgrade_url": "/pricing"
                }
            )
        
        # Return the check result along with user for potential use
        current_user._limit_check = check
        return current_user
    
    return check_limit


# Singleton instance
feature_gate = FeatureGate()

