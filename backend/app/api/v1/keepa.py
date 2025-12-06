"""
Keepa API endpoints for price history and product data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
import logging

from app.api.deps import get_current_user
from app.api.deps_test import get_current_user_optional
from app.core.config import settings
from fastapi import Request
from app.services.keepa_client import keepa_client, KeepaError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keepa", tags=["keepa"])


@router.get("/product/{asin}")
async def get_keepa_product(
    request: Request,
    asin: str,
    days: int = Query(90, ge=30, le=365),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """
    Get Keepa price history and stats for a product.
    
    Args:
        asin: Amazon ASIN
        days: Days of history (30-365)
        
    Returns:
        Product data with price history, averages, and sales estimates
    """
    
    try:
        # Check if API key is configured
        if not keepa_client.api_key:
            logger.error("KEEPA_API_KEY not configured in environment")
            return {
                "asin": asin,
                "error": "Keepa API key not configured",
                "stats": {},
                "price_history": [],
                "rank_history": [],
                "current": {},
                "averages": {}
            }
        
        # Try get_product first, fallback to get_products_batch if method doesn't exist
        data = None
        try:
            if hasattr(keepa_client, 'get_product'):
                data = await keepa_client.get_product(
                    asin=asin,
                    domain=1,  # US marketplace
                    days=days,
                    history=True
                )
            else:
                # Fallback to batch method
                results = await keepa_client.get_products_batch(
                    asins=[asin],
                    domain=1,
                    days=days,
                    history=True
                )
                data = results.get(asin) if results else None
        except AttributeError:
            # Method doesn't exist, use batch
            results = await keepa_client.get_products_batch(
                asins=[asin],
                domain=1,
                days=days,
                history=True
            )
            data = results.get(asin) if results else None
        
        if not data:
            # Return structured empty response instead of error
            logger.warning(f"Keepa returned no data for {asin}. API key configured: {bool(keepa_client.api_key)}")
            return {
                "asin": asin,
                "error": "No data available from Keepa. This may mean: (1) Keepa doesn't track this ASIN, (2) The ASIN doesn't exist, or (3) Check backend logs for API errors.",
                "stats": {},
                "price_history": [],
                "rank_history": [],
                "current": {},
                "averages": {}
            }
        
        return data
        
    except KeepaError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in Keepa endpoint for {asin}: {e}", exc_info=True)
        raise HTTPException(500, f"Internal error fetching Keepa data: {str(e)}")


@router.get("/debug/{asin}")
async def get_keepa_debug(
    request: Request,
    asin: str,
    days: int = Query(90, ge=30, le=365),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """
    Debug endpoint to see raw Keepa API response.
    Returns the actual Keepa API response for troubleshooting.
    """
    try:
        if not keepa_client.api_key:
            return {"error": "Keepa API key not configured"}
        
        # Make direct API call to see raw response
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                "https://api.keepa.com/product",
                params={
                    "key": keepa_client.api_key,
                    "domain": 1,
                    "asin": asin,
                    "stats": days,
                    "history": 1,
                    "rating": 1,
                }
            )
            
            if response.status_code != 200:
                return {
                    "error": f"Keepa API HTTP {response.status_code}",
                    "response_text": response.text[:500]
                }
            
            data = response.json()
            
            return {
                "asin": asin,
                "keepa_response_keys": list(data.keys()),
                "tokens_left": data.get("tokensLeft"),
                "has_products_key": "products" in data,
                "products_type": type(data.get("products")).__name__ if "products" in data else "missing",
                "products_length": len(data.get("products")) if isinstance(data.get("products"), list) else None,
                "products_is_none": data.get("products") is None if "products" in data else None,
                "has_error": "error" in data,
                "error_message": data.get("error") if "error" in data else None,
                "raw_response": data  # Full response for debugging
            }
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}", exc_info=True)
        return {"error": str(e)}


@router.get("/history/{asin}")
async def get_price_history(
    asin: str,
    days: int = Query(90, ge=30, le=365),
    current_user=Depends(get_current_user)
):
    """
    Get just the price history for charts.
    Lighter endpoint that returns only chart data.
    """
    
    try:
        # Try get_product first, fallback to get_products_batch if method doesn't exist
        data = None
        try:
            if hasattr(keepa_client, 'get_product'):
                data = await keepa_client.get_product(
                    asin=asin,
                    domain=1,
                    days=days,
                    history=True
                )
            else:
                # Fallback to batch method
                results = await keepa_client.get_products_batch(
                    asins=[asin],
                    domain=1,
                    days=days,
                    history=True
                )
                data = results.get(asin) if results else None
        except AttributeError:
            # Method doesn't exist, use batch
            results = await keepa_client.get_products_batch(
                asins=[asin],
                domain=1,
                days=days,
                history=True
            )
            data = results.get(asin) if results else None
        
        if not data:
            raise HTTPException(404, f"Product not found: {asin}")
        
        return {
            "asin": asin,
            "price_history": data.get("price_history", []),
            "rank_history": data.get("rank_history", []),
            "current": data.get("current", {}),
            "averages": data.get("averages", {}),
        }
        
    except KeepaError as e:
        raise HTTPException(400, str(e))


@router.post("/batch")
async def get_keepa_batch(
    asins: List[str],
    days: int = Query(90, ge=30, le=365),
    current_user=Depends(get_current_user)
):
    """
    Get Keepa data for multiple ASINs.
    Maximum 100 ASINs per request.
    """
    
    if len(asins) > 100:
        raise HTTPException(400, "Maximum 100 ASINs per request")
    
    if len(asins) == 0:
        return {"products": []}
    
    try:
        products = await keepa_client.get_products_batch(
            asins=asins,
            days=days,
            history=True
        )
        
        return {
            "products": products,
            "count": len(products)
        }
        
    except KeepaError as e:
        raise HTTPException(400, str(e))


@router.get("/tokens")
async def get_token_status(current_user=Depends(get_current_user)):
    """Get current Keepa API token balance."""
    
    return await keepa_client.get_token_status()


@router.get("/sales-estimate/{asin}")
async def get_sales_estimate(
    asin: str,
    current_user=Depends(get_current_user)
):
    """
    Get sales velocity estimate based on rank drops.
    Each rank drop roughly equals one sale.
    """
    
    try:
        # Try get_product first, fallback to get_products_batch if method doesn't exist
        data = None
        try:
            if hasattr(keepa_client, 'get_product'):
                data = await keepa_client.get_product(asin=asin, domain=1, days=180, history=False)
            else:
                # Fallback to batch method
                results = await keepa_client.get_products_batch(
                    asins=[asin],
                    domain=1,
                    days=180,
                    history=False
                )
                data = results.get(asin) if results else None
        except AttributeError:
            # Method doesn't exist, use batch
            results = await keepa_client.get_products_batch(
                asins=[asin],
                domain=1,
                days=180,
                history=False
            )
            data = results.get(asin) if results else None
        
        if not data:
            raise HTTPException(404, f"Product not found: {asin}")
        
        drops = data.get("drops", {})
        
        # Estimate monthly sales from drops
        drops_30 = drops.get("drops_30", 0) or 0
        drops_90 = drops.get("drops_90", 0) or 0
        drops_180 = drops.get("drops_180", 0) or 0
        
        return {
            "asin": asin,
            "sales_rank": data.get("current", {}).get("sales_rank"),
            "category": data.get("sales_rank_category"),
            "drops_30_days": drops_30,
            "drops_90_days": drops_90,
            "drops_180_days": drops_180,
            "estimated_monthly_sales": drops_30,  # Rough estimate
            "estimated_daily_sales": round(drops_30 / 30, 1),
            "note": "Estimates based on BSR drops. Each drop ≈ 1 sale."
        }
        
    except KeepaError as e:
        raise HTTPException(400, str(e))

