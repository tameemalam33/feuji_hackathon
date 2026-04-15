"""
Error analysis API endpoints.
Provides REST interface to Groq-powered error analysis.
"""

import logging
from flask import Blueprint, jsonify, request
from utils.error_analyzer import analyze_error

logger = logging.getLogger(__name__)
error_analysis_bp = Blueprint("error_analysis", __name__, url_prefix="/api/errors")


@error_analysis_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyze an error message using Groq AI.
    
    Request body:
    {
        "message": "Error message or traceback to analyze"
    }
    
    Response:
    {
        "explanation": "What went wrong",
        "cause": "Root cause",
        "fix": "How to fix it"
    }
    """
    data = request.get_json() or {}
    error_message = data.get("message", "").strip()
    
    if not error_message:
        return jsonify({
            "error": "Missing 'message' field",
            "explanation": "",
            "cause": "No error message provided",
            "fix": "Include error message in request"
        }), 400
    
    try:
        result = analyze_error(error_message)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error analysis endpoint error: {e}")
        return jsonify({
            "error": "Analysis failed",
            "explanation": "Error analysis service encountered an error",
            "cause": str(e),
            "fix": "Check server logs"
        }), 500


@error_analysis_bp.route("/batch", methods=["POST"])
def analyze_batch():
    """
    Analyze multiple errors in batch.
    
    Request body:
    {
        "errors": [
            "Error message 1",
            "Error message 2"
        ]
    }
    
    Response:
    {
        "results": [
            {
                "message": "Error message 1",
                "explanation": "...",
                "cause": "...",
                "fix": "..."
            }
        ]
    }
    """
    data = request.get_json() or {}
    errors = data.get("errors", [])
    
    if not errors or not isinstance(errors, list):
        return jsonify({
            "error": "Invalid request",
            "details": "'errors' must be a non-empty list"
        }), 400
    
    results = []
    for error_msg in errors:
        if isinstance(error_msg, str) and error_msg.strip():
            analysis = analyze_error(error_msg)
            results.append({
                "message": error_msg[:100],
                **analysis
            })
    
    if not results:
        return jsonify({
            "error": "No valid errors provided",
            "details": "At least one non-empty error message required"
        }), 400
    
    return jsonify({"results": results}), 200


@error_analysis_bp.route("/health", methods=["GET"])
def health_check():
    """Check if error analysis service is available."""
    try:
        from services.groq_ai_service import GroqAIService
        service = GroqAIService()
        return jsonify({
            "status": "ok",
            "service": "Groq AI",
            "model": service.model
        }), 200
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "GROQ_API_KEY not configured"
        }), 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 503
