"""
Batch processing API - Start and track background analysis jobs.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.tasks.analysis import batch_analyze_products, batch_analyze_parallel
from pydantic import BaseModel
from typing import List, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


class BatchAnalyzeRequest(BaseModel):
    product_ids: Optional[List[str]] = None  # Specific products
    stage: Optional[str] = None  # Or all products in a stage
    analyze_all_pending: Optional[bool] = False  # Or all pending


@router.post("/analyze")
async def start_batch_analyze(
    req: BatchAnalyzeRequest,
    current_user = Depends(get_current_user)
):
    """
    Start batch analysis job.
    Options:
    - product_ids: Analyze specific products
    - stage: Analyze all products in a stage
    - analyze_all_pending: Analyze all pending products
    """
    user_id = str(current_user.id)
    
    try:
        # Determine what to analyze
        if req.product_ids:
            product_ids = req.product_ids
            job_type = "analyze_selected"
        elif req.analyze_all_pending:
            # Get all pending products (via product_deals view to get products with deals)
            # This ensures we get products that have product_sources entries
            deals = supabase.table("product_deals")\
                .select("product_id")\
                .eq("user_id", user_id)\
                .eq("product_status", "pending")\
                .execute()
            product_ids = list(set([d["product_id"] for d in (deals.data or [])]))
            
            # Also get products that don't have any product_sources yet
            all_products = supabase.table("products")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("status", "pending")\
                .execute()
            all_product_ids = [p["id"] for p in (all_products.data or [])]
            
            # Combine and deduplicate
            product_ids = list(set(product_ids + all_product_ids))
            job_type = "analyze_all_pending"
        elif req.stage:
            # Get products in stage (via product_deals)
            deals = supabase.table("product_deals")\
                .select("product_id")\
                .eq("user_id", user_id)\
                .eq("stage", req.stage)\
                .eq("product_status", "pending")\
                .execute()
            product_ids = list(set([d["product_id"] for d in (deals.data or [])]))
            job_type = f"analyze_stage_{req.stage}"
        else:
            raise HTTPException(400, "Must specify product_ids, stage, or analyze_all_pending")
        
        if not product_ids:
            raise HTTPException(400, "No products to analyze")
        
        # Check for products without suppliers
        # IMPORTANT: Only check products that don't already have suppliers
        # Products on the Products page are likely already analyzed/have suppliers
        # This check is mainly for Telegram deals (new products)
        products_with_suppliers = set()
        product_source_map = {}  # product_id -> source_detail
        BATCH_SIZE = 100
        
        for i in range(0, len(product_ids), BATCH_SIZE):
            batch_ids = product_ids[i:i + BATCH_SIZE]
            try:
                sources_result = supabase.table("product_sources")\
                    .select("product_id, supplier_id, source_detail")\
                    .in_("product_id", batch_ids)\
                    .execute()
                
                # Build map: product_id -> has_supplier
                for source in (sources_result.data or []):
                    product_id = source.get("product_id")
                    if source.get("supplier_id"):  # Not null
                        products_with_suppliers.add(product_id)
                    # Track source_detail for grouping
                    if product_id:
                        product_source_map[product_id] = source.get("source_detail")
            except Exception as e:
                logger.warning(f"Error checking suppliers for batch {i//BATCH_SIZE + 1}: {e}")
                # Continue with other batches
        
        # Find products without suppliers
        products_without_suppliers = [pid for pid in product_ids if pid not in products_with_suppliers]
        
        # FIX: Only require suppliers for products that:
        # 1. Don't have suppliers AND
        # 2. Don't have any product_sources entry (new products from Telegram)
        # If a product has a product_sources entry but no supplier_id, it's likely a manual upload
        # and should be allowed to analyze (supplier can be assigned later)
        products_requiring_suppliers = []
        for pid in products_without_suppliers:
            # Check if this product has ANY product_sources entry
            has_source = pid in product_source_map
            # Only require supplier if it's a new product (no source entry)
            # OR if it's from Telegram (has source_detail but no supplier)
            if not has_source:
                products_requiring_suppliers.append(pid)
        
        if products_requiring_suppliers:
            # Get product details with source_detail for grouping
            products_data = []
            asins = []
            
            try:
                # Fetch in batches to avoid URL length issues
                BATCH_SIZE = 100
                logger.info(f"Fetching details for {len(products_requiring_suppliers)} products requiring suppliers")
                
                for i in range(0, len(products_requiring_suppliers), BATCH_SIZE):
                    batch_ids = products_requiring_suppliers[i:i + BATCH_SIZE]
                    logger.info(f"Fetching batch {i//BATCH_SIZE + 1}: {len(batch_ids)} products")
                    
                    products_info = supabase.table("products")\
                        .select("id, asin, title")\
                        .in_("id", batch_ids)\
                        .execute()
                    
                    logger.info(f"Batch result: {len(products_info.data or [])} products returned")
                    
                    if products_info.data:
                        # Add source_detail from product_sources if available
                        for product in products_info.data:
                            product_id = product["id"]
                            product["source_detail"] = product_source_map.get(product_id)
                            products_data.append(product)
                            if product.get("asin"):
                                asins.append(product["asin"])
                    else:
                        logger.warning(f"No products returned for batch {i//BATCH_SIZE + 1}")
            except Exception as e:
                logger.error(f"Failed to fetch product details for error message: {e}", exc_info=True)
                # Continue without product details - we'll still show the error
            
            # Group products by source_detail (filename) for easier assignment
            products_by_file = {}
            ungrouped_products = []
            
            for product in products_data:
                source_detail = product.get("source_detail")
                if source_detail:
                    if source_detail not in products_by_file:
                        products_by_file[source_detail] = []
                    products_by_file[source_detail].append(product)
                else:
                    ungrouped_products.append(product)
            
            # Return structured error with grouped products
            error_data = {
                "error": "products_missing_suppliers",
                "message": f"{len(products_requiring_suppliers)} product(s) have no supplier assigned. Please assign a supplier before analyzing.",
                "count": len(products_requiring_suppliers),
                "products": products_data,
                "asins": asins,
                "grouped_by_file": products_by_file,  # Products grouped by filename
                "ungrouped": ungrouped_products  # Products without source_detail
            }
            
            logger.info(f"Raising supplier missing error: {len(products_requiring_suppliers)} products, {len(products_by_file)} files")
            raise HTTPException(
                status_code=400,
                detail=error_data
            )
        
        # Create unified job record
        job_id = str(uuid.uuid4())
        
        try:
            job_data = {
                "id": job_id,
                "user_id": user_id,
                "type": "batch_analyze",
                "status": "pending",
                "total_items": len(product_ids),
                "processed_items": 0,
                "progress": 0,
                "success_count": 0,
                "error_count": 0,
                "errors": [],  # Empty array for JSONB
                "metadata": {"job_type": job_type}  # Don't set result to None - let it be NULL in DB
            }
            
            insert_result = supabase.table("jobs").insert(job_data).execute()
            
            if not insert_result.data:
                raise HTTPException(500, "Failed to create job record")
        except Exception as db_error:
            logger.error(f"Database error creating job: {db_error}")
            error_str = str(db_error)
            # Check if table exists
            if "could not find the table" in error_str.lower() or "PGRST205" in error_str:
                raise HTTPException(500, "jobs table not found. Please run the SQL migration: database/CREATE_UNIFIED_JOBS_TABLE.sql")
            raise HTTPException(500, f"Database error: {error_str}")
        
        # Queue Celery task - use parallel for large batches
        try:
            if len(product_ids) > 100:
                # Use parallel processing for large batches
                batch_analyze_parallel.delay(job_id, user_id, product_ids)
                logger.info(f"Queued PARALLEL batch analysis: {len(product_ids)} products")
            else:
                # Use sequential for small batches
                batch_analyze_products.delay(job_id, user_id, product_ids)
                logger.info(f"Queued sequential batch analysis: {len(product_ids)} products")
        except Exception as celery_error:
            logger.error(f"Failed to queue Celery task: {celery_error}")
            # Update job status to failed
            supabase.table("jobs").update({
                "status": "failed",
                "errors": [f"Failed to queue task: {str(celery_error)}"]
            }).eq("id", job_id).execute()
            raise HTTPException(500, f"Failed to start background processing: {str(celery_error)}")
        
        return {
            "job_id": job_id,
            "message": f"Started analyzing {len(product_ids)} products",
            "total": len(product_ids)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start batch analyze: {e}", exc_info=True)
        raise HTTPException(500, str(e))


# Note: Job status endpoints are now in /api/v1/jobs
# These endpoints are kept for backward compatibility but redirect to the unified jobs API

