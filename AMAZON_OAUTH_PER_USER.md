# AMAZON SP-API OAUTH - PER-USER SELLER CONNECTIONS

## What This Does

Each user connects THEIR OWN Amazon Seller account:
```
User clicks "Connect Amazon" 
    → Redirects to Amazon login
    → User authorizes YOUR app
    → Comes back with auth code
    → Exchange for THEIR refresh token
    → Store encrypted per-user
    → All API calls use THEIR token
```

---

## STEP 1: Database Schema

Add to Supabase:

```sql
-- ============================================
-- AMAZON SELLER CONNECTIONS (Per User)
-- ============================================

CREATE TABLE IF NOT EXISTS public.amazon_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Seller info
    seller_id TEXT,
    marketplace_id TEXT DEFAULT 'ATVPDKIKX0DER',
    
    -- OAuth tokens (encrypted!)
    refresh_token_encrypted TEXT,
    
    -- Connection status
    is_connected BOOLEAN DEFAULT FALSE,
    connected_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    
    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, marketplace_id)
);

CREATE INDEX idx_amazon_connections_user ON public.amazon_connections(user_id);

-- RLS
ALTER TABLE public.amazon_connections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own amazon connection" ON public.amazon_connections
    FOR SELECT USING (auth.uid() = user_id);

-- Update timestamp trigger
CREATE TRIGGER update_amazon_connections_updated_at
    BEFORE UPDATE ON public.amazon_connections
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();
```

---

## STEP 2: Amazon OAuth Service

Create: `backend/app/services/amazon_oauth.py`

```python
"""
Amazon SP-API OAuth service for per-user seller connections.
"""
import os
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.services.supabase_client import supabase
from app.config import settings

logger = logging.getLogger(__name__)

AMAZON_AUTH_URL = "https://sellercentral.amazon.com/apps/authorize/consent"
AMAZON_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


def get_encryption_key() -> bytes:
    """Derive encryption key from SECRET_KEY."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"habexa_amazon_token_salt_v1",
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))


def encrypt_token(token: str) -> str:
    f = Fernet(get_encryption_key())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted.encode()).decode()


class AmazonOAuthService:
    
    def __init__(self):
        self.client_id = settings.SPAPI_LWA_CLIENT_ID
        self.client_secret = settings.SPAPI_LWA_CLIENT_SECRET
        self.app_id = settings.SPAPI_APP_ID
        self.redirect_uri = f"{settings.BACKEND_URL}/api/v1/amazon/oauth/callback"
    
    def get_authorization_url(self, user_id: str) -> str:
        """Generate Amazon authorization URL."""
        params = {
            "application_id": self.app_id,
            "state": user_id,
            "redirect_uri": self.redirect_uri,
            "version": "beta",
        }
        return f"{AMAZON_AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, auth_code: str, user_id: str) -> Dict[str, Any]:
        """Exchange authorization code for refresh token."""
        try:
            async with httpx.AsyncClient() as client:
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
                    return {"success": False, "error": "Failed to exchange code"}
                
                data = response.json()
                refresh_token = data.get("refresh_token")
                
                if not refresh_token:
                    return {"success": False, "error": "No refresh token"}
                
                # Encrypt and store
                encrypted_token = encrypt_token(refresh_token)
                
                supabase.table("amazon_connections").upsert({
                    "user_id": user_id,
                    "marketplace_id": "ATVPDKIKX0DER",
                    "refresh_token_encrypted": encrypted_token,
                    "is_connected": True,
                    "connected_at": datetime.utcnow().isoformat(),
                    "last_error": None,
                    "error_count": 0,
                }, on_conflict="user_id,marketplace_id").execute()
                
                return {"success": True, "message": "Connected successfully"}
                
        except Exception as e:
            logger.error(f"OAuth error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_connection(self, user_id: str) -> Optional[Dict]:
        """Get user's Amazon connection status."""
        result = supabase.table("amazon_connections")\
            .select("*")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data:
            return None
        
        return {
            "is_connected": result.data.get("is_connected", False),
            "seller_id": result.data.get("seller_id"),
            "marketplace_id": result.data.get("marketplace_id"),
            "connected_at": result.data.get("connected_at"),
            "last_error": result.data.get("last_error"),
        }
    
    async def get_user_refresh_token(self, user_id: str) -> Optional[str]:
        """Get decrypted refresh token for a user."""
        result = supabase.table("amazon_connections")\
            .select("refresh_token_encrypted, is_connected")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data or not result.data.get("is_connected"):
            return None
        
        encrypted = result.data.get("refresh_token_encrypted")
        if not encrypted:
            return None
        
        try:
            return decrypt_token(encrypted)
        except:
            return None
    
    async def disconnect(self, user_id: str) -> bool:
        """Disconnect user's Amazon account."""
        try:
            supabase.table("amazon_connections").update({
                "is_connected": False,
                "refresh_token_encrypted": None,
            }).eq("user_id", user_id).execute()
            return True
        except:
            return False


amazon_oauth = AmazonOAuthService()
```

