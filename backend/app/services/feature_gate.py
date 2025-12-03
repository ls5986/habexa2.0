from typing import Dict, Any, Optional
from functools import wraps
from fastapi import HTTPException, Depends
import logging

from app.services.supabase_client import supabase
from app.api.deps import get_current_user
from app.config.tiers import TIER_LIMITS, SUPER_ADMIN_EMAILS, is_super_admin, get_tier_limits

logger = logging.getLogger(__name__)


class FeatureGate:
    """Feature gating service to enforce subscription limits."""
    
    @staticmethod
    async def get_user_tier(user_id: str, user_email: Optional[str] = None) -> str:
        """Get user's current subscription tier. Uses Redis cache if available."""
        from app.services.redis_client import cache_service
        
        # Check if user is super admin
        if is_super_admin(user_email):
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
    async def get_user_limits(user) -> Dict[str, Any]:
        """Get all limits for user's tier.
        
        Args:
            user: User object with .id and .email attributes
        """
        from app.services.permissions_service import PermissionsService
        
        limits = PermissionsService.get_effective_limits(user)
        return {
            "tier": limits["tier"],
            "limits": {k: v for k, v in limits.items() if k not in ["unlimited", "is_super_admin", "tier", "tier_display"]}
        }
    
    @staticmethod
    async def check_limit(user, feature: str) -> Dict[str, Any]:
        """
        Check if user can use a feature.
        NOW USES PermissionsService for centralized logic.
        
        Args:
            user: User object with .id and .email attributes (from get_current_user)
            feature: Feature name (e.g., "analyses_per_month")
        
        Returns:
            {
                "allowed": bool,
                "tier": str,
                "feature": str,
                "limit": int (or -1 for unlimited),
                "used": int,
                "remaining": int (or -1 for unlimited),
                "unlimited": bool,
                "upgrade_required": bool,
                "is_super_admin": bool
            }
        """
        from app.services.permissions_service import PermissionsService
        
        # Get current usage from database
        user_id = str(user.id)
        used = await FeatureGate._get_usage(user_id, feature)
        
        # Use centralized permissions service
        permission = PermissionsService.check_limit(user, feature, used)
        
        # Format response to match expected structure
        return {
            "allowed": permission["allowed"],
            "tier": permission.get("tier", "free"),
            "feature": feature,
            "limit": permission["limit"],
            "used": used,
            "remaining": permission["remaining"],
            "unlimited": permission["unlimited"],
            "is_super_admin": permission.get("is_super_admin", False),
            "upgrade_required": not permission["allowed"]
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
    async def increment_usage(user, feature: str, amount: int = 1) -> Dict[str, Any]:
        """
        Increment usage for a feature.
        DOES NOT INCREMENT FOR SUPER ADMINS.
        First checks if allowed, then increments.
        
        Args:
            user: User object with .id and .email attributes
            feature: Feature name
            amount: Amount to increment (default 1)
        """
        from app.services.permissions_service import PermissionsService
        
        # Check if we should track this user's usage (super admins skip)
        if not PermissionsService.should_track_usage(user):
            logger.info(f"Skipping usage increment for super admin: {getattr(user, 'email', 'unknown')}")
            return {
                "success": True,
                "feature": feature,
                "incremented_by": 0,
                "skipped": True,
                "reason": "super_admin"
            }
        
        # Check limit first
        user_id = str(user.id)
        check = await FeatureGate.check_limit(user, feature)
        
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
            logger.debug(f"Error calling increment_usage RPC: {e}, using fallback")
        
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
        try:
            supabase.table("usage_records").insert({
                "user_id": user_id,
                "feature": feature,
                "quantity": amount
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log usage record: {e}")
        
        return {
            "success": True,
            "feature": feature,
            "incremented_by": amount,
            "skipped": False
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
    async def can_use_feature(user, feature: str) -> bool:
        """Simple boolean check if user can use a feature."""
        
        check = await FeatureGate.check_limit(user, feature)
        return check.get("allowed", False)
    
    @staticmethod
    async def get_all_usage(user) -> Dict[str, Any]:
        """Get all usage stats for a user.
        
        Args:
            user: User object with .id and .email attributes
        """
        user_id = str(user.id)
        tier = await FeatureGate.get_user_tier(user_id, getattr(user, 'email', None))
        limits = get_tier_limits(tier)
        
        usage = {}
        for feature in ["analyses_per_month", "telegram_channels", "suppliers", "team_seats"]:
            check = await FeatureGate.check_limit(user, feature)
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
        check = await FeatureGate.check_limit(current_user, feature)
        
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
        check = await FeatureGate.check_limit(current_user, feature)
        
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

