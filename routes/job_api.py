"""
Job-based API endpoints for long-running QA operations.
Queues tests asynchronously and tracks progress via Celery.
"""

from flask import Blueprint, request, jsonify, g
from uuid import UUID
from typing import Optional
import logging
import json

from celery_app import celery_app
from services.celery_tasks import run_qa_tests, run_task_tests, generate_report
from services.job_status import JobStatus
from models.database import Database
from utils.auth import require_auth, require_api_key
from utils.helpers import validate_url

logger = logging.getLogger(__name__)

job_api_bp = Blueprint("job_api", __name__, url_prefix="/api/jobs")

_db = Database()


@job_api_bp.route("/run-tests", methods=["POST"])
@require_api_key
def queue_run_tests():
    """
    Queue a QA test run as a background job.
    
    Request body:
    {
        "url": "https://example.com",
        "mode": "standard|quick|deep|full",
        "page_limit": 30,
        "max_depth": 2
    }
    
    Response:
    {
        "job_id": "celery-task-id",
        "status": "queued",
        "message": "Test run queued successfully"
    }
    """
    try:
        data = request.get_json() or {}
        url = data.get("url", "").strip()
        mode = data.get("mode", "standard").lower()
        page_limit = data.get("page_limit")
        max_depth = data.get("max_depth")

        # Validate URL
        ok, msg = validate_url(url)
        if not ok:
            return jsonify({"error": msg}), 400

        # Queue the task
        task = run_qa_tests.delay(
            project_id=None,  # For public API
            user_id=None,
            metadata={
                "url": url,
                "mode": mode,
                "page_limit": page_limit,
                "max_depth": max_depth
            }
        )

        return jsonify({
            "job_id": task.id,
            "status": "queued",
            "message": "Test run queued successfully"
        }), 202

    except Exception as e:
        logger.error(f"Failed to queue test run: {str(e)}")
        return jsonify({"error": "Failed to queue test run"}), 500


@job_api_bp.route("/projects/<project_id>/run-tests", methods=["POST"])
@require_auth()
def queue_project_tests(project_id: str):
    """
    Queue QA tests for a SaaS project.
    
    Request body:
    {
        "url": "https://example.com (optional, uses project default)",
        "mode": "standard|quick|deep|full",
        "task_id": "uuid (optional)"
    }
    
    Response:
    {
        "job_id": "celery-task-id",
        "status": "queued",
        "project_id": "project-uuid"
    }
    """
    try:
        project_id_uuid = UUID(project_id)
        data = request.get_json() or {}

        # Verify project access
        from services.saas_service import ProjectService
        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(project_id_uuid)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Check authorization
        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        # Extract parameters
        url = data.get("url") or project.base_url
        task_id = data.get("task_id")

        # Queue the task
        task = run_qa_tests.delay(
            project_id=str(project_id_uuid),
            user_id=str(g.user_id),
            task_id=task_id,
            metadata={"url": url}
        )

        return jsonify({
            "job_id": task.id,
            "status": "queued",
            "project_id": str(project_id_uuid)
        }), 202

    except ValueError:
        return jsonify({"error": "Invalid project ID"}), 400
    except Exception as e:
        logger.error(f"Failed to queue project tests: {str(e)}")
        return jsonify({"error": "Failed to queue tests"}), 500


