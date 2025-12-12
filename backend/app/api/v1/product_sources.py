"""
Product Sources API endpoints for updating product source fields.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/product-sources", tags=["product-sources"])


@router.patch("/{product_source_id}")
async def update_product_source(
    product_source_id: str,
    updates: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a product source field (for inline editing of costs, pack size, etc.).
    """
    try:
        user_id = current_user.get('id') or current_user.get('sub')
        
        # Validate product source belongs to user
        product_source = supabase.table('product_sources').select('id, product_id').eq(
            'id', product_source_id
        ).eq('user_id', user_id).single().execute()
        
        if not product_source.data:
            raise HTTPException(404, "Product source not found")
        
        # Update product source
        result = supabase.table('product_sources').update(updates).eq(
            'id', product_source_id
        ).eq('user_id', user_id).execute()
        
        if not result.data:
            raise HTTPException(500, "Update failed")
        
        return {"success": True, "product_source": result.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Product source update failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("")
async def create_product_source(
    product_source: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new product source.
    """
    try:
        user_id = current_user.get('id') or current_user.get('sub')
        
        product_source['user_id'] = user_id
        
        result = supabase.table('product_sources').insert(product_source).execute()
        
        if not result.data:
            raise HTTPException(500, "Create failed")
        
        return {"success": True, "product_source": result.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Product source creation failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))

