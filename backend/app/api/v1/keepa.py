"""Keepa API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from typing import List
import logging
import httpx

from app.api.deps import get_current_user
from app.api.deps_test import get_current_user_optional
from app.core.config import settings
from app.services.keepa_client import get_keepa_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keepa", tags=["keepa"])


@router.get("/tokens")
async def get_tokens(
    request: Request,
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Check Keepa token status."""
    client = get_keepa_client()
    return await client.get_tokens_left()


@router.get("/product/{asin}")
async def get_product(
    request: Request,
    asin: str,
    days: int = Query(default=90, ge=1, le=365),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Get Keepa data for a product."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return _empty(asin, "Keepa API key not configured")
    
    data = await client.get_product(asin, days)
    
    if not data:
        return _empty(asin, "No data from Keepa")
    
    if data.get("error"):
        return _empty(asin, data["error"])
    
    return data


@router.get("/history/{asin}")
async def get_history(
    request: Request,
    asin: str,
    days: int = Query(default=90),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Get price/rank history for charts."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return _empty(asin, "Not configured")
    
    data = await client.get_product(asin, days)
    
    if not data:
        return _empty(asin, "No data")
    
    return {
        "asin": asin,
        "price_history": data.get("price_history", []),
        "rank_history": data.get("rank_history", []),
        "current": data.get("current", {}),
        "stats": data.get("stats", {}),
    }


@router.get("/sales-estimate/{asin}")
async def get_sales_estimate(
    request: Request,
    asin: str,
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Estimate sales from BSR."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return {"asin": asin, "estimated_sales": None}
    
    data = await client.get_product(asin, days=30)
    
    if not data:
        return {"asin": asin, "estimated_sales": None}
    
    rank = data.get("current", {}).get("sales_rank")
    drops = data.get("stats", {}).get("drops_30", 0)
    
    est = None
    if rank and rank > 0:
        if rank < 1000: est = 1000
        elif rank < 5000: est = 500
        elif rank < 10000: est = 300
        elif rank < 50000: est = 100
        elif rank < 100000: est = 50
        else: est = 20
        if drops > 50: est = int(est * 1.3)
    
    return {"asin": asin, "estimated_sales": est, "rank": rank, "drops_30": drops}


@router.post("/batch")
async def get_batch(
    request: Request,
    asins: List[str],
    days: int = 90,
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    """Get data for multiple ASINs."""
    if len(asins) > 100:
        raise HTTPException(400, "Max 100 ASINs")
    
    client = get_keepa_client()
    if not client.is_configured():
        return {"products": {}}
    
    products = await client.get_products_batch(asins, days)
    return {"products": products, "count": len(products)}


@router.get("/debug/{asin}")
async def debug_keepa(asin: str):
    """Debug - raw Keepa response."""
    client = get_keepa_client()
    
    if not client.is_configured():
        return {"error": "Not configured"}
    
    try:
        params = {"key": client.api_key, "domain": 1, "asin": asin, "stats": 30, "offers": 5}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get("https://api.keepa.com/product", params=params)
            d = r.json()
        
        prods = d.get("products", [])
        if not prods:
            return {"status": r.status_code, "tokens": d.get("tokensLeft"), "products": 0}
        
        p = prods[0]
        return {
            "status": r.status_code,
            "tokens": d.get("tokensLeft"),
            "asin": p.get("asin"),
            "title": p.get("title"),
            "brand": p.get("brand"),
            "has_stats": bool(p.get("stats")),
            "has_csv": bool(p.get("csv")),
            "current": (p.get("stats") or {}).get("current", [])[:10],
            "drops30": (p.get("stats") or {}).get("salesRankDrops30"),
            "fba": (p.get("stats") or {}).get("offerCountFBA"),
            "fbm": (p.get("stats") or {}).get("offerCountFBM"),
        }
    except Exception as e:
        return {"error": str(e)}


def _empty(asin: str, error: str = None) -> dict:
    return {
        "asin": asin, "error": error,
        "current": {}, "stats": {}, "averages": {},
        "price_history": [], "rank_history": [], "offers": []
    }
