"""
API Storage Service

Manages fetching and storing complete API data (SP-API + Keepa).
Implements caching to avoid duplicate API calls.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from app.services.supabase_client import supabase
from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import get_keepa_client
from app.services.api_data_extractor import (
    should_refresh_sp_data,
    should_refresh_keepa_data
)
from app.services.api_field_extractor import (
    SPAPIExtractor,
    KeepaExtractor
)

logger = logging.getLogger(__name__)


async def fetch_and_store_sp_api_data(asin: str, user_id: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch product details from SP-API and store everything.
    Checks cache first to avoid duplicate API calls.
    
    Args:
        asin: Product ASIN
        user_id: User ID (optional, will try to find from existing product if not provided)
        force_refresh: Force fresh API call even if cached data exists
    
    Returns: Dict with all extracted data + raw response
    """
    # Get user_id if not provided (find from existing product)
    if not user_id:
        try:
            existing = supabase.table('products')\
                .select('user_id')\
                .eq('asin', asin)\
                .limit(1)\
                .execute()
            if existing.data and len(existing.data) > 0:
                user_id = existing.data[0].get('user_id')
        except:
            pass
    
    if not user_id:
        logger.warning(f"⚠️ No user_id provided and couldn't find existing product for {asin}")
        return {}
    
    # Check if we already have fresh data
    if not force_refresh:
        try:
            existing = supabase.table('products')\
                .select('*')\
                .eq('asin', asin)\
                .eq('user_id', user_id)\
                .limit(1)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                product = existing.data[0]
                if not should_refresh_sp_data(product):
                    age_hours = _get_data_age_hours(product.get('sp_api_last_fetched'))
                    logger.info(f"✅ Using cached SP-API data for {asin} (age: {age_hours:.1f}h)")
                    return product
        except Exception as e:
            logger.warning(f"Error checking SP-API cache: {e}")
    
    # Make the API call
    logger.info(f"📡 Fetching fresh SP-API data for {asin}")
    try:
        # Use get_catalog_item to get full product data
        sp_response = await sp_api_client.get_catalog_item(asin, marketplace_id="ATVPDKIKX0DER")
        
        if not sp_response:
            logger.warning(f"⚠️ No SP-API data returned for {asin}")
            return {}
        
        # get_catalog_item returns the item directly
        item = sp_response
        
        # Extract ALL fields using comprehensive extractor
        extracted = SPAPIExtractor.extract_all(item)
        
        # Add raw response and metadata
        product_data = {
            'sp_api_raw_response': item,
            'sp_api_last_fetched': datetime.utcnow().isoformat(),
            'asin': asin,
            'user_id': user_id,
            **extracted  # All extracted fields
        }  # ✅ CRITICAL: Include user_id for proper updates
        
        # ✅ Update existing product by (user_id, asin) - this ensures we update the right product
        result = supabase.table('products')\
            .update(product_data)\
            .eq('asin', asin)\
            .eq('user_id', user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"✅ Stored complete SP-API data for {asin} (raw response + structured fields)")
            return result.data[0]
        else:
            # Product might not exist yet - log warning but return the data we have
            logger.warning(f"⚠️ Product {asin} not found for user {user_id} - data extracted but not stored")
            return product_data
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch SP-API data for {asin}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


