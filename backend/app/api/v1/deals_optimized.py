"""
OPTIMIZED DEALS API - Production-grade performance
Uses single JOIN queries, database functions, and materialized views
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.asin_analyzer import ASINAnalyzer
from app.services.redis_client import cached, cache_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeBatchRequest(BaseModel):
    deal_ids: Optional[List[str]] = None
    analyze_all_pending: bool = True


# =====================================================
# STATIC ROUTES FIRST
# =====================================================

@router.get("/stats")
@cached(ttl=30, key_prefix="deals:stats")  # Cache for 30 seconds
async def get_deal_stats(current_user=Depends(get_current_user)):
    """Get deal statistics - OPTIMIZED using database function."""
    user_id = str(current_user.id)
    
    try:
        # Use optimized database function (FAST - single query)
        result = supabase.rpc(
            "get_deal_stats_optimized",
            {"p_user_id": user_id}
        ).execute()
        
        if result.data and len(result.data) > 0:
            stats = result.data[0]
            return {
                "total": stats.get("total", 0),
                "pending": stats.get("pending", 0),
                "analyzed": stats.get("analyzed", 0),
                "profitable": stats.get("profitable", 0),
            }
        
        # Fallback to materialized view if function doesn't exist
        try:
            mv_result = supabase.table("mv_deal_stats")\
                .select("*")\
                .eq("user_id", user_id)\
                .limit(1)\
                .execute()
            
            if mv_result.data:
                stats = mv_result.data[0]
                return {
                    "total": stats.get("total_deals", 0),
                    "pending": stats.get("pending_deals", 0),
                    "analyzed": stats.get("analyzed_deals", 0),
                    "profitable": stats.get("profitable_deals", 0),
                }
        except:
            pass
        
        # Final fallback: simple query
        return {"total": 0, "pending": 0, "analyzed": 0, "profitable": 0}
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total": 0, "pending": 0, "analyzed": 0, "profitable": 0}


@router.get("")
@cached(ttl=10, key_prefix="deals:list")  # Cache for 10 seconds
async def get_deals(
    status: Optional[str] = Query(None),
    min_roi: Optional[float] = Query(None),
    is_profitable: Optional[bool] = Query(None),
    channel_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user=Depends(get_current_user)
):
    """Get all deals - OPTIMIZED with single JOIN query."""
    user_id = str(current_user.id)
    
    try:
        # Try using optimized database function first
        try:
            result = supabase.rpc(
                "get_deals_optimized",
                {
                    "p_user_id": user_id,
                    "p_status": status,
                    "p_min_roi": min_roi,
                    "p_is_profitable": is_profitable,
                    "p_limit": limit,
                    "p_offset": offset
                }
            ).execute()
            
            if result.data:
                deals = []
                for row in result.data:
                    deal = {
                        "id": row.get("deal_id"),
                        "asin": row.get("asin"),
                        "buy_cost": row.get("buy_cost"),
                        "status": row.get("status"),
                        "extracted_at": row.get("extracted_at"),
                        "analysis": {
                            "id": row.get("analysis_id"),
                            "product_title": row.get("product_title"),
                            "sell_price": row.get("sell_price"),
                            "profit": row.get("profit"),
                            "roi": row.get("roi"),
                            "margin": row.get("margin"),
                            "image_url": row.get("image_url"),
                            "gating_status": row.get("gating_status"),
                        } if row.get("analysis_id") else None,
                        "channel": {
                            "channel_name": row.get("channel_name"),
                            "channel_id": row.get("channel_id"),
                        } if row.get("channel_name") else None,
                    }
                    deals.append(deal)
                
                return {
                    "deals": deals,
                    "total": len(deals),
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            logger.debug(f"RPC function not available, using direct query: {e}")
        
        # Fallback: Single query with JOIN (still fast with indexes)
        query = supabase.table("telegram_deals")\
            .select("""
                id,
                asin,
                buy_cost,
                status,
                extracted_at,
                analysis_id,
                product_title,
                channel_id,
                analyses!telegram_deals_analysis_id_fkey (
                    id, product_title, sell_price, profit, roi, margin,
                    image_url, gating_status, sales_rank, review_count, rating,
                    analysis_data
                ),
                telegram_channels!telegram_deals_channel_id_fkey (
                    channel_name, channel_id
                )
            """)\
            .eq("user_id", user_id)
        
        # Apply filters
        if status:
            if status.lower() == "pending":
                # Include NULL status
                query = query.or_("status.is.null,status.eq.pending")
            else:
                query = query.eq("status", status)
        
        if channel_id:
            query = query.eq("channel_id", channel_id)
        
        if search:
            query = query.ilike("asin", f"%{search}%")
        
        # Order and paginate
        query = query.order("extracted_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        deals = result.data or []
        
        # Flatten nested data
        for deal in deals:
            # Rename nested objects
            if "analyses" in deal:
                analysis = deal.pop("analyses")
                if analysis and len(analysis) > 0:
                    analysis = analysis[0]
                    # Extract from analysis_data JSONB if exists
                    if analysis.get("analysis_data"):
                        analysis_data = analysis.get("analysis_data", {})
                        if isinstance(analysis_data, dict):
                            analysis = {**analysis, **analysis_data}
                    deal["analysis"] = analysis
                else:
                    deal["analysis"] = None
            else:
                deal["analysis"] = None
            
            if "telegram_channels" in deal:
                channel = deal.pop("telegram_channels")
                if channel and len(channel) > 0:
                    deal["channel"] = channel[0]
                else:
                    deal["channel"] = None
            else:
                deal["channel"] = None
        
        # Post-filter for ROI
        if min_roi is not None or is_profitable:
            target_roi = min_roi if min_roi is not None else 30
            deals = [
                d for d in deals 
                if d.get("analysis") and (d["analysis"].get("roi") or 0) >= target_roi
            ]
        
        return {
            "deals": deals,
            "total": len(deals),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Get deals error: {e}")
        import traceback
        traceback.print_exc()
        return {"deals": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/{deal_id}")
async def get_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Get single deal - OPTIMIZED with single query."""
    user_id = str(current_user.id)
    
    try:
        # Try using optimized function
        try:
            result = supabase.rpc(
                "get_deal_full",
                {
                    "p_user_id": user_id,
                    "p_deal_id": deal_id
                }
            ).execute()
            
            if result.data and len(result.data) > 0:
                row = result.data[0]
                deal = row.get("deal_data", {})
                deal["analysis"] = row.get("analysis_data")
                deal["channel"] = row.get("channel_data")
                return deal
        except Exception as e:
            logger.debug(f"RPC function not available: {e}")
        
        # Fallback: Single query with JOIN
        result = supabase.table("telegram_deals")\
            .select("""
                *,
                analyses!telegram_deals_analysis_id_fkey (*),
                telegram_channels!telegram_deals_channel_id_fkey (channel_name, channel_username)
            """)\
            .eq("id", deal_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not result.data:
            raise HTTPException(404, "Deal not found")
        
        deal = result.data[0]
        
        # Flatten nested data
        if "analyses" in deal:
            analysis = deal.pop("analyses")
            if analysis and len(analysis) > 0:
                analysis = analysis[0]
                # Extract from analysis_data JSONB
                if analysis.get("analysis_data"):
                    analysis_data = analysis.get("analysis_data", {})
                    if isinstance(analysis_data, dict):
                        analysis = {**analysis, **analysis_data}
                deal["analysis"] = analysis
            else:
                deal["analysis"] = None
        else:
            deal["analysis"] = None
        
        if "telegram_channels" in deal:
            channel = deal.pop("telegram_channels")
            if channel and len(channel) > 0:
                deal["channel"] = channel[0]
            else:
                deal["channel"] = None
        else:
            deal["channel"] = None
        
        # If no analysis linked, try to find by ASIN
        if not deal["analysis"]:
            analysis_result = supabase.table("analyses")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("asin", deal["asin"])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if analysis_result.data:
                analysis = analysis_result.data[0]
                if analysis.get("analysis_data"):
                    analysis_data = analysis.get("analysis_data", {})
                    if isinstance(analysis_data, dict):
                        analysis = {**analysis, **analysis_data}
                deal["analysis"] = analysis
        
        return deal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get deal error: {e}")
        raise HTTPException(500, str(e))


@router.post("/analyze-batch")
async def analyze_batch(
    request: AnalyzeBatchRequest = AnalyzeBatchRequest(),
    current_user=Depends(get_current_user)
):
    """Analyze multiple deals at once."""
    user_id = str(current_user.id)
    
    deal_ids = request.deal_ids
    
    if not deal_ids and request.analyze_all_pending:
        result = supabase.table("telegram_deals")\
            .select("id")\
            .eq("user_id", user_id)\
            .or_("status.is.null,status.eq.pending")\
            .limit(20)\
            .execute()
        deal_ids = [d["id"] for d in (result.data or [])]
    
    if not deal_ids:
        return {"analyzed": 0, "errors": 0, "message": "No pending deals", "results": []}
    
    results = []
    for deal_id in deal_ids[:20]:
        try:
            deal_result = supabase.table("telegram_deals")\
                .select("asin, buy_cost, channel_id")\
                .eq("id", deal_id)\
                .eq("user_id", user_id)\
                .limit(1)\
                .execute()
            
            if not deal_result.data:
                results.append({"id": deal_id, "status": "error", "error": "Deal not found"})
                continue
            
            deal = deal_result.data[0]
            
            # Get supplier_id from channel
            supplier_id = None
            if deal.get("channel_id"):
                channel_result = supabase.table("telegram_channels")\
                    .select("supplier_id")\
                    .eq("id", deal["channel_id"])\
                    .limit(1)\
                    .execute()
                if channel_result.data and channel_result.data[0].get("supplier_id"):
                    supplier_id = channel_result.data[0]["supplier_id"]
            
            # Run analysis
            analyzer = ASINAnalyzer(user_id)
            analysis = await analyzer.analyze(
                asin=deal["asin"],
                buy_cost=float(deal.get("buy_cost") or 0),
                moq=deal.get("moq", 1),
                supplier_id=supplier_id,
                message_id=deal.get("message_id")
            )
            
            # Link analysis to deal
            if analysis and analysis.get("id"):
                supabase.table("telegram_deals").update({
                    "status": "analyzed",
                    "analysis_id": analysis["id"],
                    "analyzed_at": datetime.utcnow().isoformat()
                }).eq("id", deal_id).execute()
                
                # Invalidate cache
                if cache_service:
                    cache_service.delete_pattern(f"deals:*")
            
            results.append({"id": deal_id, "status": "success"})
            
        except Exception as e:
            logger.error(f"Batch analysis error for {deal_id}: {e}")
            results.append({"id": deal_id, "status": "error", "error": str(e)})
    
    return {
        "analyzed": len([r for r in results if r["status"] == "success"]),
        "errors": len([r for r in results if r["status"] == "error"]),
        "results": results
    }


@router.post("/{deal_id}/analyze")
async def analyze_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Analyze a single deal."""
    user_id = str(current_user.id)
    
    try:
        deal_result = supabase.table("telegram_deals")\
            .select("asin, buy_cost, channel_id")\
            .eq("id", deal_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not deal_result.data:
            raise HTTPException(404, "Deal not found")
        
        deal = deal_result.data[0]
        
        supabase.table("telegram_deals").update({
            "status": "analyzing"
        }).eq("id", deal_id).execute()
        
        # Get supplier_id from channel
        supplier_id = None
        if deal.get("channel_id"):
            channel_result = supabase.table("telegram_channels")\
                .select("supplier_id")\
                .eq("id", deal["channel_id"])\
                .limit(1)\
                .execute()
            if channel_result.data and channel_result.data[0].get("supplier_id"):
                supplier_id = channel_result.data[0]["supplier_id"]
        
        # Run analysis
        analyzer = ASINAnalyzer(user_id)
        analysis = await analyzer.analyze(
            asin=deal["asin"],
            buy_cost=float(deal.get("buy_cost") or 0),
            moq=deal.get("moq", 1),
            supplier_id=supplier_id,
            message_id=None
        )
        
        # Link analysis to deal
        update_data = {
            "status": "analyzed",
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        if analysis and analysis.get("id"):
            update_data["analysis_id"] = analysis["id"]
        
        supabase.table("telegram_deals").update(update_data).eq("id", deal_id).execute()
        
        # Invalidate cache
        if cache_service:
            cache_service.delete_pattern(f"deals:*")
        
        return {"success": True, "analysis": analysis}
        
    except HTTPException:
        raise
    except Exception as e:
        supabase.table("telegram_deals").update({
            "status": "error"
        }).eq("id", deal_id).execute()
        
        logger.error(f"Analysis error for {deal_id}: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")

