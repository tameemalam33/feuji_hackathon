"""
Job Status Service for tracking Celery background jobs.
Manages job lifecycle, progress updates, and result storage in database.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class JobStatus:
    """Service for managing background job status and progress."""

    def __init__(self, db_conn):
        """Initialize with database connection."""
        self.conn = db_conn

    def create_job(
        self,
        job_id: str,
        job_type: str,
        user_id: UUID,
        project_id: UUID,
        task_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new job record.

        Args:
            job_id: Celery task ID
            job_type: Type of job (e.g., 'run_qa', 'run_task_tests')
            user_id: User initiating the job
            project_id: Associated project
            task_id: Optional associated task
            metadata: Additional job metadata

        Returns:
            Job record as dict
        """
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)

            query = """
                INSERT INTO public.job_queue 
                (job_id, job_type, user_id, project_id, task_id, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, job_id, job_type, status, created_at;
            """

            cursor.execute(
                query,
                (
                    job_id,
                    job_type,
                    str(user_id),
                    str(project_id),
                    str(task_id) if task_id else None,
                    "queued",
                    json.dumps(metadata or {})
                )
            )

            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to create job: {str(e)}")
            self.conn.rollback()
            raise

    def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[float] = None,
        progress_message: Optional[str] = None
    ) -> bool:
        """
        Update job status and progress.

        Args:
            job_id: Celery task ID
            status: New status (queued, started, progress, completed, failed, cancelled)
            progress: Progress percentage (0-100)
            progress_message: Human-readable progress message

        Returns:
            Success status
        """
        try:
            cursor = self.conn.cursor()

            query = """
                UPDATE public.job_queue
                SET 
                    status = %s,
                    progress = %s,
                    progress_message = %s,
                    updated_at = NOW()
                WHERE job_id = %s;
            """

            cursor.execute(query, (status, progress, progress_message, job_id))
            self.conn.commit()
            cursor.close()

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to update job status: {str(e)}")
            self.conn.rollback()
            return False

    def set_job_result(
        self,
        job_id: str,
        result: Dict[str, Any],
        duration_seconds: Optional[float] = None
    ) -> bool:
        """
        Set job result and mark as completed.

        Args:
            job_id: Celery task ID
            result: Job result data
            duration_seconds: Execution duration

        Returns:
            Success status
        """
        try:
            cursor = self.conn.cursor()

            query = """
                UPDATE public.job_queue
                SET 
                    status = 'completed',
                    result = %s,
                    duration_seconds = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE job_id = %s;
            """

            cursor.execute(query, (json.dumps(result), duration_seconds, job_id))
            self.conn.commit()
            cursor.close()

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to set job result: {str(e)}")
            self.conn.rollback()
            return False

    def set_job_error(
        self,
        job_id: str,
        error_message: str,
        error_traceback: Optional[str] = None
    ) -> bool:
        """
        Mark job as failed with error details.

        Args:
            job_id: Celery task ID
            error_message: Error message
            error_traceback: Full error traceback

        Returns:
            Success status
        """
        try:
            cursor = self.conn.cursor()

            query = """
                UPDATE public.job_queue
                SET 
                    status = 'failed',
                    error_message = %s,
                    error_traceback = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE job_id = %s;
            """

            cursor.execute(query, (error_message, error_traceback, job_id))
            self.conn.commit()
            cursor.close()

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to set job error: {str(e)}")
            self.conn.rollback()
            return False

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details by ID."""
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM public.job_queue WHERE job_id = %s;",
                (job_id,)
            )
            result = cursor.fetchone()
            cursor.close()

            if result:
                # Parse JSON fields
                if result.get("result"):
                    result["result"] = json.loads(result["result"])
                if result.get("metadata"):
                    result["metadata"] = json.loads(result["metadata"])

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get job: {str(e)}")
            return None

    def list_jobs(
        self,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List jobs with optional filters.

        Args:
            user_id: Filter by user
            project_id: Filter by project
            status: Filter by status
            limit: Max results

        Returns:
            List of job records
        """
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)

            query = "SELECT * FROM public.job_queue WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = %s"
                params.append(str(user_id))

            if project_id:
                query += " AND project_id = %s"
                params.append(str(project_id))

            if status:
                query += " AND status = %s"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT %s;"
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Failed to list jobs: {str(e)}")
            return []

    def cancel_job(self, job_id: str) -> bool:
        """Mark job as cancelled."""
        return self.update_job_status(job_id, "cancelled", progress_message="Cancelled by user")
