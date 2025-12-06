"""
Product data service with fallback chain.
Priority: SP-API Catalog > Keepa > Placeholder
"""
import logging
from typing import Optional, Dict
from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import keepa_client
from app.cache import cache

logger = logging.getLogger(__name__)

PLACEHOLDER_IMAGE = "https://via.placeholder.com/500x500?text=No+Image"


class ProductDataService:
    """
    Fetch product data with fallback chain.
    """
    
    async def get_product_data(self, asin: str, retries: int = 3) -> Dict:
        """
        Get product data with fallback chain and retries.
        
        Priority:
        1. SP-API Catalog (most authoritative)
        2. Keepa (good for historical data)
        3. Placeholder (last resort)
        
        Returns complete product data with all fields populated.
        """
        
        result = {
            'asin': asin,
            'title': None,
            'brand': None,
            'image': None,
            'category': None,
            'bsr': None,
            'data_source': None
        }
        
        # Check cache first
        cache_key = f"product_data:{asin}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"✅ Cache hit for product_data:{asin}")
            return cached_data
        
        # Also check catalog cache
        catalog_cache_key = f"catalog:{asin}"
        cached_catalog = cache.get(catalog_cache_key)
        if cached_catalog:
            logger.info(f"✅ Cache hit for catalog:{asin}")
        
        # Try SP-API Catalog first
        catalog_data = None
        for attempt in range(retries):
            try:
                logger.info(f"📡 Fetching from SP-API Catalog (attempt {attempt + 1}/{retries}): {asin}")
                
                # Check if get_catalog_item exists, otherwise use get_catalog_items_batch
                if hasattr(sp_api_client, 'get_catalog_item'):
                    catalog_data = await sp_api_client.get_catalog_item(asin)
                elif hasattr(sp_api_client, 'get_catalog_items_batch'):
                    batch_result = await sp_api_client.get_catalog_items_batch([asin])
                    catalog_data = batch_result.get(asin) if batch_result else None
                else:
                    # Fallback: try to get from batch_analyzer or other service
                    logger.warning(f"No catalog method found in sp_api_client")
                    break
                
                if catalog_data:
                    result['title'] = catalog_data.get('title') or catalog_data.get('productTitle')
                    result['brand'] = catalog_data.get('brand') or catalog_data.get('brandName')
                    
                    # Handle image - could be in various formats
                    images = catalog_data.get('images', [])
                    if isinstance(images, list) and len(images) > 0:
                        # Get main image
                        main_image = images[0] if isinstance(images[0], str) else images[0].get('url') or images[0].get('link')
                        result['image'] = main_image
                    elif isinstance(images, dict):
                        # Could be structured like {'main': {...}, 'variants': [...]}
                        main = images.get('main') or images.get('MAIN')
                        if main:
                            result['image'] = main.get('url') or main.get('link') or main if isinstance(main, str) else None
                    
                    result['category'] = catalog_data.get('category') or catalog_data.get('categoryName')
                    result['bsr'] = catalog_data.get('salesRank') or catalog_data.get('bsr')
                    result['data_source'] = 'sp_api_catalog'
                    
                    logger.info(f"✅ Got data from SP-API Catalog")
                    
                    # If we have all critical fields, cache and return
                    if result['title'] and result['image']:
                        cache.set(cache_key, result, ttl=86400)  # 24 hours
                        return result
                    break
                    
            except Exception as e:
                logger.warning(f"⚠️ SP-API Catalog attempt {attempt + 1} failed for {asin}: {e}")
                if attempt < retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All SP-API Catalog attempts failed for {asin}")
        
        # Fallback to Keepa if catalog missing data
        try:
            logger.info(f"📊 Fetching from Keepa: {asin}")
            keepa_data = await keepa_client.get_product(asin)
            
            if keepa_data:
                # Fill in missing fields from Keepa
                if not result['title']:
                    result['title'] = keepa_data.get('title')
                
                if not result['brand']:
                    result['brand'] = keepa_data.get('brand')
                
                if not result['image']:
                    images = keepa_data.get('imagesCSV', [])
                    if isinstance(images, list) and len(images) > 0:
                        result['image'] = images[0] if isinstance(images[0], str) else images[0].get('url')
                    elif isinstance(images, str):
                        # Comma-separated string
                        result['image'] = images.split(',')[0] if images else None
                
                if not result['category']:
                    category_tree = keepa_data.get('categoryTree', [])
                    if category_tree:
                        result['category'] = category_tree[-1] if isinstance(category_tree[-1], str) else category_tree[-1].get('name')
                
                if not result['bsr']:
                    stats = keepa_data.get('stats', {})
                    if stats and stats.get('current'):
                        result['bsr'] = stats['current'].get(3)  # BSR is at index 3
                
                if not result['data_source']:
                    result['data_source'] = 'keepa'
                else:
                    result['data_source'] = 'sp_api_catalog+keepa'
                
                logger.info(f"✅ Got additional data from Keepa")
                
        except Exception as e:
            logger.warning(f"⚠️ Keepa failed for {asin}: {e}")
        
        # Final fallback to placeholders
        if not result['title']:
            result['title'] = f"Product {asin}"
            logger.warning(f"⚠️ No title found, using placeholder")
        
        if not result['image']:
            result['image'] = PLACEHOLDER_IMAGE
            logger.warning(f"⚠️ No image found, using placeholder")
        
        if not result['data_source']:
            result['data_source'] = 'placeholder'
        
        # Cache even placeholder data (shorter TTL)
        cache.set(cache_key, result, ttl=3600)  # 1 hour for placeholder data
        
        return result
    
    async def get_product_data_batch(self, asins: list[str]) -> Dict[str, Dict]:
        """
        Fetch data for multiple ASINs in parallel with fallback chain.
        """
        import asyncio
        
        results = await asyncio.gather(*[
            self.get_product_data(asin) for asin in asins
        ], return_exceptions=True)
        
        # Convert to dict, handling exceptions
        data_dict = {}
        for asin, result in zip(asins, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to get data for {asin}: {result}")
                data_dict[asin] = {
                    'asin': asin,
                    'title': f"Product {asin}",
                    'image': PLACEHOLDER_IMAGE,
                    'data_source': 'error'
                }
            else:
                data_dict[asin] = result
        
        return data_dict


# Singleton instance
product_data_service = ProductDataService()

