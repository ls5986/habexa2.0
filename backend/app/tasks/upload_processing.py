"""
Upload Processing Tasks
Handles chunked processing of large file uploads with column mapping.
"""
from app.core.celery_app import celery_app
from app.services.supabase_client import supabase
from app.services.column_mapper import apply_mapping, validate_row
from app.tasks.file_processing import parse_csv, parse_excel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pathlib import Path
import traceback
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# CHUNK PROCESSING TASK
# ============================================================================

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_upload_chunk(self, job_id: str, chunk_id: str):
    """
    Process a single chunk of rows from an upload job.
    
    Args:
        job_id: Upload job ID
        chunk_id: Chunk ID to process
    """
    try:
        # Get chunk and job info
        chunk_result = supabase.table("upload_chunks")\
            .select("*")\
            .eq("id", chunk_id)\
            .single()\
            .execute()
        
        if not chunk_result.data:
            logger.error(f"Chunk {chunk_id} not found")
            return
        
        chunk = chunk_result.data
        
        job_result = supabase.table("upload_jobs")\
            .select("*")\
            .eq("id", job_id)\
            .single()\
            .execute()
        
        if not job_result.data:
            logger.error(f"Job {job_id} not found")
            return
        
        job = job_result.data
        
        # Check if job was cancelled
        if job["status"] == "cancelled":
            supabase.table("upload_chunks")\
                .update({"status": "cancelled"})\
                .eq("id", chunk_id)\
                .execute()
            return
        
        # Update chunk status
        supabase.table("upload_chunks")\
            .update({
                "status": "processing",
                "started_at": datetime.utcnow().isoformat()
            })\
            .eq("id", chunk_id)\
            .execute()
        
        # Read file
        file_path = Path(job.get("file_path"))
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, "rb") as f:
            contents = f.read()
        
        # Parse file
        filename_lower = job["filename"].lower()
        if filename_lower.endswith(('.xlsx', '.xls')):
            all_rows, headers = parse_excel(contents)
        else:
            all_rows, headers = parse_csv(contents)
        
        # Get rows for this chunk (1-indexed, so subtract 1 for array index)
        start_idx = chunk["start_row"] - 1
        end_idx = chunk["end_row"]
        chunk_rows = all_rows[start_idx:end_idx]
        
        # Apply column mapping
        column_mapping = job.get("column_mapping", {})
        mapped_rows = []
        errors = []
        
        for i, row in enumerate(chunk_rows):
            try:
                # Apply mapping
                mapped = apply_mapping(row, column_mapping)
                
                # Validate
                is_valid, error_msg = validate_row(mapped)
                
                if not is_valid:
                    errors.append({
                        "row": chunk["start_row"] + i,
                        "error": error_msg,
                        "data": {k: v for k, v in mapped.items() if v is not None}
                    })
                    continue
                
                mapped_rows.append(mapped)
                
            except Exception as e:
                errors.append({
                    "row": chunk["start_row"] + i,
                    "error": str(e),
                    "data": {}
                })
        
        # Create products (without ASIN lookup for now - will do lazy lookup)
        created_count = 0
        for mapped in mapped_rows:
            try:
                # Create product
                product_data = {
                    "id": str(uuid.uuid4()),
                    "user_id": job["user_id"],
                    "asin": None,  # Will be looked up later
                    "asin_status": "pending_lookup",
                    "upc": mapped.get("upc"),
                    "title": mapped.get("title"),
                    "brand": mapped.get("brand"),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                product_result = supabase.table("products").insert(product_data).execute()
                
                if product_result.data:
                    product_id = product_result.data[0]["id"]
                    
                    # Create product_source
                    source_data = {
                        "id": str(uuid.uuid4()),
                        "product_id": product_id,
                        "supplier_id": job.get("supplier_id"),
                        "buy_cost": mapped.get("buy_cost"),
                        "promo_buy_cost": mapped.get("promo_buy_cost"),
                        "pack_size": mapped.get("pack_size", 1),
                        "moq": mapped.get("moq", 1),
                        "supplier_sku": mapped.get("supplier_sku"),
                        "source": "upload",
                        "stage": "new",
                        "is_active": True,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    supabase.table("product_sources").insert(source_data).execute()
                    created_count += 1
                    
            except Exception as e:
                errors.append({
                    "row": chunk["start_row"] + mapped_rows.index(mapped),
                    "error": f"Failed to create product: {str(e)}",
                    "data": mapped
                })
        
        # Update chunk status
        supabase.table("upload_chunks")\
            .update({
                "status": "complete",
                "processed_count": len(chunk_rows),
                "success_count": created_count,
                "error_count": len(errors),
                "errors": errors if errors else None,
                "completed_at": datetime.utcnow().isoformat()
            })\
            .eq("id", chunk_id)\
            .execute()
        
        # Update job progress
        update_job_progress(job_id)
        
        # Queue next pending chunk
        queue_next_chunk(job_id)
        
    except Exception as e:
        logger.error(f"Error processing chunk {chunk_id}: {e}", exc_info=True)
        
        # Update chunk with error
        supabase.table("upload_chunks")\
            .update({
                "status": "failed",
                "errors": [{"error": str(e), "traceback": traceback.format_exc()}],
                "completed_at": datetime.utcnow().isoformat()
            })\
            .eq("id", chunk_id)\
            .execute()
        
        # Retry if not max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        else:
            # Update job progress even on failure
            update_job_progress(job_id)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def update_job_progress(job_id: str):
    """Recalculate job progress from chunks."""
    chunks_result = supabase.table("upload_chunks")\
        .select("status, processed_count, success_count, error_count")\
        .eq("job_id", job_id)\
        .execute()
    
    if not chunks_result.data:
        return
    
    chunks = chunks_result.data
    
    completed = sum(1 for c in chunks if c["status"] == "complete")
    processed = sum(c.get("processed_count", 0) or 0 for c in chunks)
    successful = sum(c.get("success_count", 0) or 0 for c in chunks)
    failed = sum(c.get("error_count", 0) or 0 for c in chunks)
    
    job_result = supabase.table("upload_jobs")\
        .select("total_chunks, total_rows")\
        .eq("id", job_id)\
        .single()\
        .execute()
    
    if not job_result.data:
        return
    
    job = job_result.data
    
    update_data = {
        "completed_chunks": completed,
        "processed_rows": processed,
        "successful_rows": successful,
        "failed_rows": failed,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Check if all chunks complete
    if completed == job.get("total_chunks", 0):
        update_data["status"] = "complete"
        update_data["completed_at"] = datetime.utcnow().isoformat()
        
        # Queue ASIN lookup for products created in this upload
        try:
            from app.tasks.asin_lookup import process_pending_asin_lookups
            # Trigger ASIN lookup (will process pending_lookup products)
            process_pending_asin_lookups.delay(100)
            logger.info(f"Queued ASIN lookup after upload job {job_id} completion")
        except Exception as e:
            logger.warning(f"Failed to queue ASIN lookup: {e}")
    else:
        update_data["status"] = "processing"
    
    supabase.table("upload_jobs")\
        .update(update_data)\
        .eq("id", job_id)\
        .execute()


def queue_next_chunk(job_id: str, max_concurrent: int = 5):
    """Queue the next pending chunk for processing."""
    # Count currently processing chunks
    processing_result = supabase.table("upload_chunks")\
        .select("id")\
        .eq("job_id", job_id)\
        .in_("status", ["queued", "processing"])\
        .execute()
    
    currently_processing = len(processing_result.data) if processing_result.data else 0
    
    if currently_processing >= max_concurrent:
        return  # Already at max concurrent
    
    # Get next pending chunk
    pending_result = supabase.table("upload_chunks")\
        .select("*")\
        .eq("job_id", job_id)\
        .eq("status", "pending")\
        .order("chunk_index")\
        .limit(1)\
        .single()\
        .execute()
    
    if not pending_result.data:
        return  # No more pending chunks
    
    chunk = pending_result.data
    
    # Queue the task
    task = process_upload_chunk.delay(job_id, chunk["id"])
    
    # Update chunk status
    supabase.table("upload_chunks")\
        .update({
            "status": "queued",
            "celery_task_id": task.id,
            "queued_at": datetime.utcnow().isoformat()
        })\
        .eq("id", chunk["id"])\
        .execute()


# ============================================================================
# INITIALIZE CHUNKS
# ============================================================================

@celery_app.task
def initialize_upload_chunks(job_id: str):
    """
    Create chunk records and queue first batch for processing.
    Called after mapping is confirmed in /upload/{job_id}/start
    """
    job_result = supabase.table("upload_jobs")\
        .select("*")\
        .eq("id", job_id)\
        .single()\
        .execute()
    
    if not job_result.data:
        logger.error(f"Job {job_id} not found")
        return
    
    job = job_result.data
    
    chunk_size = job.get("chunk_size", 500)
    total_rows = job.get("total_rows", 0)
    total_chunks = (total_rows + chunk_size - 1) // chunk_size
    
    # Create chunk records
    chunks = []
    for i in range(total_chunks):
        start_row = i * chunk_size + 1
        end_row = min((i + 1) * chunk_size, total_rows)
        
        chunk_data = {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "chunk_index": i,
            "start_row": start_row,
            "end_row": end_row,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("upload_chunks").insert(chunk_data).execute()
        if result.data:
            chunks.append(result.data[0])
    
    # Update job status
    supabase.table("upload_jobs")\
        .update({
            "status": "processing",
            "total_chunks": total_chunks,
            "started_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })\
        .eq("id", job_id)\
        .execute()
    
    # Queue first batch of chunks
    for chunk in chunks[:5]:  # Start with 5 concurrent
        queue_next_chunk(job_id)

