"""
Universal API batch fetcher.

Handles 1 ASIN or 10,000 ASINs with the same code.
Intelligently batches API calls for optimal performance.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from app.services.supabase_client import supabase
from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import get_keepa_client
from app.services.api_field_extractor import (
    SPAPIExtractor,
    KeepaExtractor
)

logger = logging.getLogger(__name__)


class APIBatchFetcher:
    """
    Fetches API data in optimal batches.
    Works for 1 ASIN or 10,000 ASINs.
    """
    
    SP_API_BATCH_SIZE = 20
    KEEPA_BATCH_SIZE = 100
    
    @classmethod
    async def fetch_and_store(
        cls,
        asins: List[str],
        user_id: str,
        force_refetch: bool = False
    ) -> Dict[str, Any]:
        """
        The ONE method that does everything.
        
        Args:
            asins: List of ASINs (1 to 10,000+)
            user_id: User who owns these products
            force_refetch: Skip cache, fetch fresh data
            
        Returns:
            {
                'total': 100,
                'sp_api_success': 98,
                'sp_api_failed': 0,
                'keepa_success': 95,
                'keepa_failed': 0,
                'updated': 100,
                'errors': []
            }
        """
        start_time = datetime.utcnow()
        
        if not asins:
            logger.warning("⚠️ No ASINs provided to fetch")
            return {
                'total': 0,
                'sp_api_success': 0,
                'sp_api_failed': 0,
                'keepa_success': 0,
                'keepa_failed': 0,
                'updated': 0,
                'errors': [],
                'duration_seconds': 0
            }
        
        # Remove duplicates
        asins = list(set(asins))
        logger.info(f"📊 Unique ASINs: {len(asins)}")
        
        logger.warning(f"🔥 API BATCH FETCHER STARTED: {len(asins)} ASINs for user {user_id}")
        
        results = {
            'total': len(asins),
            'sp_api_success': 0,
            'sp_api_failed': 0,
            'keepa_success': 0,
            'keepa_failed': 0,
            'updated': 0,
            'errors': [],
            'duration_seconds': 0
        }
        
        # ============================================
        # STEP 1: FETCH SP-API CATALOG IN BATCHES OF 20
        # ============================================
        logger.info(f"📦 STEP 1/3: Fetching SP-API catalog (batches of {cls.SP_API_BATCH_SIZE})")
        sp_data = {}
        
        for i in range(0, len(asins), cls.SP_API_BATCH_SIZE):
            batch = asins[i:i + cls.SP_API_BATCH_SIZE]
            batch_num = i // cls.SP_API_BATCH_SIZE + 1
            total_batches = (len(asins) + cls.SP_API_BATCH_SIZE - 1) // cls.SP_API_BATCH_SIZE
            
            try:
                logger.info(f"  📡 SP-API Batch {batch_num}/{total_batches}: Fetching {len(batch)} ASINs")
                
                # Call SP-API batch method
                batch_response = await sp_api_client.get_catalog_items_batch(
                    asins=batch,
                    marketplace_id='ATVPDKIKX0DER',
                    rate_limit=5  # 5 req/sec limit
                )
                
                # Store each item (get_catalog_items_batch returns Dict[asin, item])
                if batch_response:
                    for asin, item in batch_response.items():
                        if asin and item:
                            sp_data[asin] = item
                            results['sp_api_success'] += 1
                
                logger.info(f"  ✅ Batch {batch_num} complete: {len(batch_response)} items")
                
                # Rate limit protection (avoid throttling)
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"  ❌ SP-API batch {batch_num} failed: {e}", exc_info=True)
                results['sp_api_failed'] += len(batch)
                results['errors'].append(f"SP-API batch {batch_num}: {str(e)}")
                
                # Continue with other batches even if one fails
                continue
        
        logger.info(f"✅ SP-API: {results['sp_api_success']}/{len(asins)} successful")
        
        # ============================================
        # 2. FETCH KEEPA IN BATCHES OF 100
        # ============================================
        logger.info(f"📦 Fetching Keepa data (batches of {cls.KEEPA_BATCH_SIZE})")
        keepa_data = {}
        
        keepa_client_instance = get_keepa_client()
        if not keepa_client_instance or not keepa_client_instance.is_configured():
            logger.warning("⚠️ Keepa not configured, skipping Keepa data fetch")
        else:
            for i in range(0, len(asins), cls.KEEPA_BATCH_SIZE):
                batch = asins[i:i + cls.KEEPA_BATCH_SIZE]
                batch_num = i // cls.KEEPA_BATCH_SIZE + 1
                total_batches = (len(asins) + cls.KEEPA_BATCH_SIZE - 1) // cls.KEEPA_BATCH_SIZE
                
                try:
                    logger.info(f"  📡 Keepa Batch {batch_num}/{total_batches}: Fetching {len(batch)} ASINs")
                    
                    # Call Keepa batch method
                    keepa_response = await keepa_client_instance.get_products_batch(
                        asins=batch,
                        days=90,
                        return_raw=True
                    )
                    
                    # Store each product
                    if keepa_response and 'products' in keepa_response:
                        products = keepa_response.get('products', [])
                        raw_response = keepa_response.get('raw_response', {})
                        
                        for product in products:
                            product_asin = product.get('asin')
                            if product_asin:
                                keepa_data[product_asin] = {
                                    'product': product,
                                    'raw_response': raw_response
                                }
                                results['keepa_success'] += 1
                                logger.debug(f"    ✓ {product_asin}: {len(str(product))} chars")
                    
                logger.info(f"  ✅ Batch {batch_num} complete: {len(products)} products")
                
                # Rate limit protection
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"  ❌ Keepa batch {batch_num} failed: {e}", exc_info=True)
                results['keepa_failed'] += len(batch)
                results['errors'].append(f"Keepa batch {batch_num}: {str(e)}")
                
                # Continue with other batches
                continue
        
        logger.warning(f"✅ KEEPA COMPLETE: {results['keepa_success']}/{len(asins)} successful")
        
        # ============================================
        # 3. EXTRACT & STORE ALL DATA
        # ============================================
        logger.info(f"💾 STEP 3/3: Extracting and storing data for {len(asins)} products")
        
        for asin in asins:
            try:
                update_data = {}
                
                # Extract SP-API data
                if asin in sp_data:
                    sp_extracted = SPAPIExtractor.extract_all(sp_data[asin])
                    update_data.update(sp_extracted)
                    update_data['sp_api_raw_response'] = sp_data[asin]
                    update_data['sp_api_last_fetched'] = datetime.utcnow().isoformat()
                
                # Extract Keepa data
                if asin in keepa_data:
                    keepa_item = keepa_data[asin]
                    product_data = keepa_item.get('product', {})
                    raw_response = keepa_item.get('raw_response', {})
                    
                    keepa_extracted = KeepaExtractor.extract_all({
                        'products': [product_data]
                    }, asin=asin)
                    
                    update_data.update(keepa_extracted)
                    update_data['keepa_raw_response'] = raw_response
                    update_data['keepa_last_fetched'] = datetime.utcnow().isoformat()
                
                # Update database
                if update_data:
                    result = supabase.table('products').update(update_data).eq(
                        'asin', asin
                    ).eq('user_id', user_id).execute()
                    
                    if result.data:
                        results['updated'] += 1
                    else:
                        logger.warning(f"⚠️ No product found to update for ASIN {asin}")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to store data for {asin}: {e}", exc_info=True)
                results['errors'].append(f"{asin}: {str(e)}")
        
        logger.info(f"🎉 COMPLETE: Updated {results['updated']}/{len(asins)} products")
        
        return results


# ============================================
# CONVENIENCE FUNCTION
# ============================================

async def fetch_api_data_for_asins(
    asins: List[str],
    user_id: str,
    force_refetch: bool = False
) -> Dict[str, Any]:
    """
    Convenience function.
    Use this everywhere - file uploads, manual refetch, etc.
    
    Args:
        asins: List of ASINs (can be 1 or 10,000+)
        user_id: User ID
        force_refetch: Skip cache (not yet implemented)
        
    Returns:
        Results dict with success/failure counts
    """
    return await APIBatchFetcher.fetch_and_store(
        asins=asins,
        user_id=user_id,
        force_refetch=force_refetch
    )

