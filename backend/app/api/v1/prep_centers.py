"""
Prep Centers API
Manages 3PL/prep centers, fees, product assignments, and work orders.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging
import uuid

from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.prep_center_service import PrepCenterService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prep-centers", tags=["prep-centers"])


class PrepCenterCreate(BaseModel):
    company_name: str
    short_code: Optional[str] = None
    website: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    business_hours: Optional[str] = None
    shipping_address_line1: str
    shipping_address_line2: Optional[str] = None
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str = "USA"
    billing_email: Optional[str] = None
    payment_terms: Optional[str] = None
    account_number: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = {}
    max_pallet_capacity: Optional[int] = None
    storage_available: bool = True
    free_storage_days: int = 30
    api_available: bool = False
    api_endpoint: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    notes: Optional[str] = None
    status: str = "active"


class PrepCenterFeeCreate(BaseModel):
    service_name: str
    service_code: Optional[str] = None
    service_category: Optional[str] = None
    fee_type: str  # 'per_unit', 'per_pound', 'per_pallet', 'per_day', 'percentage', 'flat'
    base_cost: Optional[float] = None
    percentage_rate: Optional[float] = None
    minimum_charge: Optional[float] = None
    maximum_charge: Optional[float] = None
    tiered_pricing: Optional[List[Dict[str, Any]]] = None
    includes: Optional[str] = None
    requirements: Optional[str] = None
    size_category: Optional[str] = None
    max_dimensions: Optional[str] = None
    max_weight: Optional[float] = None
    applies_to_hazmat: bool = True
    applies_to_oversized: bool = True
    applies_to_standard: bool = True
    description: Optional[str] = None
    display_order: int = 0


class ProductPrepAssignmentRequest(BaseModel):
    product_id: str
    prep_center_id: Optional[str] = None  # If None, auto-assign
    strategy: str = "cheapest"  # 'cheapest', 'fastest', 'capability'


@router.post("")
async def create_prep_center(
    prep_center: PrepCenterCreate,
    current_user=Depends(get_current_user)
):
    """Create a new prep center."""
    user_id = str(current_user.id)
    
    try:
        data = prep_center.dict(exclude_none=True)
        data["user_id"] = user_id
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("prep_centers").insert(data).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to create prep center")
        
        return {"prep_center": result.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prep center: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create prep center: {str(e)}")


@router.get("")
async def list_prep_centers(
    current_user=Depends(get_current_user)
):
    """List all prep centers for user."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("prep_centers")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("company_name")\
            .execute()
        
        return {"prep_centers": result.data or []}
        
    except Exception as e:
        logger.error(f"Error listing prep centers: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list prep centers: {str(e)}")


