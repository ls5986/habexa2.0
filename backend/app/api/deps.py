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
    
    # Verify with Supabase directly (Supabase JWTs use their own secret, not local JWT secret)
    # Skip local JWT decode since it always fails for Supabase tokens
    try:
        result = supabase.auth.get_user(token)
        if result.user:
            return result.user
        else:
            logger.warning("Supabase get_user returned no user")
    except Exception as e:
        logger.error(f"Supabase auth error: {str(e)}", exc_info=True)
    
    # Auth failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

