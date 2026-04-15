"""
Authentication routes for AutoQA Pro SaaS
Handles user registration, login, logout, and profile management
"""

from flask import Blueprint, request, jsonify, session, g
from typing import Optional, Dict, Any
import logging
from uuid import UUID

from models.saas_models import UserRole
from services.saas_service import UserService
from utils.auth import require_auth, SessionManager, PasswordHasher
from models.database import Database

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_db = Database()


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user
    
    Request body:
    {
        "email": "user@example.com",
        "password": "password",
        "full_name": "John Doe",
        "username": "johndoe"
    }
    """
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        full_name = data.get("full_name", "").strip()
        username = data.get("username", "").strip()

        # Validate required fields
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400

        # Create user service
        user_service = UserService(_db.conn)

        # Check if email already exists
        existing_user = user_service.get_user_by_email(email)
        if existing_user:
            return jsonify({"error": "Email already registered"}), 409

        # Create new user with tester role by default
        user = user_service.create_user(
            email=email,
            password=password,
            full_name=full_name or None,
            username=username or None,
            role=UserRole.TESTER
        )

        if not user:
            return jsonify({"error": "Failed to create user"}), 500

        return jsonify({
            "message": "User registered successfully",
            "user": user.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login user with email and password
    
    Request body:
    {
        "email": "user@example.com",
        "password": "password"
    }
    """
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Authenticate user
        user_service = UserService(_db.conn)
        user = user_service.authenticate_user(email, password)

        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        if not user.is_active:
            return jsonify({"error": "User account is inactive"}), 403

        # Create session
        session_data = SessionManager.create_session(
            user_id=str(user.id),
            user_role=user.role.value,
            user_email=user.email
        )

        # Store in Flask session
        session['user_id'] = str(user.id)
        session['user_role'] = user.role.value
        session['user_email'] = user.email
        session.permanent = True

        return jsonify({
            "message": "Login successful",
            "user": user.to_dict(),
            "session": session_data
        }), 200

    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/logout", methods=["POST"])
@require_auth()
def logout():
    """Logout current user"""
    try:
        SessionManager.invalidate_session()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        logger.error(f"Error logging out: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/me", methods=["GET"])
@require_auth()
def get_current_user():
    """Get current user profile"""
    try:
        user_service = UserService(_db.conn)
        user = user_service.get_user_by_id(UUID(g.user_id))

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "user": user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/profile", methods=["PUT"])
@require_auth()
def update_profile():
    """
    Update user profile
    
    Request body:
    {
        "full_name": "New Name",
        "username": "newusername"
    }
    """
    try:
        data = request.get_json() or {}
        user_id = UUID(g.user_id)

        # Validate update fields
        allowed_updates = {}
        if "full_name" in data:
            allowed_updates["full_name"] = data["full_name"]
        if "username" in data:
            allowed_updates["username"] = data["username"]

        if not allowed_updates:
            return jsonify({"error": "No fields to update"}), 400

        user_service = UserService(_db.conn)
        user = user_service.update_user(user_id, **allowed_updates)

        if not user:
            return jsonify({"error": "Failed to update profile"}), 500

        return jsonify({
            "message": "Profile updated successfully",
            "user": user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/change-password", methods=["POST"])
@require_auth()
def change_password():
    """
    Change user password
    
    Request body:
    {
        "current_password": "oldpass",
        "new_password": "newpass"
    }
    """
    try:
        data = request.get_json() or {}
        user_id = UUID(g.user_id)
        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")

        if not current_password or not new_password:
            return jsonify({"error": "Current and new password are required"}), 400

        if len(new_password) < 8:
            return jsonify({"error": "New password must be at least 8 characters"}), 400

        user_service = UserService(_db.conn)
        user = user_service.get_user_by_id(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Verify current password
        if not PasswordHasher.verify_password(current_password, user.password_hash):
            return jsonify({"error": "Current password is incorrect"}), 401

        # Update password
        new_password_hash = PasswordHasher.hash_password(new_password)
        updated_user = user_service.update_user(user_id, password_hash=new_password_hash)

        if not updated_user:
            return jsonify({"error": "Failed to update password"}), 500

        return jsonify({
            "message": "Password changed successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return jsonify({"error": "Internal server error"}), 500
