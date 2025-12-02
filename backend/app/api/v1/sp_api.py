"""
SP-API endpoints for product data, pricing, fees, and eligibility.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.api.deps import get_current_user
from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import keepa_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sp-api", tags=["sp-api"])


@router.get("/product/{asin}/offers")
async def get_all_offers(
    asin: str,
    marketplace_id: str = Query("ATVPDKIKX0DER", description="US marketplace"),
    current_user = Depends(get_current_user)
):
    """
    Get all offers/sellers for a product using SP-API.
    Falls back to Keepa if SP-API not available.
    """
    user_id = str(current_user.id)
    
    try:
        # Try SP-API competitive pricing first
        # Get marketplace_id
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
        
        pricing = await sp_api_client.get_competitive_pricing(asin, marketplace_id)
        
        if pricing:
            # For now, return basic pricing data
            # Full offers list requires get_item_offers which needs to be implemented
            return {
                "asin": asin,
                "buy_box_price": pricing.get("buy_box_price"),
                "sales_rank": pricing.get("sales_rank"),
                "source": "sp-api"
            }
        
        # Fallback to Keepa for basic data
        keepa_data = await keepa_client.get_product(asin, domain=1, days=90, history=False)
        if keepa_data:
            current = keepa_data.get("current", {})
            return {
                "asin": asin,
                "buy_box_price": current.get("buy_box"),
                "sales_rank": keepa_data.get("sales_rank"),
                "source": "keepa"
            }
        
        raise HTTPException(404, f"No data available for {asin}")
        
    except Exception as e:
        logger.error(f"Error fetching offers for {asin}: {e}")
        raise HTTPException(500, str(e))


@router.get("/product/{asin}/fees")
async def get_product_fees(
    asin: str,
    price: float = Query(..., description="Sale price"),
    marketplace_id: str = Query("ATVPDKIKX0DER"),
    current_user = Depends(get_current_user)
):
    """
    Get FBA fees estimate from SP-API.
    Falls back to estimated fees if SP-API not available.
    """
    user_id = str(current_user.id)
    
    try:
        fees = await sp_api_client.get_fee_estimate(user_id, asin, price, is_fba=True)
        
        if fees:
            return {
                "asin": asin,
                "price": price,
                "referralFee": fees.get("referral_fee", 0),
                "fbaFee": fees.get("fba_fulfillment_fee", 0),
                "totalFees": fees.get("total_fees", 0),
                "source": "sp-api"
            }
        
        # Fallback: Estimate fees (15% referral + $5 FBA)
        referral_fee = price * 0.15
        fba_fee = 5.00
        return {
            "asin": asin,
            "price": price,
            "referralFee": referral_fee,
            "fbaFee": fba_fee,
            "totalFees": referral_fee + fba_fee,
            "source": "estimated"
        }
        
    except Exception as e:
        logger.error(f"Error fetching fees for {asin}: {e}")
        # Return estimated fees on error
        referral_fee = price * 0.15
        fba_fee = 5.00
        return {
            "asin": asin,
            "price": price,
            "referralFee": referral_fee,
            "fbaFee": fba_fee,
            "totalFees": referral_fee + fba_fee,
            "source": "estimated"
        }


@router.get("/product/{asin}/eligibility")
async def get_product_eligibility(
    asin: str,
    current_user = Depends(get_current_user)
):
    """
    Check if seller can sell this product (restrictions/gating).
    Requires user to be connected to Amazon seller account.
    Returns NOT_CONNECTED if user hasn't connected their account.
    """
    user_id = str(current_user.id)
    
    try:
        # Check if user is connected to Amazon first
        from app.services.supabase_client import supabase
        connection_result = supabase.table("amazon_connections")\
            .select("is_connected, marketplace_id")\
            .eq("user_id", user_id)\
            .eq("is_connected", True)\
            .limit(1)\
            .execute()
        
        if not connection_result.data or not connection_result.data[0].get("is_connected"):
            # User not connected - return not-connected status (don't call API)
            return {
                "asin": asin,
                "canSell": None,
                "status": "NOT_CONNECTED",
                "reasons": ["Amazon seller account not connected. Please connect your account in Settings."],
                "source": "not-connected"
            }
        
        # Get marketplace_id from connection
        marketplace_id = connection_result.data[0].get("marketplace_id") or "ATVPDKIKX0DER"
        
        # Now call eligibility check with CORRECT parameters (asin, marketplace_id)
        eligibility = await sp_api_client.check_eligibility(asin, marketplace_id)
        
        if eligibility:
            return {
                "asin": asin,
                "canSell": eligibility.get("status") == "ELIGIBLE",
                "status": eligibility.get("status", "UNKNOWN"),
                "reasons": eligibility.get("reasons", []),
                "source": "sp-api"
            }
        
        # If API call failed, return unknown
        return {
            "asin": asin,
            "canSell": None,
            "status": "UNKNOWN",
            "reasons": [],
            "source": "unknown"
        }
        
    except Exception as e:
        logger.error(f"Error checking eligibility for {asin}: {e}", exc_info=True)
        # Return safe default instead of raising error
        return {
            "asin": asin,
            "canSell": None,
            "status": "UNKNOWN",
            "reasons": [],
            "source": "error"
        }


@router.get("/product/{asin}/sales-estimate")
async def get_sales_estimate(
    asin: str,
    marketplace_id: str = Query("ATVPDKIKX0DER"),
    current_user = Depends(get_current_user)
):
    """
    Get sales rank and estimate monthly sales.
    Uses SP-API if available, falls back to Keepa.
    """
    user_id = str(current_user.id)
    
    try:
        # Try SP-API first
        # Get marketplace_id
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
        
        pricing = await sp_api_client.get_competitive_pricing(asin, marketplace_id)
        
        sales_rank = None
        category = None
        
        if pricing:
            sales_rank = pricing.get("sales_rank")
            category = pricing.get("sales_rank_category")
        
        # If no SP-API data, try Keepa
        if not sales_rank:
            keepa_data = await keepa_client.get_product(asin, domain=1, days=90, history=False)
            if keepa_data:
                sales_rank = keepa_data.get("sales_rank")
                category = keepa_data.get("category")
        
        # Estimate monthly sales based on BSR (rough formula)
        est_monthly_sales = None
        if sales_rank:
            if sales_rank < 100:
                est_monthly_sales = 3000
            elif sales_rank < 500:
                est_monthly_sales = 1500
            elif sales_rank < 1000:
                est_monthly_sales = 1000
            elif sales_rank < 5000:
                est_monthly_sales = 500
            elif sales_rank < 10000:
                est_monthly_sales = 300
            elif sales_rank < 50000:
                est_monthly_sales = 100
            elif sales_rank < 100000:
                est_monthly_sales = 50
            else:
                est_monthly_sales = max(10, int(300000 / sales_rank))
        
        return {
            "asin": asin,
            "sales_rank": sales_rank,
            "category": category,
            "est_monthly_sales": est_monthly_sales,
            "source": "sp-api" if pricing else "keepa" if sales_rank else "estimated"
        }
        
    except Exception as e:
        logger.error(f"Error getting sales estimate for {asin}: {e}")
        raise HTTPException(500, str(e))

