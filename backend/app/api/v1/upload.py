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
from typing import Optional, List, Dict, Any
import logging
import os
import uuid
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# Temporary file storage directory
UPLOAD_TEMP_DIR = Path("/tmp/habexa_uploads")
UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# STEP 1: PREPARE UPLOAD (Initialize Job)
# ============================================================================

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
    
    # Auto-map columns
    auto_mapping = auto_map_columns(headers)
    
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
        "saved_mappings": saved_mappings
    }


# ============================================================================
# STEP 3: START PROCESSING (Confirm Mapping + Queue Chunks)
# ============================================================================

@router.post("/{job_id}/start")
async def start_processing(
    job_id: str,
    column_mapping: str = Form(...),  # JSON string
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
    
    # Validate mapping
    # Get file columns from stored file
    file_path = Path(job.get("file_path"))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found")
    
    # Re-read headers for validation
    with open(file_path, "rb") as f:
        contents = f.read()
    
    filename_lower = job["filename"].lower()
    if filename_lower.endswith(('.xlsx', '.xls')):
        _, headers = parse_excel(contents)
    else:
        _, headers = parse_csv(contents)
    
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
    
    # Update job with mapping
    chunk_size = 500
    total_chunks = (job["total_rows"] + chunk_size - 1) // chunk_size
    
    supabase.table("upload_jobs")\
        .update({
            "column_mapping": mapping_dict,
            "status": "validating",
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "started_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })\
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

