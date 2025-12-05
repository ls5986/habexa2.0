"""
Jobs API - Unified background task management.
All background processing uses Celery and the unified jobs table.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.tasks.file_processing import process_file_upload
from app.tasks.analysis import batch_analyze_products, analyze_single_product
from app.tasks.exports import export_products_csv
from app.tasks.telegram import sync_telegram_channel
from pydantic import BaseModel
from typing import List, Optional
import uuid
import base64
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ==========================================
# JOB STATUS ENDPOINTS
# ==========================================

@router.get("")
async def list_jobs(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    current_user = Depends(get_current_user)
):
    """List jobs."""
    user_id = str(current_user.id)
    
    query = supabase.table("jobs")\
        .select("*")\
        .eq("user_id", user_id)
    
    if type:
        query = query.eq("type", type)
    if status:
        query = query.eq("status", status)
    
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


@router.get("/{job_id}")
async def get_job(job_id: str, current_user = Depends(get_current_user)):
    """Get job status."""
    user_id = str(current_user.id)
    
    result = supabase.table("jobs")\
        .select("*")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .limit(1)\
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Job not found")
    
    return result.data[0]


@router.delete("/{job_id}")
async def delete_job(job_id: str, current_user = Depends(get_current_user)):
    """Delete a job (only if completed, failed, or cancelled)."""
    user_id = str(current_user.id)
    
    # First verify job exists and belongs to user
    job_check = supabase.table("jobs")\
        .select("id, status")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .limit(1)\
        .execute()
    
    if not job_check.data:
        raise HTTPException(404, "Job not found")
    
    job = job_check.data[0]
    
    # Only allow deletion of completed/failed/cancelled jobs
    if job["status"] in ["pending", "processing"]:
        raise HTTPException(400, f"Cannot delete job with status '{job['status']}'. Cancel it first.")
    
    # Delete the job
    supabase.table("jobs")\
        .delete()\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .execute()
    
    return {"message": "Job deleted", "job_id": job_id}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, current_user = Depends(get_current_user)):
    """Cancel a job."""
    from datetime import datetime
    user_id = str(current_user.id)
    
    # First verify job exists and belongs to user
    job_check = supabase.table("jobs")\
        .select("id, status, type")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .limit(1)\
        .execute()
    
    if not job_check.data:
        raise HTTPException(404, "Job not found")
    
    job = job_check.data[0]
    
    # Only cancel if pending or processing
    if job["status"] not in ["pending", "processing"]:
        raise HTTPException(400, f"Job is {job['status']} and cannot be cancelled")
    
    # Update job status to cancelled
    result = supabase.table("jobs")\
        .update({
            "status": "cancelled",
            "updated_at": datetime.utcnow().isoformat()
        })\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .execute()
    
    # Try to revoke the Celery task if it's still queued
    try:
        from app.core.celery_app import celery_app
        celery_app.control.revoke(job_id, terminate=True)
        logger.info(f"Revoked Celery task {job_id}")
    except Exception as e:
        logger.warning(f"Failed to revoke Celery task {job_id}: {e}")
        # Continue anyway - the job status is updated
    
    return {"message": "Job cancelled", "job_id": job_id}


# ==========================================
# FILE UPLOAD
# ==========================================

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    supplier_id: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Upload CSV/Excel file for processing."""
    user_id = str(current_user.id)
    filename = file.filename or "unknown"
    
    if not filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(400, "File must be .csv, .xlsx, or .xls")
    
    # Validate supplier
    supplier = supabase.table("suppliers")\
        .select("id, name")\
        .eq("id", supplier_id)\
        .eq("user_id", user_id)\
        .limit(1)\
        .execute()
    
    if not supplier.data:
        raise HTTPException(400, "Invalid supplier")
    
    # Read and encode file
    contents = await file.read()
    contents_b64 = base64.b64encode(contents).decode()
    
    # Create job
    job_id = str(uuid.uuid4())
    
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "file_upload",
        "status": "pending",
        "metadata": {
            "filename": filename,
            "supplier_id": supplier_id,
            "supplier_name": supplier.data[0]["name"]
        }
    }).execute()
    
    # Queue task
    process_file_upload.delay(job_id, user_id, supplier_id, contents_b64, filename)
    
    return {
        "job_id": job_id,
        "message": f"Upload started for {supplier.data[0]['name']}",
        "status": "pending"
    }


