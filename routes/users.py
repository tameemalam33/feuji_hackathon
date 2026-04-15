"""
User management routes for AutoQA Pro SaaS
Admin-only routes for managing users, roles, and permissions
"""

from flask import Blueprint, request, jsonify, g
from typing import Optional
import logging
from uuid import UUID

from models.saas_models import UserRole
from services.saas_service import UserService
from utils.auth import require_auth
from models.database import Database

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

_db = Database()


@users_bp.route("", methods=["GET"])
@require_auth(allowed_roles=["admin"])
def list_users():
    """
    List all users (admin only)
    Query parameters:
    - limit: number of users to return (default 100)
    - offset: offset for pagination (default 0)
    """
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))

        user_service = UserService(_db.conn)
        users = user_service.list_users(limit=limit, offset=offset)

        return jsonify({
            "users": [user.to_dict() for user in users],
            "count": len(users),
            "limit": limit,
            "offset": offset
        }), 200

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({"error": "Internal server error"}), 500


@users_bp.route("/<user_id>", methods=["GET"])
@require_auth()
def get_user(user_id: str):
    """
    Get user by ID
    Only admins can view other users, users can only view themselves
    """
    try:
        user_id = UUID(user_id)

        # Check authorization
        if user_id != UUID(g.user_id) and g.user_role != "admin":
            return jsonify({"error": "Forbidden"}), 403

        user_service = UserService(_db.conn)
        user = user_service.get_user_by_id(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "user": user.to_dict()
        }), 200

    except ValueError:
        return jsonify({"error": "Invalid user ID"}), 400
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@users_bp.route("/<user_id>/role", methods=["PUT"])
@require_auth(allowed_roles=["admin"])
def update_user_role(user_id: str):
    """
    Update user role (admin only)
    
    Request body:
    {
        "role": "tester" | "developer" | "admin"
    }
    """
    try:
        user_id = UUID(user_id)
        data = request.get_json() or {}
        new_role = data.get("role", "").lower()

        # Validate role
        try:
            role = UserRole(new_role)
        except ValueError:
            return jsonify({"error": f"Invalid role. Must be one of: admin, tester, developer"}), 400

        user_service = UserService(_db.conn)

        # Check user exists
        user = user_service.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Update role
        updated_user = user_service.update_user(user_id, role=role)

        if not updated_user:
            return jsonify({"error": "Failed to update user role"}), 500

        return jsonify({
            "message": "User role updated successfully",
            "user": updated_user.to_dict()
        }), 200

    except ValueError as e:
        if "invalid literal for int" in str(e).lower():
            return jsonify({"error": "Invalid user ID"}), 400
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return jsonify({"error": "Internal server error"}), 500


@users_bp.route("/<user_id>/status", methods=["PUT"])
@require_auth(allowed_roles=["admin"])
def update_user_status(user_id: str):
    """
    Enable or disable user account (admin only)
    
    Request body:
    {
        "is_active": true | false
    }
    """
    try:
        user_id = UUID(user_id)
        data = request.get_json() or {}
        is_active = data.get("is_active", True)

        user_service = UserService(_db.conn)

        # Check user exists
        user = user_service.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Update status
        updated_user = user_service.update_user(user_id, is_active=is_active)

        if not updated_user:
            return jsonify({"error": "Failed to update user status"}), 500

        return jsonify({
            "message": f"User {'activated' if is_active else 'deactivated'} successfully",
            "user": updated_user.to_dict()
        }), 200

    except ValueError:
        return jsonify({"error": "Invalid user ID"}), 400
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        return jsonify({"error": "Internal server error"}), 500
