"""
Bug tracking and report management routes for AutoQA Pro SaaS
Handles bug reports, reports, and analysis
"""

from flask import Blueprint, request, jsonify, g
from typing import Optional
import logging
from uuid import UUID
import json

from models.saas_models import BugSeverity, BugStatus
from services.saas_service import BugService, ReportService, ProjectService
from utils.auth import require_auth
from models.database import Database

logger = logging.getLogger(__name__)

bugs_bp = Blueprint("bugs", __name__, url_prefix="/api/projects")

_db = Database()


@bugs_bp.route("/<project_id>/bugs", methods=["POST"])
@require_auth()
def create_bug(project_id: str):
    """
    Create a bug report
    
    Request body:
    {
        "title": "Login button not working",
        "description": "Button doesn't respond to clicks",
        "severity": "high",
        "page_url": "https://example.com/login",
        "error_message": "Error in console",
        "steps_to_reproduce": "1. Go to login page\n2. Click button",
        "task_id": "task-uuid"
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

        # Validate required fields
        title = data.get("title", "").strip()
        if not title:
            return jsonify({"error": "Title is required"}), 400

        description = data.get("description", "").strip()
        severity_str = data.get("severity", "medium").lower()
        page_url = data.get("page_url", "").strip()
        error_message = data.get("error_message", "").strip()
        steps = data.get("steps_to_reproduce", "").strip()
        task_id_str = data.get("task_id")

        # Validate severity
        try:
            severity = BugSeverity(severity_str)
        except ValueError:
            return jsonify({"error": f"Invalid severity. Must be one of: low, medium, high, critical"}), 400

        # Parse task_id if provided
        task_id = None
        if task_id_str:
            try:
                task_id = UUID(task_id_str)
            except ValueError:
                return jsonify({"error": "Invalid task_id"}), 400

        # Create bug
        bug_service = BugService(_db.conn)
        bug = bug_service.create_bug(
            project_id=project_id,
            title=title,
            severity=severity,
            description=description or None,
            reported_by=UUID(g.user_id),
            task_id=task_id,
            page_url=page_url or None,
            error_message=error_message or None,
            steps_to_reproduce=steps or None
        )

        if not bug:
            return jsonify({"error": "Failed to create bug"}), 500

        # Optionally generate AI explanation if requested and error message is available
        ai_explanation = None
        if data.get("generate_explanation") and error_message:
            try:
                from services.groq_ai_service import GroqAIService
                ai_service = GroqAIService()
                ai_explanation = ai_service.explain_error(
                    error_message=error_message,
                    error_type=data.get("error_type"),
                    context=f"Bug: {title}\nDescription: {description}"
                )
            except Exception as e:
                logger.warning(f"Failed to generate AI explanation: {e}")

        response_data = {
            "message": "Bug reported successfully",
            "bug": bug.to_dict()
        }
        if ai_explanation:
            response_data["ai_explanation"] = ai_explanation

        return jsonify(response_data), 201

    except ValueError as e:
        if "invalid literal for int" in str(e).lower():
            return jsonify({"error": "Invalid project ID"}), 400
        raise
    except Exception as e:
        logger.error(f"Error creating bug: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bugs_bp.route("/<project_id>/bugs", methods=["GET"])
@require_auth()
def list_project_bugs(project_id: str):
    """
    List bugs for a project
    
    Query parameters:
    - limit: number of bugs to return (default 100)
    - offset: offset for pagination (default 0)
    - severity: filter by severity (low, medium, high, critical)
    - status: filter by status (open, in_progress, resolved, won_t_fix)
    """
    try:
        project_id = UUID(project_id)
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))

        # Verify project access
        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        # Get bugs with optional filtering
        bug_service = BugService(_db.conn)
        bugs = bug_service.get_project_bugs(
            project_id=project_id,
            limit=limit,
            offset=offset
        )

        # Apply client-side filtering if needed
        severity_filter = request.args.get("severity", "").lower()
        status_filter = request.args.get("status", "").lower()

        filtered_bugs = bugs
        if severity_filter:
            filtered_bugs = [b for b in filtered_bugs if b.severity.value == severity_filter]
        if status_filter:
            filtered_bugs = [b for b in filtered_bugs if b.status.value == status_filter]

        return jsonify({
            "bugs": [bug.to_dict() for bug in filtered_bugs],
            "count": len(filtered_bugs),
            "total_count": len(bugs),
            "limit": limit,
            "offset": offset
        }), 200

    except ValueError:
        return jsonify({"error": "Invalid project ID"}), 400
    except Exception as e:
        logger.error(f"Error listing bugs: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bugs_bp.route("/<project_id>/reports", methods=["POST"])
@require_auth()
def create_report(project_id: str):
    """
    Create a test report
    
    Request body:
    {
        "title": "Homepage test report",
        "task_id": "task-uuid",
        "total_tests": 25,
        "passed_tests": 23,
        "failed_tests": 2,
        "success_rate": 92.0,
        "test_duration_ms": 5000,
        "report_json": { ... },
        "sqlite_run_id": 123
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

        # Validate required fields
        title = data.get("title", "").strip()
        if not title:
            return jsonify({"error": "Title is required"}), 400

        # Parse optional fields
        task_id_str = data.get("task_id")
        task_id = None
        if task_id_str:
            try:
                task_id = UUID(task_id_str)
            except ValueError:
                return jsonify({"error": "Invalid task_id"}), 400

        total_tests = data.get("total_tests")
        passed_tests = data.get("passed_tests")
        failed_tests = data.get("failed_tests")
        success_rate = data.get("success_rate")
        test_duration_ms = data.get("test_duration_ms")
        report_json = data.get("report_json")
        sqlite_run_id = data.get("sqlite_run_id")
        sqlite_batch_id = data.get("sqlite_batch_id")

        # Create report
        report_service = ReportService(_db.conn)
        report = report_service.create_report(
            project_id=project_id,
            title=title,
            task_id=task_id,
            sqlite_run_id=sqlite_run_id,
            sqlite_batch_id=sqlite_batch_id,
            report_json=report_json,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            test_duration_ms=test_duration_ms
        )

        if not report:
            return jsonify({"error": "Failed to create report"}), 500

        return jsonify({
            "message": "Report created successfully",
            "report": report.to_dict()
        }), 201

    except ValueError as e:
        if "invalid literal for int" in str(e).lower():
            return jsonify({"error": "Invalid project ID"}), 400
        raise
    except Exception as e:
        logger.error(f"Error creating report: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bugs_bp.route("/<project_id>/reports", methods=["GET"])
@require_auth()
def list_project_reports(project_id: str):
    """
    List reports for a project
    
    Query parameters:
    - limit: number of reports to return (default 100)
    - offset: offset for pagination (default 0)
    """
    try:
        project_id = UUID(project_id)
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))

        # Verify project access
        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        # Get reports
        report_service = ReportService(_db.conn)
        reports = report_service.get_project_reports(
            project_id=project_id,
            limit=limit,
            offset=offset
        )

        return jsonify({
            "reports": [report.to_dict() for report in reports],
            "count": len(reports),
            "limit": limit,
            "offset": offset
        }), 200

    except ValueError:
        return jsonify({"error": "Invalid project ID"}), 400
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        return jsonify({"error": "Internal server error"}), 500
