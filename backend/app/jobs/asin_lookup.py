"""
Background job to process ASIN lookups and retries.

Runs periodically to find ASINs for products with UPCs.
Uses Celery workers for async processing.
"""
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def trigger_asin_lookup_job(batch_size: int = 100):
    """
    Trigger Celery task for ASIN lookup.
    This is a wrapper that can be called from scheduler or API endpoints.
    """
    from app.tasks.asin_lookup import process_pending_asin_lookups
    
    # Queue Celery task
    task = process_pending_asin_lookups.delay(batch_size)
    logger.info(f"✅ Queued ASIN lookup Celery task: {task.id} (batch_size={batch_size})")
    return task.id

def trigger_product_asin_lookup(product_ids: List[str]):
    """
    Trigger Celery task for specific products.
    """
    from app.tasks.asin_lookup import lookup_product_asins
    
    # Queue Celery task
    task = lookup_product_asins.delay(product_ids)
    logger.info(f"✅ Queued product ASIN lookup Celery task: {task.id} ({len(product_ids)} products)")
    return task.id

# Legacy async function for compatibility (now just triggers Celery)
async def process_pending_asin_lookups():
    """
    Process all products pending ASIN lookup.
    Runs every 30 minutes.
    """
    from app.services.supabase_client import supabase
    from app.services.upc_converter import upc_converter
    
    try:
        # Find products with PENDING_ ASINs that need lookup
        result = supabase.table('products') \
            .select('id, upc, asin, title, user_id, lookup_attempts') \
            .or_('asin.like.PENDING_%,asin.like.Unknown%,asin.is.null') \
            .not_.is_('upc', 'null') \
            .neq('upc', '') \
            .limit(100) \
            .execute()
        
        products = result.data or []
        logger.info(f"🔍 Found {len(products)} products pending ASIN lookup")
        
        if not products:
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for product in products:
            try:
                product_id = product['id']
                upc = product['upc']
                user_id = product['user_id']
                current_attempts = product.get('lookup_attempts', 0) or 0
                
                # Skip if no UPC
                if not upc or len(str(upc).strip()) < 10:
                    skipped_count += 1
                    continue
                
                # Update status to "looking_up"
                supabase.table('products').update({
                    'lookup_status': 'looking_up',
                    'lookup_attempts': current_attempts + 1
                }).eq('id', product_id).execute()
                
                # Try ASIN lookup
                logger.info(f"🔎 Looking up ASIN for UPC: {upc} (attempt {current_attempts + 1}/3)")
                
                # Use the upc_converter service
                try:
                    asin_result, status = await upc_converter.upc_to_asins(str(upc).strip())
                    
                    # Handle result
                    if status == "found" and asin_result and len(asin_result) > 0:
                        # Get the first ASIN (or best match)
                        asin = asin_result[0].get('asin') if isinstance(asin_result[0], dict) else asin_result[0]
                        
                        if asin and not str(asin).startswith('PENDING') and not str(asin).startswith('Unknown'):
                            # Success! Update product
                            supabase.table('products').update({
                                'asin': asin,
                                'lookup_status': 'found',
                                'status': 'pending',  # Ready for analysis
                                'asin_found_at': datetime.utcnow().isoformat()
                            }).eq('id', product_id).execute()
                            
                            success_count += 1
                            logger.info(f"✅ Found ASIN {asin} for UPC {upc}")
                            
                            # Queue for analysis
                            try:
                                from app.tasks.analysis import batch_analyze_products
                                from uuid import uuid4
                                
                                # Create analysis job
                                analysis_job_id = str(uuid4())
                                supabase.table("jobs").insert({
                                    "id": analysis_job_id,
                                    "user_id": user_id,
                                    "type": "batch_analyze",
                                    "status": "pending",
                                    "total_items": 1,
                                    "metadata": {
                                        "triggered_by": "asin_lookup_job",
                                        "product_id": product_id
                                    }
                                }).execute()
                                
                                # Queue analysis
                                batch_analyze_products.delay(analysis_job_id, user_id, [product_id])
                                logger.info(f"📊 Queued product {product_id} for analysis")
                            except Exception as e:
                                logger.error(f"Failed to queue analysis for {product_id}: {e}")
                        else:
                            # Invalid ASIN result
                            raise ValueError(f"Invalid ASIN result: {asin}")
                    elif status == "multiple" and asin_result and len(asin_result) > 1:
                        # Multiple ASINs found - user needs to choose
                        # Store potential ASINs and mark for selection
                        supabase.table('products').update({
                            'lookup_status': 'multiple_found',
                            'potential_asins': asin_result,
                            'status': 'needs_selection'
                        }).eq('id', product_id).execute()
                        logger.info(f"⚠️ Multiple ASINs found for UPC {upc} - user must choose")
                        skipped_count += 1
                    else:
                        # Not found
                        raise ValueError(f"ASIN not found for UPC {upc}")
                        
                except Exception as lookup_error:
                    logger.warning(f"ASIN lookup failed for UPC {upc}: {lookup_error}")
                    
                    # Failed - check retry count
                    new_attempts = current_attempts + 1
                    
                    if new_attempts >= 3:
                        # Max retries reached - mark as manual entry
                        supabase.table('products').update({
                            'lookup_status': 'failed',
                            'status': 'pending'  # Keep as pending for manual entry
                        }).eq('id', product_id).execute()
                        logger.warning(f"❌ ASIN lookup failed after 3 attempts for UPC {upc}")
                        failed_count += 1
                    else:
                        # Will retry next run
                        supabase.table('products').update({
                            'lookup_status': 'retry_pending'
                        }).eq('id', product_id).execute()
                        logger.info(f"⏳ Will retry ASIN lookup for UPC {upc} (attempt {new_attempts}/3)")
                        skipped_count += 1
                
                # Rate limiting - wait between lookups
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing product {product.get('id')}: {e}", exc_info=True)
                failed_count += 1
        
        logger.info(f"✅ ASIN lookup job complete: {success_count} success, {failed_count} failed, {skipped_count} skipped")
        return {'success': success_count, 'failed': failed_count, 'skipped': skipped_count}
        
    except Exception as e:
        logger.error(f"Error in ASIN lookup job: {e}", exc_info=True)
        return {'success': 0, 'failed': 0, 'skipped': 0, 'error': str(e)}

