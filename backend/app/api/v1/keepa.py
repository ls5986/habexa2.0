"""Minimal Keepa router."""
from fastapi import APIRouter, Depends, Query
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
    request=None,
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    client = get_keepa_client()
    return await client.get_tokens_left()


@router.get("/product/{asin}")
async def get_product(
    asin: str,
    days: int = Query(default=90),
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    client = get_keepa_client()
    
    if not client.is_configured():
        return {"asin": asin, "error": "Not configured", "current": {}, "stats": {}}
    
    data = await client.get_product(asin, days)
    
    if not data:
        return {"asin": asin, "error": "No data", "current": {}, "stats": {}}
    
    return data


@router.get("/history/{asin}")
async def get_history(
    asin: str,
    days: int = 90,
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    client = get_keepa_client()
    data = await client.get_product(asin, days) if client.is_configured() else None
    return {
        "asin": asin,
        "price_history": (data or {}).get("price_history", []),
        "rank_history": (data or {}).get("rank_history", []),
    }


@router.get("/sales-estimate/{asin}")
async def get_sales_estimate(
    asin: str,
    current_user=Depends(get_current_user_optional if settings.TEST_MODE else get_current_user)
):
    client = get_keepa_client()
    data = await client.get_product(asin, 30) if client.is_configured() else None
    
    rank = (data or {}).get("current", {}).get("sales_rank")
    est = None
    if rank and rank > 0:
        if rank < 1000: est = 1000
        elif rank < 10000: est = 300
        elif rank < 50000: est = 100
        else: est = 30
    
    return {"asin": asin, "estimated_sales": est, "rank": rank}


@router.get("/debug/{asin}")
async def debug_keepa(asin: str):
    client = get_keepa_client()
    if not client.is_configured():
        return {"error": "Not configured"}
    
    try:
        params = {"key": client.api_key, "domain": 1, "asin": asin, "stats": 30}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get("https://api.keepa.com/product", params=params)
            d = r.json()
        
        prods = d.get("products", [])
        if not prods:
            return {"products": 0, "tokens": d.get("tokensLeft")}
        
        p = prods[0]
        stats = p.get("stats") or {}
        return {
            "tokens": d.get("tokensLeft"),
            "title": p.get("title"),
            "brand": p.get("brand"),
            "current": (stats.get("current") or [])[:10],
            "drops30": stats.get("salesRankDrops30"),
            "fba": stats.get("offerCountFBA"),
        }
    except Exception as e:
        return {"error": str(e)}
