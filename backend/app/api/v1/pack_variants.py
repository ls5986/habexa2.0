"""
Pack Variants API - Discover and manage pack size variants
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import logging

from app.api.deps import get_current_user
from app.services.pack_variant_discovery import PackVariantDiscovery
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pack-variants", tags=["pack-variants"])


@router.post("/discover/{product_id}")
async def discover_pack_variants(
    product_id: str,
    current_user = Depends(get_current_user)
):
    """
    Discover all pack size variants for a product.
    
    Searches:
    - SP-API variations
    - Keepa product family
    - UPC pattern matching
    
    Returns list of variants with PPU calculations.
    """
    user_id = str(current_user.id)
    
    try:
        # Get product data
        product_result = supabase.table('products').select(
            'id, asin, upc, title'
        ).eq('id', product_id).eq('user_id', user_id).limit(1).execute()
        
        if not product_result.data:
            raise HTTPException(404, "Product not found")
        
        product = product_result.data[0]
        
        # Discover variants
        discovery = PackVariantDiscovery(user_id)
        variants = await discovery.discover_variants(
            product_id=product_id,
            base_asin=product.get('asin'),
            upc=product.get('upc'),
            title=product.get('title')
        )
        
        # Store variants in database
        if variants:
            # Delete existing variants
            supabase.table('product_pack_variants').delete().eq('product_id', product_id).execute()
            
            # Insert new variants
            variant_records = []
            for variant in variants:
                variant_records.append({
                    'product_id': product_id,
                    'user_id': user_id,
                    'asin': variant.get('asin'),
                    'pack_size': variant.get('pack_size', 1),
                    'buy_box_price': variant.get('price'),
                    'profit_per_unit': variant.get('ppu', 0),
                    'is_recommended': variant.get('is_recommended', False),
                    'recommendation_reason': variant.get('recommendation_reason')
                })
            
            if variant_records:
                supabase.table('product_pack_variants').insert(variant_records).execute()
        
        return {
            'success': True,
            'variants': variants,
            'count': len(variants)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pack variant discovery failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/{product_id}")
async def get_pack_variants(
    product_id: str,
    current_user = Depends(get_current_user)
):
    """Get all pack variants for a product."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table('product_pack_variants').select(
            '''
            *,
            product:products(asin, title, image_url)
            '''
        ).eq('product_id', product_id).eq('user_id', user_id).order('profit_per_unit', desc=True).execute()
        
        return {
            'variants': result.data or [],
            'count': len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Failed to get pack variants: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/bulk-discover")
async def bulk_discover_variants(
    product_ids: List[str],
    current_user = Depends(get_current_user)
):
    """Discover variants for multiple products."""
    user_id = str(current_user.id)
    
    results = []
    errors = []
    
    discovery = PackVariantDiscovery(user_id)
    
    for product_id in product_ids:
        try:
            # Get product data
            product_result = supabase.table('products').select(
                'id, asin, upc, title'
            ).eq('id', product_id).eq('user_id', user_id).limit(1).execute()
            
            if not product_result.data:
                errors.append(f"{product_id}: Product not found")
                continue
            
            product = product_result.data[0]
            
            # Discover variants
            variants = await discovery.discover_variants(
                product_id=product_id,
                base_asin=product.get('asin'),
                upc=product.get('upc'),
                title=product.get('title')
            )
            
            # Store variants
            if variants:
                supabase.table('product_pack_variants').delete().eq('product_id', product_id).execute()
                
                variant_records = []
                for variant in variants:
                    variant_records.append({
                        'product_id': product_id,
                        'user_id': user_id,
                        'asin': variant.get('asin'),
                        'pack_size': variant.get('pack_size', 1),
                        'buy_box_price': variant.get('price'),
                        'profit_per_unit': variant.get('ppu', 0),
                        'is_recommended': variant.get('is_recommended', False),
                        'recommendation_reason': variant.get('recommendation_reason')
                    })
                
                if variant_records:
                    supabase.table('product_pack_variants').insert(variant_records).execute()
            
            results.append({
                'product_id': product_id,
                'variants_found': len(variants),
                'success': True
            })
        
        except Exception as e:
            logger.error(f"Failed to discover variants for {product_id}: {e}")
            errors.append(f"{product_id}: {str(e)}")
    
    return {
        'success': True,
        'processed': len(results),
        'errors': errors,
        'results': results
    }

