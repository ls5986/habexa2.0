"""
Celery application configuration for Habexa.
Centralized background task processing with queue routing.
"""
from celery import Celery
from celery.schedules import crontab
import os
import re
import logging

logger = logging.getLogger(__name__)

# Get Redis URL from environment (with fallbacks)
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or "redis://localhost:6379/0"

# Log the broker URL on startup (redact password for security)
safe_url = re.sub(r'://[^:]+:[^@]+@', '://***:***@', REDIS_URL)
print(f"🔧 Celery broker URL: {safe_url}")
logger.info(f"Celery broker URL: {safe_url}")

celery_app = Celery(
    "habexa",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.file_processing",
        "app.tasks.analysis",
        "app.tasks.telegram",
        "app.tasks.exports",
        "app.tasks.keepa_analysis",
        "app.tasks.upload_processing",
        "app.tasks.asin_lookup",
        "app.tasks.genius_scoring_tasks",
        "app.tasks.inventory_tasks",
        "app.tasks.supplier_performance_tasks",
    ],
    task_always_eager=False  # Don't execute tasks synchronously
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # Soft limit 55 min
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Queues
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "analysis": {"exchange": "analysis", "routing_key": "analysis"},
        "telegram": {"exchange": "telegram", "routing_key": "telegram"},
    },
    task_default_queue="default",
    
    # Route tasks to queues
    task_routes={
        "app.tasks.analysis.*": {"queue": "analysis"},
        "app.tasks.telegram.*": {"queue": "telegram"},
        "app.tasks.file_processing.*": {"queue": "default"},
        "app.tasks.upload_processing.*": {"queue": "default"},
        "app.tasks.exports.*": {"queue": "default"},
    },
    
    # Rate limiting for SP-API
    task_annotations={
        "app.tasks.analysis.analyze_single_product": {"rate_limit": "5/s"},
        "app.tasks.analysis.batch_analyze_products": {"rate_limit": "1/s"},
    },
    
    # Periodic tasks
    beat_schedule={
        "check-telegram-channels": {
            "task": "app.tasks.telegram.check_all_channels",
            "schedule": 60.0,  # Every 60 seconds
        },
        "process-pending-asins": {
            "task": "app.tasks.asin_lookup.process_pending_asin_lookups",
            "schedule": 300.0,  # Every 5 minutes
            "args": (100,),  # Process 100 products per run
        },
        "process-pending-asin-lookups-new": {
            "task": "app.tasks.asin_lookup.process_pending_asin_lookups",
            "schedule": 1800.0,  # Every 30 minutes (backup to the 5-minute job)
            "args": (100,),
        },
        "refresh-genius-scores-daily": {
            "task": "app.tasks.genius_scoring_tasks.refresh_genius_scores_daily",
            "schedule": crontab(hour=3, minute=0),  # 3 AM every day
            "options": {"queue": "default"}
        },
        "sync-fba-inventory-daily": {
            "task": "app.tasks.inventory_tasks.sync_fba_inventory_daily",
            "schedule": crontab(hour=2, minute=0),  # 2 AM every day
            "options": {"queue": "default"}
        },
    },
)

