"""
Buy List API - Manage user's buy list items
Buy list items are products with stage='buy_list'
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.core.exceptions import NotFoundError
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()


class BuyListItemCreate(BaseModel):
    product_id: str
    quantity: int = 1


class BuyListItemUpdate(BaseModel):
    quantity: int


@router.get("")
async def get_buy_list(current_user=Depends(get_current_user)):
    """Get user's buy list items (products with stage='buy_list')."""
    try:
        # Use product_deals view for consistency with products endpoint
        result = supabase.table("product_deals")\
            .select("*")\
            .eq("user_id", str(current_user.id))\
            .eq("stage", "buy_list")\
            .order("deal_created_at", desc=True)\
            .execute()
        
        items = []
        for deal in result.data or []:
            items.append({
                "id": deal.get("deal_id"),  # product_sources.id
                "product_id": deal.get("product_id"),
                "deal_id": deal.get("deal_id"),
                "asin": deal.get("asin"),
                "title": deal.get("title"),
                "image_url": deal.get("image_url"),
                "buy_cost": deal.get("buy_cost", 0),
                "moq": deal.get("moq", 1),
                "quantity": deal.get("moq", 1),  # Use MOQ as quantity
                "supplier_id": deal.get("supplier_id"),
                "supplier_name": deal.get("supplier_name"),
                "created_at": deal.get("deal_created_at"),
            })
        
        return items
    except Exception as e:
        logger.error(f"Error fetching buy list: {e}")
        # Fallback to product_sources if view doesn't exist
        try:
            result = supabase.table("product_sources")\
                .select("*, products!inner(*)")\
                .eq("products.user_id", str(current_user.id))\
                .eq("stage", "buy_list")\
                .execute()
            
            items = []
            for source in result.data or []:
                product = source.get("products", {})
                if isinstance(product, list) and product:
                    product = product[0]
                items.append({
                    "id": source["id"],
                    "product_id": source["product_id"],
                    "deal_id": source["id"],
                    "asin": product.get("asin") if isinstance(product, dict) else None,
                    "title": product.get("title") if isinstance(product, dict) else None,
                    "image_url": product.get("image_url") if isinstance(product, dict) else None,
                    "buy_cost": source.get("buy_cost", 0),
                    "moq": source.get("moq", 1),
                    "quantity": source.get("moq", 1),
                    "supplier_id": source.get("supplier_id"),
                    "supplier_name": source.get("supplier_name"),
                    "created_at": source.get("created_at"),
                })
            return items
        except Exception as fallback_error:
            logger.error(f"Fallback buy list query also failed: {fallback_error}")
            return []


@router.post("")
async def add_to_buy_list(data: BuyListItemCreate, current_user=Depends(get_current_user)):
    """Add product to buy list by setting stage to 'buy_list'."""
    try:
        # First verify the product_source belongs to the user via products table
        # product_sources doesn't have user_id directly, need to check via products
        check_result = supabase.table("product_sources")\
            .select("id, products!inner(user_id)")\
            .eq("id", data.product_id)\
            .execute()
        
        if not check_result.data:
            raise NotFoundError("Product source")
        
        # Verify ownership
        product = check_result.data[0].get("products", {})
        if isinstance(product, list) and product:
            product = product[0]
        if isinstance(product, dict) and product.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to modify this product")
        
        # Update product source stage
        result = supabase.table("product_sources")\
            .update({
                "stage": "buy_list",
                "moq": data.quantity  # Update MOQ to requested quantity
            })\
            .eq("id", data.product_id)\
            .execute()
        
        if not result.data:
            raise NotFoundError("Product")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to buy list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{item_id}")
async def update_buy_list_item(
    item_id: str,
    data: BuyListItemUpdate,
    current_user=Depends(get_current_user)
):
    """Update buy list item quantity."""
    try:
        # Verify ownership first
        check_result = supabase.table("product_sources")\
            .select("id, products!inner(user_id)")\
            .eq("id", item_id)\
            .eq("stage", "buy_list")\
            .execute()
        
        if not check_result.data:
            raise NotFoundError("Buy list item")
        
        # Verify ownership
        product = check_result.data[0].get("products", {})
        if isinstance(product, list) and product:
            product = product[0]
        if isinstance(product, dict) and product.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to modify this item")
        
        # Update quantity
        result = supabase.table("product_sources")\
            .update({"moq": data.quantity})\
            .eq("id", item_id)\
            .eq("stage", "buy_list")\
            .execute()
        
        if not result.data:
            raise NotFoundError("Buy list item")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating buy list item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