@job_api_bp.route("/tasks/<task_id>/run-tests", methods=["POST"])
@require_auth()
def queue_task_tests(task_id: str):
    """
    Queue tests for a specific task.
    
    Response:
    {
        "job_id": "celery-task-id",
        "status": "queued",
        "task_id": "task-uuid"
    }
    """
    try:
        task_id_uuid = UUID(task_id)

        # Verify task and get project
        from services.saas_service import TaskService
        task_service = TaskService(_db.conn)
        task = task_service.get_task_by_id(task_id_uuid)

        if not task:
            return jsonify({"error": "Task not found"}), 404

        # Verify project access
        from services.saas_service import ProjectService
        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(task.project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        # Queue the task
        celery_task = run_task_tests.delay(
            task_id=str(task_id_uuid),
            project_id=str(task.project_id),
            user_id=str(g.user_id)
        )

        return jsonify({
            "job_id": celery_task.id,
            "status": "queued",
            "task_id": str(task_id_uuid)
        }), 202

    except ValueError:
        return jsonify({"error": "Invalid task ID"}), 400
    except Exception as e:
        logger.error(f"Failed to queue task tests: {str(e)}")
        return jsonify({"error": "Failed to queue tests"}), 500


@job_api_bp.route("/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    """
    Get the status and details of a job.
    
    Response:
    {
        "job_id": "celery-task-id",
        "status": "queued|started|progress|completed|failed|cancelled",
        "progress": 45,
        "progress_message": "Running tests on page 15/50",
        "result": {...},
        "error": "Error message if failed",
        "created_at": "ISO timestamp",
        "completed_at": "ISO timestamp"
    }
    """
    try:
        job_service = JobStatus(_db.conn)
        job = job_service.get_job(job_id)

        if not job:
            return jsonify({"error": "Job not found"}), 404

        # Also check Celery task state for real-time status
        celery_state = celery_app.AsyncResult(job_id)

        response = {
            "job_id": job_id,
            "status": job.get("status", "unknown"),
            "progress": job.get("progress"),
            "progress_message": job.get("progress_message"),
            "created_at": job.get("created_at").isoformat() if job.get("created_at") else None,
            "updated_at": job.get("updated_at").isoformat() if job.get("updated_at") else None,
            "completed_at": job.get("completed_at").isoformat() if job.get("completed_at") else None,
        }

        # Include result if completed
        if job.get("result"):
            try:
                response["result"] = json.loads(job["result"]) if isinstance(job["result"], str) else job["result"]
            except:
                response["result"] = job.get("result")

        # Include error if failed
        if job.get("error_message"):
            response["error"] = job["error_message"]

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        return jsonify({"error": "Failed to get job status"}), 500


@job_api_bp.route("", methods=["GET"])
@require_auth()
def list_jobs():
    """
    List jobs for the current user.
    
    Query parameters:
    - project_id: Filter by project
    - status: Filter by status
    - limit: Max results (default 50)
    
    Response:
    [
        {
            "job_id": "...",
            "status": "...",
            "job_type": "run_qa|run_task_tests|generate_report",
            "progress": 50,
            "created_at": "..."
        }
    ]
    """
    try:
        project_id = request.args.get("project_id")
        status = request.args.get("status")
        limit = min(int(request.args.get("limit", 50)), 100)

        job_service = JobStatus(_db.conn)
        jobs = job_service.list_jobs(
            user_id=UUID(g.user_id) if g.user_id else None,
            project_id=UUID(project_id) if project_id else None,
            status=status,
            limit=limit
        )

        return jsonify([{
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "job_type": job.get("job_type"),
            "progress": job.get("progress"),
            "created_at": job.get("created_at").isoformat() if job.get("created_at") else None,
        } for job in jobs]), 200

    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        return jsonify({"error": "Failed to list jobs"}), 500


@job_api_bp.route("/<job_id>", methods=["DELETE"])
def cancel_job(job_id: str):
    """
    Cancel a running job.
    
    Response:
    {
        "job_id": "celery-task-id",
        "status": "cancelled"
    }
    """
    try:
        # Revoke the Celery task
        celery_app.control.revoke(job_id, terminate=True)

        # Update job status in database
        job_service = JobStatus(_db.conn)
        job_service.cancel_job(job_id)

        return jsonify({
            "job_id": job_id,
            "status": "cancelled"
        }), 200

    except Exception as e:
        logger.error(f"Failed to cancel job: {str(e)}")
        return jsonify({"error": "Failed to cancel job"}), 500
