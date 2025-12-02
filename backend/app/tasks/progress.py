"""
Atomic job progress tracking across multiple Celery workers.
Uses Redis for real-time counters, syncs to Supabase periodically.
"""
import redis
import os
import json
import logging
from datetime import datetime
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class AtomicJobProgress:
    """
    Track job progress atomically across multiple workers.
    Uses Redis for real-time counters, syncs to Supabase periodically.
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=False)
        except Exception as e:
            logger.error(f"Failed to connect to Redis for progress tracking: {e}")
            self.redis = None
        
        self.key_processed = f"job:{job_id}:processed"
        self.key_success = f"job:{job_id}:success"
        self.key_errors = f"job:{job_id}:errors"
        self.key_error_list = f"job:{job_id}:error_list"
        self.key_total = f"job:{job_id}:total"
    
    def init(self, total: int):
        """Initialize job tracking."""
        if self.redis:
            try:
                self.redis.set(self.key_total, total)
                self.redis.set(self.key_processed, 0)
                self.redis.set(self.key_success, 0)
                self.redis.set(self.key_errors, 0)
                self.redis.delete(self.key_error_list)
                
                # Set expiry (2 hours)
                for key in [self.key_total, self.key_processed, self.key_success, self.key_errors, self.key_error_list]:
                    self.redis.expire(key, 7200)
            except Exception as e:
                logger.warning(f"Redis init error: {e}")
        
        # Update Supabase
        try:
            supabase.table("jobs").update({
                "status": "processing",
                "total_items": total,
                "processed_items": 0,
                "progress": 0,
                "started_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", self.job_id).execute()
        except Exception as e:
            logger.error(f"Failed to init job in Supabase: {e}")
    
    def increment_success(self):
        """Atomically increment success counter."""
        if self.redis:
            try:
                self.redis.incr(self.key_processed)
                self.redis.incr(self.key_success)
            except Exception as e:
                logger.warning(f"Redis increment error: {e}")
    
    def increment_error(self, error_msg: str = None):
        """Atomically increment error counter."""
        if self.redis:
            try:
                self.redis.incr(self.key_processed)
                self.redis.incr(self.key_errors)
                if error_msg:
                    error_str = error_msg[:200] if isinstance(error_msg, str) else str(error_msg)[:200]
                    self.redis.rpush(self.key_error_list, error_str)
                    self.redis.ltrim(self.key_error_list, -100, -1)  # Keep last 100
            except Exception as e:
                logger.warning(f"Redis increment error: {e}")
    
    def get_progress(self) -> dict:
        """Get current progress."""
        if not self.redis:
            # Fallback: query Supabase
            try:
                result = supabase.table("jobs")\
                    .select("processed_items, total_items, success_count, error_count, errors")\
                    .eq("id", self.job_id)\
                    .limit(1)\
                    .execute()
                
                if result.data:
                    data = result.data[0]
                    total = data.get("total_items", 1)
                    processed = data.get("processed_items", 0)
                    return {
                        "processed": processed,
                        "total": total,
                        "success": data.get("success_count", 0),
                        "errors": data.get("error_count", 0),
                        "progress": int((processed / total) * 100) if total > 0 else 0,
                        "error_list": data.get("errors", []) or []
                    }
            except Exception as e:
                logger.warning(f"Failed to get progress from Supabase: {e}")
            
            return {"processed": 0, "total": 1, "success": 0, "errors": 0, "progress": 0, "error_list": []}
        
        try:
            processed = int(self.redis.get(self.key_processed) or 0)
            total = int(self.redis.get(self.key_total) or 1)
            success = int(self.redis.get(self.key_success) or 0)
            errors = int(self.redis.get(self.key_errors) or 0)
            error_list = self.redis.lrange(self.key_error_list, 0, -1)
            
            return {
                "processed": processed,
                "total": total,
                "success": success,
                "errors": errors,
                "progress": int((processed / total) * 100) if total > 0 else 0,
                "error_list": [e.decode() if isinstance(e, bytes) else e for e in error_list]
            }
        except Exception as e:
            logger.warning(f"Redis get_progress error: {e}")
            return {"processed": 0, "total": 1, "success": 0, "errors": 0, "progress": 0, "error_list": []}
    
    def sync_to_db(self):
        """Sync current progress to Supabase."""
        progress = self.get_progress()
        
        try:
            supabase.table("jobs").update({
                "processed_items": progress["processed"],
                "total_items": progress["total"],
                "progress": progress["progress"],
                "success_count": progress["success"],
                "error_count": progress["errors"],
                "errors": progress["error_list"][-50:] if progress["error_list"] else [],
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", self.job_id).execute()
            
            logger.info(f"📊 Job {self.job_id}: {progress['processed']}/{progress['total']} ({progress['progress']}%) - {progress['success']} success, {progress['errors']} errors")
        except Exception as e:
            logger.error(f"Failed to sync progress to Supabase: {e}")
    
    def complete(self):
        """Mark job as complete."""
        progress = self.get_progress()
        
        try:
            supabase.table("jobs").update({
                "status": "completed",
                "processed_items": progress["total"],
                "total_items": progress["total"],
                "progress": 100,
                "success_count": progress["success"],
                "error_count": progress["errors"],
                "errors": progress["error_list"][-50:] if progress["error_list"] else [],
                "result": {
                    "success_count": progress["success"],
                    "error_count": progress["errors"],
                    "total_processed": progress["processed"]
                },
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", self.job_id).execute()
            
            # Cleanup Redis
            if self.redis:
                try:
                    for key in [self.key_total, self.key_processed, self.key_success, self.key_errors, self.key_error_list]:
                        self.redis.delete(key)
                except Exception as e:
                    logger.warning(f"Redis cleanup error: {e}")
            
            logger.info(f"✅ Job {self.job_id} complete: {progress['success']}/{progress['total']} success, {progress['errors']} errors")
        except Exception as e:
            logger.error(f"Failed to complete job in Supabase: {e}")
    
    def is_cancelled(self) -> bool:
        """Check if job was cancelled."""
        try:
            result = supabase.table("jobs")\
                .select("status")\
                .eq("id", self.job_id)\
                .limit(1)\
                .execute()
            return result.data and result.data[0].get("status") == "cancelled"
        except Exception as e:
            logger.warning(f"Failed to check cancellation: {e}")
            return False

