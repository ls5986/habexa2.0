"""
User endpoints - provides /users/me as alias for /auth/me
"""
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/me")
async def get_current_user_info(current_user=Depends(get_current_user)):
    """Get current authenticated user information.
    
    This endpoint is an alias for /api/v1/auth/me for backward compatibility.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "user_metadata": current_user.user_metadata or {}
    }

