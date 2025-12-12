"""
FBA Shipment Creation API - Phase 5 Implementation
Create and manage FBA shipments from 3PL prepped inventory to Amazon FCs.
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

router = APIRouter(prefix="/fba-shipments", tags=["fba-shipments"])


class FBAShipmentCreate(BaseModel):
    tpl_inbound_id: str
    shipment_name: Optional[str] = None
    shipment_type: str = "SP"  # SP or LTL
    label_prep_type: str = "SELLER_LABEL"
    notes: Optional[str] = None


class FBAShipmentUpdate(BaseModel):
    shipment_name: Optional[str] = None
    status: Optional[str] = None
    shipment_type: Optional[str] = None
    label_prep_type: Optional[str] = None
    carrier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_date: Optional[str] = None
    delivered_date: Optional[str] = None
    received_date: Optional[str] = None
    estimated_shipping_cost: Optional[float] = None
    actual_shipping_cost: Optional[float] = None
    notes: Optional[str] = None


class FBAShipmentItemCreate(BaseModel):
    tpl_inbound_item_id: str
    quantity_shipped: int
    fnsku: Optional[str] = None
    seller_sku: Optional[str] = None
    prep_owner: str = "SELLER"
    notes: Optional[str] = None


@router.get("")
async def list_fba_shipments(
    status: Optional[str] = Query(None),
    tpl_inbound_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """List all FBA shipments for the current user."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table("fba_shipments")\
            .select("""
                *,
                tpl_inbounds(
                    id,
                    inbound_number,
                    warehouse_name: tpl_warehouses(name),
                    supplier_order_id,
                    supplier_orders(order_number, suppliers(name))
                )
            """)\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)
        
        if status:
            query = query.eq("status", status)
        if tpl_inbound_id:
            query = query.eq("tpl_inbound_id", tpl_inbound_id)
        
        response = query.execute()
        
        # Format response
        shipments = []
        for shipment in response.data or []:
            inbound = shipment.get("tpl_inbounds", {})
            if isinstance(inbound, list) and inbound:
                inbound = inbound[0]
            
            warehouse = inbound.get("tpl_warehouses", {}) if inbound else {}
            if isinstance(warehouse, list) and warehouse:
                warehouse = warehouse[0]
            
            supplier_order = inbound.get("supplier_orders", {}) if inbound else {}
            if isinstance(supplier_order, list) and supplier_order:
                supplier_order = supplier_order[0]
            
            supplier = supplier_order.get("suppliers", {}) if supplier_order else {}
            if isinstance(supplier, list) and supplier:
                supplier = supplier[0]
            
            shipments.append({
                **shipment,
                "inbound_number": inbound.get("inbound_number") if isinstance(inbound, dict) else None,
                "warehouse_name": warehouse.get("name") if isinstance(warehouse, dict) else None,
                "supplier_order_number": supplier_order.get("order_number") if isinstance(supplier_order, dict) else None,
                "supplier_name": supplier.get("name") if isinstance(supplier, dict) else None,
            })
        
        return {"fba_shipments": shipments}
    except Exception as e:
        logger.error(f"Error listing FBA shipments: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list FBA shipments: {str(e)}")


@router.post("/create-from-3pl-inbound")
async def create_fba_shipment_from_3pl_inbound(
    tpl_inbound_id: str,
    shipment_name: Optional[str] = None,
    shipment_type: str = "SP",
    label_prep_type: str = "SELLER_LABEL",
    item_selections: Optional[List[Dict[str, Any]]] = None,  # List of {tpl_inbound_item_id, quantity_shipped, fnsku}
    notes: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """
    Create an FBA shipment from a 3PL inbound.
    Automatically includes all prepped items, or use item_selections to specify.
    """
    user_id = str(current_user.id)
    
    try:
        # Verify 3PL inbound ownership and status
        inbound_response = supabase.table("tpl_inbounds")\
            .select("id, status, requires_prep")\
            .eq("id", tpl_inbound_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not inbound_response.data:
            raise HTTPException(404, "3PL inbound not found")
        
        inbound = inbound_response.data
        
        if inbound.get("status") not in ["prep_complete", "ready_for_fba"]:
            raise HTTPException(400, f"Cannot create FBA shipment from inbound with status: {inbound.get('status')}")
        
        # Get prepped items from inbound
        items_query = supabase.table("tpl_inbound_items")\
            .select("""
                *,
                products!inner(
                    id,
                    asin,
                    title,
                    image_url,
                    sell_price
                )
            """)\
            .eq("tpl_inbound_id", tpl_inbound_id)
        
        # If prep is required, only include items with prep_status = 'complete'
        if inbound.get("requires_prep"):
            items_query = items_query.eq("prep_status", "complete")
        
        items_response = items_query.execute()
        
        if not items_response.data:
            raise HTTPException(400, "No prepped items available for FBA shipment")
        
        # Generate shipment name if not provided
        if not shipment_name:
            shipment_name = f"FBA Shipment - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # Create FBA shipment
        shipment_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tpl_inbound_id": tpl_inbound_id,
            "shipment_name": shipment_name,
            "shipment_type": shipment_type,
            "label_prep_type": label_prep_type,
            "status": "draft",
            "notes": notes,
            "created_date": datetime.utcnow().isoformat()
        }
        
        shipment_response = supabase.table("fba_shipments")\
            .insert(shipment_data)\
            .execute()
        
        if not shipment_response.data:
            raise HTTPException(500, "Failed to create FBA shipment")
        
        shipment = shipment_response.data[0]
        shipment_id = shipment["id"]
        
        # Create shipment items
        shipment_items = []
        fnsku_labels = []
        
        # Use item_selections if provided, otherwise use all prepped items
        items_to_ship = item_selections if item_selections else [
            {
                "tpl_inbound_item_id": item.get("id"),
                "quantity_shipped": item.get("quantity_prepped", item.get("quantity", 1)),
                "fnsku": None,  # Will be generated or fetched from SP-API
                "seller_sku": None
            }
            for item in items_response.data
        ]
        
        for item_selection in items_to_ship:
            # Find the corresponding inbound item
            inbound_item = next(
                (item for item in items_response.data if item.get("id") == item_selection.get("tpl_inbound_item_id")),
                None
            )
            
            if not inbound_item:
                logger.warning(f"Inbound item {item_selection.get('tpl_inbound_item_id')} not found, skipping")
                continue
            
            product = inbound_item.get("products", {})
            if isinstance(product, list) and product:
                product = product[0]
            
            quantity_shipped = item_selection.get("quantity_shipped", inbound_item.get("quantity_prepped", inbound_item.get("quantity", 1)))
            
            if quantity_shipped <= 0:
                continue
            
            # Get or generate FNSKU
            fnsku = item_selection.get("fnsku")
            if not fnsku:
                # Try to get FNSKU from product or generate placeholder
                # In production, this would call SP-API to get actual FNSKU
                fnsku = f"FNSKU_{product.get('asin', 'UNKNOWN')}" if isinstance(product, dict) else "FNSKU_UNKNOWN"
            
            seller_sku = item_selection.get("seller_sku") or f"SKU_{product.get('asin', 'UNKNOWN')}" if isinstance(product, dict) else "SKU_UNKNOWN"
            
            # Create shipment item
            shipment_item_data = {
                "id": str(uuid.uuid4()),
                "fba_shipment_id": shipment_id,
                "tpl_inbound_item_id": inbound_item.get("id"),
                "product_id": inbound_item.get("product_id"),
                "asin": product.get("asin") if isinstance(product, dict) else None,
                "seller_sku": seller_sku,
                "fnsku": fnsku,
                "quantity_shipped": quantity_shipped,
                "quantity_received": 0,
                "prep_owner": item_selection.get("prep_owner", "SELLER"),
                "notes": item_selection.get("notes")
            }
            
            shipment_items.append(shipment_item_data)
            
            # Create FNSKU label record
            fnsku_label_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "product_id": inbound_item.get("product_id"),
                "fba_shipment_item_id": shipment_item_data["id"],
                "fnsku": fnsku,
                "asin": product.get("asin") if isinstance(product, dict) else None,
                "seller_sku": seller_sku,
                "status": "pending",
                "quantity": quantity_shipped
            }
            
            fnsku_labels.append(fnsku_label_data)
        
        # Bulk insert shipment items
        if shipment_items:
            items_response = supabase.table("fba_shipment_items")\
                .insert(shipment_items)\
                .execute()
            
            # Update FNSKU label records with actual shipment item IDs
            for i, label in enumerate(fnsku_labels):
                if items_response.data and i < len(items_response.data):
                    label["fba_shipment_item_id"] = items_response.data[i]["id"]
            
            # Bulk insert FNSKU labels
            if fnsku_labels:
                supabase.table("fnsku_labels")\
                    .insert(fnsku_labels)\
                    .execute()
        
        # Get updated shipment with summary
        updated_shipment = supabase.table("fba_shipments")\
            .select("""
                *,
                tpl_inbounds(
                    id,
                    inbound_number,
                    warehouse_name: tpl_warehouses(name),
                    supplier_order_id,
                    supplier_orders(order_number, suppliers(name))
                )
            """)\
            .eq("id", shipment_id)\
            .single()\
            .execute()
        
        if updated_shipment.data:
            shipment_data = updated_shipment.data
            inbound = shipment_data.get("tpl_inbounds", {})
            if isinstance(inbound, list) and inbound:
                inbound = inbound[0]
            
            return {
                "success": True,
                "fba_shipment": {
                    **shipment_data,
                    "items_count": len(shipment_items)
                }
            }
        
        return {"success": True, "fba_shipment": shipment}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating FBA shipment from 3PL inbound: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create FBA shipment: {str(e)}")


@router.get("/{shipment_id}")
async def get_fba_shipment(
    shipment_id: str,
    current_user=Depends(get_current_user)
):
    """Get FBA shipment details with items and boxes."""
    user_id = str(current_user.id)
    
    try:
        # Get shipment
        shipment_response = supabase.table("fba_shipments")\
            .select("""
                *,
                tpl_inbounds(
                    id,
                    inbound_number,
                    warehouse_name: tpl_warehouses(name),
                    supplier_order_id,
                    supplier_orders(order_number, suppliers(name))
                )
            """)\
            .eq("id", shipment_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not shipment_response.data:
            raise HTTPException(404, "FBA shipment not found")
        
        shipment = shipment_response.data
        
        # Get items with product details
        items_response = supabase.table("fba_shipment_items")\
            .select("""
                *,
                products!inner(
                    id,
                    asin,
                    title,
                    image_url,
                    sell_price
                ),
                fnsku_labels(status, generated_at, printed_at, applied_at)
            """)\
            .eq("fba_shipment_id", shipment_id)\
            .execute()
        
        items = []
        for item in items_response.data or []:
            product = item.get("products", {})
            if isinstance(product, list) and product:
                product = product[0]
            
            fnsku_label = item.get("fnsku_labels", {})
            if isinstance(fnsku_label, list) and fnsku_label:
                fnsku_label = fnsku_label[0]
            
            items.append({
                "id": item["id"],
                "product_id": item["product_id"],
                "tpl_inbound_item_id": item.get("tpl_inbound_item_id"),
                "asin": item.get("asin"),
                "seller_sku": item.get("seller_sku"),
                "fnsku": item.get("fnsku"),
                "quantity_shipped": item.get("quantity_shipped", 0),
                "quantity_received": item.get("quantity_received", 0),
                "quantity_in_case": item.get("quantity_in_case", 1),
                "prep_owner": item.get("prep_owner", "SELLER"),
                "box_id": item.get("box_id"),
                "notes": item.get("notes"),
                "product": {
                    "id": product.get("id") if isinstance(product, dict) else None,
                    "asin": product.get("asin") if isinstance(product, dict) else None,
                    "title": product.get("title") if isinstance(product, dict) else None,
                    "image_url": product.get("image_url") if isinstance(product, dict) else None,
                    "sell_price": float(product.get("sell_price", 0)) if isinstance(product, dict) and product.get("sell_price") else None,
                },
                "fnsku_label": {
                    "status": fnsku_label.get("status") if isinstance(fnsku_label, dict) else None,
                    "generated_at": fnsku_label.get("generated_at") if isinstance(fnsku_label, dict) else None,
                    "printed_at": fnsku_label.get("printed_at") if isinstance(fnsku_label, dict) else None,
                    "applied_at": fnsku_label.get("applied_at") if isinstance(fnsku_label, dict) else None,
                } if isinstance(fnsku_label, dict) else None,
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })
        
        # Get boxes
        boxes_response = supabase.table("fba_shipment_boxes")\
            .select("*")\
            .eq("fba_shipment_id", shipment_id)\
            .order("box_number")\
            .execute()
        
        boxes = boxes_response.data or []
        
        inbound = shipment.get("tpl_inbounds", {})
        if isinstance(inbound, list) and inbound:
            inbound = inbound[0]
        
        shipment["items"] = items
        shipment["boxes"] = boxes
        shipment["inbound_number"] = inbound.get("inbound_number") if isinstance(inbound, dict) else None
        
        return {"fba_shipment": shipment}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting FBA shipment: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get FBA shipment: {str(e)}")


@router.put("/{shipment_id}")
async def update_fba_shipment(
    shipment_id: str,
    data: FBAShipmentUpdate,
    current_user=Depends(get_current_user)
):
    """Update FBA shipment."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("fba_shipments")\
            .select("id")\
            .eq("id", shipment_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "FBA shipment not found")
        
        # Build update data
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        
        # Handle status transitions
        if data.status:
            if data.status not in ["draft", "working", "ready_to_ship", "shipped", "in_transit", "delivered", "received", "closed", "cancelled"]:
                raise HTTPException(400, "Invalid status")
            
            # Auto-set dates based on status
            if data.status == "shipped" and not update_data.get("shipped_date"):
                update_data["shipped_date"] = datetime.utcnow().isoformat()
            elif data.status == "delivered" and not update_data.get("delivered_date"):
                update_data["delivered_date"] = datetime.utcnow().isoformat()
            elif data.status == "received" and not update_data.get("received_date"):
                update_data["received_date"] = datetime.utcnow().isoformat()
            elif data.status == "closed" and not update_data.get("closed_date"):
                update_data["closed_date"] = datetime.utcnow().isoformat()
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("fba_shipments")\
            .update(update_data)\
            .eq("id", shipment_id)\
            .execute()
        
        return {"fba_shipment": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating FBA shipment: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update FBA shipment: {str(e)}")


@router.put("/{shipment_id}/items/{item_id}")
async def update_fba_shipment_item(
    shipment_id: str,
    item_id: str,
    quantity_received: Optional[int] = None,
    box_id: Optional[str] = None,
    notes: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Update FBA shipment item (received quantity, box assignment)."""
    user_id = str(current_user.id)
    
    try:
        # Verify shipment ownership
        shipment_check = supabase.table("fba_shipments")\
            .select("id")\
            .eq("id", shipment_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not shipment_check.data:
            raise HTTPException(404, "FBA shipment not found")
        
        # Build update data
        update_data = {}
        if quantity_received is not None:
            update_data["quantity_received"] = quantity_received
        if box_id is not None:
            update_data["box_id"] = box_id
        if notes is not None:
            update_data["notes"] = notes
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("fba_shipment_items")\
            .update(update_data)\
            .eq("id", item_id)\
            .eq("fba_shipment_id", shipment_id)\
            .execute()
        
        return {"item": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating FBA shipment item: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update FBA shipment item: {str(e)}")


@router.post("/{shipment_id}/boxes")
async def add_box_to_shipment(
    shipment_id: str,
    box_number: int,
    box_name: Optional[str] = None,
    weight: Optional[float] = None,
    dimensions_length: Optional[float] = None,
    dimensions_width: Optional[float] = None,
    dimensions_height: Optional[float] = None,
    tracking_number: Optional[str] = None,
    notes: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Add a box to FBA shipment."""
    user_id = str(current_user.id)
    
    try:
        # Verify shipment ownership
        shipment_check = supabase.table("fba_shipments")\
            .select("id")\
            .eq("id", shipment_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not shipment_check.data:
            raise HTTPException(404, "FBA shipment not found")
        
        box_data = {
            "id": str(uuid.uuid4()),
            "fba_shipment_id": shipment_id,
            "box_number": box_number,
            "box_name": box_name or f"Box {box_number}",
            "weight": weight,
            "dimensions_length": dimensions_length,
            "dimensions_width": dimensions_width,
            "dimensions_height": dimensions_height,
            "tracking_number": tracking_number,
            "status": "pending",
            "notes": notes
        }
        
        response = supabase.table("fba_shipment_boxes")\
            .insert(box_data)\
            .execute()
        
        return {"box": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding box to shipment: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to add box: {str(e)}")


@router.delete("/{shipment_id}")
async def delete_fba_shipment(
    shipment_id: str,
    current_user=Depends(get_current_user)
):
    """Delete FBA shipment (cascades to items and boxes)."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("fba_shipments")\
            .select("id")\
            .eq("id", shipment_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "FBA shipment not found")
        
        supabase.table("fba_shipments")\
            .delete()\
            .eq("id", shipment_id)\
            .execute()
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting FBA shipment: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to delete FBA shipment: {str(e)}")


@router.post("/{shipment_id}/generate-fnsku-labels")
async def generate_fnsku_labels(
    shipment_id: str,
    current_user=Depends(get_current_user)
):
    """
    Generate FNSKU labels for all items in shipment.
    In production, this would call SP-API to get actual FNSKU labels.
    For now, it marks labels as 'generated' and creates placeholder records.
    """
    user_id = str(current_user.id)
    
    try:
        # Verify shipment ownership
        shipment_check = supabase.table("fba_shipments")\
            .select("id")\
            .eq("id", shipment_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not shipment_check.data:
            raise HTTPException(404, "FBA shipment not found")
        
        # Get all shipment items
        items_response = supabase.table("fba_shipment_items")\
            .select("id, fnsku, asin, seller_sku")\
            .eq("fba_shipment_id", shipment_id)\
            .execute()
        
        if not items_response.data:
            raise HTTPException(400, "No items in shipment")
        
        # Update FNSKU labels to 'generated' status
        # In production, this would:
        # 1. Call SP-API Fulfillment Inbound API to get FNSKU
        # 2. Generate label files (PDF/PNG/ZPL)
        # 3. Store label files
        # 4. Update label records
        
        label_ids = []
        for item in items_response.data:
            label_response = supabase.table("fnsku_labels")\
                .update({
                    "status": "generated",
                    "generated_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("fba_shipment_item_id", item["id"])\
                .execute()
            
            if label_response.data:
                label_ids.extend([label["id"] for label in label_response.data])
        
        return {
            "success": True,
            "labels_generated": len(label_ids),
            "message": "FNSKU labels generated. In production, this would call SP-API to get actual labels."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating FNSKU labels: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to generate FNSKU labels: {str(e)}")

