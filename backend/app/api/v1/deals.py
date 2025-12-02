from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.asin_analyzer import ASINAnalyzer
from app.tasks.analysis import analyze_single_product, batch_analyze_products
import uuid
from app.services.redis_client import cache_service, get_redis_client
import logging
import sys
import json

# Configure logging to stdout with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeBatchRequest(BaseModel):
    deal_ids: Optional[List[str]] = None
    analyze_all_pending: bool = True


# =====================================================
# STATIC ROUTES FIRST - These must come before /{deal_id}
# =====================================================

@router.get("/stats")
async def get_deal_stats(current_user=Depends(get_current_user)):
    """Get deal statistics - OPTIMIZED single query."""
    import time
    start_time = time.time()
    user_id = str(current_user.id)
    
    try:
        # SINGLE QUERY - get deals with analysis ROI in one go
        result = supabase.table("telegram_deals")\
            .select("status, analysis_id, analyses!telegram_deals_analysis_id_fkey(roi)")\
            .eq("user_id", user_id)\
            .execute()
        
        deals = result.data or []
        total = len(deals)
        
        # Count by status
        pending = 0
        analyzed = 0
        profitable = 0
        error_count = 0
        
        for deal in deals:
            deal_status = deal.get("status") or "pending"
            deal_status_lower = deal_status.lower() if deal_status else "pending"
            
            if deal_status_lower == "pending":
                pending += 1
            elif deal_status_lower == "error":
                error_count += 1
            elif deal_status_lower == "analyzed":
                analyzed += 1
                # Check ROI from joined analysis
                analysis = deal.get("analyses")
                # Supabase returns analysis as dict or list depending on join
                if analysis:
                    if isinstance(analysis, list) and len(analysis) > 0:
                        roi = analysis[0].get("roi") or 0
                    elif isinstance(analysis, dict):
                        roi = analysis.get("roi") or 0
                    else:
                        roi = 0
                    if roi >= 30:
                        profitable += 1
        
        stats_time = time.time() - start_time
        logger.info(f"Stats query completed in {stats_time:.3f}s")
        
        result = {
            "total": total,
            "pending": pending,
            "analyzed": analyzed,
            "profitable": profitable,
            "error": error_count
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        import traceback
        traceback.print_exc()
        return {"total": 0, "pending": 0, "analyzed": 0, "profitable": 0, "error": 0}


@router.get("")
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
    """Get all deals - OPTIMIZED with caching and batch queries."""
    import time
    start_time = time.time()
    user_id = str(current_user.id)
    
    print(f"\n{'='*80}")
    print(f"🚀 [DEALS] STARTING GET /deals at {time.strftime('%H:%M:%S')}")
    print(f"   User: {user_id}")
    print(f"   Filters: status={status}, min_roi={min_roi}, is_profitable={is_profitable}, channel_id={channel_id}, search={search}")
    print(f"   Pagination: limit={limit}, offset={offset}")
    print(f"{'='*80}\n")
    
    # Generate cache key
    cache_key_start = time.time()
    cache_key = f"deals:{user_id}:{status}:{min_roi}:{is_profitable}:{channel_id}:{search}:{limit}:{offset}"
    cache_key_time = time.time() - cache_key_start
    print(f"⏱️  [TIMING] Cache key generation: {cache_key_time*1000:.2f}ms")
    
    # Try cache first
    cache_check_start = time.time()
    redis_client = get_redis_client()
    if redis_client:
        try:
            cached_result = cache_service.get(cache_key)
            cache_check_time = time.time() - cache_check_start
            if cached_result:
                total_time = time.time() - start_time
                print(f"✅ [DEALS] CACHE HIT - returning cached data (cache check: {cache_check_time*1000:.2f}ms, total: {total_time*1000:.2f}ms)")
                logger.info(f"Cache HIT for {cache_key}")
                return cached_result
            print(f"❌ [DEALS] CACHE MISS (cache check: {cache_check_time*1000:.2f}ms) - querying database")
        except Exception as e:
            cache_check_time = time.time() - cache_check_start
            print(f"⚠️  [DEALS] Cache check failed after {cache_check_time*1000:.2f}ms: {e}")
            logger.warning(f"Cache check failed: {e}")
    else:
        cache_check_time = time.time() - cache_check_start
        print(f"⚠️  [DEALS] Redis not available (check took {cache_check_time*1000:.2f}ms)")
    
    logger.info(f"GET /deals - user_id={user_id}, limit={limit}, offset={offset}")
    
    try:
        # ULTRA-SIMPLIFIED: Get deals first, then fetch analysis separately if needed
        query_start = time.time()
        logger.info(f"Starting query for user {user_id}, limit={limit}")
        
        # Step 1: Get deals only (no joins)
        query = supabase.table("telegram_deals")\
            .select("id, asin, buy_cost, status, extracted_at, analysis_id, product_title, channel_id")\
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
        
        # Order and paginate (ONLY ONCE - no duplicate order!)
        query = query.order("extracted_at", desc=True)
        query = query.limit(limit)
        if offset > 0:
            query = query.range(offset, offset + limit - 1)
        
        query_build_time = time.time() - query_start
        print(f"⏱️  [TIMING] Query build: {query_build_time*1000:.2f}ms")
        logger.info(f"Query built in {query_build_time:.3f}s")
        
        execute_start = time.time()
        print(f"🔍 [DEALS] Executing Supabase query... (started at {time.strftime('%H:%M:%S.%f')[:-3]})")
        logger.info(f"🔍 [DEALS] About to execute query")
        try:
            result = query.execute()
            execute_time = time.time() - execute_start
            rows_returned = len(result.data or [])
            print(f"✅ [DEALS] Query executed in {execute_time*1000:.2f}ms ({execute_time:.3f}s), returned {rows_returned} rows")
            logger.info(f"✅ Query executed in {execute_time:.3f}s, returned {rows_returned} rows")
            
            if execute_time > 1:
                print(f"⚠️  [DEALS] ⚠️  WARNING: Query took {execute_time:.3f}s ({execute_time*1000:.2f}ms) - this is SLOW!")
                logger.warning(f"Slow query detected: {execute_time:.3f}s")
            if execute_time > 5:
                print(f"🚨 [DEALS] 🚨 CRITICAL: Query took {execute_time:.3f}s - THIS IS VERY SLOW!")
        except Exception as e:
            execute_time = time.time() - execute_start
            print(f"❌ [DEALS] Query FAILED after {execute_time*1000:.2f}ms ({execute_time:.3f}s): {e}")
            logger.error(f"❌ Query FAILED after {execute_time:.3f}s: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        deals = result.data or []
        
        # Step 2: Fetch analysis data separately (only for deals that have analysis_id)
        analysis_start = time.time()
        analysis_ids = [d.get("analysis_id") for d in deals if d.get("analysis_id")]
        analyses_map = {}
        analysis_time = 0
        
        if analysis_ids:
            print(f"🔍 [DEALS] Fetching {len(analysis_ids)} analyses... (started at {time.strftime('%H:%M:%S.%f')[:-3]})")
            try:
                analysis_result = supabase.table("analyses")\
                    .select("id, product_title, image_url, sell_price, profit, roi, margin, gating_status")\
                    .in_("id", analysis_ids)\
                    .execute()
                
                for analysis in (analysis_result.data or []):
                    analyses_map[analysis["id"]] = analysis
                analysis_time = time.time() - analysis_start
                print(f"✅ [DEALS] Fetched {len(analyses_map)} analyses in {analysis_time*1000:.2f}ms ({analysis_time:.3f}s)")
                logger.info(f"✅ Fetched {len(analyses_map)} analyses in {analysis_time:.3f}s")
                if analysis_time > 1:
                    print(f"⚠️  [DEALS] Analysis fetch took {analysis_time:.3f}s - SLOW!")
            except Exception as e:
                analysis_time = time.time() - analysis_start
                print(f"❌ [DEALS] Failed to fetch analyses after {analysis_time*1000:.2f}ms ({analysis_time:.3f}s): {e}")
                logger.warning(f"Failed to fetch analyses: {e}")
        else:
            analysis_time = time.time() - analysis_start
            print(f"⏱️  [TIMING] No analyses to fetch: {analysis_time*1000:.2f}ms")
        
        # Step 3: Fetch channel names separately
        channel_start = time.time()
        # DEDUPLICATE channel_ids - all deals might have the same channel!
        channel_ids = list(set([d.get("channel_id") for d in deals if d.get("channel_id")]))
        channels_map = {}
        channel_time = 0
        
        if channel_ids:
            print(f"🔍 [DEALS] Fetching {len(channel_ids)} unique channels (from {len(deals)} deals)... (started at {time.strftime('%H:%M:%S.%f')[:-3]})")
            print(f"🔍 [DEALS] Fetching {len(channel_ids)} channels... (started at {time.strftime('%H:%M:%S.%f')[:-3]})")
            try:
                channel_result = supabase.table("telegram_channels")\
                    .select("id, channel_name")\
                    .in_("id", channel_ids)\
                    .execute()
                
                for channel in (channel_result.data or []):
                    channels_map[channel["id"]] = channel
                channel_time = time.time() - channel_start
                print(f"✅ [DEALS] Fetched {len(channels_map)} channels in {channel_time*1000:.2f}ms ({channel_time:.3f}s)")
                logger.info(f"✅ Fetched {len(channels_map)} channels in {channel_time:.3f}s")
                if channel_time > 1:
                    print(f"⚠️  [DEALS] Channel fetch took {channel_time:.3f}s - SLOW!")
            except Exception as e:
                channel_time = time.time() - channel_start
                print(f"❌ [DEALS] Failed to fetch channels after {channel_time*1000:.2f}ms ({channel_time:.3f}s): {e}")
                logger.warning(f"Failed to fetch channels: {e}")
        else:
            channel_time = time.time() - channel_start
            print(f"⏱️  [TIMING] No channels to fetch: {channel_time*1000:.2f}ms")
        
        # Step 4: Combine data
        combine_start = time.time()
        for deal in deals:
            deal["analysis"] = analyses_map.get(deal.get("analysis_id")) if deal.get("analysis_id") else None
            deal["channel"] = channels_map.get(deal.get("channel_id")) if deal.get("channel_id") else None
        combine_time = time.time() - combine_start
        print(f"⏱️  [TIMING] Data combination: {combine_time*1000:.2f}ms")
        
        # Post-filter for ROI
        filter_start = time.time()
        if min_roi is not None or is_profitable:
            target_roi = min_roi if min_roi is not None else 30
            deals = [
                d for d in deals 
                if d.get("analysis") and (d["analysis"].get("roi") or 0) >= target_roi
            ]
        filter_time = time.time() - filter_start
        print(f"⏱️  [TIMING] ROI filtering: {filter_time*1000:.2f}ms")
        
        total_time = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"🎯 [DEALS] TOTAL REQUEST TIME: {total_time*1000:.2f}ms ({total_time:.3f}s)")
        print(f"   Breakdown:")
        print(f"   - Cache check: {cache_check_time*1000:.2f}ms")
        print(f"   - Query build: {query_build_time*1000:.2f}ms")
        print(f"   - Query execute: {execute_time*1000:.2f}ms")
        print(f"   - Analysis fetch: {analysis_time*1000:.2f}ms")
        print(f"   - Channel fetch: {channel_time*1000:.2f}ms")
        print(f"   - Data combine: {combine_time*1000:.2f}ms")
        print(f"   - ROI filter: {filter_time*1000:.2f}ms")
        print(f"   Returning {len(deals)} deals")
        print(f"{'='*80}\n")
        logger.info(f"GET /deals completed in {total_time:.3f}s - returning {len(deals)} deals")
        
        result = {
            "deals": deals,
            "total": len(deals),
            "limit": limit,
            "offset": offset
        }
        
        # Cache the result for 60 seconds
        if redis_client:
            try:
                cache_service.set(cache_key, result, ttl=60)
                print(f"💾 [DEALS] Cached result for 60 seconds")
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Get deals error: {e}")
        import traceback
        traceback.print_exc()
        return {"deals": [], "total": 0, "limit": limit, "offset": offset}


@router.post("/analyze-batch")
async def analyze_batch(
    request: AnalyzeBatchRequest = AnalyzeBatchRequest(),
    current_user=Depends(get_current_user)
):
    """Analyze multiple deals at once."""
    user_id = str(current_user.id)
    
    deal_ids = request.deal_ids
    
    # If no specific IDs, get all pending
    if not deal_ids and request.analyze_all_pending:
        result = supabase.table("telegram_deals")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("status", "pending")\
            .limit(20)\
            .execute()
        deal_ids = [d["id"] for d in (result.data or [])]
    
    if not deal_ids:
        return {"analyzed": 0, "errors": 0, "message": "No pending deals", "results": []}
    
    # Get all deals and create/get products
    product_ids = []
    deal_to_product = {}
    
    for deal_id in deal_ids[:100]:  # Limit to 100
        try:
            # Get deal
            deal_result = supabase.table("telegram_deals")\
                .select("asin, buy_cost, channel_id")\
                .eq("id", deal_id)\
                .eq("user_id", user_id)\
                .limit(1)\
                .execute()
            
            if not deal_result.data:
                continue
            
            deal = deal_result.data[0]
            asin = deal["asin"]
            
            # Get or create product
            existing_product = supabase.table("products")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("asin", asin)\
                .limit(1)\
                .execute()
            
            if existing_product.data:
                product_id = existing_product.data[0]["id"]
            else:
                new_product = supabase.table("products").insert({
                    "user_id": user_id,
                    "asin": asin,
                    "status": "pending"
                }).execute()
                product_id = new_product.data[0]["id"] if new_product.data else None
            
            if product_id:
                product_ids.append(product_id)
                deal_to_product[deal_id] = product_id
                
                # Update deal to link to product
                supabase.table("telegram_deals").update({
                    "status": "analyzing",
                    "product_id": product_id
                }).eq("id", deal_id).execute()
        except Exception as e:
            logger.error(f"Error processing deal {deal_id}: {e}")
    
    if not product_ids:
        return {"analyzed": 0, "errors": 0, "message": "No valid products to analyze", "results": []}
    
    # Create job and queue batch analysis
    job_id = str(uuid.uuid4())
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "batch_analyze",
        "status": "pending",
        "total_items": len(product_ids),
        "metadata": {"deal_ids": deal_ids, "deal_to_product": deal_to_product}
    }).execute()
    
    # Queue to Celery
    batch_analyze_products.delay(job_id, user_id, product_ids)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "queued": len(product_ids),
        "message": f"Queued {len(product_ids)} products for analysis. Poll /jobs/{job_id} for results."
    }


