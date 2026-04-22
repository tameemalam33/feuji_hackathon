"""
Job monitoring and management endpoints.
Provides dashboards and administrative tools for job queue management.
"""

from flask import Blueprint, jsonify, g, request
from datetime import datetime, timedelta
import logging

from services.job_status import JobStatus
from models.database import Database
from utils.auth import require_auth

logger = logging.getLogger(__name__)

job_monitoring_bp = Blueprint("job_monitoring", __name__, url_prefix="/api/monitoring")

_db = Database()


@job_monitoring_bp.route("/jobs/stats", methods=["GET"])
@require_auth()
def get_job_stats():
    """
    Get job queue statistics for the current user/admin.
    
    Admin can see all stats, regular users see only their own.
    
    Response:
    {
        "total_jobs": 150,
        "queued": 5,
        "running": 3,
        "completed": 140,
        "failed": 2,
        "average_duration": 245.5,
        "success_rate": 98.6
    }
    """
    try:
        job_service = JobStatus(_db.conn)
        
        # Get stats from database
        cursor = _db.conn.cursor()
        
        if g.user_role == "admin":
            # Admin sees all jobs
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'queued' THEN 1 END) as queued,
                    COUNT(CASE WHEN status IN ('started', 'progress') THEN 1 END) as running,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration
                FROM public.job_queue;
            """)
        else:
            # Regular users see only their own
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'queued' THEN 1 END) as queued,
                    COUNT(CASE WHEN status IN ('started', 'progress') THEN 1 END) as running,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration
                FROM public.job_queue
                WHERE user_id = %s;
            """, (g.user_id,))
        
        result = cursor.fetchone()
        cursor.close()
        
        total = result[0] or 0
        completed = result[3] or 0
        success_rate = (completed / total * 100) if total > 0 else 0
        
        return jsonify({
            "total_jobs": total,
            "queued": result[1] or 0,
            "running": result[2] or 0,
            "completed": completed,
            "failed": result[4] or 0,
            "average_duration": result[5] or 0,
            "success_rate": round(success_rate, 1)
        }), 200

    except Exception as e:
        logger.error(f"Failed to get job stats: {str(e)}")
        return jsonify({"error": "Failed to get statistics"}), 500


@job_monitoring_bp.route("/jobs/recent", methods=["GET"])
@require_auth()
def get_recent_jobs():
    """
    Get recently completed or failed jobs.
    
    Query parameters:
    - hours: Look back N hours (default 24)
    - limit: Max results (default 20)
    
    Response:
    [
        {
            "job_id": "...",
            "job_type": "run_qa|run_task_tests",
            "status": "completed|failed",
            "duration": 245.5,
            "completed_at": "ISO timestamp",
            "error": "Error message if failed"
        }
    ]
    """
    try:
        hours = int(request.args.get("hours", 24))
        limit = min(int(request.args.get("limit", 20)), 100)
        
        cursor = _db.conn.cursor()
        
        if g.user_role == "admin":
            cursor.execute("""
                SELECT 
                    job_id, job_type, status, duration_seconds, completed_at, error_message
                FROM public.job_queue
                WHERE status IN ('completed', 'failed')
                AND completed_at >= NOW() - INTERVAL '%s hours'
                ORDER BY completed_at DESC
                LIMIT %s;
            """ % (hours, limit))
        else:
            cursor.execute("""
                SELECT 
                    job_id, job_type, status, duration_seconds, completed_at, error_message
                FROM public.job_queue
                WHERE status IN ('completed', 'failed')
                AND user_id = %s
                AND completed_at >= NOW() - INTERVAL '%s hours'
                ORDER BY completed_at DESC
                LIMIT %s;
            """ % (hours, limit), (g.user_id,))
        
        results = cursor.fetchall()
        cursor.close()
        
        jobs = []
        for row in results:
            jobs.append({
                "job_id": row[0],
                "job_type": row[1],
                "status": row[2],
                "duration": row[3],
                "completed_at": row[4].isoformat() if row[4] else None,
                "error": row[5]
            })
        
        return jsonify(jobs), 200

    except Exception as e:
        logger.error(f"Failed to get recent jobs: {str(e)}")
        return jsonify({"error": "Failed to get recent jobs"}), 500


@job_monitoring_bp.route("/jobs/queue-health", methods=["GET"])
@require_auth()
def get_queue_health():
    """
    Get health status of the job queue.
    
    Response:
    {
        "healthy": true,
        "queue_length": 5,
        "oldest_queued_job": "ISO timestamp",
        "processing_rate": 2.5,
        "celery_workers": 2,
        "last_check": "ISO timestamp"
    }
    """
    try:
        cursor = _db.conn.cursor()
        
        # Get queue stats
        cursor.execute("""
            SELECT 
                COUNT(*) as queue_length,
                MIN(created_at) as oldest_job
            FROM public.job_queue
            WHERE status IN ('queued', 'started', 'progress');
        """)
        
        queue_result = cursor.fetchone()
        queue_length = queue_result[0] or 0
        oldest_job = queue_result[1]
        
        # Get processing rate (jobs completed in last hour)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.job_queue
            WHERE status = 'completed'
            AND completed_at >= NOW() - INTERVAL '1 hour';
        """)
        
        processing_rate = cursor.fetchone()[0] or 0
        cursor.close()
        
        # Determine health status
        healthy = queue_length < 50 and processing_rate > 0
        
        return jsonify({
            "healthy": healthy,
            "queue_length": queue_length,
            "oldest_queued_job": oldest_job.isoformat() if oldest_job else None,
            "processing_rate": round(processing_rate / 60, 2),  # Jobs per minute
            "last_check": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Failed to get queue health: {str(e)}")
        return jsonify({"error": "Failed to get queue health"}), 500


@job_monitoring_bp.route("/jobs/cleanup", methods=["POST"])
@require_auth()
def cleanup_old_jobs():
    """
    Admin only: Cleanup old completed jobs.
    
    Request body:
    {
        "days": 7 (cleanup jobs older than N days)
    }
    
    Response:
    {
        "deleted": 42,
        "message": "Cleaned up 42 old job records"
    }
    """
    if g.user_role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    
    try:
        data = request.get_json() or {}
        days = int(data.get("days", 7))
        
        cursor = _db.conn.cursor()
        
        cursor.execute("""
            DELETE FROM public.job_queue
            WHERE status IN ('completed', 'failed', 'cancelled')
            AND updated_at < NOW() - INTERVAL '%s days';
        """ % days)
        
        deleted_count = cursor.rowcount
        _db.conn.commit()
        cursor.close()
        
        return jsonify({
            "deleted": deleted_count,
            "message": f"Cleaned up {deleted_count} old job records"
        }), 200

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        _db.conn.rollback()
        return jsonify({"error": "Cleanup failed"}), 500
