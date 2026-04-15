"""
SaaS QA Pipeline Integration
Connects the existing QA pipeline with new SaaS features like projects, reports, and bugs
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json

from models.saas_models import BugSeverity
from services.saas_service import ReportService, BugService, ProjectService
from models.database import Database

logger = logging.getLogger(__name__)


class SaasQaIntegration:
    """Integrates QA test runs with SaaS features"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.report_service = ReportService(db_connection)
        self.bug_service = BugService(db_connection)
        self.project_service = ProjectService(db_connection)

    def create_report_from_run(self, project_id: UUID, run_data: Dict[str, Any],
                               task_id: Optional[UUID] = None,
                               sqlite_run_id: Optional[int] = None) -> Optional[UUID]:
        """
        Create a SaaS report from a QA pipeline run
        
        Args:
            project_id: Project UUID
            run_data: Dictionary containing run results from QA pipeline
            task_id: Optional task ID to link the report
            sqlite_run_id: Optional SQLite run ID for backwards compatibility
            
        Returns:
            Report UUID if successful, None otherwise
        """
        try:
            # Extract test results
            total_tests = run_data.get('total_tests', 0)
            passed_tests = run_data.get('passed_tests', 0)
            failed_tests = run_data.get('failed_tests', 0)
            
            # Calculate success rate
            success_rate = None
            if total_tests > 0:
                success_rate = (passed_tests / total_tests) * 100
            
            test_duration_ms = run_data.get('duration_ms', 0)
            
            # Create report
            report = self.report_service.create_report(
                project_id=project_id,
                title=run_data.get('title', f'Test Run - {datetime.utcnow().isoformat()}'),
                task_id=task_id,
                sqlite_run_id=sqlite_run_id,
                sqlite_batch_id=run_data.get('batch_id'),
                report_json=run_data,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                success_rate=success_rate,
                test_duration_ms=test_duration_ms
            )
            
            return report.id if report else None
            
        except Exception as e:
            logger.error(f"Error creating SaaS report from run: {e}")
            return None

    def create_bugs_from_failures(self, project_id: UUID, run_data: Dict[str, Any],
                                  task_id: Optional[UUID] = None,
                                  reported_by: Optional[UUID] = None) -> list:
        """
        Create bug reports from test failures
        
        Args:
            project_id: Project UUID
            run_data: Dictionary containing run results with failures
            task_id: Optional task to link bugs to
            reported_by: User ID who reported the bugs
            
        Returns:
            List of created bug UUIDs
        """
        created_bugs = []
        
        try:
            failures = run_data.get('failures', [])
            
            for failure in failures:
                # Determine severity based on failure type
                failure_type = failure.get('type', 'general').lower()
                if 'critical' in failure_type or 'crash' in failure_type:
                    severity = BugSeverity.CRITICAL
                elif 'error' in failure_type or 'broken' in failure_type:
                    severity = BugSeverity.HIGH
                elif 'warning' in failure_type:
                    severity = BugSeverity.MEDIUM
                else:
                    severity = BugSeverity.LOW
                
                # Create bug
                bug = self.bug_service.create_bug(
                    project_id=project_id,
                    title=failure.get('title', 'Test Failure'),
                    description=failure.get('description'),
                    severity=severity,
                    reported_by=reported_by,
                    task_id=task_id,
                    page_url=failure.get('page_url'),
                    error_message=failure.get('error_message'),
                    steps_to_reproduce=failure.get('steps', failure.get('details'))
                )
                
                if bug:
                    created_bugs.append(bug.id)
                    logger.info(f"Created bug {bug.id} from test failure")
            
            return created_bugs
            
        except Exception as e:
            logger.error(f"Error creating bugs from failures: {e}")
            return created_bugs

    def link_run_to_task(self, task_id: UUID, sqlite_run_id: int) -> bool:
        """
        Link an existing SQLite run to a SaaS task
        
        Args:
            task_id: Task UUID
            sqlite_run_id: SQLite run ID
            
        Returns:
            True if successful
        """
        try:
            # This would be implemented in TaskService
            # For now, just log the link
            logger.info(f"Linked task {task_id} to SQLite run {sqlite_run_id}")
            return True
        except Exception as e:
            logger.error(f"Error linking run to task: {e}")
            return False

    def get_project_run_stats(self, project_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get aggregated statistics for all test runs in a project
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dictionary with aggregated statistics
        """
        try:
            reports = self.report_service.get_project_reports(
                project_id=project_id,
                limit=1000,
                offset=0
            )
            
            if not reports:
                return {
                    'total_runs': 0,
                    'total_tests': 0,
                    'total_passed': 0,
                    'total_failed': 0,
                    'average_success_rate': 0,
                    'total_duration_ms': 0
                }
            
            total_tests = sum(r.total_tests or 0 for r in reports)
            total_passed = sum(r.passed_tests or 0 for r in reports)
            total_failed = sum(r.failed_tests or 0 for r in reports)
            total_duration = sum(r.test_duration_ms or 0 for r in reports)
            
            avg_success_rate = 0
            if total_tests > 0:
                avg_success_rate = (total_passed / total_tests) * 100
            
            return {
                'total_runs': len(reports),
                'total_tests': total_tests,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'average_success_rate': round(avg_success_rate, 2),
                'total_duration_ms': total_duration
            }
            
        except Exception as e:
            logger.error(f"Error getting project stats: {e}")
            return None


def create_saas_run_wrapper(original_run_data: Dict[str, Any], 
                           project_id: Optional[str] = None,
                           task_id: Optional[str] = None,
                           user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Wrapper function to enhance a standard QA run with SaaS context
    
    This allows the existing QA pipeline to work with SaaS features
    without extensive refactoring of the core pipeline code.
    
    Args:
        original_run_data: Original run data from QA pipeline
        project_id: Optional SaaS project UUID
        task_id: Optional SaaS task UUID
        user_id: Optional user UUID who triggered the run
        
    Returns:
        Enhanced run data with SaaS context
    """
    enhanced_data = original_run_data.copy()
    
    if project_id:
        enhanced_data['saas_project_id'] = project_id
    if task_id:
        enhanced_data['saas_task_id'] = task_id
    if user_id:
        enhanced_data['saas_user_id'] = user_id
    
    enhanced_data['created_at'] = datetime.utcnow().isoformat()
    
    return enhanced_data
