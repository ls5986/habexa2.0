"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


@router.post("/login")
async def login(request: LoginRequest):
    """
    Login is handled client-side by Supabase Auth.
    
    This endpoint provides documentation for client-side authentication.
    Use Supabase client SDK: supabase.auth.signInWithPassword()
    """
    return {
        "message": "Use Supabase client-side auth",
        "method": "supabase.auth.signInWithPassword({ email, password })",
        "docs": "https://supabase.com/docs/reference/javascript/auth-signinwithpassword",
        "note": "Authentication is handled client-side for security. This endpoint is informational only."
    }


@router.post("/register")
async def register(request: RegisterRequest):
    """
    Registration is handled client-side by Supabase Auth.
    
    This endpoint provides documentation for client-side authentication.
    Use Supabase client SDK: supabase.auth.signUp()
    """
    return {
        "message": "Use Supabase client-side auth",
        "method": "supabase.auth.signUp({ email, password, options: { data: { full_name } } })",
        "docs": "https://supabase.com/docs/reference/javascript/auth-signup",
        "note": "Authentication is handled client-side for security. This endpoint is informational only."
    }


@router.get("/me")
async def get_current_user_info(current_user=Depends(get_current_user)):
    """Get current authenticated user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "user_metadata": current_user.user_metadata or {}
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user)
):
    """Change user's password.
    
    Note: Supabase password changes should be done client-side with the session token.
    This endpoint validates the request and returns success, but the actual password
    change should be done via supabase.auth.updateUser() on the frontend.
    """
    try:
        # Validate new password
        if len(request.new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        # Additional password strength validation
        if not any(c.isupper() for c in request.new_password):
            raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
        if not any(c.islower() for c in request.new_password):
            raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in request.new_password):
            raise HTTPException(status_code=400, detail="Password must contain at least one number")
        
        # Log password change request (for audit)
        logger.info(f"Password change validated for user {current_user.id}")
        
        # Return success - actual password change happens client-side via Supabase
        return {
            "message": "Password validation successful. Password will be updated client-side.",
            "validated": True
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

