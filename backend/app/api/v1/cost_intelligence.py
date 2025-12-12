"""
Cost Intelligence API - Manage cost types and calculations
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
import logging

from app.api.deps import get_current_user
from app.services.cost_intelligence import CostIntelligence
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost-intelligence", tags=["cost-intelligence"])


class UpdateCostTypeRequest(BaseModel):
    product_source_id: str
    cost_type: str  # 'unit', 'pack', 'case'
    pack_size_for_cost: Optional[int] = None
    case_size: Optional[int] = None


class CalculateBreakdownRequest(BaseModel):
    wholesale_cost: float
    cost_type: str
    pack_size_for_cost: Optional[int] = None
    case_size: Optional[int] = None
    amazon_pack_size: int = 1


@router.post("/calculate-breakdown")
async def calculate_cost_breakdown(
    request: CalculateBreakdownRequest,
    current_user = Depends(get_current_user)
):
    """Calculate cost breakdown for given parameters."""
    try:
        # Validate
        is_valid, error = CostIntelligence.validate_cost_type(
            request.cost_type,
            request.pack_size_for_cost,
            request.case_size
        )
        
        if not is_valid:
            raise HTTPException(400, error)
        
        # Calculate
        breakdown = CostIntelligence.calculate_cost_breakdown(
            wholesale_cost=Decimal(str(request.wholesale_cost)),
            cost_type=request.cost_type,
            pack_size_for_cost=request.pack_size_for_cost,
            case_size=request.case_size,
            amazon_pack_size=request.amazon_pack_size
        )
        
        return breakdown
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost breakdown calculation failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/update-cost-type")
async def update_cost_type(
    request: UpdateCostTypeRequest,
    current_user = Depends(get_current_user)
):
    """Update cost type for a product source."""
    user_id = str(current_user.id)
    
    try:
        # Verify product source belongs to user
        product_source_result = supabase.table('product_sources').select(
            'id, product_id, products!inner(user_id)'
        ).eq('id', request.product_source_id).limit(1).execute()
        
        if not product_source_result.data:
            raise HTTPException(404, "Product source not found")
        
        product = product_source_result.data[0].get('products', {})
        if not product or product.get('user_id') != user_id:
            raise HTTPException(403, "Product source doesn't belong to you")
        
        # Validate
        is_valid, error = CostIntelligence.validate_cost_type(
            request.cost_type,
            request.pack_size_for_cost,
            request.case_size
        )
        
        if not is_valid:
            raise HTTPException(400, error)
        
        # Update
        update_data = {
            'cost_type': request.cost_type,
            'pack_size_for_cost': request.pack_size_for_cost,
            'case_size': request.case_size
        }
        
        result = supabase.table('product_sources').update(update_data).eq(
            'id', request.product_source_id
        ).execute()
        
        # Recalculate profitability if needed
        # (This would trigger a background job in production)
        
        return {
            'success': True,
            'product_source': result.data[0] if result.data else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update cost type: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/product-source/{product_source_id}/breakdown")
async def get_product_source_breakdown(
    product_source_id: str,
    current_user = Depends(get_current_user)
):
    """Get cost breakdown for a product source."""
    user_id = str(current_user.id)
    
    try:
        # Get product source with product and Amazon pack size
        result = supabase.table('product_sources').select(
            '''
            *,
            product:products(amazon_pack_size, item_package_quantity)
            '''
        ).eq('id', product_source_id).limit(1).execute()
        
        if not result.data:
            raise HTTPException(404, "Product source not found")
        
        product_source = result.data[0]
        product = product_source.get('product', {})
        
        # Verify ownership
        product_id = product_source.get('product_id')
        product_check = supabase.table('products').select('user_id').eq(
            'id', product_id
        ).eq('user_id', user_id).limit(1).execute()
        
        if not product_check.data:
            raise HTTPException(403, "Product doesn't belong to you")
        
        # Calculate breakdown
        wholesale_cost = Decimal(str(product_source.get('wholesale_cost', 0)))
        cost_type = product_source.get('cost_type', 'unit')
        pack_size_for_cost = product_source.get('pack_size_for_cost')
        case_size = product_source.get('case_size')
        amazon_pack_size = product.get('amazon_pack_size') or product.get('item_package_quantity') or 1
        
        breakdown = CostIntelligence.calculate_cost_breakdown(
            wholesale_cost=wholesale_cost,
            cost_type=cost_type,
            pack_size_for_cost=pack_size_for_cost,
            case_size=case_size,
            amazon_pack_size=amazon_pack_size
        )
        
        return breakdown
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get breakdown: {e}", exc_info=True)
        raise HTTPException(500, str(e))

