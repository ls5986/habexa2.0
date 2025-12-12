"""
Supplier Template Management API
Handles CRUD operations for supplier templates, template testing, and versioning.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import io
import logging

from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.template_engine import TemplateEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    supplier_id: str
    template_name: str
    description: Optional[str] = None
    file_format: str  # 'xlsx', 'csv', 'tsv'
    sheet_name: Optional[str] = None
    header_row: int = 1
    data_start_row: int = 2
    column_mappings: Dict[str, str] = {}
    calculations: List[Dict[str, Any]] = []
    default_values: Dict[str, Any] = {}
    validation_rules: Dict[str, Any] = {}
    transformations: List[Dict[str, Any]] = []
    row_filters: List[Dict[str, Any]] = []
    filename_pattern: Optional[str] = None
    column_fingerprint: Optional[List[str]] = None


class TemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    description: Optional[str] = None
    column_mappings: Optional[Dict[str, str]] = None
    calculations: Optional[List[Dict[str, Any]]] = None
    default_values: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    transformations: Optional[List[Dict[str, Any]]] = None
    row_filters: Optional[List[Dict[str, Any]]] = None
    filename_pattern: Optional[str] = None
    column_fingerprint: Optional[List[str]] = None
    is_active: Optional[bool] = None


@router.post("")
async def create_template(
    template: TemplateCreate,
    current_user=Depends(get_current_user)
):
    """Create a new supplier template."""
    user_id = str(current_user.id)
    
    try:
        # Verify supplier ownership
        supplier_check = supabase.table("suppliers")\
            .select("id")\
            .eq("id", template.supplier_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not supplier_check.data:
            raise HTTPException(404, "Supplier not found")
        
        # Create template
        template_data = {
            "supplier_id": template.supplier_id,
            "user_id": user_id,
            "template_name": template.template_name,
            "description": template.description,
            "file_format": template.file_format,
            "sheet_name": template.sheet_name,
            "header_row": template.header_row,
            "data_start_row": template.data_start_row,
            "column_mappings": template.column_mappings,
            "calculations": template.calculations,
            "default_values": template.default_values,
            "validation_rules": template.validation_rules,
            "transformations": template.transformations,
            "row_filters": template.row_filters,
            "filename_pattern": template.filename_pattern,
            "column_fingerprint": template.column_fingerprint,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("supplier_templates")\
            .insert(template_data)\
            .execute()
        
        return {"template": result.data[0] if result.data else None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to create template: {str(e)}")


@router.get("/supplier/{supplier_id}")
async def get_supplier_templates(
    supplier_id: str,
    current_user=Depends(get_current_user)
):
    """Get all templates for a supplier."""
    user_id = str(current_user.id)
    
    try:
        # Verify supplier ownership
        supplier_check = supabase.table("suppliers")\
            .select("id")\
            .eq("id", supplier_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not supplier_check.data:
            raise HTTPException(404, "Supplier not found")
        
        # Get templates
        templates = supabase.table("supplier_templates")\
            .select("*")\
            .eq("supplier_id", supplier_id)\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {"templates": templates.data or []}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting templates: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get templates: {str(e)}")


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user=Depends(get_current_user)
):
    """Get template details."""
    user_id = str(current_user.id)
    
    try:
        template = supabase.table("supplier_templates")\
            .select("*")\
            .eq("id", template_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not template.data:
            raise HTTPException(404, "Template not found")
        
        return {"template": template.data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get template: {str(e)}")


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    current_user=Depends(get_current_user)
):
    """Update a template."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        template_check = supabase.table("supplier_templates")\
            .select("id")\
            .eq("id", template_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not template_check.data:
            raise HTTPException(404, "Template not found")
        
        # Build update data
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if template_update.template_name:
            update_data["template_name"] = template_update.template_name
        if template_update.description is not None:
            update_data["description"] = template_update.description
        if template_update.column_mappings is not None:
            update_data["column_mappings"] = template_update.column_mappings
        if template_update.calculations is not None:
            update_data["calculations"] = template_update.calculations
        if template_update.default_values is not None:
            update_data["default_values"] = template_update.default_values
        if template_update.validation_rules is not None:
            update_data["validation_rules"] = template_update.validation_rules
        if template_update.transformations is not None:
            update_data["transformations"] = template_update.transformations
        if template_update.row_filters is not None:
            update_data["row_filters"] = template_update.row_filters
        if template_update.filename_pattern is not None:
            update_data["filename_pattern"] = template_update.filename_pattern
        if template_update.column_fingerprint is not None:
            update_data["column_fingerprint"] = template_update.column_fingerprint
        if template_update.is_active is not None:
            update_data["is_active"] = template_update.is_active
        
        # Create version snapshot before update
        old_template = template_check.data
        version_data = {
            "template_id": template_id,
            "version_number": (old_template.get("usage_count", 0) + 1),
            "column_mappings": old_template.get("column_mappings"),
            "calculations": old_template.get("calculations"),
            "default_values": old_template.get("default_values"),
            "validation_rules": old_template.get("validation_rules"),
            "transformations": old_template.get("transformations"),
            "row_filters": old_template.get("row_filters"),
            "changed_by": user_id,
            "change_description": "Template updated",
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("template_versions").insert(version_data).execute()
        
        # Update template
        result = supabase.table("supplier_templates")\
            .update(update_data)\
            .eq("id", template_id)\
            .execute()
        
        return {"template": result.data[0] if result.data else None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update template: {str(e)}")


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user=Depends(get_current_user)
):
    """Delete a template."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        template_check = supabase.table("supplier_templates")\
            .select("id")\
            .eq("id", template_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not template_check.data:
            raise HTTPException(404, "Template not found")
        
        # Delete template
        supabase.table("supplier_templates")\
            .delete()\
            .eq("id", template_id)\
            .execute()
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to delete template: {str(e)}")


@router.post("/{template_id}/duplicate")
async def duplicate_template(
    template_id: str,
    new_name: str,
    current_user=Depends(get_current_user)
):
    """Duplicate a template."""
    user_id = str(current_user.id)
    
    try:
        # Get original template
        original = supabase.table("supplier_templates")\
            .select("*")\
            .eq("id", template_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not original.data:
            raise HTTPException(404, "Template not found")
        
        orig_data = original.data
        
        # Create duplicate
        duplicate_data = {
            "supplier_id": orig_data["supplier_id"],
            "user_id": user_id,
            "template_name": new_name,
            "description": orig_data.get("description"),
            "file_format": orig_data.get("file_format"),
            "sheet_name": orig_data.get("sheet_name"),
            "header_row": orig_data.get("header_row", 1),
            "data_start_row": orig_data.get("data_start_row", 2),
            "column_mappings": orig_data.get("column_mappings", {}),
            "calculations": orig_data.get("calculations", []),
            "default_values": orig_data.get("default_values", {}),
            "validation_rules": orig_data.get("validation_rules", {}),
            "transformations": orig_data.get("transformations", []),
            "row_filters": orig_data.get("row_filters", []),
            "filename_pattern": orig_data.get("filename_pattern"),
            "column_fingerprint": orig_data.get("column_fingerprint"),
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("supplier_templates")\
            .insert(duplicate_data)\
            .execute()
        
        return {"template": result.data[0] if result.data else None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating template: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to duplicate template: {str(e)}")


@router.post("/{template_id}/test")
async def test_template(
    template_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """Test a template against a sample file."""
    user_id = str(current_user.id)
    
    try:
        # Get template
        template_res = supabase.table("supplier_templates")\
            .select("*")\
            .eq("id", template_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not template_res.data:
            raise HTTPException(404, "Template not found")
        
        template = template_res.data
        
        # Read file
        contents = await file.read()
        
        # Parse based on format
        if template.get("file_format") == "xlsx":
            df = pd.read_excel(io.BytesIO(contents), sheet_name=template.get("sheet_name"))
        elif template.get("file_format") == "csv":
            df = pd.read_csv(io.BytesIO(contents))
        else:
            raise HTTPException(400, f"Unsupported file format: {template.get('file_format')}")
        
        # Convert to list of dicts
        rows = df.to_dict('records')
        
        # Limit to first 10 rows for testing
        test_rows = rows[:10]
        
        # Apply template
        result = TemplateEngine.apply_template(test_rows, template)
        
        return {
            "success": True,
            "test_results": {
                "rows_tested": len(test_rows),
                "processed": result["processed"],
                "skipped": result["skipped"],
                "errors": result["errors"][:5],  # First 5 errors
                "sample_products": result["products"][:3]  # First 3 products
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing template: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to test template: {str(e)}")


@router.get("/{template_id}/versions")
async def get_template_versions(
    template_id: str,
    current_user=Depends(get_current_user)
):
    """Get version history for a template."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        template_check = supabase.table("supplier_templates")\
            .select("id")\
            .eq("id", template_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not template_check.data:
            raise HTTPException(404, "Template not found")
        
        # Get versions
        versions = supabase.table("template_versions")\
            .select("*")\
            .eq("template_id", template_id)\
            .order("version_number", desc=True)\
            .execute()
        
        return {"versions": versions.data or []}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting versions: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get versions: {str(e)}")


@router.post("/detect")
async def detect_template_from_file(
    filename: str,
    columns: List[str],
    supplier_id: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Detect matching template from filename and columns."""
    user_id = str(current_user.id)
    
    try:
        template = TemplateEngine.detect_template(filename, columns, supplier_id)
        
        if template:
            # Verify user owns the template
            if template.get("user_id") != user_id:
                return {"template": None}
            
            return {"template": template}
        
        return {"template": None}
        
    except Exception as e:
        logger.error(f"Error detecting template: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to detect template: {str(e)}")

