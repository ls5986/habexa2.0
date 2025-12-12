"""
Upload Templates API
Manage CSV/Excel column mapping templates.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.api.deps import get_current_user
from app.services.upload_template_service import UploadTemplateService

router = APIRouter(prefix="/upload-templates", tags=["upload-templates"])


class CreateTemplateRequest(BaseModel):
    name: str
    supplier_id: Optional[str] = None
    column_mappings: Dict[str, str] = {}
    default_values: Dict[str, Any] = {}
    validation_rules: List[Dict[str, Any]] = []
    transformations: List[Dict[str, Any]] = []
    is_default: bool = False


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    column_mappings: Optional[Dict[str, str]] = None
    default_values: Optional[Dict[str, Any]] = None
    validation_rules: Optional[List[Dict[str, Any]]] = None
    transformations: Optional[List[Dict[str, Any]]] = None
    is_default: Optional[bool] = None


@router.post("")
async def create_template(
    request: CreateTemplateRequest,
    current_user = Depends(get_current_user)
):
    """Create a new upload template."""
    service = UploadTemplateService(user_id=str(current_user.id))
    
    template = await service.create_template(
        name=request.name,
        supplier_id=request.supplier_id,
        column_mappings=request.column_mappings,
        default_values=request.default_values,
        validation_rules=request.validation_rules,
        transformations=request.transformations,
        is_default=request.is_default
    )
    
    if not template:
        raise HTTPException(500, "Failed to create template")
    
    return template


@router.get("")
async def list_templates(
    supplier_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """List all upload templates."""
    service = UploadTemplateService(user_id=str(current_user.id))
    templates = await service.list_templates(supplier_id=supplier_id)
    return {"templates": templates, "count": len(templates)}


@router.get("/default")
async def get_default_template(
    supplier_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get the default template for a supplier."""
    service = UploadTemplateService(user_id=str(current_user.id))
    template = await service.get_default_template(supplier_id=supplier_id)
    
    if not template:
        raise HTTPException(404, "No default template found")
    
    return template


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific template."""
    service = UploadTemplateService(user_id=str(current_user.id))
    template = await service.get_template(template_id)
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    return template


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    current_user = Depends(get_current_user)
):
    """Update a template."""
    service = UploadTemplateService(user_id=str(current_user.id))
    
    template = await service.update_template(
        template_id=template_id,
        name=request.name,
        column_mappings=request.column_mappings,
        default_values=request.default_values,
        validation_rules=request.validation_rules,
        transformations=request.transformations,
        is_default=request.is_default
    )
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a template."""
    service = UploadTemplateService(user_id=str(current_user.id))
    success = await service.delete_template(template_id)
    
    if not success:
        raise HTTPException(404, "Template not found")
    
    return {"success": True, "message": "Template deleted"}


@router.post("/auto-detect")
async def auto_detect_template(
    headers: List[str],
    supplier_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Auto-detect which template to use based on file headers."""
    service = UploadTemplateService(user_id=str(current_user.id))
    template = await service.auto_detect_template(headers, supplier_id=supplier_id)
    
    if not template:
        return {"template": None, "message": "No matching template found"}
    
    return {"template": template, "message": "Template matched successfully"}

