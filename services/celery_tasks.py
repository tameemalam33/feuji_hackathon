"""
Celery tasks for long-running QA operations.
Executes test runs asynchronously and tracks progress.
"""

import time
import logging
from typing import Dict, Any, Optional
from uuid import UUID
import psycopg2

from celery_app import celery_app
from models.database import Database
from services.qa_pipeline import QAPipeline
from services.job_status import JobStatus

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.run_qa_tests",
    track_started=True,
    acks_late=True
)
def run_qa_tests(
    self,
    project_id: str,
    user_id: str,
    task_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Run QA tests for a project in the background.

    Args:
        project_id: Project UUID
        user_id: User UUID
        task_id: Optional task UUID
        metadata: Additional context

    Returns:
        Test results dictionary
    """
    job_id = self.request.id
    db = None
    job_service = None

    try:
        # Initialize database and job tracking
        db = Database()
        job_service = JobStatus(db.conn)

        # Create job record
        job_service.create_job(
            job_id=job_id,
            job_type="run_qa",
            user_id=UUID(user_id),
            project_id=UUID(project_id),
            task_id=UUID(task_id) if task_id else None,
            metadata=metadata
        )

        # Update status: started
        job_service.update_job_status(job_id, "started", progress=5)

        # Run the QA pipeline
        qa_pipeline = QAPipeline()

        # Track progress callback
        def progress_callback(step: str, progress: float, message: str):
            job_service.update_job_status(
                job_id,
                "progress",
                progress=progress,
                progress_message=message
            )
            logger.info(f"Job {job_id}: {message} ({progress}%)")

        # Run tests
        results = qa_pipeline.run(
            project_id=project_id,
            task_id=task_id,
            on_progress=progress_callback
        )

        # Store results
        job_service.set_job_result(
            job_id,
            result=results,
            duration_seconds=time.time() - self.request.start_time
        )

        logger.info(f"Job {job_id} completed successfully")
        return results

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)

        if job_service:
            job_service.set_job_error(
                job_id,
                error_message=str(e),
                error_traceback=logging.traceback.format_exc()
            )

        raise

    finally:
        if db and db.conn:
            db.conn.close()


@celery_app.task(
    bind=True,
    name="tasks.run_task_tests",
    track_started=True,
    acks_late=True
)
def run_task_tests(
    self,
    task_id: str,
    project_id: str,
    user_id: str,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Run tests for a specific task in the background.

    Args:
        task_id: Task UUID
        project_id: Project UUID
        user_id: User UUID
        metadata: Additional context

    Returns:
        Test results dictionary
    """
    job_id = self.request.id
    db = None
    job_service = None

    try:
        # Initialize database and job tracking
        db = Database()
        job_service = JobStatus(db.conn)

        # Create job record
        job_service.create_job(
            job_id=job_id,
            job_type="run_task_tests",
            user_id=UUID(user_id),
            project_id=UUID(project_id),
            task_id=UUID(task_id),
            metadata=metadata
        )

        # Update status: started
        job_service.update_job_status(job_id, "started", progress=5)

        # Run the QA pipeline for specific task
        qa_pipeline = QAPipeline()

        def progress_callback(step: str, progress: float, message: str):
            job_service.update_job_status(
                job_id,
                "progress",
                progress=progress,
                progress_message=message
            )
            logger.info(f"Job {job_id}: {message} ({progress}%)")

        # Run task tests
        results = qa_pipeline.run_task(
            task_id=task_id,
            on_progress=progress_callback
        )

        # Store results
        job_service.set_job_result(
            job_id,
            result=results,
            duration_seconds=time.time() - self.request.start_time
        )

        logger.info(f"Job {job_id} completed successfully")
        return results

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)

        if job_service:
            job_service.set_job_error(
                job_id,
                error_message=str(e),
                error_traceback=logging.traceback.format_exc()
            )

        raise

    finally:
        if db and db.conn:
            db.conn.close()


@celery_app.task(
    bind=True,
    name="tasks.generate_report",
    track_started=True,
    acks_late=True
)
def generate_report(
    self,
    project_id: str,
    user_id: str,
    filters: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive QA report in the background.

    Args:
        project_id: Project UUID
        user_id: User UUID
        filters: Report filters

    Returns:
        Report data dictionary
    """
    job_id = self.request.id
    db = None
    job_service = None

    try:
        db = Database()
        job_service = JobStatus(db.conn)

        job_service.create_job(
            job_id=job_id,
            job_type="generate_report",
            user_id=UUID(user_id),
            project_id=UUID(project_id),
            metadata={"filters": filters}
        )

        job_service.update_job_status(job_id, "started", progress=10)

        # Generate report (placeholder)
        job_service.update_job_status(job_id, "progress", progress=50, progress_message="Aggregating data")

        report_data = {
            "project_id": project_id,
            "generated_at": time.time(),
            "total_tests": 150,
            "passed": 145,
            "failed": 5,
            "success_rate": 96.7
        }

        job_service.set_job_result(job_id, result=report_data)

        logger.info(f"Job {job_id} completed successfully")
        return report_data

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)

        if job_service:
            job_service.set_job_error(job_id, error_message=str(e))

        raise

    finally:
        if db and db.conn:
            db.conn.close()


@celery_app.task(
    name="tasks.cleanup_old_jobs",
    expires=3600  # Task expires after 1 hour
)
def cleanup_old_jobs():
    """Periodic task to cleanup old job records."""
    try:
        db = Database()
        cursor = db.conn.cursor()

        # Delete jobs older than 7 days with terminal status
        cursor.execute("""
            DELETE FROM public.job_queue
            WHERE status IN ('completed', 'failed', 'cancelled')
            AND updated_at < NOW() - INTERVAL '7 days';
        """)

        deleted_count = cursor.rowcount
        db.conn.commit()
        cursor.close()
        db.conn.close()

        logger.info(f"Cleaned up {deleted_count} old job records")
        return {"deleted": deleted_count}

    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        return {"error": str(e)}
