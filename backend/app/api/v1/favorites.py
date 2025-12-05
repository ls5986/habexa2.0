"""
Favorites API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/favorites", tags=["favorites"])


class FavoriteCreate(BaseModel):
    product_id: str
    asin: Optional[str] = None
    notes: Optional[str] = None


@router.post("")
async def add_favorite(
    data: FavoriteCreate,
    current_user = Depends(get_current_user)
):
    """Add product to favorites."""
    user_id = str(current_user.id)
    
    try:
        # Check if already exists
        existing = supabase.table("favorites")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("product_id", data.product_id)\
            .limit(1)\
            .execute()
        
        if existing.data:
            raise HTTPException(status_code=400, detail="Product already in favorites")
        
        # Create favorite
        favorite = supabase.table("favorites").insert({
            "user_id": user_id,
            "product_id": data.product_id,
            "asin": data.asin,
            "notes": data.notes or ""
        }).execute()
        
        if favorite.data:
            return {
                "message": "Added to favorites",
                "id": favorite.data[0]["id"]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create favorite")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}")
async def remove_favorite(
    product_id: str,
    current_user = Depends(get_current_user)
):
    """Remove product from favorites."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("favorites")\
            .delete()\
            .eq("user_id", user_id)\
            .eq("product_id", product_id)\
            .execute()
        
        return {"message": "Removed from favorites"}
        
    except Exception as e:
        logger.error(f"Error removing favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{product_id}")
async def check_favorite(
    product_id: str,
    current_user = Depends(get_current_user)
):
    """Check if product is in favorites."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("favorites")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("product_id", product_id)\
            .limit(1)\
            .execute()
        
        return {"is_favorite": len(result.data) > 0 if result.data else False}
        
    except Exception as e:
        logger.error(f"Error checking favorite: {e}")
        return {"is_favorite": False}


@router.get("")
async def list_favorites(
    current_user = Depends(get_current_user)
):
    """List all favorites with product details."""
    user_id = str(current_user.id)
    
    try:
        # Get favorites with product and analysis data
        result = supabase.table("favorites")\
            .select("*, products(*), analyses(*)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        favorites = []
        for fav in result.data or []:
            product = fav.get("products") or {}
            analysis = fav.get("analyses") or {}
            
            # Get product source for buy_cost
            buy_cost = None
            if product.get("id"):
                try:
                    source_result = supabase.table("product_sources")\
                        .select("buy_cost")\
                        .eq("product_id", product["id"])\
                        .limit(1)\
                        .execute()
                    if source_result.data:
                        buy_cost = source_result.data[0].get("buy_cost")
                except:
                    pass
            
            favorites.append({
                "id": fav.get("id"),
                "product_id": fav.get("product_id"),
                "asin": product.get("asin") or fav.get("asin"),
                "title": product.get("title"),
                "brand": product.get("brand"),
                "image_url": product.get("image_url"),
                "buy_cost": buy_cost or product.get("buy_cost"),
                "sell_price": analysis.get("sell_price") or product.get("sell_price"),
                "profit": analysis.get("net_profit") or analysis.get("profit"),
                "roi": analysis.get("roi"),
                "created_at": fav.get("created_at"),
            })
        
        return favorites
        
    except Exception as e:
        logger.error(f"Error listing favorites: {e}")
        return []

