"""
Amazon SP-API OAuth service for per-user seller connections.
Each user connects their own Amazon Seller account.
"""
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode

from app.services.supabase_client import supabase
from app.core.encryption import encrypt_token, decrypt_token
from app.core.config import settings

logger = logging.getLogger(__name__)

AMAZON_AUTH_URL = "https://sellercentral.amazon.com/apps/authorize/consent"
AMAZON_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


class AmazonOAuthService:
    """Handle Amazon SP-API OAuth for per-user connections."""
    
    def __init__(self):
        # Use new names with fallback to legacy
        self.client_id = settings.SP_API_LWA_APP_ID or settings.SPAPI_LWA_CLIENT_ID
        self.client_secret = settings.SP_API_LWA_CLIENT_SECRET or settings.SPAPI_LWA_CLIENT_SECRET
        self.app_id = settings.SPAPI_APP_ID  # SP-API Application ID (different from LWA client ID)
        # Use backend URL for callback
        self.redirect_uri = f"{settings.BACKEND_URL}/api/v1/integrations/amazon/oauth/callback"
    
    def get_authorization_url(self, user_id: str) -> str:
        """Generate Amazon authorization URL for a user."""
        
        if not self.app_id:
            raise ValueError("SPAPI_APP_ID not configured")
        
        params = {
            "application_id": self.app_id,
            "state": user_id,  # Use user_id as state for simplicity
            "redirect_uri": self.redirect_uri,
            "version": "beta",
        }
        return f"{AMAZON_AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(
        self,
        auth_code: str,
        user_id: str,
        selling_partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for refresh token."""
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    AMAZON_TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to exchange code: {response.text}"
                    }
                
                data = response.json()
                refresh_token = data.get("refresh_token")
                
                if not refresh_token:
                    return {
                        "success": False,
                        "error": "No refresh token in response"
                    }
                
                # Encrypt and store
                encrypted_token = encrypt_token(refresh_token)
                
                # Store connection
                connection_data = {
                    "user_id": user_id,
                    "marketplace_id": settings.MARKETPLACE_ID or "ATVPDKIKX0DER",
                    "refresh_token_encrypted": encrypted_token,
                    "is_connected": True,
                    "connected_at": datetime.utcnow().isoformat(),
                    "last_error": None,
                    "error_count": 0,
                }
                
                # Add seller_id if provided
                if selling_partner_id:
                    connection_data["seller_id"] = selling_partner_id
                
                supabase.table("amazon_connections").upsert(
                    connection_data,
                    on_conflict="user_id,marketplace_id"
                ).execute()
                
                logger.info(f"Amazon account connected for user {user_id}")
                
                return {
                    "success": True,
                    "message": "Connected successfully"
                }
                
        except Exception as e:
            logger.error(f"OAuth error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_user_connection(self, user_id: str) -> Optional[Dict]:
        """Get user's Amazon connection status."""
        
        try:
            result = supabase.table("amazon_connections")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("marketplace_id", settings.MARKETPLACE_ID or "ATVPDKIKX0DER")\
                .maybe_single()\
                .execute()
            
            if not result or not result.data:
                return None
            
            return {
                "is_connected": result.data.get("is_connected", False),
                "seller_id": result.data.get("seller_id"),
                "marketplace_id": result.data.get("marketplace_id"),
                "connected_at": result.data.get("connected_at"),
                "last_error": result.data.get("last_error"),
                "last_used_at": result.data.get("last_used_at"),
            }
        except Exception as e:
            # 406 errors are expected if table doesn't exist or RLS blocks access
            # Just return None instead of logging error
            logger.debug(f"Amazon connection check failed (user may not be connected): {e}")
            return None
    
    async def get_user_refresh_token(self, user_id: str) -> Optional[str]:
        """Get decrypted refresh token for a user."""
        
        try:
            result = supabase.table("amazon_connections")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("marketplace_id", settings.MARKETPLACE_ID or "ATVPDKIKX0DER")\
                .maybe_single()\
                .execute()
            
            if not result or not result.data:
                return None
            
            if not result.data.get("is_connected"):
                return None
            
            encrypted = result.data.get("refresh_token_encrypted")
            if not encrypted:
                return None
            
            try:
                return decrypt_token(encrypted)
            except Exception as e:
                logger.error(f"Token decryption failed: {e}")
                return None
        except Exception as e:
            logger.error(f"Error getting refresh token: {e}")
            return None
    
    async def disconnect(self, user_id: str) -> bool:
        """Disconnect user's Amazon account."""
        
        try:
            supabase.table("amazon_connections").update({
                "is_connected": False,
                "refresh_token_encrypted": None,
                "last_error": "User disconnected",
            }).eq("user_id", user_id).execute()
            
            logger.info(f"Amazon account disconnected for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False
    
    async def update_last_used(self, user_id: str):
        """Update last_used_at timestamp."""
        
        try:
            supabase.table("amazon_connections").update({
                "last_used_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
        except Exception as e:
            logger.debug(f"Failed to update last_used: {e}")


# Singleton instance
amazon_oauth = AmazonOAuthService()