---

## STEP 3: Update SP-API Client

Update: `backend/app/services/sp_api_client.py`

```python
"""
SP-API client using EACH USER'S credentials.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from sp_api.api import ProductFees, ListingsRestrictions
from sp_api.base import Marketplaces, SellingApiException

from app.services.supabase_client import supabase
from app.services.amazon_oauth import decrypt_token
from app.config import settings

logger = logging.getLogger(__name__)


class SPAPIClient:
    
    def __init__(self):
        self.marketplace = Marketplaces.US
    
    def _get_credentials_for_user(self, user_id: str) -> Optional[Dict]:
        """Get SP-API credentials for a specific user."""
        result = supabase.table("amazon_connections")\
            .select("refresh_token_encrypted, seller_id, is_connected")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data or not result.data.get("is_connected"):
            return None
        
        encrypted_token = result.data.get("refresh_token_encrypted")
        if not encrypted_token:
            return None
        
        try:
            refresh_token = decrypt_token(encrypted_token)
        except:
            return None
        
        return {
            "refresh_token": refresh_token,
            "lwa_app_id": settings.SPAPI_LWA_CLIENT_ID,
            "lwa_client_secret": settings.SPAPI_LWA_CLIENT_SECRET,
            "aws_access_key": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_key": settings.AWS_SECRET_ACCESS_KEY,
            "role_arn": settings.SP_API_ROLE_ARN,
        }
    
    async def check_eligibility(self, user_id: str, asin: str) -> Dict[str, Any]:
        """Check if THIS USER can list this product."""
        
        credentials = self._get_credentials_for_user(user_id)
        
        if not credentials:
            return {
                "asin": asin,
                "status": "NOT_CONNECTED",
                "can_list": None,
                "error": "Connect your Amazon Seller account first",
            }
        
        # Get seller ID
        conn = supabase.table("amazon_connections")\
            .select("seller_id")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        seller_id = conn.data.get("seller_id") if conn.data else None
        
        try:
            restrictions_api = ListingsRestrictions(
                credentials=credentials,
                marketplace=self.marketplace
            )
            
            response = restrictions_api.get_listings_restrictions(
                asin=asin,
                sellerId=seller_id,
                marketplaceIds=[settings.MARKETPLACE_ID]
            )
            
            restrictions = response.payload.get("restrictions", [])
            
            if not restrictions:
                return {
                    "asin": asin,
                    "status": "ELIGIBLE",
                    "can_list": True,
                    "reasons": []
                }
            else:
                reasons = []
                approval_required = False
                
                for restriction in restrictions:
                    for reason in restriction.get("reasons", []):
                        reason_code = reason.get("reasonCode", "UNKNOWN")
                        message = reason.get("message", "Restriction applies")
                        reasons.append({"code": reason_code, "message": message})
                        if reason_code == "APPROVAL_REQUIRED":
                            approval_required = True
                
                return {
                    "asin": asin,
                    "status": "APPROVAL_REQUIRED" if approval_required else "NOT_ELIGIBLE",
                    "can_list": False,
                    "reasons": reasons
                }
                
        except SellingApiException as e:
            logger.error(f"SP-API error: {e}")
            return {
                "asin": asin,
                "status": "ERROR",
                "can_list": None,
                "error": str(e)
            }
    
    async def get_fee_estimate(self, user_id: str, asin: str, price: float) -> Optional[Dict]:
        """Get FBA fee estimate using user's account."""
        
        credentials = self._get_credentials_for_user(user_id)
        if not credentials:
            return None
        
        try:
            fees_api = ProductFees(
                credentials=credentials,
                marketplace=self.marketplace
            )
            
            response = fees_api.get_product_fees_estimate_for_asin(
                asin=asin,
                price=price,
                currency="USD",
                is_fba=True,
                shipping=0
            )
            
            if not response.payload:
                return None
            
            fees_result = response.payload.get("FeesEstimateResult", {})
            fees_estimate = fees_result.get("FeesEstimate", {})
            fee_details = fees_estimate.get("FeeDetailList", [])
            
            return {
                "asin": asin,
                "price": price,
                "total_fees": fees_estimate.get("TotalFeesEstimate", {}).get("Amount", 0),
                "referral_fee": self._extract_fee(fee_details, "ReferralFee"),
                "fba_fulfillment_fee": self._extract_fee(fee_details, "FBAFees"),
            }
            
        except Exception as e:
            logger.error(f"Fee estimate error: {e}")
            return None
    
    def _extract_fee(self, fee_list: List[Dict], fee_type: str) -> float:
        for fee in fee_list:
            if fee.get("FeeType") == fee_type:
                return float(fee.get("FeeAmount", {}).get("Amount", 0))
        return 0.0


sp_api_client = SPAPIClient()
```

