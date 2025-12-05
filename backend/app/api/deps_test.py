"""
Optional authentication dependencies for testing.
Allows endpoints to work with or without auth when TEST_MODE is enabled.
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.config import settings
from app.services.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)  # Don't auto-raise on missing token


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check X-Forwarded-For header (from proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP if multiple
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client
    if request.client:
        return request.client.host
    
    return "unknown"


def is_ip_allowed(ip: str) -> bool:
    """Check if IP is in allowed list."""
    if not settings.ALLOWED_IPS:
        return False
    
    allowed = [ip.strip() for ip in settings.ALLOWED_IPS.split(",") if ip.strip()]
    return ip in allowed


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Optional authentication - returns user if token provided, None otherwise.
    
    In TEST_MODE:
    - If IP is whitelisted, allows access without auth
    - Otherwise requires auth token
    """
    # If token provided, try to authenticate
    if credentials:
        token = credentials.credentials
        try:
            result = supabase.auth.get_user(token)
            if result.user:
                return result.user
        except Exception as e:
            logger.warning(f"Auth token validation failed: {e}")
    
    # No token or invalid token
    # In TEST_MODE with IP whitelist, allow access
    if settings.TEST_MODE:
        client_ip = get_client_ip(request)
        if is_ip_allowed(client_ip):
            logger.info(f"✅ TEST_MODE: Allowing access from whitelisted IP: {client_ip}")
            return None  # Return None to indicate no user, but allow access
        else:
            logger.warning(f"⚠️ TEST_MODE: IP {client_ip} not whitelisted. Allowed IPs: {settings.ALLOWED_IPS}")
    
    # Not in test mode or IP not whitelisted - require auth
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token or enable TEST_MODE with IP whitelist.",
        headers={"WWW-Authenticate": "Bearer"},
    )

