"""
Shipping Profiles API
Manage shipping cost profiles for suppliers.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from decimal import Decimal

from app.api.deps import get_current_user
from app.core.database import supabase

router = APIRouter(prefix="/shipping-profiles", tags=["shipping-profiles"])


class CreateShippingProfileRequest(BaseModel):
    supplier_id: str
    name: str
    cost_type: str  # flat_rate, per_pound, per_unit, tiered, percentage, free_above
    cost_params: Dict[str, Any]
    free_shipping_threshold: Optional[float] = None
    min_shipping_cost: Optional[float] = None
    max_shipping_cost: Optional[float] = None
    is_default: bool = False


class CalculateShippingRequest(BaseModel):
    order_value: float
    total_weight: float
    unit_count: int


@router.get("")
async def list_shipping_profiles(
    supplier_id: Optional[str] = Query(None),
    current_user = Depends(get_current_user)
):
    """List shipping profiles for user's suppliers."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table('shipping_cost_profiles').select('*').eq('user_id', user_id)
        if supplier_id:
            query = query.eq('supplier_id', supplier_id)
        
        result = query.order('created_at', desc=True).execute()
        
        return {"profiles": result.data or [], "count": len(result.data) if result.data else 0}
    
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("")
async def create_shipping_profile(
    request: CreateShippingProfileRequest,
    current_user = Depends(get_current_user)
):
    """Create a new shipping profile."""
    user_id = str(current_user.id)
    
    try:
        profile_data = {
            'user_id': user_id,
            'supplier_id': request.supplier_id,
            'name': request.name,
            'cost_type': request.cost_type,
            'cost_params': request.cost_params,
            'free_shipping_threshold': request.free_shipping_threshold,
            'min_shipping_cost': request.min_shipping_cost,
            'max_shipping_cost': request.max_shipping_cost,
            'is_default': request.is_default
        }
        
        result = supabase.table('shipping_cost_profiles').insert(profile_data).execute()
        
        if result.data:
            return result.data[0]
        raise HTTPException(500, "Failed to create shipping profile")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/{profile_id}/calculate")
async def calculate_shipping_cost(
    profile_id: str,
    request: CalculateShippingRequest,
    current_user = Depends(get_current_user)
):
    """Calculate shipping cost using a profile."""
    user_id = str(current_user.id)
    
    try:
        # Get profile
        profile_result = supabase.table('shipping_cost_profiles').select('*').eq(
            'id', profile_id
        ).eq('user_id', user_id).limit(1).execute()
        
        if not profile_result.data:
            raise HTTPException(404, "Shipping profile not found")
        
        profile = profile_result.data[0]
        
        # Use database function to calculate cost
        result = supabase.rpc('calculate_shipping_cost', {
            'p_profile_id': profile_id,
            'p_order_value': request.order_value,
            'p_total_weight': request.total_weight,
            'p_unit_count': request.unit_count
        }).execute()
        
        shipping_cost = float(result.data) if result.data else 0.0
        
        return {
            "profile_id": profile_id,
            "profile_name": profile.get('name'),
            "shipping_cost": shipping_cost,
            "order_value": request.order_value,
            "total_weight": request.total_weight,
            "unit_count": request.unit_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

