"""
ASIN Lookup Tasks
Background processing for UPC to ASIN conversion with caching.
"""
from app.core.celery_app import celery_app
from app.services.supabase_client import supabase
from app.services.upc_converter import upc_converter
from app.tasks.base import run_async
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# UPC CACHE HELPERS
# ============================================================================

def get_cached_upcs(upcs: List[str]) -> Dict[str, Optional[str]]:
    """
    Get cached UPC to ASIN mappings.
    
    Returns:
        Dictionary mapping UPC to ASIN (or None if not found)
    """
    if not upcs:
        return {}
    
    result = supabase.table("upc_asin_cache")\
        .select("upc, asin, not_found")\
        .in_("upc", upcs)\
        .execute()
    
    cached = {}
    if result.data:
        for row in result.data:
            if row.get("not_found"):
                cached[row["upc"]] = None  # Explicitly not found
            else:
                cached[row["upc"]] = row.get("asin")
    
    return cached


def cache_upc_asin(upc: str, asin: Optional[str]):
    """
    Cache a UPC to ASIN mapping.
    
    Args:
        upc: UPC code
        asin: ASIN (or None if not found)
    """
    cache_data = {
        "upc": upc,
        "asin": asin,
        "not_found": asin is None,
        "last_lookup": datetime.utcnow().isoformat()
    }
    
    # Check if exists
    existing = supabase.table("upc_asin_cache")\
        .select("upc, lookup_count")\
        .eq("upc", upc)\
        .limit(1)\
        .execute()
    
    if existing.data:
        # Update existing
        cache_data["lookup_count"] = (existing.data[0].get("lookup_count", 0) or 0) + 1
        supabase.table("upc_asin_cache")\
            .update(cache_data)\
            .eq("upc", upc)\
            .execute()
    else:
        # Insert new
        cache_data["lookup_count"] = 1
        cache_data["first_lookup"] = datetime.utcnow().isoformat()
        supabase.table("upc_asin_cache")\
            .insert(cache_data)\
            .execute()


# ============================================================================
# ASIN LOOKUP TASK
# ============================================================================

