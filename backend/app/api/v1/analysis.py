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
from app.services.product_data_service import product_data_service
from app.services.asin_ranking_service import asin_ranking_service
from app.services.asin_comparison_service import asin_comparison_service
from app.services.sp_api_client import sp_api_client
from app.tasks.analysis import analyze_single_product, batch_analyze_products, get_user_cost_settings
from app.tasks.base import run_async
from app.services.cost_calculator import (
    calculate_inbound_shipping,
    calculate_prep_cost,
    calculate_landed_cost,
    calculate_net_profit,
    calculate_roi
)
from datetime import datetime
import uuid
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)
SYNC_PROCESSING_THRESHOLD = settings.SYNC_PROCESSING_THRESHOLD

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


class SaveProductFromAnalysisRequest(BaseModel):
    asin: str
    buy_cost: float
    moq: int = 1
    supplier_id: Optional[str] = None
    notes: Optional[str] = None
    upc: Optional[str] = None
    pack_size: Optional[int] = None
    wholesale_cost: Optional[float] = None


@router.post("/single")
async def analyze_single(
    request: ASINInput,
    current_user=Depends(get_current_user)
):
    """
    Analyze a single ASIN - runs synchronously and returns results immediately.
    No job needed for single ASIN analysis (completes in ~5-10 seconds).
    """
    user_id = str(current_user.id)
    
    # Check limit (but don't block if feature_gate fails)
    try:
        limit_check = await feature_gate.check_limit(current_user, "analyses_per_month")
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
        # Convert UPC to ASIN(s) - handle multiple matches
        if not request.upc:
            raise HTTPException(400, "UPC is required when identifier_type is 'upc'")
        
        upc_clean = upc_converter.normalize_upc(request.upc)
        if not upc_clean:
            raise HTTPException(400, "Invalid UPC format. Must be 12-14 digits.")
        
        # IMPROVEMENT 1: Check for previous user selection
        previous_selection = supabase.table('upc_asin_selections') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('upc', upc_clean) \
            .execute()
        
        if previous_selection.data and len(previous_selection.data) > 0:
            # Use previously selected ASIN
            selected = previous_selection.data[0]
            request.asin = selected['asin']
            logger.info(f"✅ Using previously selected ASIN {request.asin} for UPC {upc_clean}")
        else:
            # New UPC, find all ASINs
            logger.info(f"Converting UPC {upc_clean} to ASIN(s)...")
            potential_asins, asin_status = await upc_converter.upc_to_asins(upc_clean)
            
            if asin_status == "not_found":
                raise HTTPException(404, f"Could not find ASIN for UPC {upc_clean}. Product may not be available on Amazon.")
            
            if asin_status == "error":
                raise HTTPException(500, f"Error converting UPC {upc_clean} to ASIN.")
            
            # Handle multiple ASINs - enhance with quality indicators and ranking
            if asin_status == "multiple" and len(potential_asins) > 1:
                logger.warning(f"⚠️ Multiple ASINs found for UPC {upc_clean}: {len(potential_asins)} matches")
                
                # IMPROVEMENT 3 & 5: Get parent ASIN info and quality indicators
                potential_asins_enhanced = []
                for asin_data in potential_asins:
                    asin = asin_data.get('asin')
                    
                    # Check for parent ASIN
                    parent_asin = await sp_api_client.get_parent_asin(asin)
                    is_parent = parent_asin is None or parent_asin == asin
                    
                    # Get quality indicators
                    quality = await sp_api_client.get_asin_quality_indicators(asin)
                    
                    # Get product data with fallback
                    product_data = await product_data_service.get_product_data(asin)
                    
                    enhanced_asin = {
                        **asin_data,
                        'is_parent': is_parent,
                        'parent_asin': parent_asin,
                        'quality_indicators': quality,
                        'title': product_data.get('title') or asin_data.get('title'),
                        'image': product_data.get('image') or asin_data.get('image'),
                        'brand': product_data.get('brand') or asin_data.get('brand'),
                        'category': product_data.get('category') or asin_data.get('category'),
                    }
                    
                    # Add warning if child variation
                    if parent_asin and parent_asin != asin:
                        enhanced_asin['warning'] = f"This is a variation. Parent ASIN: {parent_asin}"
                    
                    potential_asins_enhanced.append(enhanced_asin)
                
                # IMPROVEMENT 9: Find differences between ASINs
                asins_with_differences = asin_comparison_service.find_differences(potential_asins_enhanced)
                
                # IMPROVEMENT 8: Rank ASINs by quality
                ranked_asins = asin_ranking_service.rank_asins(asins_with_differences)
                
                # Create product with multiple_found status
                new_prod = supabase.table("products").insert({
                    "user_id": user_id,
                    "asin": None,  # No ASIN selected yet
                    "upc": upc_clean,
                    "status": "pending",
                    "asin_status": "multiple_found",
                    "potential_asins": [a.get("asin") for a in ranked_asins]  # Store ASIN list
                }).execute()
                
                product_id = new_prod.data[0]["id"] if new_prod.data else None
                
                if not product_id:
                    raise HTTPException(500, "Failed to create product")
                
                # Return response with enhanced ASIN data
                return {
                    "product_id": product_id,
                    "asin": None,
                    "status": "multiple_asins_found",
                    "asin_status": "multiple_found",
                    "potential_asins": ranked_asins,  # Ranked and enhanced ASIN info
                    "recommended_asin": ranked_asins[0]['asin'] if ranked_asins else None,
                    "upc": upc_clean,
                    "message": f"Found {len(ranked_asins)} products for this UPC. Please select which one to analyze."
                }
            
            # Single ASIN found - use it
            if not potential_asins or len(potential_asins) == 0:
                raise HTTPException(404, f"Could not find ASIN for UPC {upc_clean}.")
            
            asin = potential_asins[0].get("asin")
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
    
    # Calculate pack info if provided
    pack_size = getattr(request, 'pack_size', None) or (pack_quantity if identifier_type == "upc" and pack_quantity > 1 else 1)
    wholesale_cost = getattr(request, 'wholesale_cost', None)
    if wholesale_cost and pack_size > 1:
        adjusted_buy_cost = wholesale_cost / pack_size
    
    logger.info(f"🔍 Analyzing ASIN {asin} synchronously (no job needed)")
    import time
    total_start = time.time()
    
    try:
        # Run analysis synchronously - no job, no Celery, just do it
        from app.services.batch_analyzer import batch_analyzer
        from app.tasks.analysis import get_user_cost_settings
        
        # Build buy_costs, promo_costs, and source_data dicts
        buy_costs = {asin: adjusted_buy_cost}
        promo_costs = {}
        source_data = {
            asin: {
                "supplier_ships_direct": False,
            }
        }
        
        # Get user cost settings and run analysis in parallel
        analysis_start = time.time()
        user_settings_task = get_user_cost_settings(user_id)
        
        # Start analysis immediately (it will use default settings if user_settings not ready)
        # But we'll wait for user_settings before profit calculation
        results = await batch_analyzer.analyze_products(
            [asin],
            buy_costs=buy_costs,
            promo_costs=promo_costs,
            source_data=source_data,
            user_settings=await user_settings_task  # Wait for settings
        )
        
        analysis_time = time.time() - analysis_start
        logger.info(f"⚡ Analysis API calls completed in {analysis_time:.2f}s")
        
        result = results.get(asin, {})
        
        if not result:
            raise HTTPException(500, "Analysis returned no data")
        
        # OPTIMIZATION: Reduce database queries
        db_start = time.time()
        supplier_id = request.supplier_id
        
        # Get existing records (optimized - single query for product_source with supplier_id)
        # Always check for existing product_source (needed for Products page display)
        existing_source_result = None
        try:
            existing_source_result = supabase.table("product_sources")\
                .select("id, supplier_id")\
                .eq("product_id", product_id)\
                .eq("user_id", user_id)\
                .limit(1)\
                .execute()
            # Get supplier_id from source if not provided
            if not supplier_id and existing_source_result.data:
                supplier_id = existing_source_result.data[0].get("supplier_id")
        except Exception as e:
            logger.warning(f"Could not fetch product_source: {e}")
        
        # Check existing analysis
        existing_analysis_result = supabase.table("analyses")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("asin", asin)\
            .limit(1)\
            .execute()
        
        # Update/insert product_source - ALWAYS create/update after analysis
        # This ensures the product appears in the Products page (product_deals view requires product_source)
        try:
            source_update_data = {
                "moq": request.moq,
                "supplier_id": supplier_id,
                "stage": "reviewed",  # Analyzed products go to "reviewed" stage
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Only set buy_cost if provided (can be 0 or None)
            if adjusted_buy_cost is not None:
                source_update_data["buy_cost"] = adjusted_buy_cost
            
            if existing_source_result and existing_source_result.data:
                # Update existing product_source
                supabase.table("product_sources").update(source_update_data).eq("id", existing_source_result.data[0]["id"]).execute()
                logger.info(f"✅ Updated product_source for product {product_id}")
            else:
                # Create new product_source - required for product to appear in Products page
                source_insert_data = {
                    "user_id": user_id,
                    "product_id": product_id,
                    **source_update_data,
                    "source": "quick_analyze"
                }
                # Ensure buy_cost is set (default to 0 if not provided)
                if "buy_cost" not in source_insert_data:
                    source_insert_data["buy_cost"] = adjusted_buy_cost if adjusted_buy_cost is not None else 0.0
                
                supabase.table("product_sources").insert(source_insert_data).execute()
                logger.info(f"✅ Created product_source for product {product_id} (stage: reviewed)")
        except Exception as e:
            logger.error(f"❌ Failed to create/update product_source: {e}", exc_info=True)
            # Don't fail the entire analysis, but log the error
            # Product will still be created, just won't show in Products page
        
        # Prepare analysis data
        # Fix field name mapping: batch_analyzer returns fees_referral, but we need referral_fee
        referral_fee = result.get("referral_fee") or result.get("fees_referral")
        fba_fee = result.get("fba_fee") or result.get("fees_fba")
        fees_total = result.get("fees_total")
        
        # If we have fees_total but missing individual fees, calculate referral_fee from category
        if fees_total and not referral_fee and result.get("sell_price"):
            from app.services.profit_calculator import get_referral_rate
            category = result.get("category")
            referral_rate = get_referral_rate(category)
            referral_fee = result.get("sell_price") * referral_rate
            logger.info(f"📊 Calculated referral fee from category: ${referral_fee:.2f} ({referral_rate*100}%)")
        
        # Calculate referral_fee_percent if we have referral_fee and sell_price
        referral_fee_percent = None
        if referral_fee and result.get("sell_price"):
            referral_fee_percent = round((referral_fee / result.get("sell_price")) * 100, 2)
        
        analysis_data = {
            "user_id": user_id,
            "asin": asin,
            "supplier_id": supplier_id,
            "analysis_data": {},
            "pricing_status": result.get("pricing_status", "complete"),
            "pricing_status_reason": result.get("pricing_status_reason"),
            "needs_review": result.get("needs_review", False),
            "sell_price": result.get("sell_price"),
            "buy_cost": result.get("buy_cost") or adjusted_buy_cost,
            "referral_fee": referral_fee,
            "referral_fee_percent": referral_fee_percent or result.get("referral_fee_percent"),
            "fba_fee": fba_fee,
            "variable_closing_fee": result.get("variable_closing_fee"),
            "fees_total": fees_total,
            "inbound_shipping": result.get("inbound_shipping"),
            "prep_cost": result.get("prep_cost"),
            "total_landed_cost": result.get("total_landed_cost"),
            "net_profit": result.get("net_profit"),
            "roi": result.get("roi"),
            "profit_margin": result.get("profit_margin"),
            "analysis_stage": result.get("analysis_stage", "stage3"),
            "passed_stage2": result.get("passed_stage2", True),
            "stage2_roi": result.get("stage2_roi"),
        }
        
        # Update/insert analysis
        if existing_analysis_result.data:
            supabase.table("analyses").update(analysis_data).eq("id", existing_analysis_result.data[0]["id"]).execute()
        else:
            supabase.table("analyses").insert(analysis_data).execute()
        
        # Update product status
        supabase.table("products").update({
            "status": "analyzed",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", product_id).execute()
        
        db_time = time.time() - db_start
        logger.info(f"⚡ Database operations completed in {db_time:.2f}s")
        
        # Use cached usage from initial check (avoid redundant call)
        usage = {
            "analyses_remaining": limit_check.get("remaining", 999),
            "analyses_limit": limit_check.get("limit", 999),
            "unlimited": limit_check.get("unlimited", False)
        }
        
        total_time = time.time() - total_start
        logger.info(f"✅ Analysis complete for ASIN {asin} in {total_time:.2f}s (API: {analysis_time:.2f}s, DB: {db_time:.2f}s)")
        
        # Return results directly - no job needed!
        return {
            "product_id": product_id,
            "asin": asin,
            "status": "completed",
            "result": {
                "title": result.get("title"),
                "brand": result.get("brand"),
                "image_url": result.get("image_url"),
                "sell_price": result.get("sell_price"),
                "buy_cost": result.get("buy_cost") or adjusted_buy_cost,
                "net_profit": result.get("net_profit"),
                "roi": result.get("roi"),
                "profit_margin": result.get("profit_margin"),
                "deal_score": result.get("deal_score"),
                "gating_status": result.get("gating_status"),
                "meets_threshold": result.get("meets_threshold", False),
                "category": result.get("category"),
                "bsr": result.get("bsr"),
                "sales_estimate": result.get("sales_estimate"),
            },
            "usage": usage
        }
        
    except Exception as e:
        logger.error(f"❌ Analysis failed for ASIN {asin}: {e}", exc_info=True)
        # Update product status to error
        supabase.table("products").update({
            "status": "error",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", product_id).execute()
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/batch")
async def analyze_batch(
    request: BatchAnalysisRequest,
    current_user=Depends(require_feature("bulk_analyze"))
):
    """
    Analyze multiple ASINs - smart sync/async decision based on count.
    <= 10 products: Synchronous (instant results)
    > 10 products: Async with job (background + polling)
    """
    user_id = str(current_user.id)
    
    # Check if user has enough analyses remaining
    check = await feature_gate.check_limit(current_user, "analyses_per_month")
    
    item_count = len(request.items)
    logger.info(f"📦 Batch analysis request: {item_count} products (threshold: {SYNC_PROCESSING_THRESHOLD})")
    
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
    
    # DECISION: Sync or async?
    if item_count <= SYNC_PROCESSING_THRESHOLD:
        # SYNCHRONOUS - Process immediately
        logger.info(f"⚡ Processing {item_count} products synchronously (instant results)")
        
        from app.services.batch_analyzer import batch_analyzer
        
        # Get or create products and collect ASINs/buy_costs
        asins = []
        buy_costs = {}
        promo_costs = {}
        source_data = {}
        product_mapping = {}  # asin -> product_id
        item_metadata = {}  # asin -> {supplier_id, moq}
        
        for item in request.items:
            asin = item.asin.strip().upper()
            
            # Get or create product
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
                asins.append(asin)
                buy_costs[asin] = item.buy_cost
                product_mapping[asin] = product_id
                source_data[asin] = {"supplier_ships_direct": False}
                item_metadata[asin] = {
                    "supplier_id": item.supplier_id,
                    "moq": item.moq
                }
        
        if not asins:
            raise HTTPException(400, "No valid products to analyze")
        
        # Run batch analysis synchronously
        try:
            user_settings = await get_user_cost_settings(user_id)
            results = await batch_analyzer.analyze_products(
                asins,
                buy_costs=buy_costs,
                promo_costs=promo_costs,
                source_data=source_data,
                user_settings=user_settings
            )
            
            if not results:
                raise HTTPException(500, "Analysis returned no results")
        except Exception as e:
            logger.error(f"❌ Batch analysis failed: {e}", exc_info=True)
            # Return partial results if any products failed
            analysis_results = []
            for asin in asins:
                analysis_results.append({
                    "status": "failed",
                    "asin": asin,
                    "error": f"Analysis error: {str(e)}"
                })
            return {
                "mode": "sync",
                "total": item_count,
                "results": analysis_results,
                "message": f"Analysis failed: {str(e)}",
                "usage": {
                    "analyses_remaining": check.get("remaining", 0),
                    "analyses_limit": check.get("limit", 0),
                    "unlimited": check.get("unlimited", False)
                }
            }
        
        # Process results and save to database
        analysis_results = []
        for asin, result in results.items():
            product_id = product_mapping.get(asin)
            if not product_id:
                continue
            
            try:
                # Get item metadata (supplier_id, moq)
                metadata = item_metadata.get(asin, {})
                supplier_id = metadata.get("supplier_id")
                moq = metadata.get("moq", 1)
                buy_cost = buy_costs.get(asin)
                
                # Create/update product_source if buy_cost provided
                if buy_cost:
                    try:
                        existing_source = supabase.table("product_sources")\
                            .select("id")\
                            .eq("product_id", product_id)\
                            .eq("user_id", user_id)\
                            .limit(1)\
                            .execute()
                        
                        if existing_source.data:
                            supabase.table("product_sources").update({
                                "buy_cost": buy_cost,
                                "moq": moq,
                                "supplier_id": supplier_id,
                                "updated_at": datetime.utcnow().isoformat()
                            }).eq("id", existing_source.data[0]["id"]).execute()
                        else:
                            supabase.table("product_sources").insert({
                                "user_id": user_id,
                                "product_id": product_id,
                                "supplier_id": supplier_id,
                                "buy_cost": buy_cost,
                                "moq": moq,
                                "stage": "reviewed",
                                "source": "batch_analyze"
                            }).execute()
                    except Exception as e:
                        logger.warning(f"Could not create/update product_source for {asin}: {e}")
                
                # Get supplier_id from product_source if not set
                if not supplier_id:
                    try:
                        sources = supabase.table("product_sources")\
                            .select("supplier_id")\
                            .eq("product_id", product_id)\
                            .limit(1)\
                            .execute()
                        if sources.data and sources.data[0].get("supplier_id"):
                            supplier_id = sources.data[0]["supplier_id"]
                    except:
                        pass
                
                # Save analysis
                analysis_data = {
                    "user_id": user_id,
                    "asin": asin,
                    "supplier_id": supplier_id,
                    "analysis_data": {},
                    "pricing_status": result.get("pricing_status", "complete"),
                    "sell_price": result.get("sell_price"),
                    "buy_cost": result.get("buy_cost") or buy_cost,
                    "net_profit": result.get("net_profit"),
                    "roi": result.get("roi"),
                    "analysis_stage": result.get("analysis_stage", "stage3"),
                }
                
                # Upsert analysis
                existing_analysis = supabase.table("analyses")\
                    .select("id")\
                    .eq("user_id", user_id)\
                    .eq("asin", asin)\
                    .limit(1)\
                    .execute()
                
                if existing_analysis.data:
                    supabase.table("analyses").update(analysis_data).eq("id", existing_analysis.data[0]["id"]).execute()
                else:
                    supabase.table("analyses").insert(analysis_data).execute()
                
                # Update product status
                supabase.table("products").update({
                    "status": "analyzed",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", product_id).execute()
                
                analysis_results.append({
                    "status": "success",
                    "asin": asin,
                    "product_id": product_id,
                    "result": {
                        "title": result.get("title"),
                        "net_profit": result.get("net_profit"),
                        "roi": result.get("roi"),
                    }
                })
            except Exception as e:
                logger.error(f"Failed to save analysis for {asin}: {e}", exc_info=True)
                analysis_results.append({
                    "status": "failed",
                    "asin": asin,
                    "error": str(e)
                })
        
        # Get updated usage
        final_check = await feature_gate.check_limit(current_user, "analyses_per_month")
        
        logger.info(f"✅ Synchronous batch analysis complete: {len([r for r in analysis_results if r['status'] == 'success'])}/{item_count} succeeded")
        
        return {
            "mode": "sync",
            "total": item_count,
            "results": analysis_results,
            "message": f"Analyzed {item_count} products instantly",
            "usage": {
                "analyses_remaining": final_check.get("remaining", 0),
                "analyses_limit": final_check.get("limit", 0),
                "unlimited": final_check.get("unlimited", False)
            }
        }
    
    else:
        # ASYNC - Create job and queue to Celery
        logger.info(f"🚀 Queueing {item_count} products for background processing")
        
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
        try:
            batch_analyze_products.delay(job_id, user_id, product_ids)
            logger.info(f"✅ Task queued: job {job_id}")
        except Exception as e:
            logger.error(f"❌ Failed to queue task: {e}", exc_info=True)
            supabase.table("jobs").update({
                "status": "failed",
                "error_message": f"Failed to queue task: {str(e)}"
            }).eq("id", job_id).execute()
            raise HTTPException(500, f"Failed to queue analysis task: {str(e)}")
        
        # Get updated usage
        final_check = await feature_gate.check_limit(current_user, "analyses_per_month")
        
        return {
            "mode": "async",
            "job_id": job_id,
            "total": len(product_ids),
            "message": f"Analyzing {len(product_ids)} products in background",
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
    Shows full SP-API response for debugging.
    """
    from app.services.upc_converter import upc_converter
    from app.services.sp_api_client import sp_api_client
    import json
    
    logger.info(f"🧪 Testing UPC conversion for: {upc}")
    
    # Normalize UPC
    upc_clean = upc_converter.normalize_upc(upc)
    if not upc_clean:
        raise HTTPException(400, f"Invalid UPC format: {upc}. Must be 12-14 digits.")
    
    try:
        # Call SP-API directly to see full response
        logger.info(f"📞 Calling SP-API catalog search for UPC: {upc_clean}")
        raw_result = await sp_api_client.search_catalog_items(
            identifiers=[upc_clean],
            identifiers_type="UPC",
            marketplace_id="ATVPDKIKX0DER"
        )
        
        # Log the full response structure
        logger.info(f"📦 SP-API raw response type: {type(raw_result)}")
        if raw_result:
            logger.info(f"📦 SP-API response keys: {list(raw_result.keys()) if isinstance(raw_result, dict) else 'N/A (not dict)'}")
            logger.debug(f"📦 SP-API full response: {json.dumps(raw_result, indent=2, default=str)[:2000]}")
        
        # Test the conversion
        asin = await upc_converter.upc_to_asin(upc_clean)
        
        response_data = {
            "success": asin is not None,
            "upc": upc_clean,
            "asin": asin,
            "raw_sp_api_response": raw_result,
            "sp_api_response_keys": list(raw_result.keys()) if isinstance(raw_result, dict) and raw_result else None,
        }
        
        if asin:
            # Also get full catalog item details
            catalog_item = await sp_api_client.get_catalog_item(asin)
            response_data["catalog_item"] = catalog_item
            response_data["message"] = f"✅ Successfully converted UPC {upc_clean} to ASIN {asin}"
        else:
            response_data["message"] = f"❌ Could not find ASIN for UPC {upc_clean}. Product may not be available on Amazon."
            if raw_result:
                # Show what we got back
                items = raw_result.get("items") or raw_result.get("summaries") or []
                response_data["debug_info"] = {
                    "items_found": len(items),
                    "first_item_keys": list(items[0].keys()) if items and len(items) > 0 else None,
                    "first_item_sample": str(items[0])[:500] if items and len(items) > 0 else None
                }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error testing UPC conversion: {e}", exc_info=True)
        raise HTTPException(500, f"Error converting UPC: {str(e)}")


class SaveAsinSelectionRequest(BaseModel):
    upc: str
    selected_asin: str


@router.post("/save-asin-selection")
async def save_asin_selection(
    request: SaveAsinSelectionRequest,
    current_user=Depends(get_current_user)
):
    """
    Save user's ASIN selection for a UPC.
    Next time same UPC is analyzed, auto-use this ASIN.
    """
    user_id = str(current_user.id)
    
    # Normalize UPC
    upc_clean = upc_converter.normalize_upc(request.upc)
    if not upc_clean:
        raise HTTPException(400, "Invalid UPC format")
    
    # Get all ASINs for this UPC to store alternatives
    potential_asins, asin_status = await upc_converter.upc_to_asins(upc_clean)
    alternative_asins = [a.get('asin') for a in potential_asins if a.get('asin') != request.selected_asin]
    
    # Check if selection exists
    existing = supabase.table('upc_asin_selections') \
        .select('*') \
        .eq('user_id', user_id) \
        .eq('upc', upc_clean) \
        .execute()
    
    if existing.data and len(existing.data) > 0:
        # Update existing
        supabase.table('upc_asin_selections').update({
            'asin': request.selected_asin,
            'alternative_asins': alternative_asins,
            'selected_at': datetime.utcnow().isoformat(),
            'selection_count': existing.data[0].get('selection_count', 1) + 1,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('user_id', user_id).eq('upc', upc_clean).execute()
    else:
        # Insert new
        selection_data = {
            'user_id': user_id,
            'upc': upc_clean,
            'asin': request.selected_asin,
            'alternative_asins': alternative_asins,
            'selected_at': datetime.utcnow().isoformat(),
            'selection_count': 1
        }
        supabase.table('upc_asin_selections').insert(selection_data).execute()
    
    logger.info(f"✅ Saved ASIN selection: UPC {upc_clean} → ASIN {request.selected_asin}")
    
    return {'success': True, 'message': 'ASIN selection saved'}


class ManualPriceRequest(BaseModel):
    sell_price: float


@router.patch("/{analysis_id}/manual-price")
async def set_manual_price(
    analysis_id: str,
    request: ManualPriceRequest,
    current_user=Depends(get_current_user)
):
    """
    Manually set sell price for products without SP-API pricing.
    Recalculates profit based on manual price.
    """
    user_id = str(current_user.id)
    
    # Get current analysis
    result = supabase.table("analyses")\
        .select("*, products!inner(user_id, id)")\
        .eq("id", analysis_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Analysis not found")
    
    analysis = result.data[0]
    product = analysis.get("products", {})
    
    if product.get("user_id") != user_id:
        raise HTTPException(403, "Not authorized")
    
    # Get buy_cost from product_sources
    source_result = supabase.table("product_sources")\
        .select("buy_cost, pack_size")\
        .eq("product_id", product["id"])\
        .limit(1)\
        .execute()
    
    buy_cost = source_result.data[0]["buy_cost"] if source_result.data else 0
    
    if not buy_cost or buy_cost <= 0:
        raise HTTPException(400, "Product must have a buy_cost to calculate profit")
    
    sell_price = request.sell_price
    
    # Estimate fees (rough estimate without SP-API)
    # Typical: 15% referral + ~$3-5 FBA
    estimated_referral = sell_price * 0.15
    estimated_fba = 4.50  # Default estimate
    fees_total = estimated_referral + estimated_fba
    
    # Get user's shipping settings
    user_settings = run_async(get_user_cost_settings(user_id))
    inbound_rate = user_settings.get("inbound_rate_per_lb", 0.35)
    prep_cost = user_settings.get("default_prep_cost", 0.10)
    
    # Estimate weight if not available
    weight = analysis.get("item_weight_lb") or 0.5
    inbound_shipping = weight * inbound_rate
    
    # Calculate profit
    landed_cost = buy_cost + inbound_shipping + prep_cost
    net_profit = sell_price - fees_total - landed_cost
    roi = (net_profit / landed_cost) * 100 if landed_cost > 0 else 0
    
    # Update analysis
    update_data = {
        "manual_sell_price": sell_price,
        "sell_price": sell_price,
        "fees_total": round(fees_total, 2),
        "referral_fee": round(estimated_referral, 2),
        "referral_fee_percent": 15.0,
        "fba_fee": estimated_fba,
        "inbound_shipping": round(inbound_shipping, 2),
        "prep_cost": prep_cost,
        "total_landed_cost": round(landed_cost, 2),
        "net_profit": round(net_profit, 2),
        "roi": round(roi, 2),
        "profit_margin": round((net_profit / sell_price) * 100, 2) if sell_price > 0 else 0,
        "pricing_status": "manual",
        "needs_review": False,  # Reviewed - manual price set
        "analysis_stage": "stage2_complete",
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    supabase.table("analyses").update(update_data).eq("id", analysis_id).execute()
    
    return {
        "success": True,
        "calculated": {
            "sell_price": sell_price,
            "fees_total": round(fees_total, 2),
            "net_profit": round(net_profit, 2),
            "roi": round(roi, 2),
        },
        "note": "Fees are estimated. Re-analyze when product has active offers for accurate fees."
    }


@router.post("/save-product")
async def save_product_from_analysis(
    request: SaveProductFromAnalysisRequest,
    current_user=Depends(get_current_user)
):
    """
    Save a product from Quick Analyze results.
    Creates product, product_source (deal), and triggers full analysis.
    """
    user_id = str(current_user.id)
    
    try:
        # Get or create product
        existing = supabase.table("products")\
            .select("id, asin, upc")\
            .eq("user_id", user_id)\
            .eq("asin", request.asin)\
            .limit(1)\
            .execute()
        
        if existing.data:
            product_id = existing.data[0]["id"]
            # Update UPC if provided
            if request.upc and not existing.data[0].get("upc"):
                supabase.table("products")\
                    .update({"upc": request.upc})\
                    .eq("id", product_id)\
                    .execute()
            logger.info(f"✅ Using existing product {product_id} for ASIN {request.asin}")
        else:
            # Create new product
            product_data = {
                "user_id": user_id,
                "asin": request.asin,
                "status": "pending",
                "asin_status": "found"
            }
            if request.upc:
                product_data["upc"] = request.upc
            
            new_prod = supabase.table("products").insert(product_data).execute()
            product_id = new_prod.data[0]["id"] if new_prod.data else None
            
            if not product_id:
                raise HTTPException(500, "Failed to create product")
            
            logger.info(f"✅ Created new product {product_id} for ASIN {request.asin}")
        
        # Calculate buy_cost (handle pack_size if provided)
        buy_cost = request.buy_cost
        if request.pack_size and request.pack_size > 1:
            if request.wholesale_cost:
                buy_cost = request.wholesale_cost / request.pack_size
            else:
                buy_cost = request.buy_cost / request.pack_size
        
        # Get or create product_source (deal)
        # Note: product_sources doesn't have user_id - it's accessed via products table
        existing_source_query = supabase.table("product_sources")\
            .select("id")\
            .eq("product_id", product_id)
        
        if request.supplier_id:
            existing_source_query = existing_source_query.eq("supplier_id", request.supplier_id)
        else:
            existing_source_query = existing_source_query.is_("supplier_id", "null")
        
        existing_source = existing_source_query.limit(1).execute()
        
        source_data = {
            "product_id": product_id,
            "buy_cost": buy_cost,
            "moq": request.moq,
            "supplier_id": request.supplier_id,
            "source": "quick_analyze",
            "stage": "new",
            "is_active": True,
            "notes": request.notes
        }
        
        if request.pack_size:
            source_data["pack_size"] = request.pack_size
        if request.wholesale_cost:
            source_data["wholesale_cost"] = request.wholesale_cost
        
        if existing_source.data:
            # Update existing deal
            deal_id = existing_source.data[0]["id"]
            supabase.table("product_sources")\
                .update(source_data)\
                .eq("id", deal_id)\
                .execute()
            logger.info(f"✅ Updated product_source {deal_id}")
        else:
            # Create new deal
            source_result = supabase.table("product_sources").insert(source_data).execute()
            deal_id = source_result.data[0]["id"] if source_result.data else None
            logger.info(f"✅ Created product_source {deal_id}")
        
        # Trigger full analysis (SP-API + Keepa) via Celery
        try:
            from uuid import uuid4
            analysis_job_id = str(uuid4())
            
            # Create analysis job
            supabase.table("jobs").insert({
                "id": analysis_job_id,
                "user_id": user_id,
                "type": "batch_analyze",
                "status": "pending",
                "total_items": 1,
                "metadata": {
                    "triggered_by": "save_from_quick_analyze",
                    "asin": request.asin,
                    "product_id": product_id
                }
            }).execute()
            
            # Queue analysis
            batch_analyze_products.delay(analysis_job_id, user_id, [product_id])
            logger.info(f"✅ Queued full analysis for product {product_id} (job: {analysis_job_id})")
        except Exception as analysis_error:
            logger.error(f"Failed to queue analysis: {analysis_error}", exc_info=True)
            # Don't fail the save if analysis queueing fails
        
        return {
            "success": True,
            "product_id": product_id,
            "deal_id": deal_id,
            "message": "Product saved successfully. Full analysis is running in the background.",
            "analysis_job_id": analysis_job_id if 'analysis_job_id' in locals() else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save product from analysis: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to save product: {str(e)}")


@router.post("/{analysis_id}/re-analyze")
async def re_analyze_single(
    analysis_id: str,
    current_user=Depends(get_current_user)
):
    """Re-run analysis for a single product (useful after pricing becomes available)."""
    user_id = str(current_user.id)
    
    # Get analysis
    result = supabase.table("analyses")\
        .select("*, products!inner(asin, user_id, id)")\
        .eq("id", analysis_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Analysis not found")
    
    analysis = result.data[0]
    product = analysis.get("products", {})
    
    if product.get("user_id") != user_id:
        raise HTTPException(403, "Not authorized")
    
    asin = product["asin"]
    product_id = product["id"]
    
    # Get buy_cost from product_sources
    source_result = supabase.table("product_sources")\
        .select("buy_cost")\
        .eq("product_id", product_id)\
        .limit(1)\
        .execute()
    
    buy_cost = source_result.data[0]["buy_cost"] if source_result.data else None
    
    # Create job
    job_id = str(uuid.uuid4())
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "analyze_single",
        "status": "pending",
        "total_items": 1,
        "metadata": {
            "buy_cost": buy_cost,
            "supplier_id": analysis.get("supplier_id"),
        }
    }).execute()
    
    # Queue re-analysis
    analyze_single_product.delay(job_id, user_id, product_id, asin, buy_cost)
    
    return {
        "success": True,
        "job_id": job_id,
        "message": f"Re-analysis started for {asin}"
    }
