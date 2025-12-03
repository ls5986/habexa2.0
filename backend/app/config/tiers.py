"""
SINGLE SOURCE OF TRUTH FOR ALL TIER LIMITS

Every other file must import from here. Delete all other TIER_LIMITS definitions.
"""
from typing import Dict, Any

# Tier limits configuration
TIER_LIMITS: Dict[str, Dict[str, Any]] = {
    "free": {
        "telegram_channels": 1,
        "analyses_per_month": 5,  # Changed from 10 to 5 per user request
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
        "telegram_channels": -1,  # -1 means unlimited
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

# Super admin emails - get unlimited access to everything
# Move to env var in production
SUPER_ADMIN_EMAILS = [
    "lindsey@letsclink.com"
]


def is_super_admin(user_email: str) -> bool:
    """Check if user is super admin by email"""
    if not user_email:
        return False
    return user_email.lower() in [e.lower() for e in SUPER_ADMIN_EMAILS]


def get_tier_limits(tier: str) -> Dict[str, Any]:
    """Get limits for a tier, defaults to free"""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"]).copy()

