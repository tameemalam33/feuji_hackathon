"""
Project management routes for AutoQA Pro SaaS
Handles project creation, management, and task assignment
"""

from flask import Blueprint, request, jsonify, g
from typing import Optional
import logging
from uuid import UUID
from datetime import datetime

from models.saas_models import TaskStatus, TaskPriority
from services.saas_service import ProjectService, TaskService
from utils.auth import require_auth
from models.database import Database

logger = logging.getLogger(__name__)

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")

_db = Database()


@projects_bp.route("", methods=["POST"])
@require_auth()
def create_project():
    """
    Create a new project
    
    Request body:
    {
        "name": "Project Name",
        "base_url": "https://example.com",
        "description": "Project description",
        "is_public": false
    }
    """
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        base_url = data.get("base_url", "").strip()
        description = data.get("description", "").strip()
        is_public = data.get("is_public", False)

        # Validate required fields
        if not name or not base_url:
            return jsonify({"error": "Name and base_url are required"}), 400

        # Basic URL validation
        if not base_url.startswith(("http://", "https://")):
            return jsonify({"error": "base_url must start with http:// or https://"}), 400

        project_service = ProjectService(_db.conn)
        project = project_service.create_project(
            name=name,
            base_url=base_url,
            owner_id=UUID(g.user_id),
            description=description or None,
            is_public=is_public
        )

        if not project:
            return jsonify({"error": "Failed to create project"}), 500

        return jsonify({
            "message": "Project created successfully",
            "project": project.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({"error": "Internal server error"}), 500


@projects_bp.route("", methods=["GET"])
@require_auth()
def list_projects():
    """
    List projects for current user
    
    Query parameters:
    - limit: number of projects to return (default 100)
    - offset: offset for pagination (default 0)
    """
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))

        project_service = ProjectService(_db.conn)
        projects = project_service.list_user_projects(
            user_id=UUID(g.user_id),
            limit=limit,
            offset=offset
        )

        return jsonify({
            "projects": [project.to_dict() for project in projects],
            "count": len(projects),
            "limit": limit,
            "offset": offset
        }), 200

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({"error": "Internal server error"}), 500


@projects_bp.route("/<project_id>", methods=["GET"])
@require_auth()
def get_project(project_id: str):
    """Get project details"""
    try:
        project_id = UUID(project_id)

        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Check authorization (owner or admin)
        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        return jsonify({
            "project": project.to_dict()
        }), 200

    except ValueError:
        return jsonify({"error": "Invalid project ID"}), 400
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        return jsonify({"error": "Internal server error"}), 500


@projects_bp.route("/<project_id>/tasks", methods=["POST"])
@require_auth()
def create_task(project_id: str):
    """
    Create a QA task in a project
    
    Request body:
    {
        "title": "Test homepage",
        "description": "Test homepage functionality",
        "priority": "medium",
        "assigned_to": "user-uuid",
        "due_date": "2025-12-31T23:59:59Z"
    }
    """
    try:
        project_id = UUID(project_id)
        data = request.get_json() or {}

        # Verify project exists and user has access
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
        priority_str = data.get("priority", "medium").lower()
        assigned_to_str = data.get("assigned_to")
        due_date_str = data.get("due_date")

        # Validate priority
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            return jsonify({"error": f"Invalid priority. Must be one of: low, medium, high, critical"}), 400

        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return jsonify({"error": "Invalid due_date format"}), 400

        assigned_to = None
        if assigned_to_str:
            try:
                assigned_to = UUID(assigned_to_str)
            except ValueError:
                return jsonify({"error": "Invalid assigned_to user ID"}), 400

        # Create task
        task_service = TaskService(_db.conn)
        task = task_service.create_task(
            project_id=project_id,
            title=title,
            created_by=UUID(g.user_id),
            description=description or None,
            assigned_to=assigned_to,
            priority=priority,
            due_date=due_date
        )

        if not task:
            return jsonify({"error": "Failed to create task"}), 500

        return jsonify({
            "message": "Task created successfully",
            "task": task.to_dict()
        }), 201

    except ValueError as e:
        if "invalid literal for int" in str(e).lower():
            return jsonify({"error": "Invalid project ID"}), 400
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({"error": "Internal server error"}), 500


@projects_bp.route("/<project_id>/tasks", methods=["GET"])
@require_auth()
def list_project_tasks(project_id: str):
    """
    List tasks for a project
    
    Query parameters:
    - limit: number of tasks to return (default 100)
    - offset: offset for pagination (default 0)
    """
    try:
        project_id = UUID(project_id)
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))

        # Verify project exists and user has access
        project_service = ProjectService(_db.conn)
        project = project_service.get_project_by_id(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if project.owner_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        # Get tasks
        task_service = TaskService(_db.conn)
        tasks = task_service.get_project_tasks(
            project_id=project_id,
            limit=limit,
            offset=offset
        )

        return jsonify({
            "tasks": [task.to_dict() for task in tasks],
            "count": len(tasks),
            "limit": limit,
            "offset": offset
        }), 200

    except ValueError:
        return jsonify({"error": "Invalid project ID"}), 400
    except Exception as e:
        logger.error(f"Error listing project tasks: {e}")
        return jsonify({"error": "Internal server error"}), 500
