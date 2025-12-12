"""
Buy Lists API - Phase 2 Implementation
Proper buy lists system with multiple lists per user and detailed tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/buy-lists", tags=["buy-lists"])


class BuyListCreate(BaseModel):
    name: str
    description: Optional[str] = None
    notes: Optional[str] = None


class BuyListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class BuyListItemCreate(BaseModel):
    product_id: str
    product_source_id: Optional[str] = None
    quantity: int = 1
    notes: Optional[str] = None


class BuyListItemUpdate(BaseModel):
    quantity: Optional[int] = None
    notes: Optional[str] = None


@router.get("")
async def list_buy_lists(
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """List all buy lists for the current user."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table("buy_lists")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)
        
        if status:
            query = query.eq("status", status)
        
        response = query.execute()
        return {"buy_lists": response.data or []}
    except Exception as e:
        logger.error(f"Error listing buy lists: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list buy lists: {str(e)}")


@router.post("")
async def create_buy_list(
    data: BuyListCreate,
    current_user=Depends(get_current_user)
):
    """Create a new buy list."""
    user_id = str(current_user.id)
    
    try:
        buy_list_data = {
            "user_id": user_id,
            "name": data.name,
            "description": data.description,
            "notes": data.notes,
            "status": "draft"
        }
        
        response = supabase.table("buy_lists")\
            .insert(buy_list_data)\
            .execute()
        
        if not response.data:
            raise HTTPException(500, "Failed to create buy list")
        
        return {"buy_list": response.data[0]}
    except Exception as e:
        logger.error(f"Error creating buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create buy list: {str(e)}")


@router.get("/{buy_list_id}")
async def get_buy_list(
    buy_list_id: str,
    current_user=Depends(get_current_user)
):
    """Get buy list details with items."""
    user_id = str(current_user.id)
    
    try:
        # Get buy list
        buy_list_response = supabase.table("buy_lists")\
            .select("*")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not buy_list_response.data:
            raise HTTPException(404, "Buy list not found")
        
        buy_list = buy_list_response.data
        
        # Get items with product details
        items_response = supabase.table("buy_list_items")\
            .select("""
                *,
                products!inner(
                    id,
                    asin,
                    title,
                    image_url,
                    sell_price,
                    profit_amount,
                    roi_percentage,
                    margin_percentage,
                    current_sales_rank,
                    est_monthly_sales
                ),
                product_sources(
                    id,
                    supplier_id,
                    buy_cost,
                    wholesale_cost,
                    pack_size,
                    suppliers(name)
                )
            """)\
            .eq("buy_list_id", buy_list_id)\
            .execute()
        
        items = []
        for item in items_response.data or []:
            product = item.get("products", {})
            if isinstance(product, list) and product:
                product = product[0]
            
            product_source = item.get("product_sources", {})
            if isinstance(product_source, list) and product_source:
                product_source = product_source[0]
            
            supplier = product_source.get("suppliers", {}) if product_source else {}
            if isinstance(supplier, list) and supplier:
                supplier = supplier[0]
            
            items.append({
                "id": item["id"],
                "product_id": item["product_id"],
                "product_source_id": item.get("product_source_id"),
                "quantity": item["quantity"],
                "unit_cost": float(item["unit_cost"]) if item.get("unit_cost") else None,
                "total_cost": float(item["total_cost"]) if item.get("total_cost") else None,
                "expected_sell_price": float(item["expected_sell_price"]) if item.get("expected_sell_price") else None,
                "expected_profit": float(item["expected_profit"]) if item.get("expected_profit") else None,
                "expected_roi": float(item["expected_roi"]) if item.get("expected_roi") else None,
                "expected_margin": float(item["expected_margin"]) if item.get("expected_margin") else None,
                "notes": item.get("notes"),
                "product": {
                    "id": product.get("id") if isinstance(product, dict) else None,
                    "asin": product.get("asin") if isinstance(product, dict) else None,
                    "title": product.get("title") if isinstance(product, dict) else None,
                    "image_url": product.get("image_url") if isinstance(product, dict) else None,
                    "sell_price": float(product.get("sell_price", 0)) if isinstance(product, dict) and product.get("sell_price") else None,
                    "profit_amount": float(product.get("profit_amount", 0)) if isinstance(product, dict) and product.get("profit_amount") else None,
                    "roi_percentage": float(product.get("roi_percentage", 0)) if isinstance(product, dict) and product.get("roi_percentage") else None,
                    "margin_percentage": float(product.get("margin_percentage", 0)) if isinstance(product, dict) and product.get("margin_percentage") else None,
                    "current_sales_rank": product.get("current_sales_rank") if isinstance(product, dict) else None,
                    "est_monthly_sales": product.get("est_monthly_sales") if isinstance(product, dict) else None,
                },
                "product_source": {
                    "id": product_source.get("id") if isinstance(product_source, dict) else None,
                    "supplier_id": product_source.get("supplier_id") if isinstance(product_source, dict) else None,
                    "buy_cost": float(product_source.get("buy_cost", 0)) if isinstance(product_source, dict) and product_source.get("buy_cost") else None,
                    "wholesale_cost": float(product_source.get("wholesale_cost", 0)) if isinstance(product_source, dict) and product_source.get("wholesale_cost") else None,
                    "pack_size": product_source.get("pack_size", 1) if isinstance(product_source, dict) else 1,
                    "supplier_name": supplier.get("name") if isinstance(supplier, dict) else None,
                },
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })
        
        buy_list["items"] = items
        return {"buy_list": buy_list}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get buy list: {str(e)}")


