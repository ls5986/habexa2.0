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
            logger.warning(f"Keepa returned no data for {asin}")
            return {
                "asin": asin,
                "error": "No data available from Keepa",
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in Keepa endpoint for {asin}: {e}")
        raise HTTPException(500, f"Internal error fetching Keepa data: {str(e)}")


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