# ==========================================
# BATCH ANALYSIS
# ==========================================

class BatchAnalyzeRequest(BaseModel):
    product_ids: Optional[List[str]] = None
    analyze_all_pending: Optional[bool] = False


@router.post("/analyze")
async def start_batch_analyze(req: BatchAnalyzeRequest, current_user = Depends(get_current_user)):
    """Start batch analysis."""
    user_id = str(current_user.id)
    
    if req.product_ids:
        product_ids = req.product_ids
    elif req.analyze_all_pending:
        products = supabase.table("products")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("status", "pending")\
            .execute()
        product_ids = [p["id"] for p in (products.data or [])]
    else:
        raise HTTPException(400, "Specify product_ids or analyze_all_pending")
    
    if not product_ids:
        raise HTTPException(400, "No products to analyze")
    
    job_id = str(uuid.uuid4())
    
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "batch_analyze",
        "status": "pending",
        "total_items": len(product_ids)
    }).execute()
    
    batch_analyze_products.delay(job_id, user_id, product_ids)
    
    return {
        "job_id": job_id,
        "message": f"Started analyzing {len(product_ids)} products",
        "total": len(product_ids)
    }


@router.post("/analyze-single")
async def analyze_single(asin: str, current_user = Depends(get_current_user)):
    """Quick analyze single ASIN."""
    user_id = str(current_user.id)
    asin = asin.strip().upper()
    
    # Get or create product
    existing = supabase.table("products")\
        .select("id")\
        .eq("user_id", user_id)\
        .eq("asin", asin)\
        .limit(1)\
        .execute()
    
    if existing.data:
        product_id = existing.data[0]["id"]
    else:
        new_prod = supabase.table("products").insert({
            "user_id": user_id,
            "asin": asin,
            "status": "pending"
        }).execute()
        product_id = new_prod.data[0]["id"] if new_prod.data else None
    
    if not product_id:
        raise HTTPException(500, "Failed to create product")
    
    job_id = str(uuid.uuid4())
    
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "single_analyze",
        "status": "pending",
        "total_items": 1,
        "metadata": {"asin": asin, "product_id": product_id}
    }).execute()
    
    analyze_single_product.delay(job_id, user_id, product_id, asin)
    
    return {
        "job_id": job_id,
        "product_id": product_id,
        "asin": asin
    }


# ==========================================
# EXPORT
# ==========================================

class ExportRequest(BaseModel):
    stage: Optional[str] = None
    source: Optional[str] = None
    supplier_id: Optional[str] = None


@router.post("/export")
async def start_export(req: ExportRequest, current_user = Depends(get_current_user)):
    """Start CSV export."""
    user_id = str(current_user.id)
    
    job_id = str(uuid.uuid4())
    
    filters = {}
    if req.stage:
        filters["stage"] = req.stage
    if req.source:
        filters["source"] = req.source
    if req.supplier_id:
        filters["supplier_id"] = req.supplier_id
    
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "export",
        "status": "pending",
        "metadata": {"filters": filters}
    }).execute()
    
    export_products_csv.delay(job_id, user_id, filters)
    
    return {"job_id": job_id, "message": "Export started"}


# ==========================================
# TELEGRAM SYNC
# ==========================================

@router.post("/telegram-sync")
async def start_telegram_sync(
    channel_id: str,
    channel_name: str,
    message_limit: int = 500,
    current_user = Depends(get_current_user)
):
    """Start full Telegram channel sync."""
    user_id = str(current_user.id)
    
    job_id = str(uuid.uuid4())
    
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "type": "telegram_sync",
        "status": "pending",
        "metadata": {"channel_id": channel_id, "channel_name": channel_name}
    }).execute()
    
    sync_telegram_channel.delay(job_id, user_id, channel_id, channel_name, message_limit)
    
    return {"job_id": job_id, "message": f"Syncing {channel_name}"}