# =====================================================
# DYNAMIC ROUTES LAST - These come after static routes
# =====================================================

@router.get("/{deal_id}")
async def get_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Get a single deal with full analysis data. Supports both telegram_deals and product_sources (new schema)."""
    user_id = str(current_user.id)
    
    try:
        # First try product_deals view (new schema)
        result = supabase.table("product_deals")\
            .select("*")\
            .eq("deal_id", deal_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            deal = result.data[0]
            
            # Get full analysis if analysis_id exists
            if deal.get("analysis_id"):
                analysis_result = supabase.table("analyses")\
                    .select("*")\
                    .eq("id", deal["analysis_id"])\
                    .eq("user_id", user_id)\
                    .limit(1)\
                    .execute()
                
                if analysis_result.data:
                    deal["analysis"] = analysis_result.data[0]
                else:
                    deal["analysis"] = None
            else:
                deal["analysis"] = None
            
            # Map product_deals fields to expected format
            return {
                "id": deal.get("deal_id"),
                "deal_id": deal.get("deal_id"),
                "product_id": deal.get("product_id"),
                "asin": deal.get("asin"),
                "title": deal.get("title"),
                "brand": deal.get("brand_name"),
                "image_url": deal.get("image_url"),
                "buy_cost": deal.get("buy_cost"),
                "moq": deal.get("moq"),
                "sell_price": deal.get("sell_price"),
                "fees_total": deal.get("fees_total"),
                "bsr": deal.get("bsr"),
                "seller_count": deal.get("seller_count"),
                "fba_seller_count": deal.get("fba_seller_count"),
                "amazon_sells": deal.get("amazon_sells"),
                "roi": deal.get("roi"),
                "profit": deal.get("profit"),
                "stage": deal.get("stage"),
                "status": deal.get("product_status"),
                "supplier_id": deal.get("supplier_id"),
                "supplier_name": deal.get("supplier_name"),
                "source": deal.get("source"),
                "source_detail": deal.get("source_detail"),
                "analysis": deal.get("analysis"),
                "analysis_id": deal.get("analysis_id"),
                "created_at": deal.get("deal_created_at"),
                "updated_at": deal.get("deal_updated_at")
            }
        
        # Fallback to telegram_deals (old schema)
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
                deal["analysis"] = analysis[0]
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
        
        # Fallback: find analysis by ASIN if not linked
        if not deal["analysis"]:
            analysis_result = supabase.table("analyses")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("asin", deal["asin"])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if analysis_result.data:
                deal["analysis"] = analysis_result.data[0]
        
        return deal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching deal {deal_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to fetch deal: {str(e)}")


@router.post("/{deal_id}/analyze")
async def analyze_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Analyze a single deal."""
    user_id = str(current_user.id)
    
    try:
        # Get deal - use limit(1) NOT single()
        deal_result = supabase.table("telegram_deals")\
            .select("asin, buy_cost, channel_id")\
            .eq("id", deal_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not deal_result.data:
            raise HTTPException(404, "Deal not found")
        
        deal = deal_result.data[0]
        
        # Update status to analyzing
        supabase.table("telegram_deals").update({
            "status": "analyzing"
        }).eq("id", deal_id).execute()
        
        # Get supplier_id from channel
        supplier_id = None
        if deal.get("channel_id"):
            try:
                channel_result = supabase.table("telegram_channels")\
                    .select("supplier_id")\
                    .eq("id", deal["channel_id"])\
                    .limit(1)\
                    .execute()
                if channel_result.data and channel_result.data[0].get("supplier_id"):
                    supplier_id = channel_result.data[0]["supplier_id"]
            except:
                pass
        
        # Get or create product for this deal
        asin = deal["asin"]
        existing_product = supabase.table("products")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("asin", asin)\
            .limit(1)\
            .execute()
        
        if existing_product.data:
            product_id = existing_product.data[0]["id"]
        else:
            new_product = supabase.table("products").insert({
                "user_id": user_id,
                "asin": asin,
                "status": "pending"
            }).execute()
            product_id = new_product.data[0]["id"] if new_product.data else None
        
        if not product_id:
            raise HTTPException(500, "Failed to create product")
        
        # Queue to Celery
        job_id = str(uuid.uuid4())
        supabase.table("jobs").insert({
            "id": job_id,
            "user_id": user_id,
            "type": "single_analyze",
            "status": "pending",
            "total_items": 1,
            "metadata": {"deal_id": deal_id, "product_id": product_id}
        }).execute()
        
        analyze_single_product.delay(job_id, user_id, product_id, asin)
        
        # Update deal to link to product
        supabase.table("telegram_deals").update({
            "status": "analyzing",
            "product_id": product_id
        }).eq("id", deal_id).execute()
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "queued",
            "message": "Analysis queued. Poll /jobs/{job_id} for results."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Mark as error
        supabase.table("telegram_deals").update({
            "status": "error"
        }).eq("id", deal_id).execute()
        
        logger.error(f"Analysis error for {deal_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/{deal_id}/save")
async def save_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Save deal to watchlist."""
    # This endpoint references old "deals" table - keeping for compatibility
    return {"success": True}


@router.post("/{deal_id}/dismiss")
async def dismiss_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Dismiss deal."""
    # This endpoint references old "deals" table - keeping for compatibility
    return {"success": True}


@router.post("/{deal_id}/order")
async def order_deal(deal_id: str, current_user=Depends(get_current_user)):
    """Mark deal as ordered."""
    # This endpoint references old "deals" table - keeping for compatibility
    return {"success": True}
