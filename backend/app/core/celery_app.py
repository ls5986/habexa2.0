"""
Celery application configuration for Habexa.
Centralized background task processing with queue routing.
"""
from celery import Celery
from celery.schedules import crontab
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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
        "app.tasks.exports.*": {"queue": "default"},
    },
    
    # Rate limiting for SP-API
    task_annotations={
        "app.tasks.analysis.analyze_single_product": {"rate_limit": "5/s"},
        "app.tasks.analysis.batch_analyze_products": {"rate_limit": "1/s"},
    },
    
    # Periodic tasks (Telegram monitoring)
    beat_schedule={
        "check-telegram-channels": {
            "task": "app.tasks.telegram.check_all_channels",
            "schedule": 60.0,  # Every 60 seconds
        },
    },
)