# ==========================================
# UPLOAD JOBS (New Upload System)
# ==========================================

@router.get("/upload")
async def list_upload_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    current_user = Depends(get_current_user)
):
    """List all upload jobs for the current user."""
    from datetime import datetime
    
    user_id = str(current_user.id)
    
    query = supabase.table("upload_jobs")\
        .select("*, suppliers(id, name)")\
        .eq("user_id", user_id)
    
    if status:
        query = query.eq("status", status)
    
    result = query.order("created_at", desc=True).limit(limit).execute()
    
    jobs = result.data or []
    
    # Format response with progress
    formatted_jobs = []
    for job in jobs:
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
        
        formatted_jobs.append({
            "id": job["id"],
            "filename": job["filename"],
            "supplier": job.get("suppliers"),
            "status": job["status"],
            "progress": progress,
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "completed_at": job.get("completed_at")
        })
    
    return {
        "jobs": formatted_jobs,
        "total": len(formatted_jobs)
    }


@router.get("/upload/{job_id}")
async def get_upload_job(job_id: str, current_user = Depends(get_current_user)):
    """Get detailed upload job information including chunk status."""
    from datetime import datetime
    
    user_id = str(current_user.id)
    
    # Get job
    job_result = supabase.table("upload_jobs")\
        .select("*, suppliers(id, name)")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .single()\
        .execute()
    
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Upload job not found")
    
    job = job_result.data
    
    # Get chunks
    chunks_result = supabase.table("upload_chunks")\
        .select("*")\
        .eq("job_id", job_id)\
        .order("chunk_index")\
        .execute()
    
    chunks = chunks_result.data or []
    
    # Calculate chunk summary
    chunk_summary = {
        "total": len(chunks),
        "pending": sum(1 for c in chunks if c["status"] == "pending"),
        "queued": sum(1 for c in chunks if c["status"] == "queued"),
        "processing": sum(1 for c in chunks if c["status"] == "processing"),
        "complete": sum(1 for c in chunks if c["status"] == "complete"),
        "failed": sum(1 for c in chunks if c["status"] == "failed"),
        "cancelled": sum(1 for c in chunks if c["status"] == "cancelled")
    }
    
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
    
    # Error summary
    error_summary = job.get("error_summary") or {}
    if not error_summary and chunks:
        # Build error summary from chunks
        error_types = {}
        for chunk in chunks:
            if chunk.get("errors"):
                for error in chunk["errors"]:
                    error_type = error.get("error", "unknown").split(":")[0]
                    error_types[error_type] = error_types.get(error_type, 0) + 1
        error_summary = {
            "total_errors": sum(c.get("error_count", 0) or 0 for c in chunks),
            "by_type": error_types
        }
    
    return {
        "id": job["id"],
        "filename": job["filename"],
        "supplier": job.get("suppliers"),
        "status": job["status"],
        "progress": progress,
        "column_mapping": job.get("column_mapping"),
        "chunks": chunk_summary,
        "error_summary": error_summary,
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "updated_at": job["updated_at"],
        "completed_at": job.get("completed_at")
    }


