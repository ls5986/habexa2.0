"""
Base utilities for Celery tasks.
Shared JobManager, RateLimiter, and run_async helper.
"""
from app.services.supabase_client import supabase
from typing import List, Optional
import time
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async code in sync Celery task. Shared utility for all tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class JobManager:
    """Utility class for managing job status updates."""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
    
    def start(self, total_items: int = 0):
        """Mark job as started."""
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        supabase.table("jobs").update({
            "status": "processing",
            "started_at": now,
            "total_items": total_items,
            "updated_at": now
        }).eq("id", self.job_id).execute()
    
    def update_progress(self, processed: int, total: int, success: int = 0, errors: int = 0, error_list: list = None):
        """Update job progress."""
        from datetime import datetime
        progress = int((processed / total) * 100) if total > 0 else 0
        
        update_data = {
            "progress": progress,
            "processed_items": processed,
            "total_items": total,
            "success_count": success,
            "error_count": errors,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if error_list:
            # Keep last 100 errors
            update_data["errors"] = error_list[-100:] if len(error_list) > 100 else error_list
        
        supabase.table("jobs").update(update_data).eq("id", self.job_id).execute()
    
    def complete(self, result: dict = None, success: int = 0, errors: int = 0, error_list: list = None):
        """Mark job as completed."""
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        update_data = {
            "status": "completed",
            "progress": 100,
            "success_count": success,
            "error_count": errors,
            "completed_at": now,
            "updated_at": now
        }
        
        if error_list:
            update_data["errors"] = error_list[-100:] if len(error_list) > 100 else error_list
        
        if result:
            update_data["result"] = result
        
        supabase.table("jobs").update(update_data).eq("id", self.job_id).execute()
    
    def fail(self, error: str):
        """Mark job as failed."""
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        supabase.table("jobs").update({
            "status": "failed",
            "errors": [error],
            "completed_at": now,
            "updated_at": now
        }).eq("id", self.job_id).execute()
    
    def is_cancelled(self) -> bool:
        """Check if job was cancelled."""
        result = supabase.table("jobs")\
            .select("status")\
            .eq("id", self.job_id)\
            .limit(1)\
            .execute()
        
        return result.data and result.data[0].get("status") == "cancelled"


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: int = 5):
        self.calls_per_second = calls_per_second
        self.last_call_time = 0
        self.calls_this_second = 0
    
    def wait(self):
        """Wait if needed to respect rate limit."""
        current_time = time.time()
        
        if current_time - self.last_call_time >= 1:
            self.last_call_time = current_time
            self.calls_this_second = 1
        else:
            self.calls_this_second += 1
            if self.calls_this_second > self.calls_per_second:
                sleep_time = 1 - (current_time - self.last_call_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.last_call_time = time.time()
                self.calls_this_second = 1

