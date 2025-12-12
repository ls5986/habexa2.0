"""
Upload API - Large file processing with column mapping
Supports 3-step wizard: prepare -> analyze -> start
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.column_mapper import (
    auto_map_columns,
    validate_mapping,
    MAPPABLE_FIELDS
)
from app.tasks.file_processing import parse_csv, parse_excel
from app.services.template_engine import TemplateEngine
from app.tasks.enterprise_file_processing import process_large_file
from typing import Optional, List, Dict, Any
import logging
import os
import uuid
import json
import io
import pandas as pd
from datetime import datetime
from pathlib import Path
from fastapi import Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# Temporary file storage directory
UPLOAD_TEMP_DIR = Path("/tmp/habexa_uploads")
UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# STEP 1: PREPARE UPLOAD (Initialize Job)
# ============================================================================

@router.post("/file")
async def upload_product_file(
    file: UploadFile = File(...),
    supplier_id: Optional[str] = Form(None),
    column_mapping: Optional[str] = Form(None),  # JSON string
    current_user: dict = Depends(get_current_user)
):
    """
    Upload product file for enterprise processing.
    
    Supports CSV and Excel files up to 100MB.
    Handles 50,000+ products efficiently.
    
    Returns job_id for progress tracking.
    """
    try:
        # Validate file
        if not file.filename or not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(400, "Only CSV and Excel files supported")
        
        # Create unique job ID
        job_id = str(uuid.uuid4())
        
        # Save file to temp location
        upload_dir = UPLOAD_TEMP_DIR / str(current_user["id"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{job_id}_{file.filename}"
        
        # Save uploaded file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        file_size = len(contents)
        
        logger.info(f"📁 File uploaded: {file.filename} ({file_size / 1024 / 1024:.1f} MB)")
        
        # Parse column mapping if provided
        mapping_dict = {}
        if column_mapping:
            try:
                mapping_dict = json.loads(column_mapping)
            except json.JSONDecodeError:
                pass
        
        # Default column mapping if not provided
        if not mapping_dict:
            # Quick parse to get headers
            filename_lower = file.filename.lower()
            if filename_lower.endswith(('.xlsx', '.xls')):
                df_sample = pd.read_excel(io.BytesIO(contents), nrows=1)
            else:
                df_sample = pd.read_csv(io.BytesIO(contents), nrows=1)
            
            headers = list(df_sample.columns)
            mapping_dict = auto_map_columns(headers)
        
        # Create upload job record
        job_record = {
            'id': job_id,
            'user_id': current_user["id"],
            'filename': file.filename,
            'file_path': str(file_path),
            'file_size_bytes': file_size,
            'total_rows': 0,  # Will be updated during processing
            'status': 'pending',
            'supplier_id': supplier_id,
            'started_at': datetime.utcnow().isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('upload_jobs').insert(job_record).execute()
        
        # Queue Celery task for background processing
        try:
            task = process_large_file.delay(
                job_id=job_id,
                user_id=current_user["id"],
                file_path=str(file_path),
                column_mapping=mapping_dict,
                supplier_id=supplier_id
            )
            task_id = task.id
        except Exception as e:
            logger.warning(f"Celery not available, using BackgroundTasks: {e}")
            task_id = None
            # Fallback to sync processing for small files
            if file_size < 5 * 1024 * 1024:  # < 5MB
                from app.services.streaming_file_processor import StreamingFileProcessor
                processor = StreamingFileProcessor(
                    user_id=current_user["id"],
                    job_id=job_id
                )
                # Run in background
                import asyncio
                asyncio.create_task(
                    processor.process_file(
                        file_path=str(file_path),
                        column_mapping=mapping_dict,
                        supplier_id=supplier_id
                    )
                )
        
        logger.info(f"✅ Queued processing job: {job_id} (Celery task: {task_id})")
        
        return {
            'job_id': job_id,
            'task_id': task_id,
            'filename': file.filename,
            'file_size': file_size,
            'status': 'queued',
            'message': 'File upload successful. Processing started in background.'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.get("/status/{job_id}")
async def get_upload_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get real-time upload job status.
    
    Returns:
    {
        "status": "fetching_api",
        "progress": 75,
        "processed_rows": 37500,
        "total_rows": 50000,
        "current_phase": "Fetching API data",
        "duration_seconds": 180,
        "estimated_remaining": 60
    }
    """
    try:
        # Get job from database
        response = supabase.table('upload_jobs').select('*').eq(
            'id', job_id
        ).eq('user_id', current_user["id"]).single().execute()
        
        if not response.data:
            raise HTTPException(404, "Job not found")
        
        job = response.data
        
        # Calculate progress percentage
        progress = 0
        if job.get('total_rows') and job['total_rows'] > 0:
            progress = int((job.get('processed_rows', 0) / job['total_rows']) * 100)
        
        # Estimate remaining time
        estimated_remaining = None
        if job.get('status') != 'complete' and job.get('duration_seconds') and job.get('processed_rows'):
            time_per_row = job['duration_seconds'] / job['processed_rows']
            remaining_rows = job['total_rows'] - job['processed_rows']
            estimated_remaining = int(time_per_row * remaining_rows)
        
        # Map status to user-friendly phase
        phase_map = {
            'pending': 'Queued',
            'parsing': 'Parsing file',
            'converting_upcs': 'Converting UPCs to ASINs',
            'inserting': 'Saving products to database',
            'fetching_api': 'Fetching Amazon API data',
            'complete': 'Complete',
            'failed': 'Failed',
            'cancelled': 'Cancelled'
        }
        
        return {
            'job_id': job_id,
            'status': job.get('status', 'pending'),
            'current_phase': phase_map.get(job.get('status', 'pending'), job.get('status', 'pending')),
            'progress': progress,
            'total_rows': job.get('total_rows', 0),
            'processed_rows': job.get('processed_rows', 0),
            'successful_rows': job.get('successful_rows', 0),
            'failed_rows': job.get('failed_rows', 0),
            'products_created': job.get('products_created', 0),
            'cache_hits': job.get('cache_hits', 0),
            'api_calls_made': job.get('api_calls_made', 0),
            'duration_seconds': job.get('duration_seconds'),
            'estimated_remaining_seconds': estimated_remaining,
            'started_at': job.get('started_at'),
            'completed_at': job.get('completed_at'),
            'error': job.get('error_summary')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/jobs")
async def list_upload_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    List all upload jobs for current user.
    """
    try:
        response = supabase.table('upload_jobs').select('*').eq(
            'user_id', current_user["id"]
        ).order('created_at', desc=True).range(
            offset, offset + limit - 1
        ).execute()
        
        return {
            'jobs': response.data or [],
            'total': len(response.data or [])
        }
        
    except Exception as e:
        logger.error(f"List jobs failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.delete("/job/{job_id}")
async def cancel_upload_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a running upload job.
    """
    try:
        # Update job status to cancelled
        supabase.table('upload_jobs').update({
            'status': 'cancelled',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', job_id).eq('user_id', current_user["id"]).execute()
        
        # TODO: Actually cancel the Celery task
        # from app.celery_app import celery_app
        # celery_app.control.revoke(task_id, terminate=True)
        
        return {'message': 'Job cancelled'}
        
    except Exception as e:
        logger.error(f"Cancel failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/prepare")
async def prepare_upload(
    supplier_id: Optional[str] = Form(None),
    filename: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Step 1: Initialize an upload job.
    Returns job_id and upload URL for file upload.
    """
    user_id = current_user["id"]
    
    # Create upload job
    job_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "supplier_id": supplier_id,
        "filename": filename,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("upload_jobs").insert(job_data).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create upload job")
    
    job = result.data[0]
    
    return {
        "job_id": job["id"],
        "status": "pending",
        "max_size_bytes": 52428800  # 50MB
    }


# ============================================================================
# STEP 2: ANALYZE FILE (Detect Columns + Auto-Map)
# ============================================================================

@router.post("/{job_id}/analyze")
async def analyze_file(
    job_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Step 2: Upload file and analyze columns.
    Returns column list, sample values, and auto-mapping suggestions.
    """
    user_id = current_user["id"]
    
    # Verify job exists and belongs to user
    job_result = supabase.table("upload_jobs")\
        .select("*")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .single()\
        .execute()
    
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Upload job not found")
    
    job = job_result.data
    
    # Read file contents
    contents = await file.read()
    file_size = len(contents)
    
    # Save file temporarily
    file_path = UPLOAD_TEMP_DIR / f"{job_id}_{job['filename']}"
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Parse file based on extension
    filename_lower = job["filename"].lower()
    try:
        if filename_lower.endswith(('.xlsx', '.xls')):
            rows, headers = parse_excel(contents)
        else:
            rows, headers = parse_csv(contents)
    except Exception as e:
        logger.error(f"Error parsing file: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    if not headers:
        raise HTTPException(status_code=400, detail="File has no headers")
    
    # Get sample values for each column (first 5 non-empty values)
    column_samples = {}
    for col in headers:
        samples = []
        for row in rows[:100]:  # Check first 100 rows
            value = row.get(col)
            if value and str(value).strip():
                samples.append(str(value).strip())
                if len(samples) >= 5:
                    break
        column_samples[col] = samples[:5]
    
    # Try to detect template
    detected_template = None
    if job.get("supplier_id"):
        detected_template = TemplateEngine.detect_template(
            filename=job["filename"],
            columns=headers,
            supplier_id=job["supplier_id"]
        )
    
    # Auto-map columns
    auto_mapping = auto_map_columns(headers)
    
    # If template detected, use its mappings as default
    if detected_template:
        template_mappings = detected_template.get("column_mappings", {})
        # Merge template mappings with auto-mapping (template takes precedence)
        for supplier_col, habexa_field in template_mappings.items():
            if supplier_col in headers:
                auto_mapping[supplier_col] = habexa_field
    
    # Get saved mappings for this supplier (if supplier_id exists)
    saved_mappings = []
    if job.get("supplier_id"):
        mappings_result = supabase.table("supplier_column_mappings")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("supplier_id", job["supplier_id"])\
            .order("is_default", desc=True)\
            .order("updated_at", desc=True)\
            .execute()
        
        if mappings_result.data:
            saved_mappings = [
                {
                    "id": m["id"],
                    "name": m["mapping_name"],
                    "mapping": m["column_mapping"],
                    "is_default": m.get("is_default", False)
                }
                for m in mappings_result.data
            ]
    
    # Get templates for this supplier
    templates = []
    if job.get("supplier_id"):
        templates_result = supabase.table("supplier_templates")\
            .select("id, template_name, description, is_active, usage_count, last_used_at")\
            .eq("user_id", user_id)\
            .eq("supplier_id", job["supplier_id"])\
            .eq("is_active", True)\
            .order("usage_count", desc=True)\
            .execute()
        
        if templates_result.data:
            templates = templates_result.data
    
    # Update job with file info
    supabase.table("upload_jobs")\
        .update({
            "file_path": str(file_path),
            "file_size_bytes": file_size,
            "total_rows": len(rows),
            "status": "mapping",
            "updated_at": datetime.utcnow().isoformat()
        })\
        .eq("id", job_id)\
        .execute()
    
    # Format columns for response
    columns = [
        {
            "name": col,
            "sample_values": column_samples.get(col, [])
        }
        for col in headers
    ]
    
    return {
        "job_id": job_id,
        "filename": job["filename"],
        "total_rows": len(rows),
        "columns": columns,
        "auto_mapping": auto_mapping,
        "saved_mappings": saved_mappings,
        "detected_template": {
            "id": detected_template["id"],
            "template_name": detected_template["template_name"],
            "description": detected_template.get("description")
        } if detected_template else None,
        "available_templates": templates
    }


# ============================================================================
# STEP 3: START PROCESSING (Confirm Mapping + Queue Chunks)
# ============================================================================

@router.post("/{job_id}/start")
async def start_processing(
    job_id: str,
    column_mapping: str = Form(...),  # JSON string
    template_id: Optional[str] = Form(None),  # Optional template ID to apply
    save_mapping: bool = Form(False),
    mapping_name: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """
    Step 3: Confirm column mapping and start processing.
    Creates chunks and queues them for processing.
    """
    user_id = current_user["id"]
    
    # Verify job exists
    job_result = supabase.table("upload_jobs")\
        .select("*")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .single()\
        .execute()
    
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Upload job not found")
    
    job = job_result.data
    
    if job["status"] not in ["pending", "mapping"]:
        raise HTTPException(status_code=400, detail=f"Job is in {job['status']} status, cannot start")
    
    # Parse column mapping
    try:
        mapping_dict = json.loads(column_mapping)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid column_mapping JSON")
    
    # Get file columns from stored file
    file_path = Path(job.get("file_path"))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found")
    
    # Re-read headers for validation
    with open(file_path, "rb") as f:
        contents = f.read()
    
    filename_lower = job["filename"].lower()
    if filename_lower.endswith(('.xlsx', '.xls')):
        rows, headers = parse_excel(contents)
    else:
        rows, headers = parse_csv(contents)
    
    # If template_id provided, load and apply template
    template = None
    template_applied = False
    if template_id:
        template_result = supabase.table("supplier_templates")\
            .select("*")\
            .eq("id", template_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if template_result.data:
            template = template_result.data
            template_applied = True
            
            # Apply template to rows
            template_result_data = TemplateEngine.apply_template(rows[:100], template)  # Test with first 100 rows
            
            # Update mapping_dict with template mappings
            template_mappings = template.get("column_mappings", {})
            for supplier_col, habexa_field in template_mappings.items():
                if supplier_col in headers:
                    mapping_dict[supplier_col] = habexa_field
    
    # Validate mapping
    validation = validate_mapping(mapping_dict, headers)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Column mapping validation failed",
                "errors": validation["errors"]
            }
        )
    
    # Save mapping if requested
    if save_mapping and job.get("supplier_id") and mapping_name:
        # Unset other defaults for this supplier
        supabase.table("supplier_column_mappings")\
            .update({"is_default": False})\
            .eq("user_id", user_id)\
            .eq("supplier_id", job["supplier_id"])\
            .execute()
        
        # Upsert mapping
        mapping_data = {
            "user_id": user_id,
            "supplier_id": job["supplier_id"],
            "mapping_name": mapping_name,
            "column_mapping": mapping_dict,
            "is_default": True,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("supplier_column_mappings")\
            .upsert(mapping_data, on_conflict="user_id,supplier_id,mapping_name")\
            .execute()
    
    # Update job with mapping and template info
    chunk_size = 500
    total_chunks = (job["total_rows"] + chunk_size - 1) // chunk_size
    
    update_data = {
        "column_mapping": mapping_dict,
        "status": "validating",
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "started_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if template_id:
        update_data["template_id"] = template_id
        update_data["template_applied"] = True
        
        # Update template usage count
        supabase.table("supplier_templates")\
            .update({
                "usage_count": (template.get("usage_count", 0) + 1),
                "last_used_at": datetime.utcnow().isoformat()
            })\
            .eq("id", template_id)\
            .execute()
    
    supabase.table("upload_jobs")\
        .update(update_data)\
        .eq("id", job_id)\
        .execute()
    
    # Queue chunk initialization task
    from app.tasks.upload_processing import initialize_upload_chunks
    try:
        initialize_upload_chunks.delay(job_id)
    except Exception as e:
        logger.warning(f"Failed to queue Celery task, using BackgroundTasks: {e}")
        if background_tasks:
            background_tasks.add_task(initialize_upload_chunks, job_id)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "total_rows": job["total_rows"],
        "total_chunks": total_chunks,
        "estimated_time_seconds": total_chunks * 10  # Rough estimate
    }


# ============================================================================
# GET JOB STATUS
# ============================================================================

@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get current status and progress of an upload job."""
    user_id = current_user["id"]
    
    job_result = supabase.table("upload_jobs")\
        .select("*")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .single()\
        .execute()
    
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Upload job not found")
    
    job = job_result.data
    
    # Calculate progress
    progress = {
        "total_rows": job.get("total_rows", 0),
        "processed_rows": job.get("processed_rows", 0),
        "successful_rows": job.get("successful_rows", 0),
        "failed_rows": job.get("failed_rows", 0),
        "percent": 0.0
    }
    
    if progress["total_rows"] > 0:
        progress["percent"] = round(
            (progress["processed_rows"] / progress["total_rows"]) * 100, 2
        )
    
    return {
        "id": job["id"],
        "filename": job["filename"],
        "status": job["status"],
        "progress": progress,
        "created_at": job["created_at"],
        "updated_at": job["updated_at"]
    }

