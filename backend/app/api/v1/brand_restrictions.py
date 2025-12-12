"""
Brand Restrictions API - Manage brand restrictions and detection
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.api.deps import get_current_user
from app.services.brand_restriction_detector import BrandRestrictionDetector
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand-restrictions", tags=["brand-restrictions"])


class AddRestrictionRequest(BaseModel):
    brand_name: str
    restriction_type: str  # 'globally_gated', 'seller_specific', 'category_gated', 'ungated'
    category: Optional[str] = None
    notes: Optional[str] = None


class AddSupplierOverrideRequest(BaseModel):
    supplier_id: str
    brand_name: str
    override_type: str  # 'can_sell', 'cannot_sell', 'requires_approval'
    supplier_notes: Optional[str] = None


@router.post("/detect/{product_id}")
async def detect_brand_restriction(
    product_id: str,
    supplier_id: Optional[str] = Body(None),
    current_user = Depends(get_current_user)
):
    """Detect and flag brand restriction for a product."""
    user_id = str(current_user.id)
    
    try:
        # Get product
        product_result = supabase.table('products').select(
            'id, brand, product_sources(supplier_id)'
        ).eq('id', product_id).eq('user_id', user_id).limit(1).execute()
        
        if not product_result.data:
            raise HTTPException(404, "Product not found")
        
        product = product_result.data[0]
        brand_name = product.get('brand')
        
        if not brand_name:
            raise HTTPException(400, "Product has no brand name")
        
        # Get supplier_id from product_sources if not provided
        if not supplier_id and product.get('product_sources'):
            supplier_id = product.get('product_sources')[0].get('supplier_id')
        
        # Detect
        detector = BrandRestrictionDetector(user_id)
        result = await detector.detect_and_flag(product_id, brand_name, supplier_id)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Brand detection failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/global")
async def add_global_restriction(
    request: AddRestrictionRequest,
    current_user = Depends(get_current_user)
):
    """Add a brand to the global restrictions database."""
    user_id = str(current_user.id)
    
    try:
        detector = BrandRestrictionDetector(user_id)
        result = await detector.add_global_restriction(
            brand_name=request.brand_name,
            restriction_type=request.restriction_type,
            category=request.category,
            notes=request.notes
        )
        
        return {
            'success': True,
            'restriction': result
        }
    
    except Exception as e:
        logger.error(f"Failed to add restriction: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/supplier-override")
async def add_supplier_override(
    request: AddSupplierOverrideRequest,
    current_user = Depends(get_current_user)
):
    """Add supplier-specific brand override."""
    user_id = str(current_user.id)
    
    try:
        # Verify supplier belongs to user
        supplier_result = supabase.table('suppliers').select('id').eq(
            'id', request.supplier_id
        ).eq('user_id', user_id).limit(1).execute()
        
        if not supplier_result.data:
            raise HTTPException(404, "Supplier not found")
        
        # Normalize brand name
        normalized = BrandRestrictionDetector(user_id).normalize_brand_name(request.brand_name)
        
        # Check if exists
        existing = supabase.table('supplier_brand_overrides').select('id').eq(
            'supplier_id', request.supplier_id
        ).eq('brand_name_normalized', normalized).limit(1).execute()
        
        override_data = {
            'user_id': user_id,
            'supplier_id': request.supplier_id,
            'brand_name': request.brand_name,
            'brand_name_normalized': normalized,
            'override_type': request.override_type,
            'supplier_notes': request.supplier_notes
        }
        
        if existing.data:
            # Update
            result = supabase.table('supplier_brand_overrides').update(override_data).eq(
                'id', existing.data[0]['id']
            ).execute()
        else:
            # Insert
            result = supabase.table('supplier_brand_overrides').insert(override_data).execute()
        
        return {
            'success': True,
            'override': result.data[0] if result.data else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add supplier override: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/product/{product_id}")
async def get_product_brand_status(
    product_id: str,
    current_user = Depends(get_current_user)
):
    """Get brand restriction status for a product."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table('product_brand_flags').select(
            '''
            *,
            restriction:brand_restrictions(*),
            override:supplier_brand_overrides(*)
            '''
        ).eq('product_id', product_id).eq('user_id', user_id).execute()
        
        return {
            'flags': result.data or [],
            'count': len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Failed to get brand status: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/search")
async def search_restrictions(
    brand_name: Optional[str] = None,
    restriction_type: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Search brand restrictions."""
    try:
        query = supabase.table('brand_restrictions').select('*')
        
        if brand_name:
            normalized = BrandRestrictionDetector(str(current_user.id)).normalize_brand_name(brand_name)
            query = query.ilike('brand_name_normalized', f'%{normalized}%')
        
        if restriction_type:
            query = query.eq('restriction_type', restriction_type)
        
        result = query.order('brand_name').limit(100).execute()
        
        return {
            'restrictions': result.data or [],
            'count': len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))

