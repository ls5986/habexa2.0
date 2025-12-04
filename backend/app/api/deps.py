from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token
from app.services.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token."""
    
    token = credentials.credentials
    
    # Log token info (sanitized for security)
    logger.info(f"Auth attempt - Token length: {len(token) if token else 0}")
    logger.info(f"Auth attempt - Token prefix: {token[:20] if token and len(token) > 20 else token}...")
    
    # Try to decode JWT first
    try:
        payload = decode_token(token)
        logger.info(f"JWT decode result: {payload is not None}")
        
        if payload:
            user_id = payload.get("sub")
            logger.info(f"User ID from JWT: {user_id}")
            
            if user_id:
                try:
                    result = supabase.auth.get_user(token)
                    if result.user:
                        logger.info(f"User found via JWT path: {result.user.id}, email: {result.user.email}")
                        return result.user
                    else:
                        logger.warning("Supabase get_user returned no user (JWT path)")
                except Exception as supabase_error:
                    logger.error(f"Supabase get_user error (JWT path): {str(supabase_error)}")
        else:
            logger.info("JWT decode returned None - token may not be a JWT or secret key mismatch")
    except Exception as e:
        logger.error(f"JWT decode error: {str(e)}", exc_info=True)
    
    # Fallback: verify with Supabase directly
    try:
        logger.info("Trying Supabase fallback auth")
        result = supabase.auth.get_user(token)
        if result.user:
            logger.info(f"Supabase fallback success: {result.user.id}, email: {result.user.email}")
            return result.user
        else:
            logger.warning("Supabase fallback returned no user")
    except Exception as e:
        logger.error(f"Supabase fallback error: {str(e)}", exc_info=True)
    
    # All auth methods failed
    logger.error("All auth methods failed - returning 401 Unauthorized")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

