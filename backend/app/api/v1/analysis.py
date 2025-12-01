from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.api.deps import get_current_user
from app.services.asin_analyzer import ASINAnalyzer
from app.services.stripe_service import StripeService
from app.services.feature_gate import feature_gate, require_feature, require_limit

router = APIRouter()


class ASINInput(BaseModel):
    asin: str
    buy_cost: float
    moq: int = 1
    supplier_id: Optional[str] = None


class BatchAnalysisRequest(BaseModel):
    items: List[ASINInput]


@router.post("/single")
async def analyze_single(
    request: ASINInput,
    current_user=Depends(get_current_user)
):
    """Analyze a single ASIN."""
    
    # Check limit (but don't block if feature_gate fails)
    try:
        limit_check = await feature_gate.check_limit(current_user.id, "analyses_per_month")
        if not limit_check.get("allowed", True) and not limit_check.get("unlimited", False):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "limit_reached",
                    "message": f"You've reached your analysis limit ({limit_check.get('limit', 0)} per month)",
                    "remaining": limit_check.get("remaining", 0),
                    "upgrade_url": "/pricing"
                }
            )
    except Exception as e:
        # If feature gating fails, allow the analysis anyway (graceful degradation)
        import logging
        logging.getLogger(__name__).warning(f"Feature gate check failed: {e}, allowing analysis")
    
    analyzer = ASINAnalyzer(str(current_user.id))
    result = await analyzer.analyze(
        request.asin,
        request.buy_cost,
        request.moq,
        request.supplier_id
    )
    
    # Increment usage after successful analysis (non-blocking)
    try:
        await feature_gate.increment_usage(str(current_user.id), "analyses_per_month", 1)
        check = await feature_gate.check_limit(str(current_user.id), "analyses_per_month")
        result["usage"] = {
            "analyses_remaining": check.get("remaining", 999),
            "analyses_limit": check.get("limit", 999),
            "unlimited": check.get("unlimited", False)
        }
    except Exception as e:
        # If usage tracking fails, don't break the response
        import logging
        logging.getLogger(__name__).warning(f"Usage tracking failed: {e}")
        result["usage"] = {
            "analyses_remaining": 999,
            "analyses_limit": 999,
            "unlimited": True
        }
    
    return result


@router.post("/batch")
async def analyze_batch(
    request: BatchAnalysisRequest,
    current_user=Depends(require_feature("bulk_analyze"))
):
    """Analyze multiple ASINs at once. Requires Pro tier or higher."""
    
    # Check if user has enough analyses remaining
    check = await feature_gate.check_limit(current_user.id, "analyses_per_month")
    
    item_count = len(request.items)
    
    if not check.get("unlimited"):
        remaining = check.get("remaining", 0)
        
        if item_count > remaining:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_analyses",
                    "message": f"You have {remaining} analyses remaining but requested {item_count}.",
                    "remaining": remaining,
                    "requested": item_count,
                    "upgrade_url": "/pricing"
                }
            )
    
    analyzer = ASINAnalyzer(current_user.id)
    
    items = [
        {
            "asin": item.asin,
            "buy_cost": item.buy_cost,
            "moq": item.moq,
            "supplier_id": item.supplier_id
        }
        for item in request.items
    ]
    
    results = await analyzer.analyze_batch(items)
    
    # Increment usage for each successful analysis
    successful_count = len([r for r in results if not r.get("error")])
    await feature_gate.increment_usage(current_user.id, "analyses_per_month", successful_count)
    
    # Get updated usage
    final_check = await feature_gate.check_limit(current_user.id, "analyses_per_month")
    
    return {
        "results": results,
        "total": len(results),
        "successful": successful_count,
        "usage": {
            "analyses_remaining": final_check.get("remaining", 0),
            "analyses_limit": final_check.get("limit", 0),
            "unlimited": final_check.get("unlimited", False)
        }
    }
    """Analyze multiple ASINs."""
    
    analyzer = ASINAnalyzer(current_user.id)
    
    items = [
        {
            "asin": item.asin,
            "buy_cost": item.buy_cost,
            "moq": item.moq,
            "supplier_id": item.supplier_id
        }
        for item in request.items
    ]
    
    results = await analyzer.analyze_batch(items)
    
    return results


@router.get("/history")
async def get_history(current_user=Depends(get_current_user)):
    """Get analysis history."""
    
    from app.services.supabase_client import supabase
    
    result = supabase.table("deals").select("*").eq("user_id", current_user.id).order("analyzed_at", desc=True).limit(20).execute()
    
    return result.data

