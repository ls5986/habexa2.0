"""
Celery tasks for product analysis using OPTIMIZED BATCH API calls.
Uses batch_analyzer for ALL analysis - NO individual SP-API catalog/offers calls.
"""
import asyncio
import logging
from typing import List, Dict
from celery import chord
from app.core.celery_app import celery_app
from app.services.supabase_client import supabase


async def get_user_cost_settings(user_id: str) -> dict:
    """
    Get user's cost settings (shipping rates, prep costs).
    Tries user_cost_settings table first, falls back to user_settings.
    """
    try:
        # Try new user_cost_settings table first
        result = supabase.table("user_cost_settings")\
            .select("*")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if result.data:
            return {
                "inbound_rate_per_lb": result.data.get("inbound_rate_per_lb", 0.35),
                "default_prep_cost": result.data.get("default_prep_cost", 0.10),
            }
    except Exception:
        pass
    
    try:
        # Fall back to user_settings table
        result = supabase.table("user_settings")\
            .select("default_inbound_shipping, default_prep_cost")\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if result.data:
            return {
                "inbound_rate_per_lb": result.data.get("default_inbound_shipping", 0.35),
                "default_prep_cost": result.data.get("default_prep_cost", 0.10),
            }
    except Exception:
        pass
    
    # Return defaults if nothing found
    return {
        "inbound_rate_per_lb": 0.35,
        "default_prep_cost": 0.10,
    }
from app.services.batch_analyzer import batch_analyzer
from app.tasks.base import JobManager, run_async
from app.tasks.progress import AtomicJobProgress
from app.core.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

WORKERS = settings.CELERY_WORKERS  # Number of parallel chunks
PROCESS_BATCH_SIZE = settings.CELERY_PROCESS_BATCH_SIZE  # Batch size for processing


