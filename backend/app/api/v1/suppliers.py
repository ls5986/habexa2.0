from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.feature_gate import feature_gate, require_limit
from app.core.exceptions import NotFoundError

router = APIRouter()


class SupplierCreate(BaseModel):
    name: str
    telegram_username: Optional[str] = None
    telegram_channel_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    telegram_username: Optional[str] = None
    telegram_channel_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    rating: Optional[float] = None
    avg_lead_time_days: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_suppliers(current_user=Depends(get_current_user)):
    """List all suppliers."""
    
    result = supabase.table("suppliers").select("*").eq("user_id", current_user.id).order("created_at", desc=True).execute()
    
    # Add limit info
    check = await feature_gate.check_limit(current_user, "suppliers")
    
    return {
        "suppliers": result.data,
        "count": len(result.data),
        "limit": check.get("limit"),
        "remaining": check.get("remaining"),
        "unlimited": check.get("unlimited", False)
    }


@router.post("")
async def create_supplier(
    supplier: SupplierCreate,
    current_user=Depends(require_limit("suppliers"))
):
    """Create a new supplier. Enforces supplier limit based on tier."""
    
    try:
        data = supplier.dict(exclude_none=True)  # Remove None values
        data["user_id"] = str(current_user.id)
        
        # Ensure is_active is set
        if "is_active" not in data:
            data["is_active"] = True
        
        result = supabase.table("suppliers").insert(data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create supplier")
        
        # Get updated limit info
        check = await feature_gate.check_limit(current_user, "suppliers")
        
        return {
            "supplier": result.data[0],
            "limit_info": {
                "remaining": check.get("remaining"),
                "limit": check.get("limit"),
                "unlimited": check.get("unlimited", False)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating supplier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create supplier: {str(e)}")


@router.get("/{supplier_id}")
async def get_supplier(supplier_id: str, current_user=Depends(get_current_user)):
    """Get single supplier."""
    
    result = supabase.table("suppliers").select("*").eq("id", supplier_id).eq("user_id", current_user.id).single().execute()
    
    if not result.data:
        raise NotFoundError("Supplier")
    
    return result.data


@router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    supplier: SupplierUpdate,
    current_user=Depends(get_current_user)
):
    """Update supplier."""
    
    data = {k: v for k, v in supplier.dict().items() if v is not None}
    
    result = supabase.table("suppliers").update(data).eq("id", supplier_id).eq("user_id", current_user.id).execute()
    
    if not result.data:
        raise NotFoundError("Supplier")
    
    return result.data[0]


@router.delete("/{supplier_id}")
async def delete_supplier(supplier_id: str, current_user=Depends(get_current_user)):
    """Delete supplier."""
    
    supabase.table("suppliers").delete().eq("id", supplier_id).eq("user_id", current_user.id).execute()
    
    return {"success": True}


@router.get("/{supplier_id}/deals")
async def get_supplier_deals(supplier_id: str, current_user=Depends(get_current_user)):
    """Get deals for a supplier."""
    
    result = supabase.table("deals").select("*").eq("supplier_id", supplier_id).eq("user_id", current_user.id).order("created_at", desc=True).execute()
    
    return result.data