@router.get("/upload/{job_id}/chunks")
async def get_upload_chunks(
    job_id: str,
    status: Optional[str] = Query(None),
    current_user = Depends(get_current_user)
):
    """Get chunk details for an upload job (for debugging)."""
    user_id = str(current_user.id)
    
    # Verify job belongs to user
    job_check = supabase.table("upload_jobs")\
        .select("id")\
        .eq("id", job_id)\
        .eq("user_id", user_id)\
        .limit(1)\
        .execute()
    
    if not job_check.data:
        raise HTTPException(status_code=404, detail="Upload job not found")
    
    # Get chunks
    query = supabase.table("upload_chunks")\
        .select("*")\
        .eq("job_id", job_id)
    
    if status:
        query = query.eq("status", status)
    
    result = query.order("chunk_index").execute()
    
    chunks = result.data or []
    
    return {
        "chunks": [
            {
                "id": c["id"],
                "chunk_index": c["chunk_index"],
                "start_row": c["start_row"],
                "end_row": c["end_row"],
                "status": c["status"],
                "processed_count": c.get("processed_count", 0),
                "success_count": c.get("success_count", 0),
                "error_count": c.get("error_count", 0),
                "errors": c.get("errors"),
                "queued_at": c.get("queued_at"),
                "started_at": c.get("started_at"),
                "completed_at": c.get("completed_at")
            }
            for c in chunks
        ]
    }


@router.post("/upload/{job_id}/cancel")
async def cancel_upload_job(job_id: str, current_user = Depends(get_current_user)):
    """Cancel an active upload job."""
    from datetime import datetime
    
    user_id = str(current_user.id)
    
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
    
    # Only cancel if pending or processing
    if job["status"] not in ["pending", "mapping", "validating", "processing"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job is {job['status']} and cannot be cancelled"
        )
    
    # Update job status
    supabase.table("upload_jobs")\
        .update({
            "status": "cancelled",
            "updated_at": datetime.utcnow().isoformat()
        })\
        .eq("id", job_id)\
        .execute()
    
    # Cancel all pending/queued/processing chunks
    supabase.table("upload_chunks")\
        .update({
            "status": "cancelled",
            "completed_at": datetime.utcnow().isoformat()
        })\
        .eq("job_id", job_id)\
        .in_("status", ["pending", "queued", "processing"])\
        .execute()
    
    # Try to revoke Celery tasks for queued chunks
    chunks_result = supabase.table("upload_chunks")\
        .select("celery_task_id")\
        .eq("job_id", job_id)\
        .eq("status", "queued")\
        .execute()
    
    if chunks_result.data:
        try:
            from app.core.celery_app import celery_app
            for chunk in chunks_result.data:
                task_id = chunk.get("celery_task_id")
                if task_id:
                    celery_app.control.revoke(task_id, terminate=True)
        except Exception as e:
            logger.warning(f"Failed to revoke Celery tasks: {e}")
    
    return {
        "id": job_id,
        "status": "cancelled",
        "message": f"Job cancelled. {job.get('successful_rows', 0)} products were already created."
    }


@router.post("/upload/{job_id}/retry")
async def retry_upload_job(job_id: str, current_user = Depends(get_current_user)):
    """Retry failed chunks in an upload job."""
    from datetime import datetime
    
    user_id = str(current_user.id)
    
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
    
    if job["status"] not in ["complete", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry job with status '{job['status']}'. Job must be complete or failed."
        )
    
    # Get failed chunks
    failed_chunks_result = supabase.table("upload_chunks")\
        .select("*")\
        .eq("job_id", job_id)\
        .eq("status", "failed")\
        .execute()
    
    failed_chunks = failed_chunks_result.data or []
    
    if not failed_chunks:
        raise HTTPException(status_code=400, detail="No failed chunks to retry")
    
    # Reset failed chunks to pending
    chunk_ids = [c["id"] for c in failed_chunks]
    supabase.table("upload_chunks")\
        .update({
            "status": "pending",
            "errors": None,
            "error_count": 0
        })\
        .in_("id", chunk_ids)\
        .execute()
    
    # Update job status back to processing
    supabase.table("upload_jobs")\
        .update({
            "status": "processing",
            "updated_at": datetime.utcnow().isoformat()
        })\
        .eq("id", job_id)\
        .execute()
    
    # Queue the retried chunks
    from app.tasks.upload_processing import queue_next_chunk
    for _ in range(len(failed_chunks)):
        queue_next_chunk(job_id)
    
    return {
        "id": job_id,
        "status": "processing",
        "retrying_chunks": len(failed_chunks),
        "message": f"Retrying {len(failed_chunks)} failed chunks"
    }
