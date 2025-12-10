"""
Job scheduler for background tasks.

Runs ASIN lookups, analysis, and other background jobs.
Uses Celery Beat for periodic tasks (configured in celery_app.py).
This module provides helper functions to trigger jobs manually.
"""
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    """
    Start background job system.
    
    Note: Periodic tasks are handled by Celery Beat (configured in celery_app.py).
    This function is kept for compatibility but doesn't start APScheduler.
    """
    logger.info("✅ Background job system initialized")
    logger.info("   - ASIN lookup job: every 5 minutes (via Celery Beat)")
    logger.info("   - Telegram monitoring: every 60 seconds (via Celery Beat)")
    logger.info("   - Use Celery workers for all background processing")

def stop_scheduler():
    """Stop the scheduler."""
    # Celery Beat is managed separately, nothing to stop here
    logger.info("Background job system stopped")

