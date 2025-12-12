"""
Bulk product operations API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


@router.patch("/{product_id}")
async def update_product(
    product_id: str,
    updates: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a single product field (for inline editing).
    """
    try:
        # Validate product belongs to user
        product = supabase.table('products').select('id').eq(
            'id', product_id
        ).eq('user_id', current_user['id']).single().execute()
        
        if not product.data:
            raise HTTPException(404, "Product not found")
        
        # Update product
        result = supabase.table('products').update(updates).eq(
            'id', product_id
        ).eq('user_id', current_user['id']).execute()
        
        if not result.data:
            raise HTTPException(500, "Update failed")
        
        return {"success": True, "product": result.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Product update failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/bulk-hide")
async def bulk_hide_products(
    product_ids: List[str] = Body(..., embed=True, alias="product_ids"),
    current_user: dict = Depends(get_current_user)
):
    """
    Hide multiple products (set status to 'hidden').
    """
    try:
        if not product_ids:
            raise HTTPException(400, "No product IDs provided")
        
        # Update all products
        result = supabase.table('products').update({
            'status': 'hidden'
        }).in_('id', product_ids).eq('user_id', current_user['id']).execute()
        
        return {
            "success": True,
            "hidden_count": len(result.data) if result.data else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk hide failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/bulk-delete")
async def bulk_delete_products(
    product_ids: List[str] = Body(..., embed=True, alias="product_ids"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete multiple products.
    """
    try:
        if not product_ids:
            raise HTTPException(400, "No product IDs provided")
        
        # Delete products
        result = supabase.table('products').delete().in_(
            'id', product_ids
        ).eq('user_id', current_user['id']).execute()
        
        return {
            "success": True,
            "deleted_count": len(result.data) if result.data else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk delete failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/bulk-favorite")
async def bulk_favorite_products(
    product_ids: List[str] = Body(..., embed=True, alias="product_ids"),
    favorite: bool = Body(True, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Mark multiple products as favorite/unfavorite.
    """
    try:
        if not product_ids:
            raise HTTPException(400, "No product IDs provided")
        
        # Update favorite status
        result = supabase.table('products').update({
            'is_favorite': favorite
        }).in_('id', product_ids).eq('user_id', current_user['id']).execute()
        
        return {
            "success": True,
            "updated_count": len(result.data) if result.data else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk favorite failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/bulk-update-costs")
async def bulk_update_costs(
    updates: List[Dict[str, Any]] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk update costs for multiple products.
    
    Body format:
    [
      {"product_id": "uuid", "wholesale_cost": 10.99, "buy_cost": 11.50},
      {"product_id": "uuid", "pack_size": 12}
    ]
    """
    try:
        if not updates:
            raise HTTPException(400, "No updates provided")
        
        updated_count = 0
        
        for update in updates:
            product_id = update.pop('product_id')
            
            # Update product_sources table
            result = supabase.table('product_sources').update(update).eq(
                'product_id', product_id
            ).eq('user_id', current_user['id']).execute()
            
            if result.data:
                updated_count += 1
        
        return {
            "success": True,
            "updated_count": updated_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk update costs failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))