---

## STEP 4: Amazon API Endpoints

Update: `backend/app/api/v1/amazon.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user
from app.services.amazon_oauth import amazon_oauth
from app.services.sp_api_client import sp_api_client
from app.config import settings

router = APIRouter(prefix="/amazon", tags=["amazon"])


# ==========================================
# OAUTH ENDPOINTS
# ==========================================

@router.get("/oauth/authorize")
async def get_auth_url(current_user = Depends(get_current_user)):
    """Get Amazon authorization URL."""
    user_id = str(current_user.id)
    auth_url = amazon_oauth.get_authorization_url(user_id)
    return {"authorization_url": auth_url}


@router.get("/oauth/callback")
async def oauth_callback(
    spapi_oauth_code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
):
    """Handle Amazon OAuth callback."""
    if error:
        return RedirectResponse(f"{settings.FRONTEND_URL}/settings?amazon_error={error}")
    
    if not spapi_oauth_code or not state:
        return RedirectResponse(f"{settings.FRONTEND_URL}/settings?amazon_error=missing_params")
    
    user_id = state
    result = await amazon_oauth.exchange_code_for_token(spapi_oauth_code, user_id)
    
    if result.get("success"):
        return RedirectResponse(f"{settings.FRONTEND_URL}/settings?amazon_connected=true")
    else:
        return RedirectResponse(f"{settings.FRONTEND_URL}/settings?amazon_error={result.get('error')}")


@router.get("/connection")
async def get_connection_status(current_user = Depends(get_current_user)):
    """Check if user has connected Amazon."""
    user_id = str(current_user.id)
    connection = await amazon_oauth.get_user_connection(user_id)
    
    if not connection:
        return {"connected": False}
    
    return {
        "connected": connection.get("is_connected", False),
        "seller_id": connection.get("seller_id"),
        "connected_at": connection.get("connected_at"),
    }


@router.delete("/disconnect")
async def disconnect_amazon(current_user = Depends(get_current_user)):
    """Disconnect Amazon account."""
    await amazon_oauth.disconnect(str(current_user.id))
    return {"message": "Disconnected"}


# ==========================================
# SP-API ENDPOINTS (require connection)
# ==========================================

async def require_amazon_connection(current_user = Depends(get_current_user)):
    """Require user to have Amazon connected."""
    connection = await amazon_oauth.get_user_connection(str(current_user.id))
    
    if not connection or not connection.get("is_connected"):
        raise HTTPException(403, {
            "error": "amazon_not_connected",
            "message": "Connect your Amazon Seller account first"
        })
    
    return current_user


@router.get("/eligibility/{asin}")
async def check_eligibility(asin: str, current_user = Depends(require_amazon_connection)):
    """Check if YOU can list this product."""
    return await sp_api_client.check_eligibility(str(current_user.id), asin)


@router.get("/fees/{asin}")
async def get_fees(
    asin: str,
    price: float = Query(..., gt=0),
    current_user = Depends(require_amazon_connection)
):
    """Get FBA fee estimate."""
    result = await sp_api_client.get_fee_estimate(str(current_user.id), asin, price)
    if not result:
        raise HTTPException(404, "Could not get fees")
    return result
```

---

## STEP 5: Frontend Component

