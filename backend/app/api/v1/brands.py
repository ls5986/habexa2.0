"""
Brands API - Manage product brands for ungating tracking.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.redis_client import cached
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brands", tags=["brands"])

# ============================================
# SCHEMAS
# ============================================

class CreateBrandRequest(BaseModel):
    name: str
    category: Optional[str] = None
    notes: Optional[str] = None

class UpdateBrandRequest(BaseModel):
    name: Optional[str] = None
    is_ungated: Optional[bool] = None
    category: Optional[str] = None
    notes: Optional[str] = None

# ============================================
# ENDPOINTS
# ============================================

@router.get("")
@cached(ttl=60)
async def get_brands(current_user = Depends(get_current_user)):
    """Get all brands for the user."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("brands")\
            .select("*, products(count)")\
            .eq("user_id", user_id)\
            .order("name")\
            .execute()
        
        brands = result.data or []
        
        # Get product counts separately (Supabase count might not work in select)
        for brand in brands:
            count_result = supabase.table("products")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .eq("brand_id", brand["id"])\
                .execute()
            brand["product_count"] = count_result.count if hasattr(count_result, 'count') else 0
        
        return {"brands": brands}
    except Exception as e:
        logger.error(f"Failed to fetch brands: {e}")
        raise HTTPException(500, str(e))

@router.get("/{brand_id}")
async def get_brand(brand_id: str, current_user = Depends(get_current_user)):
    """Get a specific brand."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("brands")\
            .select("*")\
            .eq("id", brand_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(404, "Brand not found")
        
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch brand: {e}")
        raise HTTPException(500, str(e))

@router.post("")
async def create_brand(req: CreateBrandRequest, current_user = Depends(get_current_user)):
    """Create a new brand."""
    user_id = str(current_user.id)
    
    try:
        # Check if brand already exists
        existing = supabase.table("brands")\
            .select("id")\
            .eq("user_id", user_id)\
            .ilike("name", req.name)\
            .limit(1)\
            .execute()
        
        if existing.data:
            raise HTTPException(400, f"Brand '{req.name}' already exists")
        
        result = supabase.table("brands").insert({
            "user_id": user_id,
            "name": req.name.strip(),
            "category": req.category,
            "notes": req.notes,
            "is_ungated": False
        }).execute()
        
        return result.data[0] if result.data else None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create brand: {e}")
        raise HTTPException(500, str(e))

@router.patch("/{brand_id}")
async def update_brand(brand_id: str, req: UpdateBrandRequest, current_user = Depends(get_current_user)):
    """Update a brand (e.g., mark as ungated)."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        existing = supabase.table("brands")\
            .select("id")\
            .eq("id", brand_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not existing.data:
            raise HTTPException(404, "Brand not found")
        
        update_data = {}
        if req.name is not None:
            update_data["name"] = req.name.strip()
        if req.is_ungated is not None:
            update_data["is_ungated"] = req.is_ungated
            if req.is_ungated:
                update_data["ungated_at"] = datetime.utcnow().isoformat()
        if req.category is not None:
            update_data["category"] = req.category
        if req.notes is not None:
            update_data["notes"] = req.notes
        
        if not update_data:
            raise HTTPException(400, "No fields to update")
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("brands")\
            .update(update_data)\
            .eq("id", brand_id)\
            .execute()
        
        return result.data[0] if result.data else None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update brand: {e}")
        raise HTTPException(500, str(e))

@router.delete("/{brand_id}")
async def delete_brand(brand_id: str, current_user = Depends(get_current_user)):
    """Delete a brand (only if no products use it)."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        existing = supabase.table("brands")\
            .select("id")\
            .eq("id", brand_id)\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()
        
        if not existing.data:
            raise HTTPException(404, "Brand not found")
        
        # Check if any products use this brand
        products = supabase.table("products")\
            .select("id")\
            .eq("brand_id", brand_id)\
            .limit(1)\
            .execute()
        
        if products.data:
            raise HTTPException(400, "Cannot delete brand: products are using it")
        
        supabase.table("brands")\
            .delete()\
            .eq("id", brand_id)\
            .execute()
        
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete brand: {e}")
        raise HTTPException(500, str(e))