@router.put("/{buy_list_id}")
async def update_buy_list(
    buy_list_id: str,
    data: BuyListUpdate,
    current_user=Depends(get_current_user)
):
    """Update buy list."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("buy_lists")\
            .select("id")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Buy list not found")
        
        # Build update data
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.status is not None:
            if data.status not in ["draft", "approved", "ordered", "received", "archived"]:
                raise HTTPException(400, "Invalid status")
            update_data["status"] = data.status
        if data.notes is not None:
            update_data["notes"] = data.notes
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("buy_lists")\
            .update(update_data)\
            .eq("id", buy_list_id)\
            .execute()
        
        return {"buy_list": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update buy list: {str(e)}")


@router.delete("/{buy_list_id}")
async def delete_buy_list(
    buy_list_id: str,
    current_user=Depends(get_current_user)
):
    """Delete buy list (cascades to items)."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("buy_lists")\
            .select("id")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Buy list not found")
        
        supabase.table("buy_lists")\
            .delete()\
            .eq("id", buy_list_id)\
            .execute()
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to delete buy list: {str(e)}")


@router.post("/{buy_list_id}/items")
async def add_item_to_buy_list(
    buy_list_id: str,
    data: BuyListItemCreate,
    current_user=Depends(get_current_user)
):
    """Add product to buy list."""
    user_id = str(current_user.id)
    
    try:
        # Verify buy list ownership
        buy_list_check = supabase.table("buy_lists")\
            .select("id, status")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not buy_list_check.data:
            raise HTTPException(404, "Buy list not found")
        
        if buy_list_check.data.get("status") not in ["draft", "approved"]:
            raise HTTPException(400, "Cannot add items to buy list in current status")
        
        # Get product and product_source data
        product_query = supabase.table("products")\
            .select("id, sell_price, profit_amount, roi_percentage, margin_percentage")\
            .eq("id", data.product_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not product_query.data:
            raise HTTPException(404, "Product not found")
        
        product = product_query.data
        
        # Get product_source for cost
        product_source = None
        if data.product_source_id:
            source_query = supabase.table("product_sources")\
                .select("*")\
                .eq("id", data.product_source_id)\
                .eq("product_id", data.product_id)\
                .single()\
                .execute()
            
            if source_query.data:
                product_source = source_query.data
        else:
            # Get first active product_source for this product
            source_query = supabase.table("product_sources")\
                .select("*")\
                .eq("product_id", data.product_id)\
                .eq("is_active", True)\
                .limit(1)\
                .execute()
            
            if source_query.data:
                product_source = source_query.data[0]
        
        if not product_source:
            raise HTTPException(400, "No active product source found for this product")
        
        # Calculate costs
        unit_cost = float(product_source.get("wholesale_cost") or product_source.get("buy_cost") or 0)
        total_cost = unit_cost * data.quantity
        
        # Get expected values from product
        expected_sell_price = float(product.get("sell_price", 0)) if product.get("sell_price") else None
        expected_profit = float(product.get("profit_amount", 0)) if product.get("profit_amount") else None
        expected_roi = float(product.get("roi_percentage", 0)) if product.get("roi_percentage") else None
        expected_margin = float(product.get("margin_percentage", 0)) if product.get("margin_percentage") else None
        
        # Calculate expected profit for this quantity
        if expected_profit is not None:
            expected_profit = expected_profit * data.quantity
        
        # Create item
        item_data = {
            "buy_list_id": buy_list_id,
            "product_id": data.product_id,
            "product_source_id": product_source.get("id"),
            "quantity": data.quantity,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "expected_sell_price": expected_sell_price,
            "expected_profit": expected_profit,
            "expected_roi": expected_roi,
            "expected_margin": expected_margin,
            "notes": data.notes
        }
        
        response = supabase.table("buy_list_items")\
            .upsert(item_data, on_conflict="buy_list_id,product_id,product_source_id")\
            .execute()
        
        if not response.data:
            raise HTTPException(500, "Failed to add item to buy list")
        
        return {"item": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding item to buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to add item: {str(e)}")


@router.put("/{buy_list_id}/items/{item_id}")
async def update_buy_list_item(
    buy_list_id: str,
    item_id: str,
    data: BuyListItemUpdate,
    current_user=Depends(get_current_user)
):
    """Update buy list item (quantity, notes)."""
    user_id = str(current_user.id)
    
    try:
        # Verify buy list ownership
        buy_list_check = supabase.table("buy_lists")\
            .select("id")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not buy_list_check.data:
            raise HTTPException(404, "Buy list not found")
        
        # Get current item
        item_check = supabase.table("buy_list_items")\
            .select("*")\
            .eq("id", item_id)\
            .eq("buy_list_id", buy_list_id)\
            .single()\
            .execute()
        
        if not item_check.data:
            raise HTTPException(404, "Item not found")
        
        item = item_check.data
        
        # Build update
        update_data = {}
        if data.quantity is not None:
            if data.quantity < 1:
                raise HTTPException(400, "Quantity must be at least 1")
            update_data["quantity"] = data.quantity
            # Recalculate total_cost
            unit_cost = float(item.get("unit_cost", 0))
            update_data["total_cost"] = unit_cost * data.quantity
            # Recalculate expected_profit
            if item.get("expected_profit") is not None:
                expected_profit_per_unit = float(item.get("expected_profit", 0)) / item.get("quantity", 1)
                update_data["expected_profit"] = expected_profit_per_unit * data.quantity
        
        if data.notes is not None:
            update_data["notes"] = data.notes
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("buy_list_items")\
            .update(update_data)\
            .eq("id", item_id)\
            .execute()
        
        return {"item": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating buy list item: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update item: {str(e)}")


@router.delete("/{buy_list_id}/items/{item_id}")
async def remove_item_from_buy_list(
    buy_list_id: str,
    item_id: str,
    current_user=Depends(get_current_user)
):
    """Remove item from buy list."""
    user_id = str(current_user.id)
    
    try:
        # Verify buy list ownership
        buy_list_check = supabase.table("buy_lists")\
            .select("id")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not buy_list_check.data:
            raise HTTPException(404, "Buy list not found")
        
        supabase.table("buy_list_items")\
            .delete()\
            .eq("id", item_id)\
            .eq("buy_list_id", buy_list_id)\
            .execute()
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item from buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to remove item: {str(e)}")


@router.post("/{buy_list_id}/finalize")
async def finalize_buy_list(
    buy_list_id: str,
    current_user=Depends(get_current_user)
):
    """Finalize buy list (change status to 'approved')."""
    user_id = str(current_user.id)
    
    try:
        # Verify buy list ownership and has items
        buy_list_check = supabase.table("buy_lists")\
            .select("id, status")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not buy_list_check.data:
            raise HTTPException(404, "Buy list not found")
        
        if buy_list_check.data.get("status") != "draft":
            raise HTTPException(400, "Can only finalize draft buy lists")
        
        # Check has items
        items_check = supabase.table("buy_list_items")\
            .select("id")\
            .eq("buy_list_id", buy_list_id)\
            .limit(1)\
            .execute()
        
        if not items_check.data:
            raise HTTPException(400, "Cannot finalize empty buy list")
        
        # Update status
        response = supabase.table("buy_lists")\
            .update({
                "status": "approved",
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", buy_list_id)\
            .execute()
        
        return {"buy_list": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finalizing buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to finalize buy list: {str(e)}")


class CreateBuyListFromProductsRequest(BaseModel):
    product_ids: List[str]
    name: Optional[str] = None


@router.post("/create-from-products")
async def create_buy_list_from_products(
    request: CreateBuyListFromProductsRequest = Body(...),
    current_user=Depends(get_current_user)
):
    """Create a new buy list and add multiple products at once."""
    user_id = str(current_user.id)
    product_ids = request.product_ids
    name = request.name
    
    try:
        if not product_ids:
            raise HTTPException(400, "No products provided")
        
        # Generate name if not provided
        if not name:
            name = f"Buy List - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # Create buy list
        buy_list_data = {
            "user_id": user_id,
            "name": name,
            "status": "draft"
        }
        
        buy_list_response = supabase.table("buy_lists")\
            .insert(buy_list_data)\
            .execute()
        
        if not buy_list_response.data:
            raise HTTPException(500, "Failed to create buy list")
        
        buy_list_id = buy_list_response.data[0]["id"]
        
        # Add products
        added_items = []
        errors = []
        
        for product_id in product_ids:
            try:
                # Get product and product_source
                product_query = supabase.table("products")\
                    .select("id, sell_price, profit_amount, roi_percentage, margin_percentage")\
                    .eq("id", product_id)\
                    .eq("user_id", user_id)\
                    .single()\
                    .execute()
                
                if not product_query.data:
                    errors.append(f"Product {product_id} not found")
                    continue
                
                product = product_query.data
                
                # Get first active product_source
                source_query = supabase.table("product_sources")\
                    .select("*")\
                    .eq("product_id", product_id)\
                    .eq("is_active", True)\
                    .limit(1)\
                    .execute()
                
                if not source_query.data:
                    errors.append(f"No active product source for product {product_id}")
                    continue
                
                product_source = source_query.data[0]
                
                # Calculate costs
                unit_cost = float(product_source.get("wholesale_cost") or product_source.get("buy_cost") or 0)
                quantity = product_source.get("moq", 1)
                total_cost = unit_cost * quantity
                
                # Get expected values
                expected_sell_price = float(product.get("sell_price", 0)) if product.get("sell_price") else None
                expected_profit = float(product.get("profit_amount", 0)) * quantity if product.get("profit_amount") else None
                expected_roi = float(product.get("roi_percentage", 0)) if product.get("roi_percentage") else None
                expected_margin = float(product.get("margin_percentage", 0)) if product.get("margin_percentage") else None
                
                # Create item
                item_data = {
                    "buy_list_id": buy_list_id,
                    "product_id": product_id,
                    "product_source_id": product_source.get("id"),
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_cost": total_cost,
                    "expected_sell_price": expected_sell_price,
                    "expected_profit": expected_profit,
                    "expected_roi": expected_roi,
                    "expected_margin": expected_margin,
                }
                
                item_response = supabase.table("buy_list_items")\
                    .upsert(item_data, on_conflict="buy_list_id,product_id,product_source_id")\
                    .execute()
                
                if item_response.data:
                    added_items.append(item_response.data[0])
            except Exception as e:
                logger.error(f"Error adding product {product_id} to buy list: {e}")
                errors.append(f"Failed to add product {product_id}: {str(e)}")
        
        # Get updated buy list
        buy_list_response = supabase.table("buy_lists")\
            .select("*")\
            .eq("id", buy_list_id)\
            .single()\
            .execute()
        
        return {
            "buy_list": buy_list_response.data[0] if buy_list_response.data else None,
            "added_items": len(added_items),
            "errors": errors
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating buy list from products: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create buy list: {str(e)}")

