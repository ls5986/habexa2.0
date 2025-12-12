"""
Celery task for enterprise file processing.
Handles 50k+ products in background.
"""
import logging
import asyncio
from celery import shared_task
from typing import Dict, Any, Optional

from app.services.streaming_file_processor import StreamingFileProcessor

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_large_file(
    self,
    job_id: str,
    user_id: str,
    file_path: str,
    column_mapping: Dict[str, str],
    supplier_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process uploaded file using enterprise streaming processor.
    
    This task runs in Celery background worker.
    
    Args:
        job_id: Upload job ID for progress tracking
        user_id: User who uploaded the file
        file_path: Path to uploaded file
        column_mapping: Column mapping configuration
        supplier_id: Optional supplier ID
        
    Returns:
        Processing statistics
    """
    try:
        logger.warning(f"🚀 Celery task started: {job_id}")
        
        # Create processor
        processor = StreamingFileProcessor(
            user_id=user_id,
            job_id=job_id
        )
        
        # Run async processing in Celery worker
        # Create new event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            processor.process_file(
                file_path=file_path,
                column_mapping=column_mapping,
                supplier_id=supplier_id
            )
        )
        
        logger.warning(f"✅ Celery task complete: {results}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Celery task failed: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        
        # Retry up to 3 times with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

