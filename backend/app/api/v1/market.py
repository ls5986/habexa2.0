"""
Market Intelligence API endpoints for SmartScout-style analysis.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.services.keepa_client import keepa_client

router = APIRouter(prefix="/market-intelligence", tags=["market"])


@router.get("/{asin}")
async def get_market_intelligence(asin: str, current_user = Depends(get_current_user)):
    """Get market intelligence for an ASIN."""
    
    # Get Keepa data
    keepa_data = await keepa_client.get_product(asin, domain=1, days=90)
    
    if not keepa_data:
        return {"asin": asin, "error": "No data available"}
    
    # Calculate insights
    sales_rank = keepa_data.get("sales_rank")
    drops_30 = keepa_data.get("drops_30", 0)
    drops_90 = keepa_data.get("drops_90", 0)
    
    # Estimate monthly sales
    est_monthly_sales = int(drops_30 * 1.5) if drops_30 else None
    
    # Sales trend
    sales_trend = "stable"
    if drops_30 and drops_90:
        avg_monthly = drops_90 / 3
        if drops_30 > avg_monthly * 1.2:
            sales_trend = "increasing"
        elif drops_30 < avg_monthly * 0.8:
            sales_trend = "decreasing"
    
    return {
        "asin": asin,
        "sales_rank": sales_rank,
        "est_monthly_sales": est_monthly_sales,
        "sales_trend": sales_trend,
        "drops_30": drops_30,
        "drops_90": drops_90,
        "review_count": keepa_data.get("review_count"),
        "rating": keepa_data.get("rating"),
        "brand": keepa_data.get("brand"),
        "category": keepa_data.get("category"),
    }

