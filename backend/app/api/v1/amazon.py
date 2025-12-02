"""
Amazon SP-API endpoints with per-user OAuth.
Each user connects their own Amazon Seller account.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import List
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services.sp_api_client import sp_api_client
from app.services.amazon_oauth import amazon_oauth
from app.core.config import settings

router = APIRouter(prefix="/integrations/amazon", tags=["amazon"])


# ==========================================
# OAUTH ENDPOINTS
# ==========================================

@router.get("/oauth/authorize")
async def get_auth_url(current_user = Depends(get_current_user)):
    """Get Amazon authorization URL for current user."""
    user_id = str(current_user.id)
    try:
        auth_url = amazon_oauth.get_authorization_url(user_id)
        return {"authorization_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/oauth/callback")
async def oauth_callback(
    spapi_oauth_code: str = Query(None, alias="spapi_oauth_code"),
    state: str = Query(None),
    selling_partner_id: str = Query(None),
    error: str = Query(None),
):
    """Handle Amazon OAuth callback."""
    
    if error:
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?amazon_error={error}"
        )
    
    if not spapi_oauth_code or not state:
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?amazon_error=missing_params"
        )
    
    # state contains user_id
    user_id = state
    
    result = await amazon_oauth.exchange_code_for_token(
        spapi_oauth_code,
        user_id,
        selling_partner_id
    )
    
    if result.get("success"):
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?amazon_connected=true"
        )
    else:
        error_msg = result.get("error", "Connection failed")
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/settings?amazon_error={error_msg}"
        )


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
        "marketplace_id": connection.get("marketplace_id"),
        "connected_at": connection.get("connected_at"),
        "last_used_at": connection.get("last_used_at"),
    }


@router.delete("/disconnect")
async def disconnect_amazon(current_user = Depends(get_current_user)):
    """Disconnect Amazon account."""
    user_id = str(current_user.id)
    success = await amazon_oauth.disconnect(user_id)
    
    if success:
        return {"message": "Disconnected successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to disconnect")


# ==========================================
# SP-API ENDPOINTS (require connection)
# ==========================================

async def require_amazon_connection(current_user = Depends(get_current_user)):
    """Dependency to require user to have Amazon connected."""
    user_id = str(current_user.id)
    connection = await amazon_oauth.get_user_connection(user_id)
    
    if not connection or not connection.get("is_connected"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "amazon_not_connected",
                "message": "Connect your Amazon Seller account first"
            }
        )
    
    return current_user


@router.get("/eligibility/{asin}")
async def check_eligibility(
    asin: str,
    current_user = Depends(require_amazon_connection)
):
    """
    Check if YOU can list this product (real gating check).
    Uses YOUR connected Amazon Seller account.
    """
    user_id = str(current_user.id)
    result = await sp_api_client.check_eligibility(user_id, asin)
    return result


@router.get("/fees/{asin}")
async def get_fees(
    asin: str,
    price: float = Query(..., gt=0),
    current_user = Depends(require_amazon_connection)
):
    """
    Get FBA fee estimate for a product at given price.
    Uses YOUR connected Amazon Seller account.
    """
    user_id = str(current_user.id)
    result = await sp_api_client.get_fee_estimate(user_id, asin, price)
    
    if not result:
        raise HTTPException(status_code=404, detail="Could not get fee estimate")
    
    return result


@router.get("/pricing/{asin}")
async def get_pricing(
    asin: str,
    current_user = Depends(require_amazon_connection)
):
    """
    Get competitive pricing data.
    Uses YOUR connected Amazon Seller account.
    """
    user_id = str(current_user.id)
    # Get user's marketplace preference
    marketplace_id = "ATVPDKIKX0DER"  # Default to US
    try:
        from app.services.supabase_client import supabase
        connection_result = supabase.table("amazon_connections")\
            .select("marketplace_id")\
            .eq("user_id", user_id)\
            .eq("is_connected", True)\
            .limit(1)\
            .execute()
        if connection_result.data and connection_result.data[0].get("marketplace_id"):
            marketplace_id = connection_result.data[0]["marketplace_id"]
    except:
        pass
    
    result = await sp_api_client.get_competitive_pricing(asin, marketplace_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Could not get pricing data")
    
    return result


class BatchEligibilityRequest(BaseModel):
    asins: List[str]


@router.post("/eligibility/batch")
async def check_eligibility_batch(
    request: BatchEligibilityRequest,
    current_user = Depends(require_amazon_connection)
):
    """
    Check eligibility for multiple ASINs (max 20).
    Uses YOUR connected Amazon Seller account.
    """
    if len(request.asins) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 ASINs per request")
    
    user_id = str(current_user.id)
    results = []
    
    for asin in request.asins:
        result = await sp_api_client.check_eligibility(user_id, asin)
        results.append(result)
    
    return {
        "results": results,
        "total": len(results),
        "eligible": len([r for r in results if r.get("status") == "ELIGIBLE"]),
        "restricted": len([r for r in results if r.get("status") in ["NOT_ELIGIBLE", "APPROVAL_REQUIRED"]])
    }
