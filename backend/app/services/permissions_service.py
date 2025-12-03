"""
Centralized permissions service for tier enforcement.
Handles super admin bypass and effective limits calculation.
"""
from typing import Dict, Any
from app.config.tiers import TIER_LIMITS, is_super_admin, get_tier_limits


class PermissionsService:
    """Service for checking user permissions and limits."""
    
    @staticmethod
    def get_effective_limits(user) -> Dict[str, Any]:
        """
        Returns effective limits for user.
        Super admins get unlimited everything.
        
        Args:
            user: User object with .email attribute (from get_current_user)
        
        Returns:
            Dict with limits, unlimited flag, tier info
        """
        user_email = getattr(user, 'email', None)
        
        # SUPER ADMIN BYPASS - Check first
        if is_super_admin(user_email):
            # Return unlimited for everything (like agency tier but marked as super_admin)
            limits = {}
            for key, value in TIER_LIMITS["agency"].items():
                if isinstance(value, int):
                    limits[key] = -1  # Unlimited
                elif isinstance(value, bool):
                    limits[key] = True  # All features enabled
                else:
                    limits[key] = value
            
            limits["unlimited"] = True
            limits["is_super_admin"] = True
            limits["tier"] = "super_admin"
            limits["tier_display"] = "Super Admin (Unlimited)"
            
            return limits
        
        # Regular user - get their tier from database
        user_id = str(getattr(user, 'id', None))
        
        # Get tier from database (async, but we're in sync method)
        # Use run_async helper if available, otherwise default to free
        try:
            # Try to get tier synchronously from database
            from app.services.supabase_client import supabase
            result = supabase.table("subscriptions")\
                .select("tier, status")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            
            if result.data:
                sub = result.data
                # Check if subscription is active
                if sub.get("status") in ["active", "trialing"]:
                    tier = sub.get("tier", "free")
                else:
                    tier = "free"
            else:
                tier = "free"
        except Exception:
            # Fallback to free if database lookup fails
            tier = "free"
        
        limits = get_tier_limits(tier)
        limits["unlimited"] = False
        limits["is_super_admin"] = False
        limits["tier"] = tier
        limits["tier_display"] = tier.title()
        
        return limits
    
    @staticmethod
    def check_limit(user, feature: str, current_usage: int = 0) -> Dict[str, Any]:
        """
        Check if user can use a feature.
        
        Args:
            user: User object with .email attribute
            feature: Feature name (e.g., "analyses_per_month")
            current_usage: Current usage count for this feature
        
        Returns:
            {
                "allowed": bool,
                "remaining": int (-1 for unlimited),
                "limit": int (-1 for unlimited),
                "unlimited": bool,
                "is_super_admin": bool,
                "message": str or None
            }
        """
        limits = PermissionsService.get_effective_limits(user)
        
        # Super admin or unlimited tier
        if limits["unlimited"] or limits.get(feature) == -1:
            return {
                "allowed": True,
                "remaining": -1,
                "limit": -1,
                "unlimited": True,
                "is_super_admin": limits["is_super_admin"],
                "tier": limits["tier"],
                "tier_display": limits["tier_display"],
                "message": None
            }
        
        # Boolean features (alerts, bulk_analyze, etc.)
        if feature in ["alerts", "bulk_analyze", "api_access", "export_data", "priority_support"]:
            allowed = limits.get(feature, False)
            return {
                "allowed": allowed,
                "unlimited": False,
                "is_super_admin": False,
                "tier": limits["tier"],
                "tier_display": limits["tier_display"],
                "message": None if allowed else f"{feature.replace('_', ' ').title()} requires an upgrade."
            }
        
        # Numeric limits
        limit = limits.get(feature, 0)
        remaining = max(0, limit - current_usage)
        allowed = current_usage < limit
        
        return {
            "allowed": allowed,
            "remaining": remaining,
            "limit": limit,
            "unlimited": False,
            "is_super_admin": False,
            "tier": limits["tier"],
            "tier_display": limits["tier_display"],
            "message": None if allowed else f"You've reached your {feature.replace('_', ' ')} limit ({limit}). Upgrade to continue."
        }
    
    @staticmethod
    def should_track_usage(user) -> bool:
        """
        Returns False for super admins - their usage should not be tracked.
        
        Args:
            user: User object with .email attribute
        
        Returns:
            bool: True if usage should be tracked, False for super admins
        """
        user_email = getattr(user, 'email', None)
        return not is_super_admin(user_email)

