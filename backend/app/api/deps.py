from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token
from app.services.supabase_client import supabase

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token."""
    
    token = credentials.credentials
    
    # Try to decode JWT first
    payload = decode_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            # Get user from Supabase
            result = supabase.auth.get_user(token)
            if result.user:
                return result.user
    
    # Fallback: verify with Supabase
    try:
        result = supabase.auth.get_user(token)
        if result.user:
            return result.user
    except:
        pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

