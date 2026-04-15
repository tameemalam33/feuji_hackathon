"""
SaaS Service Layer
Handles database operations for users, projects, tasks, reports, and bugs
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import json

from models.saas_models import (
    SaasUser, SaasProject, SaasProjectMember, SaasQaTask, SaasBug,
    SaasReport, SaasReportFile,
    UserRole, ProjectMemberRole, TaskStatus, TaskPriority, 
    BugSeverity, BugStatus, ReportFileType
)
from utils.auth import PasswordHasher

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations"""

    def __init__(self, db_connection):
        self.db = db_connection

    def create_user(self, email: str, password: str, full_name: Optional[str] = None,
                   username: Optional[str] = None, role: UserRole = UserRole.TESTER) -> Optional[SaasUser]:
        """Create a new user"""
        try:
            user_id = uuid4()
            password_hash = PasswordHasher.hash_password(password)
            now = datetime.utcnow()

            query = """
                INSERT INTO public.saas_users 
                (id, email, username, full_name, password_hash, role, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """

            cursor = self.db.cursor()
            cursor.execute(query, (
                user_id, email, username, full_name, password_hash,
                role.value, True, now, now
            ))
            self.db.commit()
            row = cursor.fetchone()
            cursor.close()

            if row:
                return self._row_to_user(row)
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            self.db.rollback()
            return None

    def get_user_by_id(self, user_id: UUID) -> Optional[SaasUser]:
        """Get user by ID"""
        try:
            query = "SELECT * FROM public.saas_users WHERE id = %s"
            cursor = self.db.cursor()
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_user(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[SaasUser]:
        """Get user by email"""
        try:
            query = "SELECT * FROM public.saas_users WHERE email = %s"
            cursor = self.db.cursor()
            cursor.execute(query, (email,))
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_user(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def authenticate_user(self, email: str, password: str) -> Optional[SaasUser]:
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email)
        if not user:
            return None

        if not user.password_hash or not PasswordHasher.verify_password(password, user.password_hash):
            return None

        return user

    def update_user(self, user_id: UUID, **kwargs) -> Optional[SaasUser]:
        """Update user fields"""
        try:
            allowed_fields = ['username', 'full_name', 'email', 'role', 'is_active']
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not updates:
                return self.get_user_by_id(user_id)

            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            updates['updated_at'] = datetime.utcnow()
            set_clause += ", updated_at = %s"

            query = f"UPDATE public.saas_users SET {set_clause} WHERE id = %s RETURNING *"
            values = list(updates.values()) + [user_id]

            cursor = self.db.cursor()
            cursor.execute(query, values)
            self.db.commit()
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_user(row) if row else None
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            self.db.rollback()
            return None

    def list_users(self, limit: int = 100, offset: int = 0) -> List[SaasUser]:
        """List all users"""
        try:
            query = "SELECT * FROM public.saas_users ORDER BY created_at DESC LIMIT %s OFFSET %s"
            cursor = self.db.cursor()
            cursor.execute(query, (limit, offset))
            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_user(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    @staticmethod
    def _row_to_user(row) -> Optional[SaasUser]:
        """Convert database row to SaasUser object"""
        if not row:
            return None
        return SaasUser(
            id=row[0],
            email=row[2],
            username=row[3],
            full_name=row[4],
            password_hash=row[5],
            role=UserRole(row[6]),
            is_active=row[7],
            created_at=row[8],
            updated_at=row[9]
        )


class ProjectService:
    """Service for project management operations"""

    def __init__(self, db_connection):
        self.db = db_connection

    def create_project(self, name: str, base_url: str, owner_id: UUID,
                      description: Optional[str] = None, is_public: bool = False) -> Optional[SaasProject]:
        """Create a new project"""
        try:
            project_id = uuid4()
            now = datetime.utcnow()

            query = """
                INSERT INTO public.saas_projects
                (id, name, description, base_url, owner_id, is_public, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """

            cursor = self.db.cursor()
            cursor.execute(query, (
                project_id, name, description, base_url, owner_id, is_public, now, now
            ))
            self.db.commit()
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_project(row) if row else None
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            self.db.rollback()
            return None

    def get_project_by_id(self, project_id: UUID) -> Optional[SaasProject]:
        """Get project by ID"""
        try:
            query = "SELECT * FROM public.saas_projects WHERE id = %s"
            cursor = self.db.cursor()
            cursor.execute(query, (project_id,))
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_project(row) if row else None
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return None

    def list_user_projects(self, user_id: UUID, limit: int = 100, offset: int = 0) -> List[SaasProject]:
        """List all projects owned by a user"""
        try:
            query = """
                SELECT * FROM public.saas_projects 
                WHERE owner_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor = self.db.cursor()
            cursor.execute(query, (user_id, limit, offset))
            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_project(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing user projects: {e}")
            return []

    @staticmethod
    def _row_to_project(row) -> Optional[SaasProject]:
        """Convert database row to SaasProject object"""
        if not row:
            return None
        return SaasProject(
            id=row[0],
            name=row[1],
            description=row[2],
            base_url=row[3],
            owner_id=row[4],
            is_public=row[5],
            created_at=row[6],
            updated_at=row[7]
        )


class TaskService:
    """Service for QA task management"""

    def __init__(self, db_connection):
        self.db = db_connection

    def create_task(self, project_id: UUID, title: str, created_by: UUID,
                   description: Optional[str] = None, assigned_to: Optional[UUID] = None,
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   due_date: Optional[datetime] = None) -> Optional[SaasQaTask]:
        """Create a new QA task"""
        try:
            task_id = uuid4()
            now = datetime.utcnow()

            query = """
                INSERT INTO public.saas_qa_tasks
                (id, project_id, title, description, created_by, assigned_to, status, priority, due_date, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """

            cursor = self.db.cursor()
            cursor.execute(query, (
                task_id, project_id, title, description, created_by, assigned_to,
                TaskStatus.PENDING.value, priority.value, due_date, now, now
            ))
            self.db.commit()
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_task(row) if row else None
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            self.db.rollback()
            return None

    def get_project_tasks(self, project_id: UUID, limit: int = 100, offset: int = 0) -> List[SaasQaTask]:
        """Get all tasks for a project"""
        try:
            query = """
                SELECT * FROM public.saas_qa_tasks
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor = self.db.cursor()
            cursor.execute(query, (project_id, limit, offset))
            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_task(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting project tasks: {e}")
            return []

    @staticmethod
    def _row_to_task(row) -> Optional[SaasQaTask]:
        """Convert database row to SaasQaTask object"""
        if not row:
            return None
        return SaasQaTask(
            id=row[0],
            project_id=row[1],
            title=row[2],
            description=row[3],
            created_by=row[4],
            assigned_to=row[5],
            status=TaskStatus(row[6]),
            priority=TaskPriority(row[7]),
            due_date=row[8],
            created_at=row[9],
            updated_at=row[10]
        )


class BugService:
    """Service for bug report management"""

    def __init__(self, db_connection):
        self.db = db_connection

    def create_bug(self, project_id: UUID, title: str,
                  severity: BugSeverity = BugSeverity.MEDIUM,
                  description: Optional[str] = None,
                  reported_by: Optional[UUID] = None,
                  task_id: Optional[UUID] = None,
                  page_url: Optional[str] = None,
                  error_message: Optional[str] = None,
                  steps_to_reproduce: Optional[str] = None) -> Optional[SaasBug]:
        """Create a new bug report"""
        try:
            bug_id = uuid4()
            now = datetime.utcnow()

            query = """
                INSERT INTO public.saas_bugs
                (id, task_id, project_id, title, description, severity, status, reported_by, 
                 page_url, error_message, steps_to_reproduce, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """

            cursor = self.db.cursor()
            cursor.execute(query, (
                bug_id, task_id, project_id, title, description, severity.value,
                BugStatus.OPEN.value, reported_by, page_url, error_message,
                steps_to_reproduce, now, now
            ))
            self.db.commit()
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_bug(row) if row else None
        except Exception as e:
            logger.error(f"Error creating bug: {e}")
            self.db.rollback()
            return None

    def get_project_bugs(self, project_id: UUID, limit: int = 100, offset: int = 0) -> List[SaasBug]:
        """Get all bugs for a project"""
        try:
            query = """
                SELECT * FROM public.saas_bugs
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor = self.db.cursor()
            cursor.execute(query, (project_id, limit, offset))
            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_bug(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting project bugs: {e}")
            return []

    @staticmethod
    def _row_to_bug(row) -> Optional[SaasBug]:
        """Convert database row to SaasBug object"""
        if not row:
            return None
        return SaasBug(
            id=row[0],
            task_id=row[1],
            project_id=row[2],
            title=row[3],
            description=row[4],
            severity=BugSeverity(row[5]),
            status=BugStatus(row[6]),
            reported_by=row[7],
            assigned_to=row[8],
            screenshot_url=row[9],
            page_url=row[10],
            error_message=row[11],
            steps_to_reproduce=row[12],
            created_at=row[13],
            updated_at=row[14]
        )


class ReportService:
    """Service for test report management"""

    def __init__(self, db_connection):
        self.db = db_connection

    def create_report(self, project_id: UUID, title: str,
                     task_id: Optional[UUID] = None,
                     sqlite_run_id: Optional[int] = None,
                     sqlite_batch_id: Optional[str] = None,
                     report_json: Optional[dict] = None,
                     total_tests: Optional[int] = None,
                     passed_tests: Optional[int] = None,
                     failed_tests: Optional[int] = None,
                     success_rate: Optional[float] = None,
                     test_duration_ms: Optional[int] = None) -> Optional[SaasReport]:
        """Create a new test report"""
        try:
            report_id = uuid4()
            now = datetime.utcnow()

            query = """
                INSERT INTO public.saas_reports
                (id, project_id, task_id, title, sqlite_run_id, sqlite_batch_id, report_json,
                 total_tests, passed_tests, failed_tests, success_rate, test_duration_ms,
                 generated_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """

            report_json_str = json.dumps(report_json) if report_json else None

            cursor = self.db.cursor()
            cursor.execute(query, (
                report_id, project_id, task_id, title, sqlite_run_id, sqlite_batch_id,
                report_json_str, total_tests, passed_tests, failed_tests, success_rate,
                test_duration_ms, now, now
            ))
            self.db.commit()
            row = cursor.fetchone()
            cursor.close()

            return self._row_to_report(row) if row else None
        except Exception as e:
            logger.error(f"Error creating report: {e}")
            self.db.rollback()
            return None

    def get_project_reports(self, project_id: UUID, limit: int = 100, offset: int = 0) -> List[SaasReport]:
        """Get all reports for a project"""
        try:
            query = """
                SELECT * FROM public.saas_reports
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor = self.db.cursor()
            cursor.execute(query, (project_id, limit, offset))
            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_report(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting project reports: {e}")
            return []

    @staticmethod
    def _row_to_report(row) -> Optional[SaasReport]:
        """Convert database row to SaasReport object"""
        if not row:
            return None
        return SaasReport(
            id=row[0],
            project_id=row[1],
            task_id=row[2],
            title=row[3],
            sqlite_run_id=row[4],
            sqlite_batch_id=row[5],
            report_json=json.loads(row[6]) if row[6] else None,
            total_tests=row[7],
            passed_tests=row[8],
            failed_tests=row[9],
            success_rate=row[10],
            test_duration_ms=row[11],
            generated_at=row[12],
            created_at=row[13]
        )
