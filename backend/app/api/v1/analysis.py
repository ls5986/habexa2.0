"""
Analysis API - Now uses Celery for all analysis tasks.
Single analysis is queued to Celery and returns job_id for polling.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.stripe_service import StripeService
from app.services.feature_gate import feature_gate, require_feature, require_limit
from app.tasks.analysis import analyze_single_product, batch_analyze_products
import uuid
import logging

logger = logging.getLogger(__name__)

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
    """
    Analyze a single ASIN - queues to Celery and returns job_id.
    Frontend should poll /jobs/{job_id} for results.
    """
    user_id = str(current_user.id)
    
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
        logger.warning(f"Feature gate check failed: {e}, allowing analysis")
    
    # Get or create product
    asin = request.asin.strip().upper()
    existing = supabase.table("products")\
        .select("id")\
        .eq("user_id", user_id)\
        .eq("asin", asin)\
        .limit(1)\
        .execute()
    
    if existing.data:
        product_id = existing.data[0]["id"]
    else:
        new_prod = supabase.table("products").insert({
            "user_id": user_id,
            "asin": asin,
            "status": "pending"
        }).execute()
        product_id = new_prod.data[0]["id"] if new_prod.data else None
    
    if not product_id:
        raise HTTPException(500, "Failed to create product")
    
    # Create job record
    job_id = str(uuid.uuid4())
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "single_analyze",
        "status": "pending",
        "total_items": 1,
        "metadata": {
            "asin": asin,
            "product_id": product_id,
            "buy_cost": request.buy_cost,
            "moq": request.moq,
            "supplier_id": request.supplier_id
        }
    }).execute()
    
    # Queue to Celery
    analyze_single_product.delay(job_id, user_id, product_id, asin)
    
    # Get usage info
    try:
        check = await feature_gate.check_limit(user_id, "analyses_per_month")
        usage = {
            "analyses_remaining": check.get("remaining", 999),
            "analyses_limit": check.get("limit", 999),
            "unlimited": check.get("unlimited", False)
        }
    except Exception as e:
        logger.warning(f"Usage tracking failed: {e}")
        usage = {
            "analyses_remaining": 999,
            "analyses_limit": 999,
            "unlimited": True
        }
    
    return {
        "job_id": job_id,
        "product_id": product_id,
        "asin": asin,
        "status": "queued",
        "message": "Analysis queued. Poll /jobs/{job_id} for results.",
        "usage": usage
    }


@router.post("/batch")
async def analyze_batch(
    request: BatchAnalysisRequest,
    current_user=Depends(require_feature("bulk_analyze"))
):
    """
    Analyze multiple ASINs - queues to Celery and returns job_id.
    Frontend should poll /jobs/{job_id} for results.
    """
    user_id = str(current_user.id)
    
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
    
    # Get or create products for each ASIN
    product_ids = []
    for item in request.items:
        asin = item.asin.strip().upper()
        existing = supabase.table("products")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("asin", asin)\
            .limit(1)\
            .execute()
        
        if existing.data:
            product_id = existing.data[0]["id"]
        else:
            new_prod = supabase.table("products").insert({
                "user_id": user_id,
                "asin": asin,
                "status": "pending"
            }).execute()
            product_id = new_prod.data[0]["id"] if new_prod.data else None
        
        if product_id:
            product_ids.append(product_id)
    
    if not product_ids:
        raise HTTPException(400, "No valid products to analyze")
    
    # Create job record
    job_id = str(uuid.uuid4())
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "batch_analyze",
        "status": "pending",
        "total_items": len(product_ids),
        "metadata": {
            "item_count": item_count,
            "product_ids": product_ids
        }
    }).execute()
    
    # Queue to Celery
    batch_analyze_products.delay(job_id, user_id, product_ids)
    
    # Get updated usage
    final_check = await feature_gate.check_limit(current_user.id, "analyses_per_month")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "total": len(product_ids),
        "message": f"Queued {len(product_ids)} products for analysis. Poll /jobs/{job_id} for results.",
        "usage": {
            "analyses_remaining": final_check.get("remaining", 0),
            "analyses_limit": final_check.get("limit", 0),
            "unlimited": final_check.get("unlimited", False)
        }
    }


@router.get("/history")
async def get_history(current_user=Depends(get_current_user)):
    """Get analysis history."""
    result = supabase.table("analyses")\
        .select("*")\
        .eq("user_id", str(current_user.id))\
        .order("created_at", desc=True)\
        .limit(20)\
        .execute()
    
    return result.data or []
