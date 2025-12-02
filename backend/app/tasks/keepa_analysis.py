"""
Celery tasks for Keepa analysis when products reach TOP PRODUCTS stage.
Supports both single product and batch processing.
"""
import asyncio
import logging
from celery import Task
from typing import List, Dict, Any
from app.core.celery_app import celery_app
from app.services.supabase_client import supabase
from app.services.keepa_analysis_service import keepa_analysis_service
from datetime import datetime

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async code in sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, name="app.tasks.keepa_analysis.analyze_top_product", queue="analysis")
def analyze_top_product(self: Task, product_source_id: str, asin: str, user_id: str):
    """
    Run Keepa analysis when a product reaches TOP PRODUCTS stage.
    
    Args:
        product_source_id: ID of the product_source record
        asin: Product ASIN
        user_id: User ID
    """
    try:
        logger.info(f"🔍 Starting Keepa analysis for {asin} (product_source: {product_source_id})")
        
        # Run Keepa analysis
        analysis = run_async(keepa_analysis_service.analyze_product(asin))
        
        if not analysis:
            raise ValueError("Keepa analysis returned no data")
        
        # Get product data for profit calculation
        product_result = supabase.table("products")\
            .select("id, sell_price, fees_total")\
            .eq("asin", asin)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        product_source_result = supabase.table("product_sources")\
            .select("buy_cost, moq")\
            .eq("id", product_source_id)\
            .single()\
            .execute()
        
        product = product_result.data if product_result.data else {}
        product_source = product_source_result.data if product_source_result.data else {}
        
        # Calculate worst-case profit
        lowest_fba = analysis.get("lowest_fba_price_12m")
        supplier_cost = product_source.get("buy_cost", 0) or 0
        fba_fees = product.get("fees_total", 0) or 0
        
        if lowest_fba:
            worst_case = keepa_analysis_service.calculate_worst_case_profit(
                lowest_fba_price=lowest_fba,
                supplier_cost=supplier_cost,
                fba_fees=fba_fees
            )
            analysis["worst_case_analysis"] = worst_case
            
            # Update keepa_analysis table with worst-case data
            supabase.table("keepa_analysis")\
                .update({
                    "worst_case_profit": worst_case.get("worst_case_profit"),
                    "worst_case_margin": worst_case.get("worst_case_margin"),
                    "still_profitable": worst_case.get("still_profitable"),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("asin", asin)\
                .execute()
        
        # Link analysis to product_source
        supabase.table("product_sources")\
            .update({
                "keepa_analyzed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", product_source_id)\
            .execute()
        
        logger.info(f"✅ Keepa analysis complete for {asin}")
        return {
            "success": True,
            "asin": asin,
            "product_source_id": product_source_id,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error in Keepa analysis for {asin}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds


@celery_app.task(bind=True, max_retries=2, name="app.tasks.keepa_analysis.batch_analyze_top_products", queue="analysis")
def batch_analyze_top_products(self: Task, product_source_ids: List[str], user_id: str):
    """
    Batch Keepa analysis for multiple products in TOP PRODUCTS stage.
    More efficient than individual tasks - processes multiple products together.
    
    Args:
        product_source_ids: List of product_source IDs
        user_id: User ID
    """
    try:
        logger.info(f"🔍 Starting batch Keepa analysis for {len(product_source_ids)} products")
        
        # Get all product_source and product data in one query
        deals_result = supabase.table("product_sources")\
            .select("id, product_id, buy_cost, moq, products!inner(id, asin, user_id, sell_price, fees_total)")\
            .in_("id", product_source_ids)\
            .eq("products.user_id", user_id)\
            .execute()
        
        if not deals_result.data:
            logger.warning("No product sources found for batch Keepa analysis")
            return {"success": False, "message": "No products found"}
        
        results = {
            "total": len(deals_result.data),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        # Process each product
        for deal_data in deals_result.data:
            try:
                product = deal_data.get("products", {})
                if not isinstance(product, dict):
                    results["failed"] += 1
                    results["errors"].append(f"Invalid product data for deal {deal_data.get('id')}")
                    continue
                
                asin = product.get("asin")
                product_source_id = deal_data.get("id")
                
                if not asin:
                    results["failed"] += 1
                    results["errors"].append(f"No ASIN for deal {product_source_id}")
                    continue
                
                logger.info(f"🔍 Analyzing {asin} (deal: {product_source_id})")
                
                # Run Keepa analysis
                analysis = run_async(keepa_analysis_service.analyze_product(asin))
                
                if not analysis:
                    results["failed"] += 1
                    results["errors"].append(f"Keepa analysis returned no data for {asin}")
                    continue
                
                # Calculate worst-case profit
                lowest_fba = analysis.get("lowest_fba_price_12m")
                supplier_cost = deal_data.get("buy_cost", 0) or 0
                fba_fees = product.get("fees_total", 0) or 0
                
                if lowest_fba:
                    worst_case = keepa_analysis_service.calculate_worst_case_profit(
                        lowest_fba_price=lowest_fba,
                        supplier_cost=supplier_cost,
                        fba_fees=fba_fees
                    )
                    analysis["worst_case_analysis"] = worst_case
                    
                    # Update keepa_analysis table
                    supabase.table("keepa_analysis")\
                        .update({
                            "worst_case_profit": worst_case.get("worst_case_profit"),
                            "worst_case_margin": worst_case.get("worst_case_margin"),
                            "still_profitable": worst_case.get("still_profitable"),
                            "updated_at": datetime.utcnow().isoformat()
                        })\
                        .eq("asin", asin)\
                        .execute()
                
                # Link analysis to product_source
                supabase.table("product_sources")\
                    .update({
                        "keepa_analyzed_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", product_source_id)\
                    .execute()
                
                results["successful"] += 1
                logger.info(f"✅ Keepa analysis complete for {asin}")
                
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Error analyzing {deal_data.get('id', 'unknown')}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                # Continue with next product instead of failing entire batch
        
        logger.info(f"✅ Batch Keepa analysis complete: {results['successful']}/{results['total']} successful")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch Keepa analysis: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)

