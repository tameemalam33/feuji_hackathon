"""
API routes for AI-powered error analysis using Groq.
"""

import logging
from flask import Blueprint, request, jsonify, session
from psycopg2.extras import RealDictCursor
from services.groq_ai_service import GroqAIService
from models.database import Database
from utils.auth import require_login

logger = logging.getLogger(__name__)
ai_analysis_bp = Blueprint("ai_analysis", __name__, url_prefix="/api/ai")

# Initialize AI service
try:
    ai_service = GroqAIService()
except ValueError as e:
    logger.warning(f"Groq AI service not initialized: {e}")
    ai_service = None


def check_ai_service():
    """Check if AI service is available."""
    if not ai_service:
        return None, {"error": "AI service not configured"}, 503


@ai_analysis_bp.route("/explain-error", methods=["POST"])
@require_login
def explain_error():
    """Explain an error using Groq AI."""
    service_check = check_ai_service()
    if service_check[0] is None:
        return jsonify(service_check[1]), service_check[2]

    data = request.get_json()
    if not data or "error_message" not in data:
        return jsonify({"error": "error_message is required"}), 400

    try:
        result = ai_service.explain_error(
            error_message=data.get("error_message"),
            error_type=data.get("error_type"),
            context=data.get("context")
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error explaining error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@ai_analysis_bp.route("/bugs/<bug_id>/analyze", methods=["POST"])
@require_login
def analyze_bug(bug_id):
    """Generate AI explanation for a bug and store it."""
    service_check = check_ai_service()
    if service_check[0] is None:
        return jsonify(service_check[1]), service_check[2]

    try:
        db = Database()
        with db.connection.cursor(cursor_factory=RealDictCursor) as cur:
            # Get bug details
            cur.execute(
                """
                SELECT id, title, description, error_message, error_type
                FROM saas_bugs
                WHERE id = %s
                """,
                (bug_id,)
            )
            bug = cur.fetchone()

            if not bug:
                return jsonify({"error": "Bug not found"}), 404

            # Generate AI explanation
            error_context = f"Bug: {bug['title']}"
            if bug['description']:
                error_context += f"\nDescription: {bug['description']}"

            result = ai_service.explain_error(
                error_message=bug['error_message'] or "",
                error_type=bug['error_type'],
                context=error_context
            )

            # Store AI explanation in database
            cur.execute(
                """
                UPDATE saas_bugs
                SET explanation = %s,
                    cause = %s,
                    suggested_fix = %s,
                    raw_response = %s,
                    model = %s,
                    generated_at = NOW()
                WHERE id = %s
                RETURNING id, explanation, cause, suggested_fix, generated_at, model
                """,
                (
                    result.get("explanation"),
                    result.get("cause"),
                    result.get("suggested_fix"),
                    result.get("raw_response"),
                    result.get("model"),
                    bug_id
                )
            )
            db.connection.commit()
            updated_bug = cur.fetchone()

            return jsonify({
                "bug_id": bug_id,
                "explanation": updated_bug['explanation'],
                "cause": updated_bug['cause'],
                "suggested_fix": updated_bug['suggested_fix'],
                "model": updated_bug['model'],
                "generated_at": updated_bug['generated_at'].isoformat() if updated_bug['generated_at'] else None
            }), 200

    except Exception as e:
        logger.error(f"Error analyzing bug: {str(e)}")
        return jsonify({"error": str(e)}), 500


@ai_analysis_bp.route("/bugs/<bug_id>/explanation", methods=["GET"])
@require_login
def get_bug_explanation(bug_id):
    """Retrieve AI explanation for a bug."""
    try:
        db = Database()
        with db.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, title, explanation, cause, suggested_fix, model, generated_at
                FROM saas_bugs
                WHERE id = %s
                """,
                (bug_id,)
            )
            bug = cur.fetchone()

            if not bug:
                return jsonify({"error": "Bug not found"}), 404

            return jsonify({
                "bug_id": bug['id'],
                "title": bug['title'],
                "explanation": bug['explanation'],
                "cause": bug['cause'],
                "suggested_fix": bug['suggested_fix'],
                "model": bug['model'],
                "generated_at": bug['generated_at'].isoformat() if bug['generated_at'] else None
            }), 200

    except Exception as e:
        logger.error(f"Error retrieving explanation: {str(e)}")
        return jsonify({"error": str(e)}), 500


@ai_analysis_bp.route("/analyze-test-failure", methods=["POST"])
@require_login
def analyze_test_failure():
    """Analyze a test failure using AI."""
    service_check = check_ai_service()
    if service_check[0] is None:
        return jsonify(service_check[1]), service_check[2]

    data = request.get_json()
    if not data or "test_name" not in data or "failure_reason" not in data:
        return jsonify({"error": "test_name and failure_reason are required"}), 400

    try:
        result = ai_service.analyze_test_failure(
            test_name=data.get("test_name"),
            failure_reason=data.get("failure_reason"),
            stack_trace=data.get("stack_trace")
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error analyzing test failure: {str(e)}")
        return jsonify({"error": str(e)}), 500


@ai_analysis_bp.route("/analyze-performance", methods=["POST"])
@require_login
def analyze_performance():
    """Analyze a performance issue using AI."""
    service_check = check_ai_service()
    if service_check[0] is None:
        return jsonify(service_check[1]), service_check[2]

    data = request.get_json()
    required = ["metric", "current_value", "expected_value"]
    if not data or not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {', '.join(required)}"}), 400

    try:
        result = ai_service.analyze_performance_issue(
            metric=data.get("metric"),
            current_value=data.get("current_value"),
            expected_value=data.get("expected_value"),
            details=data.get("details")
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error analyzing performance: {str(e)}")
        return jsonify({"error": str(e)}), 500


@ai_analysis_bp.route("/batch-explain", methods=["POST"])
@require_login
def batch_explain():
    """Explain multiple errors in batch."""
    service_check = check_ai_service()
    if service_check[0] is None:
        return jsonify(service_check[1]), service_check[2]

    data = request.get_json()
    if not data or "errors" not in data:
        return jsonify({"error": "errors array is required"}), 400

    try:
        results = ai_service.batch_explain_errors(data.get("errors", []))
        return jsonify({"results": results}), 200
    except Exception as e:
        logger.error(f"Error batch explaining: {str(e)}")
        return jsonify({"error": str(e)}), 500


@ai_analysis_bp.route("/status", methods=["GET"])
def check_status():
    """Check if AI service is available."""
    return jsonify({
        "available": ai_service is not None,
        "model": ai_service.model if ai_service else None
    }), 200
