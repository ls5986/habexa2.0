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
from app.services.upc_converter import upc_converter
from app.tasks.analysis import analyze_single_product, batch_analyze_products
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ASINInput(BaseModel):
    asin: Optional[str] = None  # ASIN if identifier_type is 'asin'
    upc: Optional[str] = None  # UPC if identifier_type is 'upc'
    identifier_type: str = "asin"  # 'asin' or 'upc'
    quantity: Optional[int] = 1  # Pack quantity for UPC products
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
    
    # Handle ASIN or UPC input
    identifier_type = request.identifier_type.lower()
    
    if identifier_type == "upc":
        # Convert UPC to ASIN
        if not request.upc:
            raise HTTPException(400, "UPC is required when identifier_type is 'upc'")
        
        upc_clean = upc_converter.normalize_upc(request.upc)
        if not upc_clean:
            raise HTTPException(400, "Invalid UPC format. Must be 12-14 digits.")
        
        logger.info(f"Converting UPC {upc_clean} to ASIN...")
        asin = await upc_converter.upc_to_asin(upc_clean)
        
        if not asin:
            raise HTTPException(404, f"Could not find ASIN for UPC {upc_clean}. Product may not be available on Amazon.")
        
        logger.info(f"✅ Converted UPC {upc_clean} to ASIN {asin}")
        
        # Store UPC and quantity for reference
        upc_value = upc_clean
        pack_quantity = request.quantity or 1
    else:
        # Use ASIN directly
        if not request.asin:
            raise HTTPException(400, "ASIN is required when identifier_type is 'asin'")
        
        asin = request.asin.strip().upper()
        upc_value = None
        pack_quantity = 1
    
    # Get or create product
    existing = supabase.table("products")\
        .select("id, upc")\
        .eq("user_id", user_id)\
        .eq("asin", asin)\
        .limit(1)\
        .execute()
    
    if existing.data:
        product_id = existing.data[0]["id"]
        # Update UPC if provided
        if upc_value and not existing.data[0].get("upc"):
            supabase.table("products")\
                .update({"upc": upc_value})\
                .eq("id", product_id)\
                .execute()
    else:
        new_prod = supabase.table("products").insert({
            "user_id": user_id,
            "asin": asin,
            "upc": upc_value,
            "status": "pending"
        }).execute()
        product_id = new_prod.data[0]["id"] if new_prod.data else None
    
    if not product_id:
        raise HTTPException(500, "Failed to create product")
    
    # Adjust buy_cost if UPC and pack quantity > 1
    adjusted_buy_cost = request.buy_cost
    if identifier_type == "upc" and pack_quantity > 1:
        # buy_cost is per pack, calculate per unit for analysis
        adjusted_buy_cost = request.buy_cost / pack_quantity
    
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
            "upc": upc_value,
            "identifier_type": identifier_type,
            "pack_quantity": pack_quantity,
            "product_id": product_id,
            "buy_cost": adjusted_buy_cost,
            "original_buy_cost": request.buy_cost,
            "moq": request.moq,
            "supplier_id": request.supplier_id
        }
    }).execute()
    
    # Queue to Celery (buy_cost is retrieved from job metadata in the task)
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


@router.get("/test-upc/{upc}")
async def test_upc_conversion(upc: str, current_user=Depends(get_current_user)):
    """
    Test UPC to ASIN conversion endpoint.
    Calls SP-API /catalog/2022-04-01/items with UPC identifier.
    """
    from app.services.upc_converter import upc_converter
    
    logger.info(f"🧪 Testing UPC conversion for: {upc}")
    
    # Normalize UPC
    upc_clean = upc_converter.normalize_upc(upc)
    if not upc_clean:
        raise HTTPException(400, f"Invalid UPC format: {upc}. Must be 12-14 digits.")
    
    try:
        # Test the conversion
        asin = await upc_converter.upc_to_asin(upc_clean)
        
        if asin:
            # Also get full catalog item details
            from app.services.sp_api_client import sp_api_client
            catalog_item = await sp_api_client.get_catalog_item(asin)
            
            return {
                "success": True,
                "upc": upc_clean,
                "asin": asin,
                "catalog_item": catalog_item,
                "message": f"✅ Successfully converted UPC {upc_clean} to ASIN {asin}"
            }
        else:
            return {
                "success": False,
                "upc": upc_clean,
                "asin": None,
                "message": f"❌ Could not find ASIN for UPC {upc_clean}. Product may not be available on Amazon."
            }
    except Exception as e:
        logger.error(f"Error testing UPC conversion: {e}", exc_info=True)
        raise HTTPException(500, f"Error converting UPC: {str(e)}")
