"""
3PL (Third-Party Logistics) Integration API - Phase 4 Implementation
Manage 3PL warehouses, inbound shipments, and prep tracking.
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

router = APIRouter(prefix="/tpl", tags=["tpl"])


# ============================================================================
# 3PL WAREHOUSES
# ============================================================================

class TPLWarehouseCreate(BaseModel):
    name: str
    company: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = "United States"
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    prep_services_available: bool = True
    storage_fee_per_unit: Optional[float] = None
    prep_fee_per_unit: Optional[float] = None
    notes: Optional[str] = None


class TPLWarehouseUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None
    prep_services_available: Optional[bool] = None
    storage_fee_per_unit: Optional[float] = None
    prep_fee_per_unit: Optional[float] = None
    notes: Optional[str] = None


@router.get("/warehouses")
async def list_warehouses(
    active_only: bool = Query(False),
    current_user=Depends(get_current_user)
):
    """List all 3PL warehouses for the current user."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table("tpl_warehouses")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("name")
        
        if active_only:
            query = query.eq("is_active", True)
        
        response = query.execute()
        return {"warehouses": response.data or []}
    except Exception as e:
        logger.error(f"Error listing warehouses: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list warehouses: {str(e)}")


@router.post("/warehouses")
async def create_warehouse(
    data: TPLWarehouseCreate,
    current_user=Depends(get_current_user)
):
    """Create a new 3PL warehouse."""
    user_id = str(current_user.id)
    
    try:
        warehouse_data = {
            "user_id": user_id,
            "name": data.name,
            "company": data.company,
            "address_line1": data.address_line1,
            "address_line2": data.address_line2,
            "city": data.city,
            "state": data.state,
            "zip_code": data.zip_code,
            "country": data.country,
            "contact_name": data.contact_name,
            "contact_email": data.contact_email,
            "contact_phone": data.contact_phone,
            "prep_services_available": data.prep_services_available,
            "storage_fee_per_unit": data.storage_fee_per_unit,
            "prep_fee_per_unit": data.prep_fee_per_unit,
            "notes": data.notes,
            "is_active": True
        }
        
        response = supabase.table("tpl_warehouses")\
            .insert(warehouse_data)\
            .execute()
        
        if not response.data:
            raise HTTPException(500, "Failed to create warehouse")
        
        return {"warehouse": response.data[0]}
    except Exception as e:
        logger.error(f"Error creating warehouse: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create warehouse: {str(e)}")


