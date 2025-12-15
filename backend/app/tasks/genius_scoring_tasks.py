"""
Celery tasks for calculating Genius Scores
"""
import logging
from celery import shared_task
from datetime import datetime
from typing import List, Optional

from app.services.supabase_client import supabase
from app.services.genius_scorer import GeniusScorer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def calculate_genius_scores(
    self,
    user_id: str,
    product_ids: Optional[List[str]] = None,
    supplier_id: Optional[str] = None
):
    """
    Calculate genius scores for products.
    
    Args:
        user_id: User ID
        product_ids: Optional list of specific product IDs to score
        supplier_id: Optional supplier ID to score all products for that supplier
    
    Returns:
        dict with count of products scored
    """
    try:
        scorer = GeniusScorer()
        scored_count = 0
        error_count = 0
        
        # Build query
        query = supabase.table('products').select('*').eq('user_id', user_id)
        
        if product_ids:
            query = query.in_('id', product_ids)
        elif supplier_id:
            # Get products for this supplier via product_sources
            product_sources = supabase.table('product_sources').select('product_id').eq(
                'supplier_id', supplier_id
            ).eq('user_id', user_id).execute()
            
            if product_sources.data:
                product_ids_list = [ps['product_id'] for ps in product_sources.data]
                query = query.in_('id', product_ids_list)
        
        # Get products
        products_response = query.execute()
        products = products_response.data or []
        
        logger.info(f"Calculating genius scores for {len(products)} products (user: {user_id})")
        
        for product in products:
            try:
                # Get product source data
                product_source_response = supabase.table('product_sources').select('*').eq(
                    'product_id', product['id']
                ).eq('user_id', user_id).limit(1).execute()
                
                product_source = product_source_response.data[0] if product_source_response.data else {}
                
                # Prepare product data
                product_data = {
                    'roi': product.get('roi', 0) or product_source.get('roi', 0),
                    'profit_per_unit': product.get('profit_per_unit', 0) or product_source.get('profit_per_unit', 0),
                    'margin': product.get('margin', 0) or product_source.get('margin', 0),
                    'is_brand_restricted': product.get('is_brand_restricted', False),
                    'order_quantity': 100  # Default
                }
                
                # Get Keepa data (from products table or separate)
                keepa_data = product.get('keepa_raw_response', {}) or {}
                if isinstance(keepa_data, str):
                    import json
                    try:
                        keepa_data = json.loads(keepa_data)
                    except:
                        keepa_data = {}
                
                # Get SP-API data
                sp_api_data = {
                    'sales_rank': product.get('current_sales_rank', 999999),
                    'category': product.get('category', 'default'),
                    'fba_seller_count': product.get('fba_seller_count', 0),
                    'is_hazmat': product.get('is_hazmat', False)
                }
                
                # User config (defaults)
                user_config = {
                    'min_roi': 25,
                    'max_fba_sellers': 30,
                    'handles_hazmat': False
                }
                
                # Calculate score
                result = scorer.calculate_genius_score(
                    product_data=product_data,
                    keepa_data=keepa_data,
                    sp_api_data=sp_api_data,
                    user_config=user_config
                )
                
                # Update product with score
                update_data = {
                    'genius_score': result['total_score'],
                    'genius_grade': result['grade'],
                    'genius_breakdown': result['breakdown'],
                    'genius_insights': result['insights'],
                    'genius_score_last_calculated': datetime.utcnow().isoformat()
                }
                
                supabase.table('products').update(update_data).eq('id', product['id']).execute()
                
                scored_count += 1
                
                if scored_count % 100 == 0:
                    logger.info(f"Scored {scored_count} products so far...")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error scoring product {product.get('id')}: {e}", exc_info=True)
                continue
        
        logger.info(f"Genius scoring complete: {scored_count} scored, {error_count} errors")
        
        return {
            'scored_count': scored_count,
            'error_count': error_count,
            'total_products': len(products)
        }
    
    except Exception as e:
        logger.error(f"Failed to calculate genius scores: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def refresh_genius_scores_daily(self, user_id: str):
    """
    Daily task to refresh genius scores for all products.
    Should run after inventory sync and API data refresh.
    """
    logger.info(f"Starting daily genius score refresh for user {user_id}")
    
    try:
        result = calculate_genius_scores.delay(user_id=user_id)
        return result
    
    except Exception as e:
        logger.error(f"Failed to refresh genius scores: {e}", exc_info=True)
        raise self.retry(exc=e)