Create: `frontend/src/components/features/settings/AmazonConnect.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, Button, Alert, Chip, CircularProgress } from '@mui/material';
import { Store, CheckCircle, LinkOff } from '@mui/icons-material';
import { useSearchParams } from 'react-router-dom';
import api from '../../../services/api';

export default function AmazonConnect() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [connection, setConnection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchConnection();
    
    // Check callback params
    if (searchParams.get('amazon_connected') === 'true') {
      setMessage({ type: 'success', text: 'Amazon connected successfully!' });
      searchParams.delete('amazon_connected');
      setSearchParams(searchParams);
    }
    if (searchParams.get('amazon_error')) {
      setMessage({ type: 'error', text: searchParams.get('amazon_error') });
      searchParams.delete('amazon_error');
      setSearchParams(searchParams);
    }
  }, []);

  const fetchConnection = async () => {
    try {
      const res = await api.get('/amazon/connection');
      setConnection(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const res = await api.get('/amazon/oauth/authorize');
      window.location.href = res.data.authorization_url;
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to start connection' });
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Disconnect your Amazon account?')) return;
    try {
      await api.delete('/amazon/disconnect');
      setConnection({ connected: false });
      setMessage({ type: 'success', text: 'Disconnected' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to disconnect' });
    }
  };

  if (loading) {
    return <Card><CardContent sx={{ textAlign: 'center' }}><CircularProgress /></CardContent></Card>;
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <Store sx={{ fontSize: 32, color: '#FF9900' }} />
          <Box flex={1}>
            <Typography variant="h6">Amazon Seller Account</Typography>
            <Typography variant="body2" color="text.secondary">
              Connect to check YOUR gating and fees
            </Typography>
          </Box>
          {connection?.connected && (
            <Chip icon={<CheckCircle />} label="Connected" color="success" />
          )}
        </Box>

        {message && (
          <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
            {message.text}
          </Alert>
        )}

        {connection?.connected ? (
          <Box>
            <Typography variant="body2" color="text.secondary" mb={2}>
              Connected: {new Date(connection.connected_at).toLocaleDateString()}
            </Typography>
            <Button variant="outlined" color="error" startIcon={<LinkOff />} onClick={handleDisconnect}>
              Disconnect
            </Button>
          </Box>
        ) : (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              Connect your Amazon Seller account to see YOUR eligibility status on products.
            </Alert>
            <Button
              variant="contained"
              size="large"
              startIcon={connecting ? <CircularProgress size={20} /> : <Store />}
              onClick={handleConnect}
              disabled={connecting}
              sx={{ bgcolor: '#FF9900', '&:hover': { bgcolor: '#E88B00' } }}
            >
              {connecting ? 'Connecting...' : 'Connect Amazon'}
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## STEP 6: Update Amazon App Redirect URI

In **Amazon Seller Central → Develop Apps → Your App → Edit**:

```
OAuth Redirect URI: https://your-backend.com/api/v1/amazon/oauth/callback
```

For local dev:
```
http://localhost:8000/api/v1/amazon/oauth/callback
```

---

## CURSOR PROMPT

```
Update Amazon integration for per-user OAuth:

1. Run the amazon_connections table SQL in Supabase

2. Create backend/app/services/amazon_oauth.py with:
   - get_authorization_url(user_id) 
   - exchange_code_for_token(auth_code, user_id)
   - get_user_connection(user_id)
   - disconnect(user_id)
   - Token encryption with Fernet

3. Update backend/app/services/sp_api_client.py:
   - _get_credentials_for_user(user_id) - get per-user token
   - check_eligibility(user_id, asin)
   - get_fee_estimate(user_id, asin, price)

4. Update backend/app/api/v1/amazon.py:
   - GET /amazon/oauth/authorize
   - GET /amazon/oauth/callback  
   - GET /amazon/connection
   - DELETE /amazon/disconnect
   - require_amazon_connection dependency

5. Create frontend/src/components/features/settings/AmazonConnect.jsx

6. Add AmazonConnect to Settings page integrations tab

Each user connects THEIR OWN Amazon account and sees THEIR eligibility.
```

---

## Flow Summary

```
1. User clicks "Connect Amazon"
2. Backend returns authorization URL
3. User redirected to Amazon login
4. User authorizes your app
5. Amazon redirects to /oauth/callback with code
6. Backend exchanges code for refresh token
7. Token encrypted and stored in amazon_connections
8. User sees "Connected" status
9. All eligibility/fee checks use THEIR token
```

Now each seller sees THEIR OWN gating status! 🎯