@celery_app.task(bind=True, max_retries=3, name="app.tasks.analysis.analyze_single_product", queue="analysis")
def analyze_single_product(self, job_id: str, user_id: str, product_id: str, asin: str, buy_cost: float = None):
    """
    Analyze a single product using batch analyzer (still uses batch API calls for efficiency).
    Creates product_source entry so product appears in products list.
    """
    job = JobManager(job_id)
    
    try:
        job.start(total_items=1)
        
        # Get job metadata for buy_cost, moq, supplier_id
        job_data = job.get()
        metadata = job_data.get("metadata", {})
        buy_cost = buy_cost or metadata.get("buy_cost") or metadata.get("original_buy_cost")
        moq = metadata.get("moq", 1)
        supplier_id = metadata.get("supplier_id")
        
        # Use batch analyzer even for single product (it's still efficient)
        try:
            # Build buy_costs, promo_costs, and source_data dicts from metadata
            buy_costs = {}
            promo_costs = {}
            source_data = {}
            if buy_cost:
                buy_costs[asin] = buy_cost
            # Check for promo_buy_cost in metadata
            promo_buy_cost = metadata.get("promo_buy_cost")
            if promo_buy_cost:
                promo_costs[asin] = float(promo_buy_cost)
            
            # Get source data from metadata
            source_data[asin] = {
                "supplier_ships_direct": metadata.get("supplier_ships_direct", False),
                "inbound_rate_override": metadata.get("inbound_rate_override"),
                "prep_cost_override": metadata.get("prep_cost_override"),
            }
            
            # Get user cost settings
            user_settings = run_async(get_user_cost_settings(user_id))
            
            results = run_async(batch_analyzer.analyze_products(
                [asin],
                buy_costs=buy_costs,
                promo_costs=promo_costs,
                source_data=source_data,
                user_settings=user_settings
            ))
            result = results.get(asin, {})
        except Exception as e:
            logger.error(f"Batch analyzer failed for {asin}: {e}", exc_info=True)
            # Set error status and fail job
            supabase.table("products").update({
                "status": "error",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", product_id).execute()
            job.fail(f"Analysis failed: {str(e)}")
            raise self.retry(exc=e, countdown=60)
        
        # Check if we got any useful data (even if price unavailable)
        if result.get("success") or result.get("title") or result.get("brand"):
            # Get or create product_source entry (required for product to show in list)
            if buy_cost:
                try:
                    # Check if product_source already exists
                    existing_source = supabase.table("product_sources")\
                        .select("id, supplier_id")\
                        .eq("product_id", product_id)\
                        .eq("user_id", user_id)\
                        .limit(1)\
                        .execute()
                    
                    if existing_source.data:
                        # Update existing source
                        source_id = existing_source.data[0]["id"]
                        supabase.table("product_sources").update({
                            "buy_cost": buy_cost,
                            "moq": moq,
                            "supplier_id": supplier_id,
                            "stage": "reviewed",
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", source_id).execute()
                    else:
                        # Create new product_source
                        supabase.table("product_sources").insert({
                            "user_id": user_id,
                            "product_id": product_id,
                            "supplier_id": supplier_id,
                            "buy_cost": buy_cost,
                            "moq": moq,
                            "stage": "reviewed",
                            "source": "quick_analyze"
                        }).execute()
                    logger.info(f"✅ Created/updated product_source for product {product_id}")
                except Exception as e:
                    logger.warning(f"Could not create product_source: {e}")
            
            # Get supplier_id from product_sources if not set
            if not supplier_id:
                try:
                    sources = supabase.table("product_sources")\
                        .select("supplier_id")\
                        .eq("product_id", product_id)\
                        .limit(1)\
                        .execute()
                    if sources.data and sources.data[0].get("supplier_id"):
                        supplier_id = sources.data[0]["supplier_id"]
                except Exception as e:
                    logger.warning(f"Could not get supplier_id for product {product_id}: {e}")
            
            # Save analysis - include ALL fields
            analysis_data = {
                "user_id": user_id,
                "asin": asin,
                "supplier_id": supplier_id,  # Can be NULL
                "analysis_data": {},  # Required JSONB field
                
                # Pricing status
                "pricing_status": result.get("pricing_status", "complete"),
                "pricing_status_reason": result.get("pricing_status_reason"),
                "needs_review": result.get("needs_review", False),
                "manual_sell_price": result.get("manual_sell_price"),
                
                # Pricing
                "sell_price": result.get("sell_price"),
                "buy_cost": result.get("buy_cost"),
                
                # Fee breakdown
                "referral_fee": result.get("referral_fee"),
                "referral_fee_percent": result.get("referral_fee_percent"),
                "fba_fee": result.get("fees_fba") or result.get("fba_fee"),
                "variable_closing_fee": result.get("variable_closing_fee"),
                "fees_total": result.get("fees_total"),
                
                # Shipping & landed cost
                "inbound_shipping": result.get("inbound_shipping"),
                "prep_cost": result.get("prep_cost"),
                "total_landed_cost": result.get("total_landed_cost"),
                
                # Profit
                "net_profit": result.get("net_profit"),
                "roi": result.get("roi"),
                "profit_margin": result.get("profit_margin"),
                
                # Promo
                "promo_buy_cost": result.get("promo_buy_cost"),
                "promo_landed_cost": result.get("promo_landed_cost"),
                "promo_net_profit": result.get("promo_net_profit"),
                "promo_roi": result.get("promo_roi"),
                
                # Worst case
                "worst_case_price": result.get("worst_case_price"),
                "worst_case_fees": result.get("worst_case_fees"),
                "worst_case_profit": result.get("worst_case_profit"),
                "still_profitable_at_worst": result.get("still_profitable_at_worst"),
                
                # Dimensions
                "item_weight_lb": result.get("item_weight_lb"),
                "item_length_in": result.get("item_length_in"),
                "item_width_in": result.get("item_width_in"),
                "item_height_in": result.get("item_height_in"),
                "size_tier": result.get("size_tier"),
                
                # Competition & product
                "category": result.get("category"),
                "bsr": result.get("bsr") or result.get("current_sales_rank"),
                "fba_seller_count": result.get("fba_seller_count"),
                "fbm_seller_count": result.get("fbm_seller_count"),
                "total_seller_count": result.get("seller_count") or result.get("total_seller_count"),
                "variation_count": result.get("variation_count"),
                "review_count": result.get("review_count"),
                "rating": result.get("rating"),
                
                # 365-day
                "fba_lowest_365d": result.get("fba_lowest_365d"),
                "fba_lowest_date": result.get("fba_lowest_date"),
                "fbm_lowest_365d": result.get("fbm_lowest_365d"),
                "amazon_was_seller": result.get("amazon_was_seller"),
                "lowest_was_fba": result.get("lowest_was_fba"),
                
                # Stage
                "analysis_stage": result.get("analysis_stage"),
                "passed_stage2": result.get("passed_stage2"),
                
                # Legacy fields (for compatibility)
                "price_source": result.get("price_source", "sp-api"),
                "sales_drops_30": result.get("sales_drops_30"),
                "sales_drops_90": result.get("sales_drops_90"),
                "sales_drops_180": result.get("sales_drops_180"),
            }
            
            analysis_result = supabase.table("analyses").upsert(
                analysis_data,
                on_conflict="user_id,supplier_id,asin"
            ).execute()
            
            analysis_id = analysis_result.data[0]["id"] if analysis_result.data else None
            
            # Update product - handle both full success and partial success (no price)
            update_data = {
                "analysis_id": analysis_id,
                "title": result.get("title"),
                "image_url": result.get("image_url"),
                "brand_name": result.get("brand"),  # Schema has brand_name, not brand
                "bsr": result.get("bsr"),
                "seller_count": result.get("seller_count"),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Only set pricing fields if we have a sell_price
            if result.get("sell_price"):
                update_data["sell_price"] = result.get("sell_price")
                update_data["fees_total"] = result.get("fees_total")
                update_data["status"] = "analyzed"
            else:
                # Partial success - we have catalog data but no pricing
                # Mark as analyzed so it shows up, but frontend can indicate price unavailable
                update_data["status"] = "analyzed"
                update_data["sell_price"] = None
                logger.warning(f"⚠️ Product {asin} analyzed but no pricing available")
            
            supabase.table("products").update(update_data).eq("id", product_id).execute()
            
            job.complete({"analysis_id": analysis_id, "product_id": product_id}, success=1, errors=0)
        else:
            # Complete failure - no data from any source
            logger.error(f"❌ Analysis failed for {asin}: No data available from any source")
            supabase.table("products").update({
                "status": "error",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", product_id).execute()
            
            job.complete({"error": "No data available from SP-API or Keepa"}, success=0, errors=1, error_list=["No data"])
        
    except Exception as e:
        logger.error(f"Error analyzing {asin}: {e}", exc_info=True)
        job.fail(str(e))
        raise self.retry(exc=e, countdown=30)


@celery_app.task(bind=True, max_retries=2, name="app.tasks.analysis.batch_analyze_products", queue="analysis")
def batch_analyze_products(self, job_id: str, user_id: str, product_ids: List[str]):
    """
    Main batch analysis task. Uses batch_analyzer for ALL products.
    
    Strategy:
    - Keepa batch (100 ASINs) for catalog data
    - SP-API batch (20 ASINs) for pricing
    - SP-API batch (20 items) for fees
    
    NO individual SP-API catalog or offers calls!
    """
    job = JobManager(job_id)
    
    try:
        # Get products from database - batch to avoid URL length limits
        products = []
        BATCH_FETCH_SIZE = PROCESS_BATCH_SIZE
        
        if not product_ids:
            job.complete({"message": "No product IDs provided"}, 0, 0)
            return {"success": 0, "error": 0}
        
        # Filter out products with PENDING_ ASINs (these are placeholders for products without ASINs)
        # These should not be analyzed until a real ASIN is found
        logger.info(f"🔍 Fetching {len(product_ids)} products for analysis...")
        
        for batch_start in range(0, len(product_ids), BATCH_FETCH_SIZE):
            batch_ids = product_ids[batch_start:batch_start + BATCH_FETCH_SIZE]
            result = supabase.table("products")\
                .select("id, asin, asin_status, upc")\
                .in_("id", batch_ids)\
                .execute()
            
            for product in (result.data or []):
                asin = product.get("asin")
                asin_status = product.get("asin_status", "found")
                
                # Skip products with PENDING_ ASINs - these are placeholders
                if asin and asin.startswith("PENDING_"):
                    logger.warning(f"⏭️ Skipping product {product.get('id')} with PENDING_ ASIN: {asin} (UPC: {product.get('upc')})")
                    logger.warning(f"   This product needs manual ASIN entry. Use the 'Add ASIN' feature in the UI.")
                    continue
                
                # Skip products with asin_status = 'not_found' or 'pending'
                if asin_status in ['not_found', 'pending']:
                    logger.warning(f"⏭️ Skipping product {product.get('id')} with asin_status='{asin_status}' (ASIN: {asin})")
                    logger.warning(f"   This product needs manual ASIN entry. Use the 'Add ASIN' feature in the UI.")
                    continue
                
                # Only analyze products with real ASINs
                if asin and len(asin) == 10 and not asin.startswith("PENDING_"):
                    products.append(product)
                else:
                    logger.warning(f"⏭️ Skipping product {product.get('id')} with invalid ASIN: {asin}")
        
        logger.info(f"✅ Filtered to {len(products)} products with valid ASINs (skipped {len(product_ids) - len(products)} with PENDING_/invalid ASINs)")
        
        if not products:
            job.complete({"message": "No products with valid ASINs to analyze"}, 0, 0)
            return {"success": 0, "error": 0}
        
        for i in range(0, len(product_ids), BATCH_FETCH_SIZE):
            batch_ids = product_ids[i:i + BATCH_FETCH_SIZE]
            try:
                products_result = supabase.table("products")\
                    .select("id, asin, status")\
                    .eq("user_id", user_id)\
                    .in_("id", batch_ids)\
                    .execute()
                
                if products_result.data:
                    products.extend(products_result.data)
            except Exception as e:
                logger.warning(f"Failed to fetch product batch {i}-{i+len(batch_ids)}: {e}")
        
        total = len(products)
        
        if not total:
            job.complete({"message": "No products"}, 0, 0)
            return {"success": 0, "error": 0}
        
        # Log status breakdown
        status_counts = {}
        for p in products:
            status = p.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        logger.info(f"📊 Product status breakdown: {status_counts}")
        
        job.start(total_items=total)
        
        logger.info(f"🚀 Starting BATCH analysis: {total} products")
        logger.info(f"📊 Using batch_analyzer - NO individual SP-API catalog/offers calls")
        logger.info(f"📋 Product IDs: {[p['id'] for p in products[:10]]}{'...' if total > 10 else ''}")
        
        # Get marketplace_id
        marketplace_id = "ATVPDKIKX0DER"  # Default to US
        try:
            connection_result = supabase.table("amazon_connections")\
                .select("marketplace_id")\
                .eq("user_id", user_id)\
                .eq("is_connected", True)\
                .limit(1)\
                .execute()
            if connection_result.data and connection_result.data[0].get("marketplace_id"):
                marketplace_id = connection_result.data[0]["marketplace_id"]
        except:
            pass
        
        processed = 0
        success_count = 0
        error_count = 0
        error_list = []
        
        # Process in batches of 100 (optimized for Keepa)
        for i in range(0, total, PROCESS_BATCH_SIZE):
            # Check for cancellation
            if job.is_cancelled():
                logger.info("Job cancelled")
                break
            
            batch = products[i:i + PROCESS_BATCH_SIZE]
            batch_asins = [p["asin"] for p in batch]
            batch_num = (i // PROCESS_BATCH_SIZE) + 1
            total_batches = (total + PROCESS_BATCH_SIZE - 1) // PROCESS_BATCH_SIZE
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} products)")
            
            # Build buy_costs, promo_costs, and source_data dicts from product_sources
            buy_costs = {}
            promo_costs = {}
            source_data = {}
            try:
                product_ids_batch = [p["id"] for p in batch]
                sources_result = supabase.table("product_sources")\
                    .select("product_id, buy_cost, promo_buy_cost, supplier_ships_direct, inbound_rate_override, prep_cost_override")\
                    .in_("product_id", product_ids_batch)\
                    .execute()
                
                # Create mapping: product_id -> buy_cost, promo_buy_cost, and shipping overrides
                product_id_to_buy_cost = {}
                product_id_to_promo_cost = {}
                product_id_to_source = {}
                for source in (sources_result.data or []):
                    pid = source.get("product_id")
                    cost = source.get("buy_cost")
                    promo_cost = source.get("promo_buy_cost")
                    if pid and cost:
                        product_id_to_buy_cost[pid] = float(cost)
                    if pid and promo_cost:
                        product_id_to_promo_cost[pid] = float(promo_cost)
                    if pid:
                        product_id_to_source[pid] = {
                            "supplier_ships_direct": source.get("supplier_ships_direct", False),
                            "inbound_rate_override": source.get("inbound_rate_override"),
                            "prep_cost_override": source.get("prep_cost_override"),
                        }
                
                # Map to ASINs
                for product in batch:
                    asin = product["asin"]
                    product_id = product["id"]
                    if product_id in product_id_to_buy_cost:
                        buy_costs[asin] = product_id_to_buy_cost[product_id]
                    if product_id in product_id_to_promo_cost:
                        promo_costs[asin] = product_id_to_promo_cost[product_id]
                    if product_id in product_id_to_source:
                        source_data[asin] = product_id_to_source[product_id]
            except Exception as e:
                logger.warning(f"Could not fetch buy_costs for batch: {e}")
            
            # Get user cost settings
            user_settings = run_async(get_user_cost_settings(user_id))
            
            # =====================================================
            # USE BATCH ANALYZER - This uses:
            # - Keepa batch (100 ASINs) for catalog
            # - SP-API batch (20 ASINs) for pricing
            # - SP-API batch (20 items) for fees
            # NO individual SP-API catalog or offers calls!
            # =====================================================
            results = run_async(batch_analyzer.analyze_products(
                batch_asins,
                buy_costs=buy_costs,
                promo_costs=promo_costs,
                source_data=source_data,
                user_settings=user_settings,
                marketplace_id=marketplace_id
            ))
            
            # Save results to database
            for product in batch:
                asin = product["asin"]
                product_id = product["id"]
                result = results.get(asin, {})
                
                try:
                    if result.get("success"):
                        # Get supplier_id from product_sources (required for unique constraint)
                        supplier_id = None
                        try:
                            sources = supabase.table("product_sources")\
                                .select("supplier_id")\
                                .eq("product_id", product_id)\
                                .limit(1)\
                                .execute()
                            if sources.data and sources.data[0].get("supplier_id"):
                                supplier_id = sources.data[0]["supplier_id"]
                        except Exception as e:
                            logger.warning(f"Could not get supplier_id for product {product_id}: {e}")
                        
                        # Save analysis - include ALL fields
                        analysis_data = {
                            "user_id": user_id,
                            "asin": asin,
                            "supplier_id": supplier_id,  # Can be NULL
                            "analysis_data": {},  # Required JSONB field
                            
                            # Pricing
                            "sell_price": result.get("sell_price"),
                            "buy_cost": result.get("buy_cost"),
                            
                            # Fee breakdown
                            "referral_fee": result.get("referral_fee"),
                            "referral_fee_percent": result.get("referral_fee_percent"),
                            "fba_fee": result.get("fees_fba") or result.get("fba_fee"),
                            "variable_closing_fee": result.get("variable_closing_fee"),
                            "fees_total": result.get("fees_total"),
                            
                            # Shipping & landed cost
                            "inbound_shipping": result.get("inbound_shipping"),
                            "prep_cost": result.get("prep_cost"),
                            "total_landed_cost": result.get("total_landed_cost"),
                            
                            # Profit
                            "net_profit": result.get("net_profit"),
                            "roi": result.get("roi"),
                            "profit_margin": result.get("profit_margin"),
                            
                            # Promo
                            "promo_buy_cost": result.get("promo_buy_cost"),
                            "promo_landed_cost": result.get("promo_landed_cost"),
                            "promo_net_profit": result.get("promo_net_profit"),
                            "promo_roi": result.get("promo_roi"),
                            
                            # Worst case
                            "worst_case_price": result.get("worst_case_price"),
                            "worst_case_fees": result.get("worst_case_fees"),
                            "worst_case_profit": result.get("worst_case_profit"),
                            "still_profitable_at_worst": result.get("still_profitable_at_worst"),
                            
                            # Dimensions
                            "item_weight_lb": result.get("item_weight_lb"),
                            "item_length_in": result.get("item_length_in"),
                            "item_width_in": result.get("item_width_in"),
                            "item_height_in": result.get("item_height_in"),
                            "size_tier": result.get("size_tier"),
                            
                            # Competition & product
                            "category": result.get("category"),
                            "bsr": result.get("bsr") or result.get("current_sales_rank"),
                            "fba_seller_count": result.get("fba_seller_count"),
                            "fbm_seller_count": result.get("fbm_seller_count"),
                            "total_seller_count": result.get("seller_count") or result.get("total_seller_count"),
                            "variation_count": result.get("variation_count"),
                            "review_count": result.get("review_count"),
                            "rating": result.get("rating"),
                            
                            # 365-day
                            "fba_lowest_365d": result.get("fba_lowest_365d"),
                            "fba_lowest_date": result.get("fba_lowest_date"),
                            "fbm_lowest_365d": result.get("fbm_lowest_365d"),
                            "amazon_was_seller": result.get("amazon_was_seller"),
                            "lowest_was_fba": result.get("lowest_was_fba"),
                            
                            # Stage
                            "analysis_stage": result.get("analysis_stage"),
                            "passed_stage2": result.get("passed_stage2"),
                            
                            # Legacy fields (for compatibility)
                            "price_source": result.get("price_source", "sp-api"),
                            "sales_drops_30": result.get("sales_drops_30"),
                            "sales_drops_90": result.get("sales_drops_90"),
                            "sales_drops_180": result.get("sales_drops_180"),
                        }
                        
                        # Keepa data (secondary) - only add if value exists
                        if result.get("category"):
                            analysis_data["category"] = result.get("category")
                        if result.get("sales_drops_30") is not None:
                            analysis_data["sales_drops_30"] = result.get("sales_drops_30")
                        if result.get("sales_drops_90") is not None:
                            analysis_data["sales_drops_90"] = result.get("sales_drops_90")
                        if result.get("sales_drops_180") is not None:
                            analysis_data["sales_drops_180"] = result.get("sales_drops_180")
                        if result.get("variation_count") is not None:
                            analysis_data["variation_count"] = result.get("variation_count")
                        if result.get("amazon_in_stock") is not None:
                            analysis_data["amazon_in_stock"] = result.get("amazon_in_stock")
                        if result.get("rating") is not None:
                            analysis_data["rating"] = result.get("rating")
                        if result.get("review_count") is not None:
                            analysis_data["review_count"] = result.get("review_count")
                        
                        # Stage tracking
                        if result.get("analysis_stage"):
                            analysis_data["analysis_stage"] = result.get("analysis_stage")
                        if result.get("stage2_roi") is not None:
                            analysis_data["stage2_roi"] = result.get("stage2_roi")
                        if result.get("passed_stage2") is not None:
                            analysis_data["passed_stage2"] = result.get("passed_stage2")
                        
                        # Keepa 365-day data
                        if result.get("fba_lowest_365d") is not None:
                            analysis_data["fba_lowest_365d"] = result.get("fba_lowest_365d")
                        if result.get("fba_lowest_date"):
                            analysis_data["fba_lowest_date"] = result.get("fba_lowest_date")
                        if result.get("fbm_lowest_365d") is not None:
                            analysis_data["fbm_lowest_365d"] = result.get("fbm_lowest_365d")
                        if result.get("fbm_lowest_date"):
                            analysis_data["fbm_lowest_date"] = result.get("fbm_lowest_date")
                        if result.get("lowest_was_fba") is not None:
                            analysis_data["lowest_was_fba"] = result.get("lowest_was_fba")
                        if result.get("amazon_was_seller") is not None:
                            analysis_data["amazon_was_seller"] = result.get("amazon_was_seller")
                        
                        # Worst case
                        if result.get("worst_case_profit") is not None:
                            analysis_data["worst_case_profit"] = result.get("worst_case_profit")
                        if result.get("still_profitable_at_worst") is not None:
                            analysis_data["still_profitable_at_worst"] = result.get("still_profitable_at_worst")
                        
                        # Competition
                        if result.get("fba_seller_count") is not None:
                            analysis_data["fba_seller_count"] = result.get("fba_seller_count")
                        if result.get("fbm_seller_count") is not None:
                            analysis_data["fbm_seller_count"] = result.get("fbm_seller_count")
                        
                        # Promo analysis
                        if result.get("promo_net_profit") is not None:
                            analysis_data["promo_net_profit"] = result.get("promo_net_profit")
                        if result.get("promo_roi") is not None:
                            analysis_data["promo_roi"] = result.get("promo_roi")
                        
                        # Upsert with correct unique constraint
                        analysis_result = supabase.table("analyses").upsert(
                            analysis_data,
                            on_conflict="user_id,supplier_id,asin"
                        ).execute()
                        
                        analysis_id = analysis_result.data[0]["id"] if analysis_result.data else None
                        
                        # Update product
                        supabase.table("products").update({
                            "analysis_id": analysis_id,
                            "title": result.get("title"),
                            "image_url": result.get("image_url"),
                            "brand_name": result.get("brand"),  # Schema has brand_name, not brand
                            "sell_price": result.get("sell_price"),
                            "fees_total": result.get("fees_total"),
                            "bsr": result.get("bsr"),
                            "seller_count": result.get("seller_count"),
                            "status": "analyzed",
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", product_id).execute()
                        
                        # Update product_sources stage to "reviewed" when analysis completes
                        sources_result = supabase.table("product_sources")\
                            .select("id")\
                            .eq("product_id", product_id)\
                            .execute()
                        
                        if sources_result.data:
                            source_ids = [s["id"] for s in sources_result.data]
                            supabase.table("product_sources")\
                                .update({
                                    "stage": "reviewed",
                                    "updated_at": datetime.utcnow().isoformat()
                                })\
                                .in_("id", source_ids)\
                                .execute()
                        
                        success_count += 1
                    else:
                        # Mark as error
                        supabase.table("products").update({
                            "status": "error",
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", product_id).execute()
                        
                        error_count += 1
                        error_list.append(f"{asin}: No SP-API price")
                        
                except Exception as e:
                    error_count += 1
                    error_list.append(f"{asin}: {str(e)[:50]}")
                
                processed += 1
            
            # Update job progress
            job.update_progress(processed, total, success_count, error_count, error_list[-10:])
            logger.info(f"📊 Progress: {processed}/{total} ({success_count} ok, {error_count} errors)")
        
        # Complete job
        job.complete({
            "success_count": success_count,
            "error_count": error_count,
            "total_processed": processed
        }, success_count, error_count, error_list)
        
        logger.info(f"🏁 Analysis complete: {success_count}/{total} successful")
        
        return {"success": success_count, "error": error_count}
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        import traceback
        traceback.print_exc()
        job.fail(str(e))
        raise


@celery_app.task
def analyze_all_pending_for_user(user_id: str):
    """Find all pending products and queue them for analysis."""
    from uuid import uuid4
    
    # Get pending products
    products = supabase.table("products")\
        .select("id")\
        .eq("user_id", user_id)\
        .eq("status", "pending")\
        .execute()
    
    product_ids = [p["id"] for p in (products.data or [])]
    
    if not product_ids:
        return {"message": "No pending products"}
    
    # Create job
    job_id = str(uuid4())
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "batch_analyze",
        "status": "pending",
        "total_items": len(product_ids)
    }).execute()
    
    # Queue analysis - use parallel version for large batches
    if len(product_ids) > settings.CELERY_PROCESS_BATCH_SIZE:
        batch_analyze_parallel.delay(job_id, user_id, product_ids)
    else:
        batch_analyze_products.delay(job_id, user_id, product_ids)
    
    return {"job_id": job_id, "product_count": len(product_ids)}


# ==========================================
# PARALLEL PROCESSING TASKS
# ==========================================


@celery_app.task(bind=True, name="app.tasks.analysis.analyze_chunk", queue="analysis")
def analyze_chunk(self, job_id: str, user_id: str, product_chunk: List[Dict], chunk_index: int):
    """
    Analyze a chunk using BATCH analyzer only.
    
    Uses:
    - Keepa batch (100 ASINs) for catalog data
    - SP-API batch (20 ASINs) for pricing
    - SP-API batch (20 items) for fees
    
    Does NOT use:
    - Individual SP-API getCatalogItem calls
    - Individual SP-API offers calls
    - ASINAnalyzer (old per-product approach)
    """
    logger.info(f"📦 Chunk {chunk_index}: Processing {len(product_chunk)} products with BATCH analyzer")
    
    progress = AtomicJobProgress(job_id)
    
    try:
        # Extract ASINs and product IDs
        asins = [p["asin"] for p in product_chunk]
        asin_to_id = {p["asin"]: p["id"] for p in product_chunk}
        
        if not asins:
            return {"success": 0, "error": 0, "chunk_index": chunk_index}
        
        # Get marketplace_id
        marketplace_id = "ATVPDKIKX0DER"  # Default
        try:
            connection_result = supabase.table("amazon_connections")\
                .select("marketplace_id")\
                .eq("user_id", user_id)\
                .eq("is_connected", True)\
                .limit(1)\
                .execute()
            if connection_result.data and connection_result.data[0].get("marketplace_id"):
                marketplace_id = connection_result.data[0]["marketplace_id"]
        except:
            pass
        
        # Build buy_costs, promo_costs, and source_data dicts from product_sources
        buy_costs = {}
        promo_costs = {}
        source_data = {}
        try:
            product_ids_chunk = [p["id"] for p in product_chunk]
            sources_result = supabase.table("product_sources")\
                .select("product_id, buy_cost, promo_buy_cost, supplier_ships_direct, inbound_rate_override, prep_cost_override")\
                .in_("product_id", product_ids_chunk)\
                .execute()
            
            # Create mapping: product_id -> buy_cost, promo_buy_cost, and shipping overrides
            product_id_to_buy_cost = {}
            product_id_to_promo_cost = {}
            product_id_to_source = {}
            for source in (sources_result.data or []):
                pid = source.get("product_id")
                cost = source.get("buy_cost")
                promo_cost = source.get("promo_buy_cost")
                if pid and cost:
                    product_id_to_buy_cost[pid] = float(cost)
                if pid and promo_cost:
                    product_id_to_promo_cost[pid] = float(promo_cost)
                if pid:
                    product_id_to_source[pid] = {
                        "supplier_ships_direct": source.get("supplier_ships_direct", False),
                        "inbound_rate_override": source.get("inbound_rate_override"),
                        "prep_cost_override": source.get("prep_cost_override"),
                    }
            
            # Map to ASINs
            for product in product_chunk:
                asin = product["asin"]
                product_id = product["id"]
                if product_id in product_id_to_buy_cost:
                    buy_costs[asin] = product_id_to_buy_cost[product_id]
                if product_id in product_id_to_promo_cost:
                    promo_costs[asin] = product_id_to_promo_cost[product_id]
                if product_id in product_id_to_source:
                    source_data[asin] = product_id_to_source[product_id]
        except Exception as e:
            logger.warning(f"Could not fetch buy_costs for chunk: {e}")
        
        # Get user cost settings
        user_settings = run_async(get_user_cost_settings(user_id))
        
        # =====================================================
        # USE BATCH ANALYZER - This uses:
        # - Keepa batch (100 ASINs) for catalog
        # - SP-API batch (20 ASINs) for pricing
        # - SP-API batch (20 items) for fees
        # NO individual SP-API catalog or offers calls!
        # =====================================================
        logger.info(f"📦 Chunk {chunk_index}: Calling batch_analyzer.analyze_products()")
        results = run_async(batch_analyzer.analyze_products(
            asins,
            buy_costs=buy_costs,
            promo_costs=promo_costs,
            source_data=source_data,
            user_settings=user_settings,
            marketplace_id=marketplace_id
        ))
        
        success_count = 0
        error_count = 0
        
        for asin, result in results.items():
            product_id = asin_to_id.get(asin)
            if not product_id:
                continue
            
            try:
                # Save ALL products, even if they don't have pricing
                # Products without pricing will have pricing_status = 'no_pricing' and needs_review = True
                if result.get("success") or result.get("pricing_status") == "no_pricing" or result.get("title") or result.get("brand"):
                    # Get supplier_id from product_sources if available
                    supplier_id = None
                    try:
                        sources = supabase.table("product_sources")\
                            .select("supplier_id")\
                            .eq("product_id", product_id)\
                            .limit(1)\
                            .execute()
                        if sources.data and sources.data[0].get("supplier_id"):
                            supplier_id = sources.data[0]["supplier_id"]
                    except Exception as e:
                        logger.warning(f"Could not get supplier_id for product {product_id}: {e}")
                    
                    # Save analysis - include ALL fields (same format as single product)
                    analysis_data_chunk = {
                        "user_id": user_id,
                        "asin": asin,
                        "supplier_id": supplier_id,  # Can be NULL
                        "analysis_data": {},  # Required JSONB field
                        
                        # Pricing status
                        "pricing_status": result.get("pricing_status", "complete"),
                        "pricing_status_reason": result.get("pricing_status_reason"),
                        "needs_review": result.get("needs_review", False),
                        "manual_sell_price": result.get("manual_sell_price"),
                        
                        # Pricing
                        "sell_price": result.get("sell_price"),
                        "buy_cost": result.get("buy_cost"),
                        
                        # Fee breakdown
                        "referral_fee": result.get("referral_fee"),
                        "referral_fee_percent": result.get("referral_fee_percent"),
                        "fba_fee": result.get("fees_fba") or result.get("fba_fee"),
                        "variable_closing_fee": result.get("variable_closing_fee"),
                        "fees_total": result.get("fees_total"),
                        
                        # Shipping & landed cost
                        "inbound_shipping": result.get("inbound_shipping"),
                        "prep_cost": result.get("prep_cost"),
                        "total_landed_cost": result.get("total_landed_cost"),
                        
                        # Profit
                        "net_profit": result.get("net_profit"),
                        "roi": result.get("roi"),
                        "profit_margin": result.get("profit_margin"),
                        
                        # Promo
                        "promo_buy_cost": result.get("promo_buy_cost"),
                        "promo_landed_cost": result.get("promo_landed_cost"),
                        "promo_net_profit": result.get("promo_net_profit"),
                        "promo_roi": result.get("promo_roi"),
                        
                        # Worst case
                        "worst_case_price": result.get("worst_case_price"),
                        "worst_case_fees": result.get("worst_case_fees"),
                        "worst_case_profit": result.get("worst_case_profit"),
                        "still_profitable_at_worst": result.get("still_profitable_at_worst"),
                        
                        # Dimensions
                        "item_weight_lb": result.get("item_weight_lb"),
                        "item_length_in": result.get("item_length_in"),
                        "item_width_in": result.get("item_width_in"),
                        "item_height_in": result.get("item_height_in"),
                        "size_tier": result.get("size_tier"),
                        
                        # Competition & product
                        "category": result.get("category"),
                        "bsr": result.get("bsr") or result.get("current_sales_rank"),
                        "fba_seller_count": result.get("fba_seller_count"),
                        "fbm_seller_count": result.get("fbm_seller_count"),
                        "total_seller_count": result.get("seller_count") or result.get("total_seller_count"),
                        "variation_count": result.get("variation_count"),
                        "review_count": result.get("review_count"),
                        "rating": result.get("rating"),
                        
                        # 365-day
                        "fba_lowest_365d": result.get("fba_lowest_365d"),
                        "fba_lowest_date": result.get("fba_lowest_date"),
                        "fbm_lowest_365d": result.get("fbm_lowest_365d"),
                        "amazon_was_seller": result.get("amazon_was_seller"),
                        "lowest_was_fba": result.get("lowest_was_fba"),
                        
                        # Stage
                        "analysis_stage": result.get("analysis_stage"),
                        "passed_stage2": result.get("passed_stage2"),
                        
                        # Legacy fields (for compatibility)
                        "price_source": result.get("price_source", "sp-api"),
                        "title": result.get("title"),
                        "brand": result.get("brand"),
                        "image_url": result.get("image_url"),
                        "sales_drops_30": result.get("sales_drops_30"),
                        "sales_drops_90": result.get("sales_drops_90"),
                        "sales_drops_180": result.get("sales_drops_180"),
                        "amazon_in_stock": result.get("amazon_in_stock"),
                    }
                    
                    # Add optional fields only if they exist (already included above)
                    if result.get("stage2_roi") is not None:
                        analysis_data_chunk["stage2_roi"] = result.get("stage2_roi")
                    if result.get("passed_stage2") is not None:
                        analysis_data_chunk["passed_stage2"] = result.get("passed_stage2")
                    if result.get("fba_lowest_365d") is not None:
                        analysis_data_chunk["fba_lowest_365d"] = result.get("fba_lowest_365d")
                    if result.get("fba_lowest_date"):
                        analysis_data_chunk["fba_lowest_date"] = result.get("fba_lowest_date")
                    if result.get("fbm_lowest_365d") is not None:
                        analysis_data_chunk["fbm_lowest_365d"] = result.get("fbm_lowest_365d")
                    if result.get("fbm_lowest_date"):
                        analysis_data_chunk["fbm_lowest_date"] = result.get("fbm_lowest_date")
                    if result.get("lowest_was_fba") is not None:
                        analysis_data_chunk["lowest_was_fba"] = result.get("lowest_was_fba")
                    if result.get("amazon_was_seller") is not None:
                        analysis_data_chunk["amazon_was_seller"] = result.get("amazon_was_seller")
                    if result.get("worst_case_profit") is not None:
                        analysis_data_chunk["worst_case_profit"] = result.get("worst_case_profit")
                    if result.get("still_profitable_at_worst") is not None:
                        analysis_data_chunk["still_profitable_at_worst"] = result.get("still_profitable_at_worst")
                    if result.get("fba_seller_count") is not None:
                        analysis_data_chunk["fba_seller_count"] = result.get("fba_seller_count")
                    if result.get("fbm_seller_count") is not None:
                        analysis_data_chunk["fbm_seller_count"] = result.get("fbm_seller_count")
                    if result.get("promo_net_profit") is not None:
                        analysis_data_chunk["promo_net_profit"] = result.get("promo_net_profit")
                    if result.get("promo_roi") is not None:
                        analysis_data_chunk["promo_roi"] = result.get("promo_roi")
                    
                    analysis_result = supabase.table("analyses").upsert(
                        analysis_data_chunk,
                        on_conflict="user_id,supplier_id,asin"
                    ).execute()
                    
                    analysis_id = analysis_result.data[0]["id"] if analysis_result.data else None
                    
                    # Update product
                    supabase.table("products").update({
                        "analysis_id": analysis_id,
                        "title": result.get("title"),
                        "image_url": result.get("image_url"),
                        "brand_name": result.get("brand"),  # Schema has brand_name, not brand
                        "sell_price": result.get("sell_price"),
                        "fees_total": result.get("fees_total"),
                        "bsr": result.get("bsr"),
                        "seller_count": result.get("seller_count"),
                        "status": "analyzed",
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", product_id).execute()
                    
                    # Update product_sources stage
                    sources_result = supabase.table("product_sources")\
                        .select("id")\
                        .eq("product_id", product_id)\
                        .execute()
                    
                    if sources_result.data:
                        source_ids = [s["id"] for s in sources_result.data]
                        supabase.table("product_sources")\
                            .update({
                                "stage": "reviewed",
                                "updated_at": datetime.utcnow().isoformat()
                            })\
                            .in_("id", source_ids)\
                            .execute()
                    
                    success_count += 1
                    progress.increment_success()
                else:
                    supabase.table("products").update({
                        "status": "error",
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", product_id).execute()
                    
                    error_count += 1
                    progress.increment_error(f"{asin}: No SP-API price")
                    
            except Exception as e:
                logger.error(f"Error saving {asin}: {e}")
                error_count += 1
                progress.increment_error(f"{asin}: {str(e)[:50]}")
        
        # Sync progress
        progress.sync_to_db()
        
        logger.info(f"✅ Chunk {chunk_index}: {success_count}/{len(product_chunk)} successful")
        return {"success": success_count, "error": error_count, "chunk_index": chunk_index}
        
    except Exception as e:
        logger.error(f"Chunk {chunk_index} failed: {e}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task
def finalize_batch(results, job_id: str):
    """Called after all chunks complete."""
    progress = AtomicJobProgress(job_id)
    progress.complete()
    logger.info(f"🏁 Batch job {job_id} fully complete")
    return {"job_id": job_id, "results": results}


@celery_app.task(bind=True, name="app.tasks.analysis.batch_analyze_parallel", queue="analysis")
def batch_analyze_parallel(self, job_id: str, user_id: str, product_ids: List[str]):
    """
    Main entry point: Split into chunks and process in parallel.
    All chunks use batch_analyzer - NO individual SP-API calls.
    """
    try:
        # Get products - batch to avoid URL length limits
        products = []
        BATCH_FETCH_SIZE = PROCESS_BATCH_SIZE
        
        for i in range(0, len(product_ids), BATCH_FETCH_SIZE):
            batch_ids = product_ids[i:i + BATCH_FETCH_SIZE]
            try:
                products_result = supabase.table("products")\
                    .select("id, asin")\
                    .eq("user_id", user_id)\
                    .in_("id", batch_ids)\
                    .execute()
                
                if products_result.data:
                    products.extend(products_result.data)
            except Exception as e:
                logger.warning(f"Failed to fetch product batch {i}-{i+len(batch_ids)}: {e}")
        
        total = len(products)
        
        logger.info(f"🚀 Starting PARALLEL batch: {total} products across {WORKERS} workers")
        logger.info(f"📊 All chunks use batch_analyzer - NO individual SP-API catalog/offers calls")
        
        if total == 0:
            supabase.table("jobs").update({
                "status": "completed",
                "progress": 100,
                "result": {"message": "No products"},
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
            return {"job_id": job_id, "message": "No products"}
        
        # Initialize progress tracking
        progress = AtomicJobProgress(job_id)
        progress.init(total)
        
        # Split into chunks
        chunk_size = max(1, (total + WORKERS - 1) // WORKERS)  # Ceiling division
        chunks = []
        for i in range(0, total, chunk_size):
            chunks.append(products[i:i + chunk_size])
        
        logger.info(f"Split into {len(chunks)} chunks of ~{chunk_size} each")
        
        # Create parallel tasks with callback
        chunk_tasks = [
            analyze_chunk.s(job_id, user_id, chunk, i) 
            for i, chunk in enumerate(chunks)
        ]
        
        # Use chord: run all chunks in parallel, then finalize
        workflow = chord(chunk_tasks)(finalize_batch.s(job_id))
        
        return {"job_id": job_id, "chunks": len(chunks), "total": total}
        
    except Exception as e:
        logger.error(f"Batch parallel failed: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        
        supabase.table("jobs").update({
            "status": "failed",
            "errors": [str(e)],
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", job_id).execute()
        raise
