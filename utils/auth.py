"""
Authentication utilities for AutoQA Pro SaaS
Handles password hashing, session management, and user authentication
"""

import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, jsonify, session, g
import logging

logger = logging.getLogger(__name__)


class PasswordHasher:
    """Utility class for secure password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to check
            password_hash: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False


class SessionManager:
    """Manages user sessions"""

    @staticmethod
    def create_session(user_id: str, user_role: str, user_email: str) -> Dict[str, Any]:
        """
        Create a new session for a user.
        
        Args:
            user_id: User ID
            user_role: User role
            user_email: User email
            
        Returns:
            Session data dictionary
        """
        session_token = secrets.token_urlsafe(32)
        
        return {
            'user_id': user_id,
            'user_role': user_role,
            'user_email': user_email,
            'session_token': session_token,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    @staticmethod
    def invalidate_session():
        """Invalidate the current session"""
        session.clear()


class TokenGenerator:
    """Generates secure tokens for API authentication"""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_reset_token(user_id: str) -> str:
        """Generate a password reset token"""
        token_data = f"{user_id}:{secrets.token_hex(16)}"
        return hashlib.sha256(token_data.encode()).hexdigest()


def require_auth(allowed_roles: Optional[list] = None):
    """
    Decorator to require authentication for Flask routes.
    
    Args:
        allowed_roles: List of allowed user roles. If None, any authenticated user is allowed.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for session
            user_id = session.get('user_id')
            user_role = session.get('user_role')
            
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Check role if specified
            if allowed_roles and user_role not in allowed_roles:
                return jsonify({'error': 'Forbidden'}), 403
            
            # Add user info to Flask g object for use in route
            g.user_id = user_id
            g.user_role = user_role
            g.user_email = session.get('user_email')
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_api_key(f):
    """
    Decorator to require API key authentication.
    Expects API key in header: Authorization: Bearer <api_key>
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # In a real implementation, verify this API key against the database
        # For now, we'll just ensure it's not empty
        if not api_key:
            return jsonify({'error': 'Unauthorized'}), 401
        
        g.api_key = api_key
        return f(*args, **kwargs)
    
    return decorated_function
