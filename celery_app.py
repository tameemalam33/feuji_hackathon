"""
Celery application configuration for background job processing.
Connects to Redis (Upstash) for job queueing and result tracking.
"""

from celery import Celery
from config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_ACCEPT_CONTENT,
    CELERY_TASK_SERIALIZER,
    CELERY_RESULT_SERIALIZER,
    CELERY_TIMEZONE,
    CELERY_TASK_TRACK_STARTED,
    CELERY_TASK_TIME_LIMIT,
    CELERY_TASK_SOFT_TIME_LIMIT,
    CELERY_RESULT_EXPIRES,
)

# Create Celery app
celery_app = Celery(__name__)

# Configure Celery
celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    accept_content=CELERY_ACCEPT_CONTENT,
    task_serializer=CELERY_TASK_SERIALIZER,
    result_serializer=CELERY_RESULT_SERIALIZER,
    timezone=CELERY_TIMEZONE,
    task_track_started=CELERY_TASK_TRACK_STARTED,
    task_time_limit=CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=CELERY_TASK_SOFT_TIME_LIMIT,
    result_expires=CELERY_RESULT_EXPIRES,
)

# Auto-discover tasks from services
celery_app.autodiscover_tasks(['services'])

@celery_app.task(bind=True)
def debug_task(self):
    """Simple test task for debugging."""
    print(f'Request: {self.request!r}')
