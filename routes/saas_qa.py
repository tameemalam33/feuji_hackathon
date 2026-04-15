"""
SaaS-aware QA pipeline endpoints
Integrates the core QA pipeline with SaaS features
"""

from flask import Blueprint, request, jsonify, g
import logging
import threading
from uuid import UUID
from typing import Optional

from services.saas_qa_integration import SaasQaIntegration, create_saas_run_wrapper
from services.saas_service import ProjectService, TaskService
from services.qa_pipeline import run_qa_pipeline
from services.report_payload import build_report_payload
from utils.auth import require_auth, require_api_key
from models.database import Database

logger = logging.getLogger(__name__)

saas_qa_bp = Blueprint("saas_qa", __name__, url_prefix="/api")

_db = Database()


@saas_qa_bp.route("/projects/<project_id>/run-test", methods=["POST"])
@require_auth()
def run_project_test(project_id: str):
    """
    Run QA test for a project in the SaaS system
    
    Request body (same as core QA pipeline):
    {
        "url": "https://example.com",
        "mode": "standard",
        "page_limit": 30,
        "max_depth": 2,
        "task_id": "task-uuid" (optional)
    }
    """
    try:
        project_id = UUID(project_id)
        data = request.get_json() or {}

        # Verify project access
        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        # Extract test parameters
        url = data.get("url") or project.base_url
        mode = data.get("mode", "standard")
        page_limit = data.get("page_limit")
        max_depth = data.get("max_depth")
        task_id_str = data.get("task_id")

        # Validate task if provided
        task_id = None
        if task_id_str:
            try:
                task_id = UUID(task_id_str)
                # Verify task belongs to this project
                task_service = TaskService(_db.conn)
                task = task_service.get_project_tasks(project_id, limit=1, offset=0)
                task_exists = any(t.id == task_id for t in task)
                if not task_exists:
                    return jsonify({"error": "Task not found in this project"}), 404
            except ValueError:
                return jsonify({"error": "Invalid task_id"}), 400

        # Prepare run data with SaaS context
        run_data = {
            "url": url,
            "mode": mode,
            "saas_project_id": str(project_id),
            "saas_task_id": str(task_id) if task_id else None,
            "saas_user_id": g.user_id
        }

        if page_limit:
            run_data["page_limit"] = page_limit
        if max_depth:
            run_data["max_depth"] = max_depth

        # Run test asynchronously in background
        def background_test():
            try:
                # Run the core QA pipeline
                run_result = run_qa_pipeline(
                    url=url,
                    mode=mode,
                    page_limit=page_limit,
                    max_depth=max_depth
                )

                if run_result:
                    # Enhance result with SaaS context
                    saas_result = create_saas_run_wrapper(
                        run_result,
                        project_id=str(project_id),
                        task_id=str(task_id) if task_id else None,
                        user_id=g.user_id
                    )

                    # Create SaaS report
                    integration = SaasQaIntegration(_db.conn)
                    report_id = integration.create_report_from_run(
                        project_id=project_id,
                        run_data=saas_result,
                        task_id=task_id,
                        sqlite_run_id=run_result.get('sqlite_run_id')
                    )

                    # Create bugs from failures
                    if run_result.get('failures'):
                        bug_ids = integration.create_bugs_from_failures(
                            project_id=project_id,
                            run_data=saas_result,
                            task_id=task_id,
                            reported_by=UUID(g.user_id)
                        )
                        logger.info(f"Created {len(bug_ids)} bugs from test failures")

                    logger.info(f"SaaS test completed for project {project_id}, report {report_id}")

            except Exception as e:
                logger.error(f"Error in background test: {e}")

        # Start background thread
        thread = threading.Thread(target=background_test, daemon=True)
        thread.start()

        return jsonify({
            "message": "Test started",
            "project_id": str(project_id),
            "task_id": str(task_id) if task_id else None,
            "status": "running"
        }), 202

    except ValueError as e:
        if "invalid literal for int" in str(e).lower():
            return jsonify({"error": "Invalid project ID"}), 400
        raise
    except Exception as e:
        logger.error(f"Error starting test: {e}")
        return jsonify({"error": "Internal server error"}), 500


@saas_qa_bp.route("/projects/<project_id>/test-status", methods=["GET"])
@require_auth()
def get_project_test_status(project_id: str):
    """
    Get aggregated test statistics for a project
    
    This endpoint returns overall statistics without detailed test results
    """
    try:
        project_id = UUID(project_id)

        # Verify project access
        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        # Get stats
        integration = SaasQaIntegration(_db.conn)
        stats = integration.get_project_run_stats(project_id)

        return jsonify({
            "project_id": str(project_id),
            "stats": stats
        }), 200

    except ValueError:
        return jsonify({"error": "Invalid project ID"}), 400
    except Exception as e:
        logger.error(f"Error getting test status: {e}")
        return jsonify({"error": "Internal server error"}), 500
