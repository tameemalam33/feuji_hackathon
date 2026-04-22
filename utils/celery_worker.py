"""
Celery worker utilities for managing background job processing.
Includes worker startup script and monitoring helpers.
"""

import logging
import os
from celery_app import celery_app
from services.celery_tasks import (
    run_qa_tests,
    run_task_tests,
    generate_report,
    cleanup_old_jobs
)

logger = logging.getLogger(__name__)


def start_worker():
    """Start the Celery worker."""
    app = celery_app
    
    # Configure worker options
    worker = app.Worker(
        queues=['default'],
        loglevel='INFO',
        pool='prefork',  # Use prefork pool for process isolation
        concurrency=int(os.environ.get('CELERY_CONCURRENCY', 2)),
        time_limit=30 * 60,  # Hard limit: 30 minutes
        soft_time_limit=25 * 60,  # Soft limit: 25 minutes
        task_acks_late=True,  # Ack after task completes
        worker_prefetch_multiplier=1,  # Process one task at a time
    )
    
    logger.info("Starting Celery worker...")
    worker.start()


def get_worker_stats():
    """Get current worker statistics."""
    try:
        stats = celery_app.control.inspect().stats()
        active = celery_app.control.inspect().active()
        
        return {
            "workers": list(stats.keys()) if stats else [],
            "worker_count": len(stats) if stats else 0,
            "active_tasks": active if active else {},
            "status": "healthy" if stats else "offline"
        }
    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def get_registered_tasks():
    """Get list of registered Celery tasks."""
    try:
        registered = celery_app.control.inspect().registered()
        if registered:
            # Return unique task names across all workers
            all_tasks = set()
            for tasks in registered.values():
                all_tasks.update(tasks)
            return sorted(list(all_tasks))
        return []
    except Exception as e:
        logger.error(f"Failed to get registered tasks: {e}")
        return []


def purge_queue():
    """Purge all pending tasks from the queue (use with caution)."""
    try:
        celery_app.control.purge()
        logger.warning("Queue purged - all pending tasks removed")
        return {"message": "Queue purged successfully"}
    except Exception as e:
        logger.error(f"Failed to purge queue: {e}")
        return {"error": str(e)}


def graceful_shutdown(timeout=30):
    """Gracefully shutdown workers."""
    try:
        logger.info(f"Initiating graceful shutdown with {timeout}s timeout...")
        celery_app.control.shutdown(timeout=timeout)
        return {"message": f"Shutdown initiated with {timeout}s timeout"}
    except Exception as e:
        logger.error(f"Failed to shutdown gracefully: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    start_worker()