@router.get("/{prep_center_id}")
async def get_prep_center(
    prep_center_id: str,
    current_user=Depends(get_current_user)
):
    """Get prep center details."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("prep_centers")\
            .select("*")\
            .eq("id", prep_center_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(404, "Prep center not found")
        
        return {"prep_center": result.data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prep center: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get prep center: {str(e)}")


@router.put("/{prep_center_id}")
async def update_prep_center(
    prep_center_id: str,
    prep_center: PrepCenterCreate,
    current_user=Depends(get_current_user)
):
    """Update prep center."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("prep_centers")\
            .select("id")\
            .eq("id", prep_center_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Prep center not found")
        
        data = prep_center.dict(exclude_none=True)
        data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("prep_centers")\
            .update(data)\
            .eq("id", prep_center_id)\
            .execute()
        
        return {"prep_center": result.data[0] if result.data else None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prep center: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update prep center: {str(e)}")


@router.delete("/{prep_center_id}")
async def delete_prep_center(
    prep_center_id: str,
    current_user=Depends(get_current_user)
):
    """Delete prep center."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("prep_centers")\
            .select("id")\
            .eq("id", prep_center_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Prep center not found")
        
        supabase.table("prep_centers")\
            .delete()\
            .eq("id", prep_center_id)\
            .execute()
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prep center: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to delete prep center: {str(e)}")


@router.post("/{prep_center_id}/fees")
async def create_fee(
    prep_center_id: str,
    fee: PrepCenterFeeCreate,
    current_user=Depends(get_current_user)
):
    """Add a fee to a prep center."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        check = supabase.table("prep_centers")\
            .select("id")\
            .eq("id", prep_center_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not check.data:
            raise HTTPException(404, "Prep center not found")
        
        data = fee.dict(exclude_none=True)
        data["prep_center_id"] = prep_center_id
        data["user_id"] = user_id
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("prep_center_fees").insert(data).execute()
        
        return {"fee": result.data[0] if result.data else None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fee: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create fee: {str(e)}")


@router.get("/{prep_center_id}/fees")
async def list_fees(
    prep_center_id: str,
    current_user=Depends(get_current_user)
):
    """List all fees for a prep center."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("prep_center_fees")\
            .select("*")\
            .eq("prep_center_id", prep_center_id)\
            .eq("user_id", user_id)\
            .order("display_order, service_name")\
            .execute()
        
        return {"fees": result.data or []}
        
    except Exception as e:
        logger.error(f"Error listing fees: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to list fees: {str(e)}")


@router.post("/products/{product_id}/assign")
async def assign_product_to_prep(
    product_id: str,
    request: ProductPrepAssignmentRequest = Body(...),
    current_user=Depends(get_current_user)
):
    """Assign product to prep center (auto or manual)."""
    user_id = str(current_user.id)
    
    try:
        # Get product
        product_res = supabase.table("products")\
            .select("*")\
            .eq("id", product_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not product_res.data:
            raise HTTPException(404, "Product not found")
        
        product = product_res.data
        
        # Auto-assign or use provided center
        if not request.prep_center_id:
            assignment = PrepCenterService.auto_assign_prep_center(
                product, user_id, request.strategy
            )
            
            if not assignment:
                raise HTTPException(400, "Could not auto-assign prep center")
            
            prep_center_id = assignment["prep_center_id"]
            required_services = assignment["required_services"]
            total_prep_cost = assignment["total_prep_cost_per_unit"]
            breakdown = assignment["breakdown"]
            assignment_reason = assignment["assignment_reason"]
        else:
            # Manual assignment - determine services and calculate cost
            required_services = PrepCenterService.determine_required_services(product)
            
            # Match services to fees
            matched_services = []
            for service in required_services:
                service_code = service.get("service_code")
                fee = PrepCenterService.find_matching_fees(
                    request.prep_center_id, service_code, product
                )
                
                if fee:
                    matched_services.append({
                        "service_code": service_code,
                        "service_name": service.get("service_name"),
                        "fee_id": fee["id"]
                    })
            
            # Calculate cost
            cost_result = PrepCenterService.calculate_prep_cost(
                product, request.prep_center_id, matched_services, quantity=1
            )
            
            prep_center_id = request.prep_center_id
            required_services = matched_services
            total_prep_cost = cost_result.get("unit_cost", 0)
            breakdown = cost_result.get("breakdown", {})
            assignment_reason = "manual"
        
        # Deactivate existing assignment
        supabase.table("product_prep_assignments")\
            .update({"is_active": False})\
            .eq("product_id", product_id)\
            .eq("user_id", user_id)\
            .execute()
        
        # Create new assignment
        assignment_data = {
            "product_id": product_id,
            "prep_center_id": prep_center_id,
            "user_id": user_id,
            "assignment_reason": assignment_reason,
            "required_services": required_services,
            "total_prep_cost_per_unit": total_prep_cost,
            "breakdown": breakdown,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("product_prep_assignments").insert(assignment_data).execute()
        
        # Update product with prep cost
        supabase.table("products")\
            .update({
                "prep_cost_per_unit": total_prep_cost,
                "prep_center_id": prep_center_id,
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", product_id)\
            .execute()
        
        return {
            "assignment": result.data[0] if result.data else None,
            "prep_cost_per_unit": total_prep_cost,
            "breakdown": breakdown
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning product to prep: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to assign product: {str(e)}")


@router.get("/products/{product_id}/assignment")
async def get_product_assignment(
    product_id: str,
    current_user=Depends(get_current_user)
):
    """Get prep center assignment for a product."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table("product_prep_assignments")\
            .select("*, prep_centers(*)")\
            .eq("product_id", product_id)\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .single()\
            .execute()
        
        if not result.data:
            return {"assignment": None}
        
        return {"assignment": result.data}
        
    except Exception as e:
        logger.error(f"Error getting assignment: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get assignment: {str(e)}")


@router.post("/products/auto-assign")
async def auto_assign_multiple_products(
    product_ids: List[str] = Body(...),
    strategy: str = Body("cheapest"),
    current_user=Depends(get_current_user)
):
    """Auto-assign multiple products to prep centers."""
    user_id = str(current_user.id)
    
    try:
        assignments = []
        
        for product_id in product_ids:
            # Get product
            product_res = supabase.table("products")\
                .select("*")\
                .eq("id", product_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if not product_res.data:
                continue
            
            product = product_res.data
            
            # Auto-assign
            assignment = PrepCenterService.auto_assign_prep_center(product, user_id, strategy)
            
            if assignment:
                # Save assignment (same logic as single assignment)
                supabase.table("product_prep_assignments")\
                    .update({"is_active": False})\
                    .eq("product_id", product_id)\
                    .eq("user_id", user_id)\
                    .execute()
                
                assignment_data = {
                    "product_id": product_id,
                    "prep_center_id": assignment["prep_center_id"],
                    "user_id": user_id,
                    "assignment_reason": assignment["assignment_reason"],
                    "required_services": assignment["required_services"],
                    "total_prep_cost_per_unit": assignment["total_prep_cost_per_unit"],
                    "breakdown": assignment["breakdown"],
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                supabase.table("product_prep_assignments").insert(assignment_data).execute()
                
                # Update product
                supabase.table("products")\
                    .update({
                        "prep_cost_per_unit": assignment["total_prep_cost_per_unit"],
                        "prep_center_id": assignment["prep_center_id"]
                    })\
                    .eq("id", product_id)\
                    .execute()
                
                assignments.append({
                    "product_id": product_id,
                    "prep_center_id": assignment["prep_center_id"],
                    "prep_cost": assignment["total_prep_cost_per_unit"]
                })
        
        return {
            "assigned": len(assignments),
            "total": len(product_ids),
            "assignments": assignments
        }
        
    except Exception as e:
        logger.error(f"Error auto-assigning products: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to auto-assign products: {str(e)}")