@celery_app.task(bind=True, max_retries=2)
def process_pending_asin_lookups(self, batch_size: int = 100):
    """
    Process products that need ASIN lookup.
    
    This task:
    1. Gets products with PENDING_ ASINs or lookup_status='pending'
    2. Checks UPC cache first
    3. Looks up uncached UPCs via SP-API
    4. Updates products with ASINs
    5. Queues analysis for found ASINs
    6. Caches results
    
    Args:
        batch_size: Number of products to process per run
    """
    try:
        # Get products needing lookup
        # Priority: lookup_status='pending' or 'retry_pending', then PENDING_ ASINs
        # CRITICAL: Only get products with UPCs (can't lookup without UPC)
        # FIX: Simplified query - get products with pending lookup status OR PENDING_ ASINs
        try:
            # Try query with lookup_status first (most reliable)
            products_result = supabase.table("products")\
                .select("id, upc, asin, asin_status, lookup_status, lookup_attempts, user_id")\
                .or_('lookup_status.eq.pending,lookup_status.eq.retry_pending')\
                .not_.is_("upc", "null")\
                .neq("upc", "")\
                .limit(batch_size)\
                .execute()
            
            products = products_result.data or []
            
            # If not enough products, also get ones with PENDING_ ASINs but no lookup_status set
            if len(products) < batch_size:
                pending_asin_result = supabase.table("products")\
                    .select("id, upc, asin, asin_status, lookup_status, lookup_attempts, user_id")\
                    .like("asin", "PENDING_%")\
                    .is_("lookup_status", "null")\
                    .not_.is_("upc", "null")\
                    .neq("upc", "")\
                    .limit(batch_size - len(products))\
                    .execute()
                
                additional = pending_asin_result.data or []
                products.extend(additional)
                
                # Update these products to have lookup_status='pending'
                if additional:
                    product_ids_to_update = [p['id'] for p in additional]
                    supabase.table("products")\
                        .update({"lookup_status": "pending", "lookup_attempts": 0})\
                        .in_("id", product_ids_to_update)\
                        .execute()
                    logger.info(f"✅ Updated {len(product_ids_to_update)} products with PENDING_ ASINs to lookup_status='pending'")
        except Exception as e:
            logger.error(f"Error querying products: {e}", exc_info=True)
            # Fallback to simple query
            products_result = supabase.table("products")\
                .select("id, upc, asin, asin_status, lookup_status, lookup_attempts, user_id")\
                .like("asin", "PENDING_%")\
                .not_.is_("upc", "null")\
                .neq("upc", "")\
                .limit(batch_size)\
                .execute()
            products = products_result.data or []
        
        products = products_result.data or []
        
        if not products:
            logger.info("No products pending ASIN lookup")
            return {"processed": 0, "found": 0, "not_found": 0}
        
        logger.info(f"Processing {len(products)} products for ASIN lookup")
        
        # Extract unique UPCs
        upcs = list(set(p["upc"] for p in products if p.get("upc")))
        
        # Check cache first
        cached = get_cached_upcs(upcs)
        uncached_upcs = [u for u in upcs if u not in cached]
        
        logger.info(f"Found {len(cached)} in cache, {len(uncached_upcs)} need lookup")
        
        # Lookup uncached UPCs via SP-API (with rate limiting)
        lookups = {}
        if uncached_upcs:
            try:
                # Batch lookup (20 at a time)
                batch_size_api = 20
                for i in range(0, len(uncached_upcs), batch_size_api):
                    batch = uncached_upcs[i:i + batch_size_api]
                    logger.info(f"Looking up batch {i//batch_size_api + 1}: {len(batch)} UPCs")
                    
                    # Use run_async to call the async method
                    batch_results = run_async(upc_converter.upcs_to_asins_batch(batch))
                    lookups.update(batch_results)
                    
                    # Small delay between batches to respect rate limits
                    if i + batch_size_api < len(uncached_upcs):
                        import time
                        time.sleep(1)
                
                # Cache all results
                for upc, asin in lookups.items():
                    cache_upc_asin(upc, asin)
                
                logger.info(f"Looked up {len(lookups)} UPCs, found {sum(1 for a in lookups.values() if a)} ASINs")
                
            except Exception as e:
                logger.error(f"Error during UPC lookup: {e}", exc_info=True)
                # Continue with cached results only
        
        # Combine cached and newly looked up
        all_results = {**cached, **lookups}
        
        # Update products with ASINs
        found_count = 0
        not_found_count = 0
        products_to_analyze = []
        
        for product in products:
            upc = product.get("upc")
            product_id = product.get("id")
            user_id = product.get("user_id")
            current_attempts = product.get("lookup_attempts", 0) or 0
            
            if not upc:
                continue
            
            # Update status to "looking_up"
            supabase.table("products").update({
                "lookup_status": "looking_up",
                "lookup_attempts": current_attempts + 1
            }).eq("id", product_id).execute()
            
            asin = all_results.get(upc)
            
            if asin:
                # Found ASIN - update product
                supabase.table("products")\
                    .update({
                        "asin": asin,
                        "asin_status": "found",
                        "lookup_status": "found",
                        "asin_found_at": datetime.utcnow().isoformat(),
                        "status": "pending",  # Ready for analysis
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", product_id)\
                    .execute()
                found_count += 1
                
                # Queue for analysis
                if user_id:
                    products_to_analyze.append((product_id, user_id))
            else:
                # Not found - check retry count
                new_attempts = current_attempts + 1
                
                if new_attempts >= 3:
                    # Max retries reached
                    supabase.table("products")\
                        .update({
                            "asin_status": "not_found",
                            "lookup_status": "failed",
                            "status": "pending",  # Keep as pending for manual entry
                            "updated_at": datetime.utcnow().isoformat()
                        })\
                        .eq("id", product_id)\
                        .execute()
                    not_found_count += 1
                    logger.warning(f"❌ ASIN lookup failed after 3 attempts for product {product_id} (UPC: {upc})")
                else:
                    # Will retry next run
                    supabase.table("products")\
                        .update({
                            "lookup_status": "retry_pending",
                            "updated_at": datetime.utcnow().isoformat()
                        })\
                        .eq("id", product_id)\
                        .execute()
                    logger.info(f"⏳ Will retry ASIN lookup for product {product_id} (attempt {new_attempts}/3)")
        
        # Queue analysis for products with found ASINs
        if products_to_analyze:
            try:
                from app.tasks.analysis import batch_analyze_products
                from uuid import uuid4
                
                # Group by user_id
                from collections import defaultdict
                user_products = defaultdict(list)
                for product_id, user_id in products_to_analyze:
                    user_products[user_id].append(product_id)
                
                # Queue analysis for each user
                for user_id, product_ids in user_products.items():
                    analysis_job_id = str(uuid4())
                    supabase.table("jobs").insert({
                        "id": analysis_job_id,
                        "user_id": user_id,
                        "type": "batch_analyze",
                        "status": "pending",
                        "total_items": len(product_ids),
                        "metadata": {
                            "triggered_by": "asin_lookup_job",
                            "product_ids": product_ids
                        }
                    }).execute()
                    
                    # Queue analysis
                    batch_analyze_products.delay(analysis_job_id, user_id, product_ids)
                    logger.info(f"📊 Queued analysis for {len(product_ids)} products (user: {user_id})")
            except Exception as e:
                logger.error(f"Failed to queue analysis: {e}", exc_info=True)
        
        result = {
            "processed": len(products),
            "found": found_count,
            "not_found": not_found_count,
            "cached": len(cached),
            "looked_up": len(lookups)
        }
        
        logger.info(f"ASIN lookup complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in process_pending_asin_lookups: {e}", exc_info=True)
        return {"processed": 0, "error": str(e)}


# ============================================================================
# MANUAL ASIN LOOKUP (for specific products)
# ============================================================================

@celery_app.task(bind=True, max_retries=2)
def lookup_product_asins(self, product_ids: List[str]):
    """
    Manually trigger ASIN lookup for specific products.
    
    Args:
        product_ids: List of product IDs to lookup
    """
    try:
        # Get products with lookup fields
        products_result = supabase.table("products")\
            .select("id, upc, asin, asin_status, lookup_status, lookup_attempts, user_id")\
            .in_("id", product_ids)\
            .not_.is_("upc", "null")\
            .neq("upc", "")\
            .execute()
        
        products = products_result.data or []
        
        if not products:
            logger.warning(f"❌ No products with UPCs found for {len(product_ids)} product IDs")
            return {"processed": 0, "message": "No products with UPCs found"}
        
        logger.info(f"📦 Found {len(products)} products with UPCs out of {len(product_ids)} requested")
        
        # Extract unique UPCs
        upcs = list(set([p["upc"] for p in products if p.get("upc")]))
        logger.info(f"🔢 Extracted {len(upcs)} unique UPCs")
        
        # Check cache
        cached = get_cached_upcs(upcs)
        uncached_upcs = [u for u in upcs if u not in cached]
        
        logger.info(f"💾 Cache hit: {len(cached)}, Need lookup: {len(uncached_upcs)}")
        
        # Lookup uncached - CRITICAL FIX: Process in batches of 20 (SP-API limit)
        lookups = {}
        if uncached_upcs:
            try:
                logger.info(f"🚀 Calling SP-API for {len(uncached_upcs)} UPCs (will process in batches of 20)...")
                
                # Process in batches of 20 (SP-API limit per request)
                BATCH_SIZE = 20
                total_batches = (len(uncached_upcs) + BATCH_SIZE - 1) // BATCH_SIZE
                
                for batch_idx in range(0, len(uncached_upcs), BATCH_SIZE):
                    batch_upcs = uncached_upcs[batch_idx:batch_idx + BATCH_SIZE]
                    batch_num = (batch_idx // BATCH_SIZE) + 1
                    
                    logger.info(f"📦 Processing batch {batch_num}/{total_batches}: {len(batch_upcs)} UPCs")
                    
                    try:
                        batch_results = run_async(upc_converter.upcs_to_asins_batch(batch_upcs))
                        lookups.update(batch_results)
                        
                        batch_found = sum(1 for a in batch_results.values() if a)
                        logger.info(f"✅ Batch {batch_num} complete: {batch_found}/{len(batch_upcs)} found")
                        
                        # Cache results immediately
                        for upc, asin in batch_results.items():
                            if asin:  # Only cache successful lookups
                                cache_upc_asin(upc, asin)
                    except Exception as batch_error:
                        logger.error(f"❌ Error in batch {batch_num}: {batch_error}", exc_info=True)
                        # Mark this batch as failed but continue with next batch
                        for upc in batch_upcs:
                            lookups[upc] = None
                
                found_count = sum(1 for a in lookups.values() if a)
                logger.info(f"✅ SP-API lookup complete: {found_count}/{len(uncached_upcs)} found across {total_batches} batches")
                
            except Exception as e:
                logger.error(f"❌ Error during UPC lookup: {e}", exc_info=True)
                import traceback
                logger.error(traceback.format_exc())
        
        # Combine results
        all_results = {**cached, **lookups}
        
        # Update products with new lookup_status fields
        found_count = 0
        not_found_count = 0
        products_to_analyze = []
        
        for product in products:
            upc = product.get("upc")
            product_id = product.get("id")
            user_id = product.get("user_id")
            current_attempts = product.get("lookup_attempts", 0) or 0
            
            # Update status to "looking_up"
            supabase.table("products").update({
                "lookup_status": "looking_up",
                "lookup_attempts": current_attempts + 1
            }).eq("id", product_id).execute()
            
            asin = all_results.get(upc)
            
            if asin:
                # Found ASIN
                supabase.table("products")\
                    .update({
                        "asin": asin,
                        "asin_status": "found",
                        "lookup_status": "found",
                        "asin_found_at": datetime.utcnow().isoformat(),
                        "status": "pending",  # Ready for analysis
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", product_id)\
                    .execute()
                found_count += 1
                
                # Queue for analysis
                if user_id:
                    products_to_analyze.append((product_id, user_id))
            else:
                # Not found - check retry count
                new_attempts = current_attempts + 1
                
                if new_attempts >= 3:
                    supabase.table("products")\
                        .update({
                            "asin_status": "not_found",
                            "lookup_status": "failed",
                            "status": "pending",
                            "updated_at": datetime.utcnow().isoformat()
                        })\
                        .eq("id", product_id)\
                        .execute()
                    not_found_count += 1
                else:
                    supabase.table("products")\
                        .update({
                            "lookup_status": "retry_pending",
                            "updated_at": datetime.utcnow().isoformat()
                        })\
                        .eq("id", product_id)\
                        .execute()
        
        # Queue analysis for found ASINs
        if products_to_analyze:
            try:
                from app.tasks.analysis import batch_analyze_products
                from uuid import uuid4
                from collections import defaultdict
                
                user_products = defaultdict(list)
                for product_id, user_id in products_to_analyze:
                    user_products[user_id].append(product_id)
                
                for user_id, p_ids in user_products.items():
                    analysis_job_id = str(uuid4())
                    supabase.table("jobs").insert({
                        "id": analysis_job_id,
                        "user_id": user_id,
                        "type": "batch_analyze",
                        "status": "pending",
                        "total_items": len(p_ids),
                        "metadata": {
                            "triggered_by": "manual_asin_lookup",
                            "product_ids": p_ids
                        }
                    }).execute()
                    
                    batch_analyze_products.delay(analysis_job_id, user_id, p_ids)
                    logger.info(f"📊 Queued analysis for {len(p_ids)} products (user: {user_id})")
            except Exception as e:
                logger.error(f"Failed to queue analysis: {e}", exc_info=True)
        
        return {
            "processed": len(products),
            "found": found_count,
            "not_found": not_found_count,
            "queued_for_analysis": len(products_to_analyze)
        }
        
    except Exception as e:
        logger.error(f"Error in lookup_product_asins: {e}", exc_info=True)
        return {"processed": 0, "error": str(e)}