@router.get("/warehouses/{warehouse_id}")
async def get_warehouse(
    warehouse_id: str,
    current_user=Depends(get_current_user)
):
    """Get warehouse details."""
    user_id = str(current_user.id)
    
    try:
        response = supabase.table("tpl_warehouses")\
            .select("*")\
            .eq("id", warehouse_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(404, "Warehouse not found")
        
        return {"warehouse": response.data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warehouse: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get warehouse: {str(e)}")


@router.put("/warehouses/{warehouse_id}")
async def update_warehouse(
    warehouse_id: str,
    data: TPLWarehouseUpdate,
    current_user=Depends(get_current_user)
):
    """Update warehouse."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("tpl_warehouses")\
            .select("id")\
            .eq("id", warehouse_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Warehouse not found")
        
        # Build update data
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("tpl_warehouses")\
            .update(update_data)\
            .eq("id", warehouse_id)\
            .execute()
        
        return {"warehouse": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating warehouse: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update warehouse: {str(e)}")


@router.delete("/warehouses/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: str,
    current_user=Depends(get_current_user)
):
    """Delete warehouse."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("tpl_warehouses")\
            .select("id")\
            .eq("id", warehouse_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Warehouse not found")
        
        supabase.table("tpl_warehouses")\
            .delete()\
            .eq("id", warehouse_id)\
            .execute()
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting warehouse: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to delete warehouse: {str(e)}")


# ============================================================================
# 3PL INBOUNDS
# ============================================================================

class TPLInboundCreate(BaseModel):
    supplier_order_id: str
    tpl_warehouse_id: str
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    shipped_date: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    requires_prep: bool = False
    prep_instructions: Optional[str] = None
    notes: Optional[str] = None


class TPLInboundUpdate(BaseModel):
    inbound_number: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    status: Optional[str] = None
    shipped_date: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    received_date: Optional[str] = None
    prep_started_date: Optional[str] = None
    prep_completed_date: Optional[str] = None
    requires_prep: Optional[bool] = None
    prep_instructions: Optional[str] = None
    notes: Optional[str] = None


@router.get("/inbounds")
async def list_inbounds(
    status: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """List all 3PL inbounds for the current user."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table("tpl_inbounds")\
            .select("""
                *,
                tpl_warehouses(name, company),
                supplier_orders(order_number, suppliers(name))
            """)\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)
        
        if status:
            query = query.eq("status", status)
        if warehouse_id:
            query = query.eq("tpl_warehouse_id", warehouse_id)
        
        response = query.execute()
        
        # Format response
        inbounds = []
        for inbound in response.data or []:
            warehouse = inbound.get("tpl_warehouses", {})
            if isinstance(warehouse, list) and warehouse:
                warehouse = warehouse[0]
            
            supplier_order = inbound.get("supplier_orders", {})
            if isinstance(supplier_order, list) and supplier_order:
                supplier_order = supplier_order[0]
            
            supplier = supplier_order.get("suppliers", {}) if supplier_order else {}
            if isinstance(supplier, list) and supplier:
                supplier = supplier[0]
            
            inbounds.append({
                **inbound,
                "warehouse_name": warehouse.get("name") if isinstance(warehouse, dict) else None,
                "warehouse_company": warehouse.get("company") if isinstance(warehouse, dict) else None,
                "supplier_order_number": supplier_order.get("order_number") if isinstance(supplier_order, dict) else None,
                "supplier_name": supplier.get("name") if isinstance(supplier, dict) else None,
            })
        
        return {"inbounds": inbounds}
    except Exception as e:
        logger.error(f"Error listing inbounds: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list inbounds: {str(e)}")


@router.post("/inbounds/create-from-supplier-order")
async def create_inbound_from_supplier_order(
    supplier_order_id: str,
    tpl_warehouse_id: str,
    tracking_number: Optional[str] = None,
    carrier: Optional[str] = None,
    shipped_date: Optional[str] = None,
    expected_delivery_date: Optional[str] = None,
    requires_prep: bool = False,
    prep_instructions: Optional[str] = None,
    notes: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """
    Create a 3PL inbound shipment from a supplier order.
    Automatically adds all items from the supplier order.
    """
    user_id = str(current_user.id)
    
    try:
        # Verify supplier order ownership
        order_response = supabase.table("supplier_orders")\
            .select("id, status")\
            .eq("id", supplier_order_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not order_response.data:
            raise HTTPException(404, "Supplier order not found")
        
        # Verify warehouse ownership
        warehouse_response = supabase.table("tpl_warehouses")\
            .select("id, is_active")\
            .eq("id", tpl_warehouse_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not warehouse_response.data:
            raise HTTPException(404, "3PL warehouse not found")
        
        if not warehouse_response.data.get("is_active"):
            raise HTTPException(400, "3PL warehouse is not active")
        
        # Get supplier order items
        items_response = supabase.table("supplier_order_items")\
            .select("""
                *,
                products(id, asin, title, image_url)
            """)\
            .eq("supplier_order_id", supplier_order_id)\
            .execute()
        
        if not items_response.data:
            raise HTTPException(400, "Supplier order has no items")
        
        # Create inbound
        inbound_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "supplier_order_id": supplier_order_id,
            "tpl_warehouse_id": tpl_warehouse_id,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "status": "pending",
            "shipped_date": shipped_date,
            "expected_delivery_date": expected_delivery_date,
            "requires_prep": requires_prep,
            "prep_instructions": prep_instructions,
            "notes": notes
        }
        
        inbound_response = supabase.table("tpl_inbounds")\
            .insert(inbound_data)\
            .execute()
        
        if not inbound_response.data:
            raise HTTPException(500, "Failed to create inbound")
        
        inbound = inbound_response.data[0]
        inbound_id = inbound["id"]
        
        # Create inbound items
        inbound_items = []
        for item in items_response.data:
            product = item.get("products", {})
            if isinstance(product, list) and product:
                product = product[0]
            
            inbound_item_data = {
                "id": str(uuid.uuid4()),
                "tpl_inbound_id": inbound_id,
                "supplier_order_item_id": item.get("id"),
                "product_id": item.get("product_id"),
                "quantity": item.get("quantity", 1),
                "quantity_received": 0,
                "quantity_prepped": 0,
                "prep_status": "pending" if requires_prep else "not_required",
                "notes": item.get("notes")
            }
            
            inbound_items.append(inbound_item_data)
        
        # Bulk insert inbound items
        if inbound_items:
            items_response = supabase.table("tpl_inbound_items")\
                .insert(inbound_items)\
                .execute()
        
        # Get updated inbound with summary
        updated_inbound = supabase.table("tpl_inbounds")\
            .select("""
                *,
                tpl_warehouses(name, company),
                supplier_orders(order_number, suppliers(name))
            """)\
            .eq("id", inbound_id)\
            .single()\
            .execute()
        
        if updated_inbound.data:
            inbound_data = updated_inbound.data
            warehouse = inbound_data.get("tpl_warehouses", {})
            if isinstance(warehouse, list) and warehouse:
                warehouse = warehouse[0]
            
            supplier_order = inbound_data.get("supplier_orders", {})
            if isinstance(supplier_order, list) and supplier_order:
                supplier_order = supplier_order[0]
            
            supplier = supplier_order.get("suppliers", {}) if supplier_order else {}
            if isinstance(supplier, list) and supplier:
                supplier = supplier[0]
            
            return {
                "success": True,
                "inbound": {
                    **inbound_data,
                    "warehouse_name": warehouse.get("name") if isinstance(warehouse, dict) else None,
                    "warehouse_company": warehouse.get("company") if isinstance(warehouse, dict) else None,
                    "supplier_order_number": supplier_order.get("order_number") if isinstance(supplier_order, dict) else None,
                    "supplier_name": supplier.get("name") if isinstance(supplier, dict) else None,
                }
            }
        
        return {"success": True, "inbound": inbound}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating inbound from supplier order: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create inbound: {str(e)}")


@router.get("/inbounds/{inbound_id}")
async def get_inbound(
    inbound_id: str,
    current_user=Depends(get_current_user)
):
    """Get 3PL inbound details with items."""
    user_id = str(current_user.id)
    
    try:
        # Get inbound
        inbound_response = supabase.table("tpl_inbounds")\
            .select("""
                *,
                tpl_warehouses(name, company, address_line1, city, state, zip_code, contact_name, contact_email, contact_phone),
                supplier_orders(order_number, suppliers(name, email, phone))
            """)\
            .eq("id", inbound_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not inbound_response.data:
            raise HTTPException(404, "3PL inbound not found")
        
        inbound = inbound_response.data
        
        # Get items with product details
        items_response = supabase.table("tpl_inbound_items")\
            .select("""
                *,
                products!inner(
                    id,
                    asin,
                    title,
                    image_url
                )
            """)\
            .eq("tpl_inbound_id", inbound_id)\
            .execute()
        
        items = []
        for item in items_response.data or []:
            product = item.get("products", {})
            if isinstance(product, list) and product:
                product = product[0]
            
            items.append({
                "id": item["id"],
                "product_id": item["product_id"],
                "supplier_order_item_id": item.get("supplier_order_item_id"),
                "quantity": item["quantity"],
                "quantity_received": item.get("quantity_received", 0),
                "quantity_prepped": item.get("quantity_prepped", 0),
                "prep_status": item.get("prep_status", "pending"),
                "prep_notes": item.get("prep_notes"),
                "notes": item.get("notes"),
                "product": {
                    "id": product.get("id") if isinstance(product, dict) else None,
                    "asin": product.get("asin") if isinstance(product, dict) else None,
                    "title": product.get("title") if isinstance(product, dict) else None,
                    "image_url": product.get("image_url") if isinstance(product, dict) else None,
                },
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })
        
        warehouse = inbound.get("tpl_warehouses", {})
        if isinstance(warehouse, list) and warehouse:
            warehouse = warehouse[0]
        
        supplier_order = inbound.get("supplier_orders", {})
        if isinstance(supplier_order, list) and supplier_order:
            supplier_order = supplier_order[0]
        
        supplier = supplier_order.get("suppliers", {}) if supplier_order else {}
        if isinstance(supplier, list) and supplier:
            supplier = supplier[0]
        
        inbound["items"] = items
        inbound["warehouse_name"] = warehouse.get("name") if isinstance(warehouse, dict) else None
        inbound["warehouse_company"] = warehouse.get("company") if isinstance(warehouse, dict) else None
        inbound["warehouse_address"] = f"{warehouse.get('address_line1', '')}, {warehouse.get('city', '')}, {warehouse.get('state', '')} {warehouse.get('zip_code', '')}".strip(", ") if isinstance(warehouse, dict) else None
        inbound["supplier_order_number"] = supplier_order.get("order_number") if isinstance(supplier_order, dict) else None
        inbound["supplier_name"] = supplier.get("name") if isinstance(supplier, dict) else None
        
        return {"inbound": inbound}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inbound: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get inbound: {str(e)}")


@router.put("/inbounds/{inbound_id}")
async def update_inbound(
    inbound_id: str,
    data: TPLInboundUpdate,
    current_user=Depends(get_current_user)
):
    """Update 3PL inbound."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("tpl_inbounds")\
            .select("id")\
            .eq("id", inbound_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "3PL inbound not found")
        
        # Build update data
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        
        # Handle status transitions
        if data.status:
            if data.status not in ["pending", "in_transit", "received", "prep_in_progress", "prep_complete", "ready_for_fba", "cancelled"]:
                raise HTTPException(400, "Invalid status")
            
            # Auto-set dates based on status
            if data.status == "received" and not update_data.get("received_date"):
                update_data["received_date"] = datetime.utcnow().isoformat()
            elif data.status == "prep_in_progress" and not update_data.get("prep_started_date"):
                update_data["prep_started_date"] = datetime.utcnow().isoformat()
            elif data.status == "prep_complete" and not update_data.get("prep_completed_date"):
                update_data["prep_completed_date"] = datetime.utcnow().isoformat()
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("tpl_inbounds")\
            .update(update_data)\
            .eq("id", inbound_id)\
            .execute()
        
        return {"inbound": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating inbound: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update inbound: {str(e)}")


@router.put("/inbounds/{inbound_id}/items/{item_id}")
async def update_inbound_item(
    inbound_id: str,
    item_id: str,
    quantity_received: Optional[int] = None,
    quantity_prepped: Optional[int] = None,
    prep_status: Optional[str] = None,
    prep_notes: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Update 3PL inbound item (received quantity, prep status)."""
    user_id = str(current_user.id)
    
    try:
        # Verify inbound ownership
        inbound_check = supabase.table("tpl_inbounds")\
            .select("id")\
            .eq("id", inbound_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not inbound_check.data:
            raise HTTPException(404, "3PL inbound not found")
        
        # Build update data
        update_data = {}
        if quantity_received is not None:
            update_data["quantity_received"] = quantity_received
        if quantity_prepped is not None:
            update_data["quantity_prepped"] = quantity_prepped
        if prep_status is not None:
            if prep_status not in ["pending", "in_progress", "complete", "not_required"]:
                raise HTTPException(400, "Invalid prep_status")
            update_data["prep_status"] = prep_status
        if prep_notes is not None:
            update_data["prep_notes"] = prep_notes
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("tpl_inbound_items")\
            .update(update_data)\
            .eq("id", item_id)\
            .eq("tpl_inbound_id", inbound_id)\
            .execute()
        
        return {"item": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating inbound item: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update inbound item: {str(e)}")


@router.delete("/inbounds/{inbound_id}")
async def delete_inbound(
    inbound_id: str,
    current_user=Depends(get_current_user)
):
    """Delete 3PL inbound (cascades to items)."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("tpl_inbounds")\
            .select("id")\
            .eq("id", inbound_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "3PL inbound not found")
        
        supabase.table("tpl_inbounds")\
            .delete()\
            .eq("id", inbound_id)\
            .execute()
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting inbound: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to delete inbound: {str(e)}")

