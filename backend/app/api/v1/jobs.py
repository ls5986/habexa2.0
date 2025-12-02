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
