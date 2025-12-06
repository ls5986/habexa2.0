"""Keepa router - FIXED."""
from fastapi import APIRouter, Depends, Query
from typing import List
import httpx
import logging

from app.api.deps import get_current_user
from app.api.deps_test import get_current_user_optional
from app.core.config import settings
from app.services.keepa_client import get_keepa_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keepa", tags=["keepa"])


@router.get("/tokens")
async def get_tokens(current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)):
    """Get token status."""
    return await get_keepa_client().get_tokens_left()


@router.get("/product/{asin}")
async def get_product(
    asin: str,
    days: int = Query(default=90),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Get Keepa data for single product."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return {"asin": asin, "error": "Not configured", "current": {}, "stats": {}}
    
    data = await client.get_product(asin, days)
    
    if not data:
        return {"asin": asin, "error": "No data from Keepa", "current": {}, "stats": {}}
    
    return data


@router.get("/history/{asin}")
async def get_history(
    asin: str,
    days: int = Query(default=90),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Get price/rank history."""
    client = get_keepa_client()
    data = await client.get_product(asin, days) if client.is_configured() else None
    
    return {
        "asin": asin,
        "price_history": (data or {}).get("price_history", []),
        "rank_history": (data or {}).get("rank_history", []),
        "current": (data or {}).get("current", {}),
        "stats": (data or {}).get("stats", {}),
    }


@router.get("/sales-estimate/{asin}")
async def get_sales_estimate(
    asin: str,
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Estimate monthly sales from BSR."""
    client = get_keepa_client()
    data = await client.get_product(asin, 30) if client.is_configured() else None
    
    rank = (data or {}).get("current", {}).get("sales_rank")
    drops = (data or {}).get("stats", {}).get("drops_30", 0)
    
    est = None
    if rank and rank > 0:
        if rank < 1000: est = 1000
        elif rank < 5000: est = 500
        elif rank < 10000: est = 300
        elif rank < 50000: est = 100
        elif rank < 100000: est = 50
        else: est = 20
        
        # Boost by drops
        if drops > 50:
            est = int(est * 1.3)
    
    return {
        "asin": asin,
        "estimated_sales": est,
        "rank": rank,
        "drops_30": drops,
    }


@router.post("/batch")
async def get_batch(
    asins: List[str],
    days: int = Query(default=90),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Get Keepa data for multiple ASINs."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return {"error": "Not configured", "products": {}}
    
    if len(asins) > 100:
        return {"error": "Max 100 ASINs per request", "products": {}}
    
    products = await client.get_products_batch(asins, days)
    
    return {
        "products": products,
        "count": len(products),
        "requested": len(asins),
    }


@router.get("/debug/{asin}")
async def debug_keepa(asin: str):
    """Debug endpoint - raw response. NO AUTH."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return {"error": "Not configured"}
    
    try:
        params = {
            "key": client.api_key,
            "domain": 1,
            "asin": asin,
            "stats": 30,
            "offers": 5,
        }
        
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get("https://api.keepa.com/product", params=params)
            d = r.json()
        
        prods = d.get("products") or []
        
        if not prods:
            return {
                "status": r.status_code,
                "products_length": 0,
                "tokens": d.get("tokensLeft"),
            }
        
        p = prods[0]
        stats = p.get("stats") or {}
        
        return {
            "status": r.status_code,
            "products_length": len(prods),
            "tokens": d.get("tokensLeft"),
            "asin": p.get("asin"),
            "title": p.get("title"),
            "brand": p.get("brand"),
            "current": (stats.get("current") or [])[:10],
            "drops30": stats.get("salesRankDrops30"),
            "fba": stats.get("offerCountFBA"),
            "fbm": stats.get("offerCountFBM"),
        }
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/test/{asin}")
async def test_keepa(asin: str, days: int = Query(default=90)):
    """Test endpoint - NO AUTH. Uses the fixed client."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return {"error": "Not configured", "asin": asin}
    
    data = await client.get_product(asin, days)
    
    if not data:
        return {"error": "No data", "asin": asin}
    
    return data