async def remove_from_buy_list(item_id: str, current_user=Depends(get_current_user)):
    """Remove item from buy list by setting stage back to 'reviewed'."""
    try:
        # Verify ownership first
        check_result = supabase.table("product_sources")\
            .select("id, products!inner(user_id)")\
            .eq("id", item_id)\
            .eq("stage", "buy_list")\
            .execute()
        
        if not check_result.data:
            raise NotFoundError("Buy list item")
        
        # Verify ownership
        product = check_result.data[0].get("products", {})
        if isinstance(product, list) and product:
            product = product[0]
        if isinstance(product, dict) and product.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to modify this item")
        
        # Update stage
        result = supabase.table("product_sources")\
            .update({"stage": "reviewed"})\
            .eq("id", item_id)\
            .eq("stage", "buy_list")\
            .execute()
        
        if not result.data:
            raise NotFoundError("Buy list item")
        
        return {"success": True, "message": "Removed from buy list"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from buy list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
async def clear_buy_list(current_user=Depends(get_current_user)):
    """Clear all items from buy list."""
    try:
        # Get all buy list items for this user (via products join)
        # Then update them
        user_id = str(current_user.id)
        
        # Get product_sources that belong to user's products
        check_result = supabase.table("product_sources")\
            .select("id, products!inner(user_id)")\
            .eq("products.user_id", user_id)\
            .eq("stage", "buy_list")\
            .execute()
        
        if not check_result.data:
            return {
                "success": True,
                "message": "Buy list is already empty"
            }
        
        # Get IDs to update
        item_ids = [item["id"] for item in check_result.data]
        
        # Update all items
        result = supabase.table("product_sources")\
            .update({"stage": "reviewed"})\
            .in_("id", item_ids)\
            .eq("stage", "buy_list")\
            .execute()
        
        return {
            "success": True,
            "message": f"Cleared {len(result.data or [])} items from buy list"
        }
    except Exception as e:
        logger.error(f"Error clearing buy list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-order")
async def create_order_from_buy_list(current_user=Depends(get_current_user)):
    """Create order from all buy list items and clear buy list."""
    try:
        user_id = str(current_user.id)
        
        # Get all buy list items for this user (via products join)
        buy_list_result = supabase.table("product_sources")\
            .select("*, products!inner(*)")\
            .eq("products.user_id", user_id)\
            .eq("stage", "buy_list")\
            .execute()
        
        if not buy_list_result.data:
            raise HTTPException(status_code=400, detail="Buy list is empty")
        
        # Create orders for each item
        orders = []
        for source in buy_list_result.data:
            product = source.get("products", {})
            order_data = {
                "id": str(uuid.uuid4()),
                "user_id": str(current_user.id),
                "supplier_id": source.get("supplier_id"),
                "asin": product.get("asin"),
                "quantity": source.get("moq", 1),
                "unit_cost": source.get("buy_cost", 0),
                "total_cost": (source.get("buy_cost", 0) * source.get("moq", 1)),
                "status": "pending",
                "notes": f"Created from buy list"
            }
            
            order_result = supabase.table("orders").insert(order_data).execute()
            if order_result.data:
                orders.append(order_result.data[0])
        
        # Clear buy list (set stage back to reviewed)
        # Get IDs from the buy_list_result
        item_ids = [item["id"] for item in buy_list_result.data]
        if item_ids:
            supabase.table("product_sources")\
                .update({"stage": "reviewed"})\
                .in_("id", item_ids)\
                .eq("stage", "buy_list")\
                .execute()
        
        return {
            "success": True,
            "orders_created": len(orders),
            "orders": orders
        }
    except Exception as e:
        logger.error(f"Error creating order from buy list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

