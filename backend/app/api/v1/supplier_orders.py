"""
Supplier Orders API - Phase 3 Implementation
Create and manage orders sent to suppliers, grouped by supplier from buy lists.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/supplier-orders", tags=["supplier-orders"])


class SupplierOrderCreate(BaseModel):
    buy_list_id: str
    notes: Optional[str] = None


class SupplierOrderUpdate(BaseModel):
    order_number: Optional[str] = None
    status: Optional[str] = None
    shipping_method: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    sent_date: Optional[str] = None
    received_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
async def list_supplier_orders(
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    buy_list_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """List all supplier orders for the current user."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table("supplier_orders")\
            .select("""
                *,
                suppliers(name, email, phone),
                buy_lists(name)
            """)\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)
        
        if status:
            query = query.eq("status", status)
        if supplier_id:
            query = query.eq("supplier_id", supplier_id)
        if buy_list_id:
            query = query.eq("buy_list_id", buy_list_id)
        
        response = query.execute()
        
        # Format response
        orders = []
        for order in response.data or []:
            supplier = order.get("suppliers", {})
            if isinstance(supplier, list) and supplier:
                supplier = supplier[0]
            
            buy_list = order.get("buy_lists", {})
            if isinstance(buy_list, list) and buy_list:
                buy_list = buy_list[0]
            
            orders.append({
                **order,
                "supplier_name": supplier.get("name") if isinstance(supplier, dict) else None,
                "buy_list_name": buy_list.get("name") if isinstance(buy_list, dict) else None,
            })
        
        return {"supplier_orders": orders}
    except Exception as e:
        logger.error(f"Error listing supplier orders: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list supplier orders: {str(e)}")


@router.post("/create-from-buy-list")
async def create_orders_from_buy_list(
    buy_list_id: str,
    current_user=Depends(get_current_user)
):
    """
    Create supplier orders from a buy list.
    Automatically groups products by supplier and creates one order per supplier.
    """
    user_id = str(current_user.id)
    
    try:
        # Verify buy list ownership and status
        buy_list_response = supabase.table("buy_lists")\
            .select("id, status, name")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not buy_list_response.data:
            raise HTTPException(404, "Buy list not found")
        
        buy_list = buy_list_response.data
        
        if buy_list.get("status") not in ["approved", "draft"]:
            raise HTTPException(400, f"Cannot create orders from buy list with status: {buy_list.get('status')}")
        
        # Get all buy list items with product and supplier info
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
                    margin_percentage
                ),
                product_sources!inner(
                    id,
                    supplier_id,
                    buy_cost,
                    wholesale_cost,
                    pack_size,
                    suppliers!inner(id, name, email, phone)
                )
            """)\
            .eq("buy_list_id", buy_list_id)\
            .execute()
        
        if not items_response.data:
            raise HTTPException(400, "Buy list is empty")
        
        # Group items by supplier
        items_by_supplier: Dict[str, List[Dict]] = {}
        
        for item in items_response.data:
            product_source = item.get("product_sources", {})
            if isinstance(product_source, list) and product_source:
                product_source = product_source[0]
            
            supplier = product_source.get("suppliers", {}) if product_source else {}
            if isinstance(supplier, list) and supplier:
                supplier = supplier[0]
            
            supplier_id = supplier.get("id") if isinstance(supplier, dict) else None
            
            if not supplier_id:
                logger.warning(f"Item {item.get('id')} has no supplier, skipping")
                continue
            
            if supplier_id not in items_by_supplier:
                items_by_supplier[supplier_id] = []
            
            items_by_supplier[supplier_id].append(item)
        
        if not items_by_supplier:
            raise HTTPException(400, "No items with valid suppliers found in buy list")
        
        # Create one order per supplier
        created_orders = []
        
        for supplier_id, items in items_by_supplier.items():
            # Get supplier info
            supplier_response = supabase.table("suppliers")\
                .select("id, name")\
                .eq("id", supplier_id)\
                .single()\
                .execute()
            
            if not supplier_response.data:
                logger.warning(f"Supplier {supplier_id} not found, skipping")
                continue
            
            supplier = supplier_response.data
            
            # Create supplier order
            order_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "buy_list_id": buy_list_id,
                "supplier_id": supplier_id,
                "status": "draft",
                "notes": f"Created from buy list: {buy_list.get('name')}"
            }
            
            order_response = supabase.table("supplier_orders")\
                .insert(order_data)\
                .execute()
            
            # Auto-generate prep instructions if order has items
            if order_response.data:
                order_id = order_response.data[0]['id']
                try:
                    from app.services.prep_instructions_service import PrepInstructionsService
                    prep_service = PrepInstructionsService(user_id)
                    await prep_service.generate_prep_instructions_for_order(order_id)
                except Exception as e:
                    logger.warning(f"Failed to generate prep instructions for order {order_id}: {e}")
            
            if not order_response.data:
                logger.error(f"Failed to create order for supplier {supplier_id}")
                continue
            
            order = order_response.data[0]
            order_id = order["id"]
            
            # Create order items
            order_items = []
            for item in items:
                product = item.get("products", {})
                if isinstance(product, list) and product:
                    product = product[0]
                
                product_source = item.get("product_sources", {})
                if isinstance(product_source, list) and product_source:
                    product_source = product_source[0]
                
                # Use values from buy_list_item (snapshot at time of adding to buy list)
                quantity = item.get("quantity", 1)
                unit_cost = float(item.get("unit_cost", 0))
                total_cost = float(item.get("total_cost", 0))
                expected_sell_price = float(item.get("expected_sell_price", 0)) if item.get("expected_sell_price") else None
                expected_profit = float(item.get("expected_profit", 0)) if item.get("expected_profit") else None
                expected_roi = float(item.get("expected_roi", 0)) if item.get("expected_roi") else None
                expected_margin = float(item.get("expected_margin", 0)) if item.get("expected_margin") else None
                
                order_item_data = {
                    "id": str(uuid.uuid4()),
                    "supplier_order_id": order_id,
                    "buy_list_item_id": item.get("id"),
                    "product_id": item.get("product_id"),
                    "product_source_id": product_source.get("id") if isinstance(product_source, dict) else None,
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_cost": total_cost,
                    "expected_sell_price": expected_sell_price,
                    "expected_profit": expected_profit,
                    "expected_roi": expected_roi,
                    "expected_margin": expected_margin,
                    "notes": item.get("notes")
                }
                
                order_items.append(order_item_data)
            
            # Bulk insert order items
            if order_items:
                items_response = supabase.table("supplier_order_items")\
                    .insert(order_items)\
                    .execute()
                
                if items_response.data:
                    # Get updated order with summary metrics
                    updated_order = supabase.table("supplier_orders")\
                        .select("""
                            *,
                            suppliers(name, email, phone),
                            buy_lists(name)
                        """)\
                        .eq("id", order_id)\
                        .single()\
                        .execute()
                    
                    if updated_order.data:
                        order_data = updated_order.data
                        supplier = order_data.get("suppliers", {})
                        if isinstance(supplier, list) and supplier:
                            supplier = supplier[0]
                        
                        buy_list_ref = order_data.get("buy_lists", {})
                        if isinstance(buy_list_ref, list) and buy_list_ref:
                            buy_list_ref = buy_list_ref[0]
                        
                        created_orders.append({
                            **order_data,
                            "supplier_name": supplier.get("name") if isinstance(supplier, dict) else None,
                            "buy_list_name": buy_list_ref.get("name") if isinstance(buy_list_ref, dict) else None,
                            "items_count": len(order_items)
                        })
        
        if not created_orders:
            raise HTTPException(500, "Failed to create any orders")
        
        # Update buy list status to 'ordered' if all items were processed
        supabase.table("buy_lists")\
            .update({"status": "ordered", "updated_at": datetime.utcnow().isoformat()})\
            .eq("id", buy_list_id)\
            .execute()
        
        return {
            "success": True,
            "orders_created": len(created_orders),
            "orders": created_orders
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating orders from buy list: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create orders: {str(e)}")


@router.get("/{order_id}")
async def get_supplier_order(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """Get supplier order details with items."""
    user_id = str(current_user.id)
    
    try:
        # Get order
        order_response = supabase.table("supplier_orders")\
            .select("""
                *,
                suppliers(name, email, phone, address),
                buy_lists(name)
            """)\
            .eq("id", order_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not order_response.data:
            raise HTTPException(404, "Supplier order not found")
        
        order = order_response.data
        
        # Get items with product details
        items_response = supabase.table("supplier_order_items")\
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
            .eq("supplier_order_id", order_id)\
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
                "buy_list_item_id": item.get("buy_list_item_id"),
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
        
        supplier = order.get("suppliers", {})
        if isinstance(supplier, list) and supplier:
            supplier = supplier[0]
        
        buy_list_ref = order.get("buy_lists", {})
        if isinstance(buy_list_ref, list) and buy_list_ref:
            buy_list_ref = buy_list_ref[0]
        
        order["items"] = items
        order["supplier_name"] = supplier.get("name") if isinstance(supplier, dict) else None
        order["supplier_email"] = supplier.get("email") if isinstance(supplier, dict) else None
        order["supplier_phone"] = supplier.get("phone") if isinstance(supplier, dict) else None
        order["supplier_address"] = supplier.get("address") if isinstance(supplier, dict) else None
        order["buy_list_name"] = buy_list_ref.get("name") if isinstance(buy_list_ref, dict) else None
        
        return {"supplier_order": order}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier order: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get supplier order: {str(e)}")


@router.put("/{order_id}")
async def update_supplier_order(
    order_id: str,
    data: SupplierOrderUpdate,
    current_user=Depends(get_current_user)
):
    """Update supplier order."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("supplier_orders")\
            .select("id")\
            .eq("id", order_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Supplier order not found")
        
        # Build update data
        update_data = {}
        if data.order_number is not None:
            update_data["order_number"] = data.order_number
        if data.status is not None:
            if data.status not in ["draft", "sent", "confirmed", "in_transit", "received", "cancelled"]:
                raise HTTPException(400, "Invalid status")
            update_data["status"] = data.status
        if data.shipping_method is not None:
            update_data["shipping_method"] = data.shipping_method
        if data.estimated_delivery_date is not None:
            update_data["estimated_delivery_date"] = data.estimated_delivery_date
        if data.sent_date is not None:
            update_data["sent_date"] = data.sent_date
        if data.received_date is not None:
            update_data["received_date"] = data.received_date
        if data.notes is not None:
            update_data["notes"] = data.notes
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("supplier_orders")\
            .update(update_data)\
            .eq("id", order_id)\
            .execute()
        
        return {"supplier_order": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating supplier order: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update supplier order: {str(e)}")


@router.delete("/{order_id}")
async def delete_supplier_order(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """Delete supplier order (cascades to items)."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("supplier_orders")\
            .select("id")\
            .eq("id", order_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Supplier order not found")
        
        supabase.table("supplier_orders")\
            .delete()\
            .eq("id", order_id)\
            .execute()
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting supplier order: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to delete supplier order: {str(e)}")


@router.post("/{order_id}/export")
async def export_supplier_order(
    order_id: str,
    format: str = Query("csv", regex="^(csv|excel|pdf)$"),
    current_user=Depends(get_current_user)
):
    """
    Export supplier order to CSV/Excel/PDF.
    Returns order details formatted for sending to supplier.
    """
    user_id = str(current_user.id)
    
    try:
        # Get order with items
        order_response = supabase.table("supplier_orders")\
            .select("""
                *,
                suppliers(name, email, phone, address),
                buy_lists(name),
                supplier_order_items(
                    *,
                    products(asin, title, package_quantity),
                    product_sources(pack_size, moq)
                )
            """)\
            .eq("id", order_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not order_response.data:
            raise HTTPException(404, "Supplier order not found")
        
        order = order_response.data
        
        # Format for export
        if format == "csv":
            # Generate CSV content
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(["Supplier Order"])
            writer.writerow([f"Order ID: {order_id}"])
            writer.writerow([f"Date: {order.get('created_at', '')[:10]}"])
            writer.writerow([])
            
            supplier = order.get("suppliers", {})
            if isinstance(supplier, list) and supplier:
                supplier = supplier[0]
            
            writer.writerow(["Supplier:", supplier.get("name", "") if isinstance(supplier, dict) else ""])
            writer.writerow([])
            
            # Items
            writer.writerow(["ASIN", "Product Title", "Quantity", "Unit Cost", "Total Cost"])
            
            items = order.get("supplier_order_items", [])
            for item in items:
                product = item.get("products", {})
                if isinstance(product, list) and product:
                    product = product[0]
                
                writer.writerow([
                    product.get("asin", "") if isinstance(product, dict) else "",
                    product.get("title", "") if isinstance(product, dict) else "",
                    item.get("quantity", 0),
                    f"${item.get('unit_cost', 0):.2f}",
                    f"${item.get('total_cost', 0):.2f}"
                ])
            
            writer.writerow([])
            writer.writerow(["Total Cost:", f"${order.get('total_cost', 0):.2f}"])
            
            output.seek(0)
            csv_content = output.getvalue()
            
            from fastapi.responses import Response
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="supplier_order_{order_id[:8]}.csv"'
                }
            )
        else:
            raise HTTPException(400, f"Export format {format} not yet implemented")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting supplier order: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to export supplier order: {str(e)}")