async def fetch_and_store_keepa_data(asin: str, user_id: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch data from Keepa API and store everything.
    Checks cache first to avoid duplicate API calls.
    
    Args:
        asin: Product ASIN
        user_id: User ID (optional, will try to find from existing product if not provided)
        force_refresh: Force fresh API call even if cached data exists
    
    Returns: Dict with all extracted data + raw response
    """
    # Get user_id if not provided (find from existing product)
    if not user_id:
        try:
            existing = supabase.table('products')\
                .select('user_id')\
                .eq('asin', asin)\
                .limit(1)\
                .execute()
            if existing.data and len(existing.data) > 0:
                user_id = existing.data[0].get('user_id')
        except:
            pass
    
    if not user_id:
        logger.warning(f"⚠️ No user_id provided and couldn't find existing product for {asin}")
        return {}
    
    # Check if we already have fresh data
    if not force_refresh:
        try:
            existing = supabase.table('products')\
                .select('*')\
                .eq('asin', asin)\
                .eq('user_id', user_id)\
                .limit(1)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                product = existing.data[0]
                if not should_refresh_keepa_data(product):
                    age_hours = _get_data_age_hours(product.get('keepa_last_fetched'))
                    logger.info(f"✅ Using cached Keepa data for {asin} (age: {age_hours:.1f}h)")
                    return product
        except Exception as e:
            logger.warning(f"Error checking Keepa cache: {e}")
    
    # Make the API call
    logger.info(f"📡 Fetching fresh Keepa data for {asin}")
    try:
        keepa_client = get_keepa_client()
        
        if not keepa_client.is_configured():
            logger.warning(f"⚠️ Keepa not configured, skipping")
            return {}
        
        # Get product data with raw response
        keepa_response = await keepa_client.get_products_batch([asin], days=90, return_raw=True)
        
        if not keepa_response or 'raw_response' not in keepa_response:
            logger.warning(f"⚠️ No Keepa data returned for {asin}")
            return {}
        
        # Get the raw API response for storage
        raw_response = keepa_response['raw_response']
        products = keepa_response.get('products', [])
        
        if not products or len(products) == 0:
            logger.warning(f"⚠️ No products in Keepa response for {asin}")
            return {}
        
        # Get the product data (first product should be our ASIN)
        product_data = products[0]
        
        # Extract ALL fields using comprehensive extractor
        # Construct response structure for extractor (expects {'products': [...]})
        response_for_extractor = {'products': [product_data]}
        extracted = KeepaExtractor.extract_all(response_for_extractor, asin=asin)
        
        # Add raw response and metadata
        structured_data = {
            'keepa_raw_response': raw_response,  # Full API response
            'keepa_last_fetched': datetime.utcnow().isoformat(),
            'asin': asin,
            'user_id': user_id,
            **extracted  # All extracted fields
        }  # ✅ CRITICAL: Include user_id for proper updates
        
        # ✅ Update existing product by (user_id, asin) - this ensures we update the right product
        result = supabase.table('products')\
            .update(structured_data)\
            .eq('asin', asin)\
            .eq('user_id', user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"✅ Stored complete Keepa data for {asin} (raw response + structured fields)")
            return result.data[0]
        else:
            # Product might not exist yet - log warning but return the data we have
            logger.warning(f"⚠️ Product {asin} not found for user {user_id} - data extracted but not stored")
            return structured_data
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch Keepa data for {asin}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


async def fetch_and_store_all_api_data(asin: str, user_id: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch and store data from BOTH SP-API and Keepa.
    This is the main function to call when you need complete product data.
    
    Args:
        asin: Product ASIN
        user_id: User ID (optional, will try to find from existing product if not provided)
        force_refresh: Force fresh API call even if cached data exists
    
    Returns: Merged dict with all data from both APIs
    """
    # Get user_id if not provided
    if not user_id:
        try:
            existing = supabase.table('products')\
                .select('user_id')\
                .eq('asin', asin)\
                .limit(1)\
                .execute()
            if existing.data and len(existing.data) > 0:
                user_id = existing.data[0].get('user_id')
        except:
            pass
    
    if not user_id:
        logger.warning(f"⚠️ No user_id provided and couldn't find existing product for {asin}")
        return {}
    
    logger.info(f"🔍 Fetching complete API data for {asin} (user_id={user_id}, force_refresh={force_refresh})")
    
    # Fetch both in parallel
    import asyncio
    sp_data, keepa_data = await asyncio.gather(
        fetch_and_store_sp_api_data(asin, user_id=user_id, force_refresh=force_refresh),
        fetch_and_store_keepa_data(asin, user_id=user_id, force_refresh=force_refresh),
        return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(sp_data, Exception):
        logger.error(f"❌ SP-API fetch failed: {sp_data}")
        sp_data = {}
    if isinstance(keepa_data, Exception):
        logger.error(f"❌ Keepa fetch failed: {keepa_data}")
        keepa_data = {}
    
    # Merge data (keepa takes precedence for overlapping fields)
    merged = {**sp_data, **keepa_data}
    merged['asin'] = asin
    merged['user_id'] = user_id
    
    return merged


def _get_data_age_hours(last_fetched: Optional[str]) -> float:
    """Calculate age of data in hours."""
    if not last_fetched:
        return float('inf')
    
    try:
        if isinstance(last_fetched, str):
            last_fetched = last_fetched.replace('Z', '+00:00')
        last_fetched_dt = datetime.fromisoformat(last_fetched)
        age_hours = (datetime.utcnow() - last_fetched_dt.replace(tzinfo=None)).total_seconds() / 3600
        return age_hours
    except Exception:
        return float('inf')

